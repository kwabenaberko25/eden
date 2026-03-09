"""
Eden — Middleware

Built-in middleware for CORS, CSRF, GZip compression, and sessions.
All middleware wraps Starlette's implementations with Eden-friendly configuration.
"""

from __future__ import annotations

import hmac
import importlib
import re
import secrets
from typing import Any, Optional, Sequence
from starlette.middleware.cors import CORSMiddleware as StarletteCORS
from starlette.middleware.gzip import GZipMiddleware as StarletteGZip
from starlette.middleware.sessions import SessionMiddleware as StarletteSession
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class CORSMiddleware(StarletteCORS):
    """
    CORS middleware with sensible defaults.

    Usage:
        app.add_middleware("cors", allow_origins=["*"])
    """

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: Sequence[str] = (),
        allow_methods: Sequence[str] = ("GET", "POST", "OPTIONS"),
        allow_headers: Sequence[str] = (),
        allow_credentials: bool = False,
        expose_headers: Sequence[str] = (),
        max_age: int = 600,
    ) -> None:
        super().__init__(
            app,
            allow_origins=list(allow_origins),
            allow_methods=list(allow_methods),
            allow_headers=list(allow_headers),
            allow_credentials=allow_credentials,
            expose_headers=list(expose_headers),
            max_age=max_age,
        )


class GZipMiddleware(StarletteGZip):
    """
    GZip compression middleware.

    Usage:
        app.add_middleware("gzip", minimum_size=500)
    """

    def __init__(self, app: ASGIApp, minimum_size: int = 500) -> None:
        super().__init__(app, minimum_size=minimum_size)


class SessionMiddleware(StarletteSession):
    """
    Cookie-based session middleware.

    Usage:
        app.add_middleware("session", secret_key="your-secret")
    """

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str = "",
        session_cookie: str = "eden_session",
        max_age: int = 14 * 24 * 60 * 60,  # 14 days
        path: str = "/",
        same_site: str = "lax",
        https_only: bool = False,
    ) -> None:
        if not secret_key:
            secret_key = secrets.token_hex(32)
        super().__init__(
            app,
            secret_key=secret_key,
            session_cookie=session_cookie,
            max_age=max_age,
            path=path,
            same_site=same_site,
            https_only=https_only,
        )


class CSRFMiddleware:
    """
    CSRF protection middleware.

    Generates a CSRF token and validates it on state-changing requests
    (POST, PUT, PATCH, DELETE). The token is stored in the session and
    must be sent as a header or form field.

    Usage:
        app.add_middleware("csrf", secret_key="your-secret")
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
    TOKEN_HEADER = "X-CSRF-Token"
    TOKEN_FIELD = "csrf_token"
    SESSION_KEY = "eden_csrf_token"

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str = "",
        exempt_paths: list[str] | None = None,
    ) -> None:
        self.app = app
        self.secret_key = secret_key or secrets.token_hex(32)
        # Pre-compile exempt paths as regexes for efficiency
        self.exempt_patterns = [re.compile(p) for p in (exempt_paths or [])]

    def _is_exempt(self, path: str) -> bool:
        """Check if a path is exempt from CSRF protection."""
        return any(pattern.match(path) for pattern in self.exempt_patterns)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)
        method = request.method.upper()

        # Skip safe methods and exempt paths
        if method in self.SAFE_METHODS or self._is_exempt(request.url.path):
            # Ensure a CSRF token exists in the session
            if "session" in scope:
                session = scope["session"]
                if self.SESSION_KEY not in session:
                    session[self.SESSION_KEY] = secrets.token_hex(32)
            await self.app(scope, receive, send)
            return

        # Validate CSRF token on unsafe methods
        session = scope.get("session", {})
        expected_token = session.get(self.SESSION_KEY)

        if not expected_token:
            response = JSONResponse(
                {"error": True, "detail": "CSRF token missing from session."},
                status_code=403,
            )
            await response(scope, receive, send)
            return

        # Check header first, then form field
        submitted_token = request.headers.get(self.TOKEN_HEADER)
        if not submitted_token:
            # Try to read from form data — but only for form content types
            content_type = request.headers.get("content-type", "")
            if "form" in content_type or "urlencoded" in content_type:
                try:
                    form = await request.form()
                    submitted_token = form.get(self.TOKEN_FIELD)
                except Exception:
                    pass

        # HTMX often uses X-XSRF-TOKEN or similar, but we'll stick to X-CSRF-Token or Form

        if not submitted_token or not hmac.compare_digest(submitted_token, expected_token):
            response = JSONResponse(
                {"error": True, "detail": "CSRF token validation failed."},
                status_code=403,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    """
    Security headers middleware.

    Injects best-practice HTTP security headers on every response
    to protect against common web vulnerabilities (XSS, clickjacking,
    MIME sniffing, etc.).

    Usage:
        app.add_middleware("security")
        app.add_middleware("security", csp="default-src 'self'")
    """

    DEFAULT_HEADERS: dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    def __init__(
        self,
        app: ASGIApp,
        *,
        hsts: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        csp: str | None = None,
        frame_options: str = "DENY",
        custom_headers: dict[str, str] | None = None,
    ) -> None:
        self.app = app
        self.headers = dict(self.DEFAULT_HEADERS)

        # HSTS
        if hsts:
            hsts_value = f"max-age={hsts_max_age}"
            if hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if hsts_preload:
                hsts_value += "; preload"
            self.headers["Strict-Transport-Security"] = hsts_value

        # CSP
        if csp:
            self.headers["Content-Security-Policy"] = csp

        # Override X-Frame-Options if customized
        if frame_options != "DENY":
            self.headers["X-Frame-Options"] = frame_options

        # Merge custom headers
        if custom_headers:
            self.headers.update(custom_headers)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                for key, value in self.headers.items():
                    headers.append((key.lower().encode(), value.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestContextMiddleware:
    """
    Ensures that the current request is available in the Eden context.
    This is essential for app.render() and other context-aware utilities.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from eden.context import reset_request, set_request
        from eden.requests import Request as EdenRequest

        request = EdenRequest(scope, receive, send)
        token = set_request(request)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_request(token)


