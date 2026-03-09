"""
Eden — Response Classes

JSON, HTML, Redirect, and File responses with auto-serialization
of Pydantic models and dictionaries.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import pydantic
from starlette.responses import FileResponse as StarletteFileResponse
from starlette.responses import HTMLResponse as StarletteHTMLResponse
from starlette.responses import JSONResponse as StarletteJSONResponse
from starlette.responses import RedirectResponse as StarletteRedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse as StarletteStreamingResponse


def _serialize(data: Any) -> Any:
    """
    Recursively serialize data for JSON encoding.
    Handles Pydantic models, dicts, lists, and primitives.
    """
    if isinstance(data, pydantic.BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, dict):
        return {key: _serialize(value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return [_serialize(item) for item in data]
    if isinstance(data, (set, frozenset)):
        return [_serialize(item) for item in data]
    return data


class Response(StarletteResponse):
    """Base response with Eden helpers."""

    pass


class JsonResponse(StarletteJSONResponse):
    """
    JSON response with automatic serialization of Pydantic models.

    Usage:
        return JsonResponse({"key": "value"})
        return JsonResponse(my_pydantic_model)
        return JsonResponse([item1, item2])
    """

    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        serialized = _serialize(content)
        super().__init__(content=serialized, status_code=status_code, headers=headers, **kwargs)


class HtmlResponse(StarletteHTMLResponse):
    """HTML response for rendered templates or raw HTML."""

    pass


class RedirectResponse(StarletteRedirectResponse):
    """HTTP redirect response."""
    pass


class SafeRedirectResponse(RedirectResponse):
    """
    HTTP redirect response that prevents open redirect vulnerabilities.
    Only allows local redirects (starting with /) or redirects to explicitly
    allowed hosts.
    """

    def __init__(
        self,
        url: str,
        status_code: int = 307,
        headers: dict[str, str] | None = None,
        allowed_hosts: set[str] | None = None,
        **kwargs: Any,
    ) -> None:
        if not self._is_safe_url(url, allowed_hosts):
            # Default to root if unsafe
            url = "/"
        super().__init__(url=url, status_code=status_code, headers=headers, **kwargs)

    def _is_safe_url(self, url: str, allowed_hosts: set[str] | None) -> bool:
        """Validate if a URL is safe for redirection."""
        if not url:
            return False

        parsed = urlparse(url)
        # Local paths are safe (empty netloc and starts with /)
        if not parsed.netloc and url.startswith("/"):
            return not url.startswith("//")

        # Check against allowed hosts if external
        if allowed_hosts and parsed.netloc in allowed_hosts:
            return True

        return False


class FileResponse(StarletteFileResponse):
    """File download response."""

    pass


class StreamingResponse(StarletteStreamingResponse):
    """Streaming response for large payloads or SSE."""

    pass


def json(
    data: Any,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> JsonResponse:
    """Shortcut function: return a JSON response."""
    return JsonResponse(content=data, status_code=status_code, headers=headers)


def html(
    content: str,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> HtmlResponse:
    """Shortcut function: return an HTML response."""
    return HtmlResponse(content=content, status_code=status_code, headers=headers)


def redirect(
    url: str,
    status_code: int = 307,
    headers: dict[str, str] | None = None,
    safe: bool = False,
    allowed_hosts: set[str] | None = None,
) -> RedirectResponse:
    """Shortcut function: return a redirect response."""
    if safe:
        return SafeRedirectResponse(url=url, status_code=status_code, headers=headers, allowed_hosts=allowed_hosts)
    return RedirectResponse(url=url, status_code=status_code, headers=headers)
