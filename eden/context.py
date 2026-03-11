"""
Eden — Context Utilities

Provides async-safe storage for the current request and user using ContextVars.
"""

import contextvars
from typing import TYPE_CHECKING, Any, Optional


if TYPE_CHECKING:
    from eden.auth.models import BaseUser
    from eden.requests import Request

# Context variables
_request_ctx = contextvars.ContextVar("request", default=None)
_user_ctx = contextvars.ContextVar("user", default=None)
_app_ctx = contextvars.ContextVar("app", default=None)


def set_request(request: "Request") -> contextvars.Token:
    """Set the current request in context."""
    return _request_ctx.set(request)

def get_request() -> Optional["Request"]:
    """Get the current request from context."""
    return _request_ctx.get()

def set_user(user: "BaseUser") -> contextvars.Token:
    """Set the current user in context."""
    return _user_ctx.set(user)

def get_user() -> Optional["BaseUser"]:
    """Get the current user from context."""
    return _user_ctx.get()

def reset_request(token: contextvars.Token) -> None:
    """Reset the request context."""
    _request_ctx.reset(token)

def reset_user(token: contextvars.Token) -> None:
    """Reset the user context."""
    _user_ctx.reset(token)

def set_app(app: Any) -> contextvars.Token:
    """Set the current app in context."""
    return _app_ctx.set(app)

def get_app() -> Any:
    """Get the current app from context."""
    return _app_ctx.get()


class ContextProxy:
    """
    Proxy object that redirects attribute access to the current context-local object.
    Similar to Flask's 'request' or 'session' objects.
    """
    def __init__(self, getter, name):
        self._getter = getter
        self._name = name

    def __getattr__(self, name):
        obj = self._getter()
        if obj is None:
            raise RuntimeError(f"Working outside of {self._name} context.")
        return getattr(obj, name)

    def __setattr__(self, name, value):
        if name in ("_getter", "_name"):
            super().__setattr__(name, value)
        else:
            obj = self._getter()
            if obj is None:
                raise RuntimeError(f"Working outside of {self._name} context.")
            setattr(obj, name, value)

    def __bool__(self):
        return bool(self._getter())

    def __repr__(self):
        obj = self._getter()
        return repr(obj) if obj else f"<unbound {self._name} proxy>"

# Global proxies
request = ContextProxy(get_request, "request")
user = ContextProxy(get_user, "user")
