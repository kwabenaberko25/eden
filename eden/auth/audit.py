"""
Eden — Authentication Audit Logger

Provides structured logging for all authentication events.
Events are emitted as structured JSON for easy ingestion by
monitoring systems (ELK, Datadog, etc.).

Usage:
    from eden.auth.audit import auth_audit
    
    auth_audit.login_success(request, user)
    auth_audit.login_failed(request, email="alice@example.com", reason="invalid_password")
    auth_audit.logout(request, user)
"""

import datetime
import logging
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from eden.auth.base import BaseUser
    from eden.requests import Request

logger = logging.getLogger("eden.auth.audit")


class AuthAuditLogger:
    """
    Structured audit logger for authentication events.
    
    All events include:
    - Timestamp (UTC ISO format)
    - Event type
    - IP address
    - User agent
    - User ID (if available)
    - Email (if available)
    """
    
    def _get_client_info(self, request: "Request") -> dict[str, str]:
        """Extract client information from request."""
        client = getattr(request, "client", None)
        ip = client.host if client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        return {"ip_address": ip, "user_agent": user_agent}
    
    def _emit(self, event: str, request: Optional["Request"] = None, **extra: Any) -> None:
        """Emit a structured audit log entry."""
        entry = {
            "event": event,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            **extra,
        }
        
        if request:
            entry.update(self._get_client_info(request))
        
        logger.info("AUTH_AUDIT: %s", entry)
    
    def login_success(self, request: "Request", user: "BaseUser") -> None:
        """Log a successful login."""
        self._emit(
            "login_success",
            request,
            user_id=str(user.id),
            email=getattr(user, "email", "unknown"),
        )
    
    def login_failed(
        self,
        request: "Request",
        email: str = "",
        reason: str = "invalid_credentials",
    ) -> None:
        """Log a failed login attempt."""
        self._emit(
            "login_failed",
            request,
            email=email,
            reason=reason,
        )
    
    def logout(self, request: "Request", user: Optional["BaseUser"] = None) -> None:
        """Log a logout event."""
        self._emit(
            "logout",
            request,
            user_id=str(user.id) if user else "unknown",
            email=getattr(user, "email", "unknown") if user else "unknown",
        )
    
    def logout_all(self, user: "BaseUser") -> None:
        """Log a 'logout everywhere' event."""
        self._emit(
            "logout_all",
            user_id=str(user.id),
            email=getattr(user, "email", "unknown"),
        )
    
    def password_changed(self, request: "Request", user: "BaseUser") -> None:
        """Log a password change event."""
        self._emit(
            "password_changed",
            request,
            user_id=str(user.id),
            email=getattr(user, "email", "unknown"),
        )
    
    def token_revoked(self, jti: str, user_id: str = "") -> None:
        """Log a token revocation."""
        self._emit("token_revoked", jti=jti, user_id=user_id)


# Global singleton
auth_audit = AuthAuditLogger()
