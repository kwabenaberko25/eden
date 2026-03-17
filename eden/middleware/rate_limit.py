"""
Eden — Rate Limiting Middleware

Protects endpoints from abuse by limiting requests per time period.

**Features:**
- Per-IP rate limiting
- Per-user rate limiting
- Per-endpoint rate limiting
- Custom key functions
- Multiple strategies (fixed window, sliding window)
- Redis-backed for distributed systems

**Setup:**

    from eden.middleware import RateLimitMiddleware
    from eden import Eden
    
    app = Eden(__name__)
    
    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        default_limit="100/minute",  # 100 requests per minute
        storage_url="redis://localhost:6379",  # Or "memory://" for testing
    )

**Usage with Route Decorators:**

    from eden import Router, rate_limit
    from starlette.responses import JSONResponse
    
    router = Router()
    
    @router.get("/api/search")
    @rate_limit("10/minute")  # Max 10 requests per minute per IP
    async def search(request):
        query = request.query_params.get("q")
        return JSONResponse({"results": search_index(query)})
    
    @router.post("/api/login")
    @rate_limit("5/minute", key="user_email")  # Per email address
    async def login(request):
        data = await request.json()
        user = await authenticate(data["email"], data["password"])
        return JSONResponse({"token": user.auth_token})

**Limit Format:**

    "100/minute"      # 100 requests per minute
    "1000/hour"       # 1000 requests per hour
    "10/second"       # 10 requests per second
    "5/day"           # 5 requests per day (UTC)

**Custom Key Functions:**

    @rate_limit("30/minute", key=lambda req: req.user.id if req.user else req.client.host)
    async def protected_endpoint(request):
        return JSONResponse({"data": "success"})
"""

import logging
import time
from typing import Callable, Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class RateLimitStore:
    """Base interface for rate limit storage backends."""
    
    async def get_count(self, key: str) -> int:
        """Get current request count for key."""
        raise NotImplementedError
    
    async def increment(self, key: str, ttl: int) -> int:
        """Increment counter and return new count. Sets expiry to ttl seconds."""
        raise NotImplementedError
    
    async def reset(self, key: str) -> None:
        """Reset counter for key."""
        raise NotImplementedError


class MemoryRateLimitStore(RateLimitStore):
    """In-memory rate limit store (single-process only)."""
    
    def __init__(self):
        self._store: Dict[str, tuple[int, float]] = {}  # key -> (count, expires_at)
    
    async def get_count(self, key: str) -> int:
        """Get current count, check expiration."""
        if key not in self._store:
            return 0
        
        count, expires_at = self._store[key]
        if time.time() > expires_at:
            del self._store[key]
            return 0
        
        return count
    
    async def increment(self, key: str, ttl: int) -> int:
        """Increment and set expiry."""
        current_time = time.time()
        expires_at = current_time + ttl
        
        if key in self._store:
            count, old_expires = self._store[key]
            if current_time > old_expires:
                # Expired, reset
                count = 0
        else:
            count = 0
        
        count += 1
        self._store[key] = (count, expires_at)
        return count
    
    async def reset(self, key: str) -> None:
        """Reset counter."""
        if key in self._store:
            del self._store[key]


