"""
Eden Error Handling — Standardized Response Format

This module provides consistent error responses across the entire API.
All error responses follow a standard contract for predictable client handling.

Standard Error Response Format:
{
    "error": {
        "code": "RESOURCE_NOT_FOUND",
        "message": "User with ID 42 not found",
        "status": 404,
        "timestamp": "2024-01-15T10:30:45.123Z",
        "path": "/api/users/42",
        "details": {
            "resource_type": "User",
            "resource_id": "42"
        }
    }
}

Usage:
    from eden.errors import (
        APIError, BadRequest, NotFound, Unauthorized,
        error_handler, format_error_response
    )
    
    @app.exception_handler(APIError)
    async def handle_api_error(request, exc):
        return error_handler(exc)
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict, field
from starlette.responses import JSONResponse
from starlette.requests import Request

logger = logging.getLogger(__name__)


# ============================================================================
# ERROR CODES
# ============================================================================

class ErrorCode(str, Enum):
    """Standard error codes for API responses."""
    
    # Client Errors (4xx)
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNPROCESSABLE_ENTITY = "UNPROCESSABLE_ENTITY"
    RATE_LIMITED = "RATE_LIMITED"
    
    # Server Errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    
    # Domain-specific Errors
    AUTH_FAILED = "AUTH_FAILED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    INVALID_STATE = "INVALID_STATE"


# ============================================================================
# ERROR RESPONSE DATA STRUCTURE
# ============================================================================

@dataclass
class ErrorDetail:
    """Individual validation error."""
    field: str
    message: str
    code: Optional[str] = None


@dataclass
class ErrorInfo:
    """Complete error information."""
    code: ErrorCode
    message: str
    status: int
    path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    details: Dict[str, Any] = field(default_factory=dict)
    validation_errors: list[ErrorDetail] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response dict."""
        result: Dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
            "status": self.status,
            "timestamp": self.timestamp,
        }
        
        if self.path:
            result["path"] = self.path
        
        if self.details:
            result["details"] = self.details
        
        if self.validation_errors:
            result["validation_errors"] = [
                {
                    "field": err.field,
                    "message": err.message,
                    "code": err.code,
                }
                for err in self.validation_errors
            ]
        
        return result


# ============================================================================
# BASE EXCEPTION CLASSES
# ============================================================================

class APIError(Exception):
    """
    Base exception for API errors.
    
    Automatically converted to standardized JSON response.
    """
    
    code = ErrorCode.INTERNAL_ERROR
    status = 500
    message = "An error occurred"
    
    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[ErrorCode] = None,
        status: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message or self.message
        self.code = code or self.code
        self.status = status or self.status
        self.details = details or {}
        super().__init__(self.message)
    
    def to_error_info(self, path: Optional[str] = None) -> ErrorInfo:
        """Convert exception to ErrorInfo."""
        return ErrorInfo(
            code=self.code,
            message=self.message,
            status=self.status,
            path=path,
            details=self.details,
        )


class BadRequest(APIError):
    """400 Bad Request."""
    code = ErrorCode.BAD_REQUEST
    status = 400
    message = "Bad request"


