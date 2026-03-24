"""
Eden — API Versioning Support

Manage multiple API versions cleanly (/v1/, /v2/, etc.) with version negotiation
and deprecation warnings.

**Features:**
- URL-based versioning (/v1/, /v2/)
- Header-based versioning (Accept-Version, API-Version)
- Version deprecation warnings
- Automatic version selection
- Request/response transformations per version

**Setup:**

    from eden import Eden, APIVersion, VersionedRouter
    
    app = Eden(__name__)
    
    # Register API versions
    v1 = APIVersion("v1", deprecated=False)
    v2 = APIVersion("v2", default=True)
    
    app.register_api_version(v1)
    app.register_api_version(v2)

**Usage with Routes:**

    from eden import VersionedRouter
    
    # Create versioned router
    router = VersionedRouter()
    
    # V1 endpoint
    @router.get("/users", versions=["v1"])
    async def get_users_v1(request):
        return JSONResponse({"users": [{"id": 1, "name": "Alice"}]})
    
    # V2 endpoint (same path, different response)
    @router.get("/users", versions=["v2"])
    async def get_users_v2(request):
        return JSONResponse({
            "data": [{"id": 1, "name": "Alice", "email": "alice@example.com"}],
            "pagination": {"page": 1, "total": 100}
        })
    
    app.add_router(router)

**Version Negotiation (Priority):**

    1. URL path: /v2/users (highest)
    2. Request header: API-Version: v2
    3. Accept-Version: v2
    4. Default version (lowest)

**Deprecation Handling:**

    v1 = APIVersion("v1", deprecated=True, sunset_date="2025-12-31")
    
    # Returns header: Sunset: Sun, 31 Dec 2025 00:00:00 GMT
    # Returns header: Deprecation: true
    # Returns header: Warning: 299 - "API v1 is deprecated"

**Request Transformation:**

    class UserTransformer:
        async def transform_v1_to_v2(self, user_v1):
            '''Convert v1 user format to v2'''
            return {
                "id": user_v1["id"],
                "name": user_v1["name"],
                "email": user_v1.get("email", ""),
            }
    
    app.set_version_transformer("User", UserTransformer())
"""

import logging
from typing import Optional, List, Callable, Any, Dict
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)