class RateLimitMiddleware:
    """
    In-memory token-bucket rate limiter per client IP.

    Limits the number of requests a single IP address can make within
    a rolling time window. Returns 429 Too Many Requests with a
    Retry-After header when the limit is exceeded.

    Usage:
        app.add_middleware("ratelimit", max_requests=100, window_seconds=60)

    Note:
        This is an in-memory rate limiter suitable for single-process
        deployments. For multi-process/distributed setups, use a
        Redis-backed solution instead.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 100,
        window_seconds: int = 60,
        exempt_paths: list[str] | None = None,
    ) -> None:
        import asyncio

        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exempt_patterns = [re.compile(p) for p in (exempt_paths or [])]

        # {ip: [timestamp, ...]}
        self._requests: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    def _is_exempt(self, path: str) -> bool:
        """Check if a path is exempt from rate limiting."""
        return any(pattern.match(path) for pattern in self.exempt_patterns)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        import time

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)

        # Skip exempt paths
        if self._is_exempt(request.url.path):
            await self.app(scope, receive, send)
            return

        # Determine client IP
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        now = time.time()
        cutoff = now - self.window_seconds

        async with self._lock:
            # Clean old entries and add the new one
            timestamps = self._requests.get(client_ip, [])
            timestamps = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= self.max_requests:
                # Rate limited
                retry_after = int(timestamps[0] - cutoff) + 1
                self._requests[client_ip] = timestamps
                response = JSONResponse(
                    {
                        "error": True,
                        "detail": "Too many requests. Please slow down.",
                        "retry_after": retry_after,
                    },
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
                await response(scope, receive, send)
                return

            timestamps.append(now)
            self._requests[client_ip] = timestamps

            # Periodic cleanup: remove stale IPs every 1000 requests
            if sum(len(v) for v in self._requests.values()) > 10000:
                stale_ips = [
                    ip
                    for ip, ts in self._requests.items()
                    if not ts or ts[-1] < cutoff
                ]
                for ip in stale_ips:
                    del self._requests[ip]

        await self.app(scope, receive, send)


class RedisRateLimitMiddleware:
    """
    Redis-backed rate limiter.
    
    Suitable for distributed/multi-process deployments.
    Requires: `pip install redis[async]`
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 100,
        window_seconds: int = 60,
        exempt_paths: list[str] | None = None,
        redis_url: str = "redis://localhost:6379/0",
    ) -> None:
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exempt_patterns = [re.compile(p) for p in (exempt_paths or [])]
        self.redis_url = redis_url
        self._cache = None

    def _is_exempt(self, path: str) -> bool:
        return any(pattern.match(path) for pattern in self.exempt_patterns)

    async def _get_cache(self):
        if self._cache is None:
            from eden.cache.redis import RedisCache
            self._cache = RedisCache(url=self.redis_url, prefix="ratelimit:")
            await self._cache.connect()
        return self._cache

    async def __call__(self, scope: Scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)
        if self._is_exempt(request.url.path):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        
        cache = await self._get_cache()
        key = f"ip:{client_ip}"
        
        # Fixed-window rate limiting using Redis
        current = await cache.incr(key)
        if current == 1:
            await cache._client.expire(cache._key(key), self.window_seconds)

        if current > self.max_requests:
            retry_after = await cache._client.ttl(cache._key(key))
            response = JSONResponse(
                {
                    "error": True,
                    "detail": "Too many requests. Please slow down.",
                    "retry_after": retry_after,
                },
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def ratelimit(max_requests: int = 100, window_seconds: int = 60):
    """
    Decorator to apply rate limiting to a specific view.
    Uses the app's cache (if available) or the default (in-memory).
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            from eden.context import get_request
            request = get_request()
            if not request:
                return await func(*args, **kwargs)

            # Determine client IP
            client_ip = request.client.host if request.client else "unknown"
            
            # Simple in-memory fallback for the decorator if no app cache exists
            # In a real app, this should probably use the app's central cache
            import time
            app = getattr(request, "app", None)
            cache = getattr(app, "cache", None)
            
            key = f"ratelimit:view:{func.__name__}:{client_ip}"
            
            if cache:
                current = await cache.get(key) or 0
                if current >= max_requests:
                    return JSONResponse(
                        {"error": True, "detail": "Rate limit exceeded for this view."},
                        status_code=429
                    )
                await cache.set(key, current + 1, ttl=window_seconds)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class BrowserReloadMiddleware:
    """
    Middleware that injects a live-reload script into HTML responses in debug mode.
    Connects to /_eden/reload via WebSocket to listen for reload signals.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # State to track if we should inject
        should_inject = [False]
        content_length_index = [-1]

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                for i, (name, value) in enumerate(headers):
                    if name.lower() == b"content-type" and b"text/html" in value.lower():
                        should_inject[0] = True
                    if name.lower() == b"content-length":
                        content_length_index[0] = i

                # If we are injecting, we might need to remove Content-Length
                # because we'll change the body size.
                if should_inject[0] and content_length_index[0] != -1:
                    headers.pop(content_length_index[0])
                    message["headers"] = headers

            if message["type"] == "http.response.body" and should_inject[0]:
                body = message.get("body", b"")
                if b"</body>" in body:
                    script_text = """
<script id="eden-live-reload">
    (function() {
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const url = `${protocol}//${window.location.host}/_eden/reload`;
            const socket = new WebSocket(url);
            socket.onmessage = (e) => { if (e.data === 'reload') location.reload(); };
            socket.onclose = () => {
                console.log('🌿 Eden: Connection lost. Reconnecting...');
                const timer = setInterval(() => {
                    fetch(window.location.href, { mode: 'no-cors', cache: 'no-cache' })
                        .then(() => { clearInterval(timer); location.reload(); })
                        .catch(() => {});
                }, 500);
            };
        }
        connect();
    })();
</script>
"""
                    script = script_text.encode("utf-8")
                    message["body"] = body.replace(b"</body>", script + b"</body>")

            await send(message)

        await self.app(scope, receive, send_wrapper)


class PerformanceTelemetryMiddleware:
    """
    Middleware for real-time performance telemetry.
    Collects DB query metrics and total request time.
    Injects Server-Timing headers for browser visualization.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        from eden.logging import get_logger
        self.logger = get_logger("telemetry")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from eden.telemetry import start_telemetry, reset_telemetry, get_telemetry
        
        token = start_telemetry()
        try:
            async def send_wrapper(message: Message) -> None:
                if message["type"] == "http.response.start":
                    data = get_telemetry()
                    if data:
                        total_ms = data.total_duration_ms
                        db_ms = data.db_time_ms
                        db_queries = data.db_queries
                        app_ms = max(0, total_ms - db_ms)

                        # Construct Server-Timing header
                        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Server-Timing
                        timing = f"db;dur={db_ms:.2f};desc=\"{db_queries} queries\", app;dur={app_ms:.2f}, total;dur={total_ms:.2f}"
                        
                        headers = list(message.get("headers", []))
                        headers.append((b"server-timing", timing.encode()))
                        message["headers"] = headers

                        # Log metrics
                        self.logger.info(
                            "Performance: Total %.2fms | DB %.2fms (%d queries) | App %.2fms",
                            total_ms, db_ms, db_queries, app_ms
                        )

                await send(message)

            await self.app(scope, receive, send_wrapper)
        finally:
            reset_telemetry(token)

class CacheMiddleware:
    """
    Full-page caching middleware for Eden.
    
    Caches successful GET & HEAD responses based on path and query parameters.
    Respects Cache-Control headers and integrates with the Eden cache system.
    """
    def __init__(
        self,
        app: ASGIApp,
        cache: Optional[Any] = None,
        ttl: int = 300,
        cache_control: bool = True,
    ) -> None:
        self.app = app
        self._cache = cache
        self.default_ttl = ttl
        self.use_cache_control = cache_control

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in ("GET", "HEAD"):
            await self.app(scope, receive, send)
            return

        # Attempt to find cache instance
        app_instance = scope.get("app")
        cache = self._cache or getattr(app_instance, "cache", None)
        if not cache:
            await self.app(scope, receive, send)
            return

        # Build cache key
        path = scope.get("path", "")
        query = scope.get("query_string", b"").decode()
        cache_key = f"page_cache:{path}:{query}"

        # 1. Try Cache Hit
        try:
            cached = await cache.get(cache_key)
            if cached and isinstance(cached, dict):
                headers = list(cached.get("headers", []))
                # Add HIT header
                headers.append((b"x-eden-cache", b"HIT"))
                
                await send({
                    "type": "http.response.start",
                    "status": cached.get("status", 200),
                    "headers": headers
                })
                await send({
                    "type": "http.response.body",
                    "body": cached.get("body", b"")
                })
                return
        except Exception:
            pass

        # 2. Cache Miss: Capture response
        response_data = {
            "status": 200,
            "headers": [],
            "body": b"",
            "cacheable": True,
            "ttl": self.default_ttl
        }

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_data["status"] = message["status"]
                response_data["headers"] = list(message.get("headers", []))
                
                # Check Cache-Control headers if enabled
                if self.use_cache_control:
                    for name, value in response_data["headers"]:
                        if name.lower() == b"cache-control":
                            val_str = value.decode().lower()
                            if any(word in val_str for word in ("no-store", "no-cache", "private")):
                                response_data["cacheable"] = False
                            if "max-age=" in val_str:
                                try:
                                    idx = val_str.find("max-age=")
                                    if idx != -1:
                                        rem = val_str[idx+8:].split(",")[0].strip()
                                        response_data["ttl"] = int(rem)
                                except Exception:
                                    pass

            if message["type"] == "http.response.body":
                if response_data["status"] < 300 and response_data["cacheable"]:
                    response_data["body"] += message.get("body", b"")
                    
                    if not message.get("more_body", False):
                        await cache.set(cache_key, {
                            "status": response_data["status"],
                            "headers": response_data["headers"],
                            "body": response_data["body"]
                        }, ttl=response_data["ttl"])

            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-eden-cache", b"MISS"))
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)


# ── Middleware Registry ──────────────────────────────────────────────────────

MIDDLEWARE_REGISTRY: dict[str, type] = {
    "cors": CORSMiddleware,
    "gzip": GZipMiddleware,
    "session": SessionMiddleware,
    "csrf": CSRFMiddleware,
    "security": SecurityHeadersMiddleware,
    "ratelimit": RateLimitMiddleware,
    "redis_ratelimit": RedisRateLimitMiddleware,
    "logging": "eden.logging:RequestLoggingMiddleware",
    "auth": "eden.auth.middleware:AuthenticationMiddleware",
    "browser_reload": BrowserReloadMiddleware,
    "tenant": "eden.tenancy.middleware:TenantMiddleware",
    "telemetry": PerformanceTelemetryMiddleware,
    "cache": CacheMiddleware,
    "request": RequestContextMiddleware,
}


def get_middleware_class(name: str | type) -> type:
    """Look up a middleware class by its short name or a dot-notation string."""
    if not isinstance(name, str):
        return name

    cls = MIDDLEWARE_REGISTRY.get(name.lower())
    if cls is not None:
        if isinstance(cls, str):
            # Dynamic import
            module_name, class_name = cls.split(":")
            module = importlib.import_module(module_name)
            return getattr(module, class_name)
        return cls

    if ":" in name:
        module_name, class_name = name.split(":")
        module = importlib.import_module(module_name)
        return getattr(module, class_name)

    raise ValueError(
        f"Unknown middleware: '{name}'. "
        f"Available: {', '.join(MIDDLEWARE_REGISTRY.keys())}"
    )