class ValidationError(APIError):
    """422 Validation Error."""
    code = ErrorCode.VALIDATION_ERROR
    status = 422
    message = "Validation failed"
    
    def __init__(
        self,
        message: str = "Validation failed",
        errors: Optional[list[ErrorDetail]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.validation_errors = errors or []
    
    def to_error_info(self, path: Optional[str] = None) -> ErrorInfo:
        info = super().to_error_info(path)
        info.validation_errors = self.validation_errors
        return info


class Unauthorized(APIError):
    """401 Unauthorized."""
    code = ErrorCode.UNAUTHORIZED
    status = 401
    message = "Unauthorized"


class Forbidden(APIError):
    """403 Forbidden."""
    code = ErrorCode.FORBIDDEN
    status = 403
    message = "Forbidden"


class NotFound(APIError):
    """404 Not Found."""
    code = ErrorCode.NOT_FOUND
    status = 404
    message = "Not found"


class Conflict(APIError):
    """409 Conflict."""
    code = ErrorCode.CONFLICT
    status = 409
    message = "Conflict"


class RateLimited(APIError):
    """429 Too Many Requests."""
    code = ErrorCode.RATE_LIMITED
    status = 429
    message = "Rate limit exceeded"


class InternalError(APIError):
    """500 Internal Server Error."""
    code = ErrorCode.INTERNAL_ERROR
    status = 500
    message = "Internal server error"


# ============================================================================
# ERROR RESPONSE HANDLERS
# ============================================================================

def format_error_response(error_info: ErrorInfo) -> Dict[str, Any]:
    """
    Format ErrorInfo as JSON response body.
    
    Args:
        error_info: ErrorInfo instance
        
    Returns:
        Dict suitable for JSON serialization
        
    Example:
        >>> error = APIError("Something wrong", status=400)
        >>> info = error.to_error_info("/api/users")
        >>> response_body = format_error_response(info)
        >>> print(response_body["status"])
        400
    """
    return {
        "error": error_info.to_dict()
    }


async def error_handler(
    request: Request,
    exc: APIError,
) -> JSONResponse:
    """
    Convert APIError to JSON response.
    
    Automatically called by error handler middleware.
    Can be registered with Starlette:
    
    Example:
        @app.exception_handler(APIError)
        async def handle_api_error(request, exc):
            return await error_handler(request, exc)
    
    Args:
        request: Starlette request
        exc: APIError instance
        
    Returns:
        JSONResponse with error details
    """
    path = str(request.url.path)
    error_info = exc.to_error_info(path=path)
    
    # Log error
    log_level = logging.WARNING if exc.status < 500 else logging.ERROR
    logger.log(
        log_level,
        f"{exc.status} {exc.code.value}: {exc.message}",
        extra={
            "path": path,
            "status": exc.status,
            "code": exc.code.value,
            "details": exc.details,
        }
    )
    
    return JSONResponse(
        status_code=exc.status,
        content=format_error_response(error_info),
    )


async def validation_error_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    """
    Handler for validation errors with field-level details.
    
    Example:
        errors = [
            ErrorDetail(field="email", message="Invalid email format"),
            ErrorDetail(field="password", message="Too short"),
        ]
        exc = ValidationError("Form validation failed", errors=errors)
    """
    return await error_handler(request, exc)


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_required(value: Any, field_name: str) -> None:
    """
    Validate that a field is provided.
    
    Args:
        value: Field value
        field_name: Field name (for error message)
        
    Raises:
        ValidationError: If value is None or empty
        
    Example:
        validate_required(email, "email")
    """
    if not value:
        raise ValidationError(
            f"Field '{field_name}' is required",
            errors=[ErrorDetail(field=field_name, message="This field is required", code="required")]
        )


def validate_email(email: str) -> None:
    """
    Validate email format.
    
    Args:
        email: Email string
        
    Raises:
        ValidationError: If email invalid
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError(
            "Invalid email format",
            errors=[ErrorDetail(field="email", message="Invalid email format", code="invalid")]
        )


def validate_range(
    value: int,
    field_name: str,
    min_val: Optional[int] = None,
    max_val: Optional[int] = None,
) -> None:
    """
    Validate integer is within range.
    
    Args:
        value: Integer to validate
        field_name: Field name
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)
        
    Raises:
        ValidationError: If out of range
    """
    errors = []
    if min_val is not None and value < min_val:
        errors.append(ErrorDetail(
            field=field_name,
            message=f"Value must be >= {min_val}",
            code="too_small"
        ))
    if max_val is not None and value > max_val:
        errors.append(ErrorDetail(
            field=field_name,
            message=f"Value must be <= {max_val}",
            code="too_large"
        ))
    if errors:
        raise ValidationError(f"Invalid {field_name}", errors=errors)


# ============================================================================
# ERROR CONTEXT & CHAINING
# ============================================================================

class ErrorContext:
    """
    Track error context for better debugging.
    
    Example:
        with ErrorContext(operation="user_creation", user_id=42):
            raise APIError("Something went wrong")
    """
    
    _stack: list[Dict[str, Any]] = []
    
    def __init__(self, **context):
        self.context = context
    
    def __enter__(self):
        self._stack.append(self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stack.pop()
        if exc_type is APIError and self._stack:
            # Add context to exception details
            exc_val.details.update({"context": self._stack[-1]})


# ============================================================================
# INTEGRATION WITH MIDDLEWARE
# ============================================================================

def setup_error_handling(app):
    """
    Setup global error handling middleware.
    
    Args:
        app: Starlette application
        
    Example:
        from starlette.applications import Starlette
        app = Starlette()
        setup_error_handling(app)
    """
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        return await error_handler(request, exc)
    
    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception", exc_info=exc)
        error = InternalError("An unexpected error occurred")
        return await error_handler(request, error)


__all__ = [
    # Codes
    "ErrorCode",
    # Models
    "ErrorDetail",
    "ErrorInfo",
    # Exceptions
    "APIError",
    "BadRequest",
    "ValidationError",
    "Unauthorized",
    "Forbidden",
    "NotFound",
    "Conflict",
    "RateLimited",
    "InternalError",
    # Handlers
    "format_error_response",
    "error_handler",
    "validation_error_handler",
    # Validation
    "validate_required",
    "validate_email",
    "validate_range",
    # Context
    "ErrorContext",
    # Setup
    "setup_error_handling",
]
