"""
Eden — Request Wrapper

Extends Starlette's Request with convenience methods for JSON, form data,
file uploads, and type-safe access to params/headers/cookies.
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request as StarletteRequest


class Request(StarletteRequest):
    """
    Enhanced request object with convenience accessors.

    Wraps Starlette's Request to provide a cleaner API for common
    operations like reading JSON, form data, and uploaded files.
    """

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