class RedisRateLimitStore(RateLimitStore):
    """Redis-backed rate limit store (distributed)."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        try:
            import redis.asyncio as redis
        except ImportError:
            raise ImportError(
                "RedisRateLimitStore requires redis. "
                "Install with: pip install redis"
            )
        
        self.redis = redis.from_url(redis_url)
    
    async def get_count(self, key: str) -> int:
        """Get count from Redis."""
        value = await self.redis.get(f"ratelimit:{key}")
        return int(value) if value else 0
    
    async def increment(self, key: str, ttl: int) -> int:
        """Increment and set expiry in Redis."""
        redis_key = f"ratelimit:{key}"
        count = await self.redis.incr(redis_key)
        await self.redis.expire(redis_key, ttl)
        return count
    
    async def reset(self, key: str) -> None:
        """Reset in Redis."""
        await self.redis.delete(f"ratelimit:{key}")


def parse_rate_limit(limit_str: str) -> tuple[int, int]:
    """
    Parse rate limit string into (count, ttl_seconds).
    
    Args:
        limit_str: Format like "100/minute", "10/second"
    
    Returns:
        Tuple of (max_requests, ttl_seconds)
    
    Raises:
        ValueError: If format is invalid
    """
    try:
        count, period = limit_str.split("/")
        count = int(count)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid rate limit format: {limit_str}. Use '100/minute'")
    
    # Try direct numeric period first (seconds)
    if period.isdigit():
        return count, int(period)
    
    # Convert period to seconds
    period_lookup = {
        "second": 1,
        "seconds": 1,
        "minute": 60,
        "minutes": 60,
        "hour": 3600,
        "hours": 3600,
        "day": 86400,
        "days": 86400,
    }
    
    p_lower = period.lower()
    ttl = period_lookup.get(p_lower)
    
    if ttl is None:
        # Try to extract number from "60seconds"
        import re
        match = re.match(r"(\d+)\s*(.*)", p_lower)
        if match:
            num = int(match.group(1))
            unit = match.group(2)
            if not unit:
                return count, num
            unit_ttl = period_lookup.get(unit)
            if unit_ttl:
                return count, num * unit_ttl

        raise ValueError(f"Unknown period: {period}. Use 'second', 'minute', 'hour', 'day', or a number of seconds")
    
    return count, ttl


def generate_rate_limit_key(
    request_ip: str,
    user_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    custom_key: Optional[str] = None,
) -> str:
    """
    Generate deterministic rate limit key.
    
    Args:
        request_ip: Client IP address
        user_id: Optional user identifier
        endpoint: Optional endpoint path
        custom_key: Optional custom key
    
    Returns:
        Rate limit key (SHA256 hash for consistent length)
    """
    components = [request_ip]
    
    if custom_key:
        components.append(custom_key)
    elif user_id:
        components.append(f"user:{user_id}")
    
    if endpoint:
        components.append(f"endpoint:{endpoint}")
    
    key_str = "|".join(components)
    # Hash for consistent length
    return hashlib.sha256(key_str.encode()).hexdigest()


class RateLimitMiddleware:
    """
    ASGI middleware for rate limiting.
    
    Limits requests per time period, returns 429 (Too Many Requests) when exceeded.
    """
    
    def __init__(
        self,
        app: Any,
        default_limit: str = "100/minute",
        storage_url: str = "memory://",
        key_func: Optional[Callable] = None,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
        exempt_paths: Optional[list[str]] = None,
        redis_url: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            app: ASGI app
            default_limit: Default rate limit (format: "100/minute")
            storage_url: Storage backend ("memory://" or "redis://...")
            key_func: Optional custom key function (request -> str)
            max_requests: Optional max requests to override default_limit
            window_seconds: Optional window size in seconds
            exempt_paths: Optional list of paths to exempt from rate limiting
        """
        if redis_url:
            storage_url = redis_url
        
        self.app = app
        self.default_limit = default_limit
        self.key_func = key_func
        self.exempt_paths = exempt_paths or []
        
        if max_requests is not None and window_seconds is not None:
            self.default_limit = f"{max_requests}/{window_seconds}seconds"
        
        # Initialize storage backend
        if storage_url.startswith("redis"):
            self.store = RedisRateLimitStore(storage_url)
        else:
            self.store = MemoryRateLimitStore()
        
        logger.info(f"Rate limiting enabled: {default_limit}")
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware entry point."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check exempt paths
        path = scope.get("path", "")
        if any(path == p or path.startswith(p + "/") for p in self.exempt_paths):
            await self.app(scope, receive, send)
            return

        # Get endpoint and metadata from scope (populated by Eden Router)
        endpoint = scope.get("endpoint")
        limit_str = getattr(endpoint, "_rate_limit", self.default_limit)
        max_requests, ttl = parse_rate_limit(limit_str)
        
        # Determine the rate limit key (identity)
        key_func = getattr(endpoint, "_rate_limit_key", self.key_func)
        
        if key_func:
            from eden.requests import Request
            req = Request.from_scope(scope, receive, send)
            import inspect
            try:
                res = key_func(req)
                if inspect.isawaitable(res):
                    identity = await res
                else:
                    identity = res
            except Exception as e:
                logger.error(f"Error in rate limit key function: {e}")
                identity = scope.get("client", ("unknown", None))[0]
        else:
            identity = scope.get("client", ("unknown", None))[0]

        # Generate full rate limit key
        path = scope.get("path", "")
        limit_key = generate_rate_limit_key(identity, endpoint=path)
        
        # Increment counter
        count = await self.store.increment(limit_key, ttl)
        
        async def send_with_headers(message):
            """Wrap send to add rate limit headers."""
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-ratelimit-limit", str(max_requests).encode()))
                headers.append((b"x-ratelimit-remaining", str(max(0, max_requests - count)).encode()))
                headers.append((b"x-ratelimit-reset", str(int(time.time()) + ttl).encode()))
                message["headers"] = headers
            
            await send(message)
        
        # Check if limit exceeded
        if count > max_requests:
            # Rate limit exceeded
            logger.warning(f"Rate limit exceeded for {identity}: {count}/{max_requests}")
            
            await send_with_headers({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"retry-after", str(ttl).encode()),
                ],
            })
            
            await send({
                "type": "http.response.body",
                "body": b'{"error": true, "detail": "Too many requests. Please slow down."}',
            })
            return
        
        # Continue to app
        await self.app(scope, receive, send_with_headers)


def rate_limit(limit: str, key: Optional[Callable] = None):
    """
    Decorator for endpoint-specific rate limiting.
    
    Args:
        limit: Rate limit string (e.g., "100/minute")
        key: Optional key function to customize the rate limit key
    
    Returns:
        Decorator function
    """
    def decorator(func):
        # Store limit config in function metadata
        func._rate_limit = limit
        func._rate_limit_key = key
        return func
    
    return decorator
# Aliases for backward compatibility and registry integration
RedisRateLimitMiddleware = RateLimitMiddleware
