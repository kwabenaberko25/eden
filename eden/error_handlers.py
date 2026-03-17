"""
Context-aware error handlers for specific exception types.

These handlers catch domain-specific errors (database, filesystem, API errors)
and add detailed context to help with debugging while presenting user-friendly messages.

Handlers are registered with the error handler registry and automatically dispatched
by ErrorHandlerMiddleware based on exception type matching.

Usage:
    # Register handlers at app startup
    from eden.error_handlers import DatabaseErrorHandler, StorageErrorHandler
    
    app.register_error_handler(DatabaseErrorHandler())
    app.register_error_handler(StorageErrorHandler())
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from starlette.requests import Request
from starlette.responses import JSONResponse

from eden.exceptions import ErrorHandler, EdenException

logger = logging.getLogger(__name__)


class DatabaseErrorHandler(ErrorHandler):
    """
    Catch database errors and add operation context.
    
    Detects:
    - SQLAlchemy integrity errors (unique constraint, foreign key)
    - Connection pool exhaustion
    - Query timeouts
    - Transaction deadlocks
    
    Context added:
    - Operation (INSERT, UPDATE, DELETE, SELECT)
    - Table/model affected
    - Query duration
    - Connection pool status
    
    Example error:
        DatabaseError(
            detail="Unique constraint violation on email",
            status_code=409,
            context={
                "table": "users",
                "operation": "INSERT",
                "field": "email",
                "attempted_value": "alice@example.com",
                "duration_ms": 45,
            }
        )
    """
    
    def matches(self, exc: Exception) -> bool:
        """Check if exception is database-related."""
        import_names = [
            'sqlalchemy',
            'asyncpg',
            'psycopg2',
            'pymongo',
            'redis',
        ]
        
        exc_module = type(exc).__module__ or ""
        exc_name = type(exc).__name__
        
        # Check module prefix
        is_db_module = any(exc_module.startswith(name) for name in import_names)
        
        # Check exception name (common DB errors)
        is_db_error = any(
            db_err in exc_name
            for db_err in [
                'Integrity', 'Constraint', 'Foreign', 'Unique',
                'Connection', 'Timeout', 'Deadlock', 'OperationalError',
                'ProgrammingError', 'DatabaseError',
            ]
        )
        
        return is_db_module or is_db_error or hasattr(exc, '__module__') and 'database' in str(exc.__module__).lower()
    
    async def handle(self, exc: Exception, request: Request) -> JSONResponse:
        """Handle database error with context."""
        exc_name = type(exc).__name__
        exc_str = str(exc)
        
        # Extract context from exception if available
        context = getattr(exc, 'context', {})
        if isinstance(exc, EdenException):
            context = exc.context
        
        # Add server-side context based on error type
        if "Unique" in exc_name or "unique" in exc_str.lower():
            context.setdefault("error_type", "duplicate_value")
            context.setdefault("message", "A record with this value already exists")
        elif "Foreign" in exc_name or "foreign" in exc_str.lower():
            context.setdefault("error_type", "missing_reference")
            context.setdefault("message", "Referenced record does not exist")
        elif "Connection" in exc_name or "connection" in exc_str.lower():
            context.setdefault("error_type", "database_unavailable")
            context.setdefault("message", "Database connection failed")
        elif "Timeout" in exc_name or "timeout" in exc_str.lower():
            context.setdefault("error_type", "query_timeout")
            context.setdefault("message", "Database query took too long")
        elif "Deadlock" in exc_name or "deadlock" in exc_str.lower():
            context.setdefault("error_type", "transaction_conflict")
            context.setdefault("message", "Transaction conflict, please retry")
        else:
            context.setdefault("error_type", "database_error")
            context.setdefault("message", "Database operation failed")
        
        # Log with context
        logger.error(
            f"Database error: {exc_name}",
            extra={
                "exc_info": exc,
                "context": context,
                "path": request.url.path,
                "method": request.method,
                "request_id": getattr(request, "scope", {}).get("eden_request_id", ""),
            }
        )
        
        # Determine HTTP status based on error type
        status_code = 500
        if context.get("error_type") == "duplicate_value":
            status_code = 409  # Conflict
        elif context.get("error_type") == "missing_reference":
            status_code = 400  # Bad Request
        elif context.get("error_type") == "database_unavailable":
            status_code = 503  # Service Unavailable
        elif context.get("error_type") == "query_timeout":
            status_code = 504  # Gateway Timeout
        
        # Return response with user-friendly message
        return JSONResponse(
            {
                "status": "error",
                "detail": context.get("message", "Database error"),
                "type": context.get("error_type", "database_error"),
            },
            status_code=status_code,
        )


class StorageErrorHandler(ErrorHandler):
    """
    Catch file storage and I/O errors with operation context.
    
    Detects:
    - S3 access denied, bucket not found
    - File not found, permission denied
    - Disk full, quota exceeded
    - Network errors during upload/download
    - Invalid file format
    
    Context added:
    - File path or bucket
    - Operation (upload, download, delete)
    - File size
    - Backend (S3, Supabase, local)
    - Bytes transferred before failure
    
    Example error:
        StorageError(
            detail="Failed to upload avatar.jpg to S3",
            status_code=413,
            context={
                "backend": "s3",
                "operation": "upload",
                "filename": "avatar.jpg",
                "file_size_bytes": 5242880,
                "bytes_transferred": 2621440,
                "reason": "Payload too large",
            }
        )
    """
    
    def matches(self, exc: Exception) -> bool:
        """Check if exception is storage/IO-related."""
        import_names = [
            'botocore',
            'aioboto3',
            'supabase',
            'boto3',
        ]
        
        exc_module = type(exc).__module__ or ""
        exc_name = type(exc).__name__
        
        # Check module prefix
        is_storage_module = any(exc_module.startswith(name) for name in import_names)
        
        # Check exception name (common IO/storage errors)
        is_io_error = any(
            io_err in exc_name
            for io_err in [
                'FileNotFound', 'PermissionDenied', 'IOError', 'OSError',
                'NoSuchKey', 'AccessDenied', 'Forbidden', 'NotFound',
                'ClientError', 'BotoCoreError', 'EndpointConnectionError',
                'ClientConnectionError', 'ReadTimeout', 'ConnectTimeout',
            ]
        )
        
        # Check for IO-related builtins
        is_builtin = exc_name in ['IOError', 'OSError', 'FileNotFoundError', 'PermissionError']
        
        return is_storage_module or is_io_error or is_builtin
    
    async def handle(self, exc: Exception, request: Request) -> JSONResponse:
        """Handle storage error with context."""
        exc_name = type(exc).__name__
        exc_str = str(exc)
        
        # Extract context
        context = getattr(exc, 'context', {})
        if isinstance(exc, EdenException):
            context = exc.context
        
        # Determine error type and user message
        if "NotFound" in exc_name or "NoSuchKey" in exc_name:
            context.setdefault("error_type", "file_not_found")
            context.setdefault("message", "File not found")
            status_code = 404
        elif "PermissionDenied" in exc_name or "AccessDenied" in exc_name or "Forbidden" in exc_name:
            context.setdefault("error_type", "access_denied")
            context.setdefault("message", "Permission denied")
            status_code = 403
        elif "Full" in exc_name or "quota" in exc_str.lower():
            context.setdefault("error_type", "storage_full")
            context.setdefault("message", "Storage full, unable to save file")
            status_code = 507  # Insufficient Storage
        elif "Payload" in exc_name or "TooLarge" in exc_name or "Size" in exc_name:
            context.setdefault("error_type", "file_too_large")
            context.setdefault("message", "File is too large")
            status_code = 413  # Payload Too Large
        elif "Timeout" in exc_name or "Connection" in exc_name:
            context.setdefault("error_type", "network_error")
            context.setdefault("message", "Network error during transfer")
            status_code = 504  # Gateway Timeout
        else:
            context.setdefault("error_type", "storage_error")
            context.setdefault("message", "File operation failed")
            status_code = 500
        
        # Log with context
        logger.error(
            f"Storage error: {exc_name}",
            extra={
                "exc_info": exc,
                "context": context,
                "path": request.url.path,
                "method": request.method,                "request_id": getattr(request, "scope", {}).get("eden_request_id", ""),            }
        )
        
        # Return response
        return JSONResponse(
            {
                "status": "error",
                "detail": context.get("message", "Storage error"),
                "type": context.get("error_type", "storage_error"),
            },
            status_code=status_code,
        )


class ValidationErrorHandler(ErrorHandler):
    """
    Catch validation errors and add field-specific context.
    
    Detects:
    - Pydantic validation errors
    - Form validation errors
    - Type validation failures
    
    Context added:
    - Field names with errors
    - Expected vs actual type
    - Min/max constraints violated
    - Constraint descriptions
    
    Example error:
        ValidationError(
            detail="Validation failed",
            status_code=422,
            context={
                "fields": {
                    "email": "Invalid email format",
                    "age": "Must be between 18 and 120",
                }
            }
        )
    """
    
    def matches(self, exc: Exception) -> bool:
        """Check if exception is validation-related."""
        exc_name = type(exc).__name__
        
        return exc_name in [
            'ValidationError',  # Pydantic v2
            'ValidatorError',  # Custom validators
            'ValueError',  # Often used for validation
        ] or 'validation' in str(type(exc).__module__).lower()
    
    async def handle(self, exc: Exception, request: Request) -> JSONResponse:
        """Handle validation error with field details."""
        context = getattr(exc, 'context', {})
        if isinstance(exc, EdenException):
            context = exc.context
        
        # Extract field errors from Pydantic if available
        errors_dict = {}
        try:
            if hasattr(exc, 'errors'):
                for err in exc.errors():
                    loc = err.get('loc', ['unknown'])[0]
                    msg = err.get('msg', 'Invalid value')
                    errors_dict[str(loc)] = msg
        except Exception:
            pass
        
        context.setdefault("error_type", "validation_error")
        context.setdefault("message", "Validation failed")
        if errors_dict:
            context.setdefault("fields", errors_dict)
        
        # Log validation errors
        logger.warning(
            "Validation error",
            extra={
                "context": context,
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        return JSONResponse(
            {
                "status": "error",
                "detail": context.get("message", "Validation failed"),
                "type": "validation_error",
                "fields": context.get("fields", {}),
            },
            status_code=422,  # Unprocessable Entity
        )


class AuthenticationErrorHandler(ErrorHandler):
    """
    Catch authentication errors (missing/invalid credentials).
    
    Detects:
    - Missing authorization header
    - Invalid token format
    - Token expired
    - Invalid credentials
    
    Context added:
    - Why auth failed (missing token, expired, invalid signature)
    - Token type (Bearer, Basic)
    - User attempted to access
    """
    
    def matches(self, exc: Exception) -> bool:
        """Check if exception is authentication-related."""
        exc_name = type(exc).__name__
        exc_str = str(exc).lower()
        
        return bool(
            'auth' in exc_name.lower()
            or 'credential' in exc_name.lower()
            or 'token' in exc_name.lower()
            or 'unauthorized' in exc_str
            or 'unauthenticated' in exc_str
        )
    
    async def handle(self, exc: Exception, request: Request) -> JSONResponse:
        """Handle authentication error."""
        context = getattr(exc, 'context', {})
        if isinstance(exc, EdenException):
            context = exc.context
        
        context.setdefault("error_type", "authentication_error")
        context.setdefault("message", "Authentication required")
        
        logger.warning(
            "Authentication error",
            extra={
                "context": context,
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        return JSONResponse(
            {
                "status": "error",
                "detail": context.get("message", "Authentication failed"),
                "type": "authentication_error",
            },
            status_code=401,  # Unauthorized
        )


class AuthorizationErrorHandler(ErrorHandler):
    """
    Catch authorization errors (insufficient permissions).
    
    Detects:
    - Permission denied
    - Resource forbidden
    - Role/scope insufficient
    
    Context added:
    - Resource type and ID
    - Required vs actual permissions
    - User role/scopes
    """
    
    def matches(self, exc: Exception) -> bool:
        """Check if exception is authorization-related."""
        exc_name = type(exc).__name__
        exc_str = str(exc).lower()
        
        return bool(
            'permission' in exc_name.lower()
            or 'forbidden' in exc_name.lower()
            or 'access' in exc_name.lower()
            or 'denied' in exc_str
            or 'insufficient' in exc_str
        )
    
    async def handle(self, exc: Exception, request: Request) -> JSONResponse:
        """Handle authorization error."""
        context = getattr(exc, 'context', {})
        if isinstance(exc, EdenException):
            context = exc.context
        
        context.setdefault("error_type", "authorization_error")
        context.setdefault("message", "Access denied")
        
        logger.warning(
            "Authorization error",
            extra={
                "context": context,
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        return JSONResponse(
            {
                "status": "error",
                "detail": context.get("message", "Access denied"),
                "type": "authorization_error",
            },
            status_code=403,  # Forbidden
        )


__all__ = [
    "DatabaseErrorHandler",
    "StorageErrorHandler",
    "ValidationErrorHandler",
    "AuthenticationErrorHandler",
    "AuthorizationErrorHandler",
]