class APIVersion:
    """Represents an API version."""
    
    def __init__(
        self,
        name: str,
        default: bool = False,
        deprecated: bool = False,
        sunset_date: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """
        Initialize API version.
        
        Args:
            name: Version identifier (e.g., "v1", "v2")
            default: Is this the default version?
            deprecated: Is this version deprecated?
            sunset_date: Deprecation sunset date (ISO format: "YYYY-MM-DD")
            description: Human-readable description
        """
        self.name = name
        self.default = default
        self.deprecated = deprecated
        self.sunset_date = sunset_date
        self.description = description or f"API version {name}"
        
        logger.debug(f"API Version registered: {name} (default={default}, deprecated={deprecated})")
    
    def get_deprecation_headers(self) -> Dict[bytes, bytes]:
        """Get HTTP headers for deprecation warning."""
        if not self.deprecated:
            return {}
        
        headers = {
            b"deprecation": b"true",
            b"warning": b'299 - "This API version is deprecated"',
        }
        
        if self.sunset_date:
            headers[b"sunset"] = str(self.sunset_date).encode()
        
        return headers


class VersionedRouter:
    """Router that handles versioned endpoints."""
    
    def __init__(self):
        self.routes: Dict[str, Dict[str, Any]] = {}
    
    def get(self, path: str, versions: Optional[List[str]] = None):
        """Register GET endpoint for specific versions."""
        def decorator(func: Callable) -> Callable:
            route_key = f"GET:{path}"
            versions_list = versions or ["v1"]
            
            if route_key not in self.routes:
                self.routes[route_key] = {}
            
            for version in versions_list:
                self.routes[route_key][version] = func
            
            logger.debug(f"Versioned route registered: {route_key} for versions {versions_list}")
            return func
        
        return decorator
    
    def post(self, path: str, versions: Optional[List[str]] = None):
        """Register POST endpoint for specific versions."""
        def decorator(func: Callable) -> Callable:
            route_key = f"POST:{path}"
            versions_list = versions or ["v1"]
            
            if route_key not in self.routes:
                self.routes[route_key] = {}
            
            for version in versions_list:
                self.routes[route_key][version] = func
            
            return func
        
        return decorator
    
    def get_handler(self, method: str, path: str, version: str) -> Optional[Callable]:
        """Get handler for method/path/version combination."""
        route_key = f"{method}:{path}"
        if route_key in self.routes:
            return self.routes[route_key].get(version)
        return None

    def mount(self, app: Any, prefix: str = ""):
        """
        Mount this versioned router into an Eden app.
        Registers shim handlers that dispatch to the correct version at runtime.
        """
        from eden.responses import JsonResponse
        
        # Group routes by path and method
        for route_key, version_map in self.routes.items():
            method, path = route_key.split(":", 1)
            full_path = f"{prefix.rstrip('/')}/{path.lstrip('/')}"
            
            # Create a localized shim for this specific route
            # We capture version_map in the closure
            async def shim(request: Any, v_map=version_map, m=method, p=full_path):
                version = get_api_version(request.scope)
                
                handler = v_map.get(version)
                if not handler:
                    # Fallback to default version if specified in app
                    default_version = getattr(app, "_default_api_version", "v1")
                    handler = v_map.get(default_version)
                
                if not handler:
                    return JsonResponse(
                        {"error": f"Endpoint not available for API version {version}"}, 
                        status_code=404
                    )
                
                return await handler(request)

            # Register the shim on the main app router
            register_method = getattr(app, method.lower())
            register_method(full_path)(shim)


class VersionNegotiator:
    """Determines which API version to use from request."""
    
    def __init__(self, default_version: str):
        self.default_version = default_version
    
    def negotiate(
        self,
        path: str,
        headers: Dict[str, str],
        registered_versions: List[str],
    ) -> str:
        """
        Negotiate API version from request.
        
        Priority:
        1. URL path (/v1/users, /v2/users)
        2. API-Version header
        3. Accept-Version header
        4. Default version
        
        Args:
            path: Request path
            headers: Request headers
            registered_versions: List of available versions
        
        Returns:
            Selected version name
        """
        # 1. Check URL path
        for version in registered_versions:
            if path.startswith(f"/{version}/"):
                logger.debug(f"Version negotiated from URL path: {version}")
                return version
        
        # 2. Check API-Version header
        api_version = headers.get("api-version") or headers.get("API-Version")
        if api_version and api_version in registered_versions:
            logger.debug(f"Version negotiated from API-Version header: {api_version}")
            return api_version
        
        # 3. Check Accept-Version header
        accept_version = headers.get("accept-version") or headers.get("Accept-Version")
        if accept_version and accept_version in registered_versions:
            logger.debug(f"Version negotiated from Accept-Version header: {accept_version}")
            return accept_version
        
        # 4. Default
        logger.debug(f"Using default version: {self.default_version}")
        return self.default_version


class VersionedMiddleware:
    """ASGI middleware for API versioning."""
    
    def __init__(
        self,
        app: Any,
        versions: Optional[List[APIVersion]] = None,
        default_version: Optional[str] = None,
    ):
        """
        Initialize versioning middleware.
        
        Args:
            app: ASGI app
            versions: List of APIVersion instances
            default_version: Default version name
        """
        self.app = app
        self.versions = {v.name: v for v in (versions or [])}
        self.default_version = default_version or "v1"
        
        if self.default_version not in self.versions:
            logger.warning(f"Default version {self.default_version} not registered")
        
        self.negotiator = VersionNegotiator(self.default_version)
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware entry point."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Get request version
        path = scope.get("path", "")
        headers = {
            name.decode().lower(): value.decode()
            for name, value in (scope.get("headers") or [])
        }
        
        version = self.negotiator.negotiate(path, headers, list(self.versions.keys()))
        
        # Store version in scope for downstream handlers
        scope["api_version"] = version
        
        # Wrap send to add deprecation headers
        async def send_with_version_headers(message):
            if message["type"] == "http.response.start":
                api_ver = self.versions.get(version)
                if api_ver:
                    headers_list = list(message.get("headers", []))
                    headers_list.append((b"x-api-version", version.encode()))
                    
                    # Add deprecation headers
                    for header_name, header_value in api_ver.get_deprecation_headers().items():
                        headers_list.append((header_name, header_value))
                    
                    message["headers"] = headers_list
            
            await send(message)
        
        await self.app(scope, receive, send_with_version_headers)


def get_api_version(scope: Dict[str, Any]) -> str:
    """Get current API version from request scope."""
    return scope.get("api_version", "v1")
