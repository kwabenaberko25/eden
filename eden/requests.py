from __future__ import annotations
"""
Eden — Request Wrapper

Extends Starlette's Request with convenience methods for JSON, form data,
file uploads, and type-safe access to params/headers/cookies.
"""


from typing import Any

from starlette.requests import Request as StarletteRequest


class Request(StarletteRequest):
    """
    Enhanced request object with convenience accessors.

    Wraps Starlette's Request to provide a cleaner API for common
    operations like reading JSON, form data, and uploaded files.
    """
    def __init__(self, scope: Any, receive: Any = None, send: Any = None) -> None:
        super().__init__(scope, receive, send)
        # Store in scope to allow reuse across middleware
        if "eden_request" not in scope:
            scope["eden_request"] = self

    @classmethod
    def from_scope(cls, scope: Any, receive: Any = None, send: Any = None) -> Request:
        """
        Get existing Eden Request from scope or create new one.
        Prevents duplicate body reading issues in middleware.
        """
        if "eden_request" in scope:
            return scope["eden_request"]
        return cls(scope, receive, send)
    @property
    def user(self) -> Any:
        """
        Return the authenticated user, or None if not authenticated.
        """
        return self.scope.get("user")

    @user.setter
    def user(self, value: Any) -> None:
        """
        Set the authenticated user in the request scope.
        """
        self.scope["user"] = value

    @property
    def app(self) -> Any:
        """
        Return the Eden application instance.
        """
        return self.scope.get("eden_app") or super().app

    def render(self, template_name: str, context: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """
        Render a template using the application's templating engine.
        
        Usage:
            return request.render("index.html", user=user)
        """
        return self.app.eden.render(template_name, context, request=self, **kwargs)

    def url_for(self, name: str, **path_params: Any) -> Any:
        """
        Generate a URL for a given route name.
        Returns an absolute URL when possible.
        """
        try:
            # Try Starlette's native url_for first (handles absolute URLs)
            return super().url_for(name, **path_params)
        except Exception:
            # Fallback to Eden's reverse router for custom logical names/namespaces
            path = self.app.eden._router.url_for(name, **path_params)
            # Reconstruct absolute URL
            return str(self.base_url).rstrip("/") + path

    async def json_body(self) -> Any:
        """
        Parse and return the JSON request body.

        Returns:
            Parsed JSON data (dict, list, or scalar).

        Raises:
            ValueError: If body is not valid JSON.
        """
        return await self.json()

    async def form_data(self) -> dict[str, Any]:
        """
        Parse and return form data as a dictionary.

        Returns:
            Dictionary of form field names to values.
        """
        form = await self.form()
        return dict(form)

    async def uploaded_files(self) -> dict[str, Any]:
        """
        Extract uploaded files from the request.

        Returns:
            Dictionary of field names to UploadFile objects.
        """
        form = await self.form()
        return {
            key: value
            for key, value in form.items()
            if hasattr(value, "filename")
        }

    @property
    def client_host(self) -> str | None:
        """Get the client's host address."""
        if self.client:
            return self.client.host
        return None

    @property
    def content_type(self) -> str | None:
        """Get the Content-Type header."""
        return self.headers.get("content-type")

    @property
    def is_json(self) -> bool:
        """Check if the request has a JSON content type."""
        ct = self.content_type
        if ct is None:
            return False
        return "application/json" in ct

    @property
    def is_form(self) -> bool:
        """Check if the request has form data content type."""
        ct = self.content_type
        if ct is None:
            return False
        return any(
            t in ct
            for t in ("application/x-www-form-urlencoded", "multipart/form-data")
        )

    def get_header(self, name: str, default: str | None = None) -> str | None:
        """Get a header value by name (case-insensitive)."""
        return self.headers.get(name.lower(), default)

    def get_cookie(self, name: str, default: str | None = None) -> str | None:
        """Get a cookie value by name."""
        return self.cookies.get(name, default)

    def get_query(self, name: str, default: str | None = None) -> str | None:
        """Get a query parameter by name."""
        return self.query_params.get(name, default)

    def get_query_list(self, name: str) -> list[str]:
        """Get all values for a query parameter (multi-valued)."""
        return self.query_params.getlist(name)

    @property
    def messages(self) -> Any:
        """
        Access the messaging container for this request.
        """
        from eden.messages import get_messages
        return get_messages(self)
