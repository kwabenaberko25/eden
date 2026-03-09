"""
Eden — Exception Classes

Structured error handling with automatic JSON error responses.
"""

from __future__ import annotations

from typing import Any

from eden.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


class EdenException(Exception):
    """Base exception for all Eden errors."""

    status_code: int = HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred."

    def __init__(
        self,
        detail: str | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        self.headers = headers or {}
        self.extra = extra or {}
        super().__init__(self.detail)

    def to_dict(self) -> dict[str, Any]:
        """Serialize exception to a JSON-friendly dictionary."""
        result: dict[str, Any] = {
            "error": True,
            "status_code": self.status_code,
            "detail": self.detail,
        }
        if self.extra:
            result["extra"] = self.extra
        return result


class HttpException(EdenException):
    """General HTTP exception with a specific status code."""

    pass


class BadRequest(EdenException):
    """400 Bad Request."""

    status_code = HTTP_400_BAD_REQUEST
    detail = "Bad request."


class Unauthorized(EdenException):
    """401 Unauthorized."""

    status_code = HTTP_401_UNAUTHORIZED
    detail = "Authentication required."


class Forbidden(EdenException):
    """403 Forbidden."""

    status_code = HTTP_403_FORBIDDEN
    detail = "Permission denied."


class NotFound(EdenException):
    """404 Not Found."""

    status_code = HTTP_404_NOT_FOUND
    detail = "Resource not found."


class MethodNotAllowed(EdenException):
    """405 Method Not Allowed."""

    status_code = HTTP_405_METHOD_NOT_ALLOWED
    detail = "Method not allowed."


class Conflict(EdenException):
    """409 Conflict."""

    status_code = HTTP_409_CONFLICT
    detail = "Resource conflict."


class ValidationError(EdenException):
    """422 Unprocessable Entity — request body validation failed."""

    status_code = HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation error."

    def __init__(
        self,
        errors: list[dict[str, Any]] | None = None,
        detail: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.errors = errors or []
        super().__init__(detail=detail, extra={"errors": self.errors}, **kwargs)


class TooManyRequests(EdenException):
    """429 Too Many Requests."""

    status_code = HTTP_429_TOO_MANY_REQUESTS
    detail = "Too many requests. Please slow down."


class InternalServerError(EdenException):
    """500 Internal Server Error."""

    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Internal server error."
