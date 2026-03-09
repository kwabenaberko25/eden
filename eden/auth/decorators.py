"""
Eden — Authorization Decorators
"""

import functools
from collections.abc import Callable, Sequence
from typing import Any

from eden.auth.base import get_current_user
from eden.exceptions import Forbidden, Unauthorized


def login_required(func: Callable) -> Callable:
    """ decorator to ensure the user is logged in. """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Note: This assumes the first argument to a view function might be a request?
        # Actually, in Eden, we use Dependencies.
        # But for decorators, we can try to find the request in kwargs or args.
        request = kwargs.get("request")
        if not request:
            # Fallback for positional args
            for arg in args:
                from eden.requests import Request
                if isinstance(arg, Request):
                    request = arg
                    break

        if not request:
            raise RuntimeError("Request object not found in view arguments.")

        user = await get_current_user(request)
        if not user:
            raise Unauthorized(detail="Login required.")

        return await func(*args, **kwargs)

    return wrapper

def roles_required(roles: Sequence[str]) -> Callable:
    """Decorator to ensure the user has at least one of the specified roles."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    from eden.requests import Request
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                raise RuntimeError("Request object not found in view arguments.")

            user = await get_current_user(request)
            if not user:
                raise Unauthorized(detail="Login required.")

            # Check roles
            user_roles = getattr(user, "roles", [])
            if not any(role in user_roles for role in roles) and not getattr(user, "is_superuser", False):
                raise Forbidden(detail=f"Missing one of the required roles: {', '.join(roles)}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator

def permissions_required(permissions: Sequence[str]) -> Callable:
    """Decorator to ensure the user has all the specified permissions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    from eden.requests import Request
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                raise RuntimeError("Request object not found in view arguments.")

            user = await get_current_user(request)
            if not user:
                raise Unauthorized(detail="Login required.")

            # Check permissions
            user_permissions = getattr(user, "permissions", [])
            if not all(perm in user_permissions for perm in permissions) and not getattr(user, "is_superuser", False):
                raise Forbidden(detail=f"Missing required permissions: {', '.join(permissions)}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_permission(permission: str) -> Callable:
    """Decorator to ensure the user has a specific permission, considering role hierarchy."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    from eden.requests import Request
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                raise RuntimeError("Request object not found in view arguments.")

            user = await get_current_user(request)
            if not user:
                raise Unauthorized(detail="Login required.")

            if getattr(user, "is_superuser", False):
                return await func(*args, **kwargs)

            # Check direct permissions
            user_permissions = getattr(user, "permissions", [])
            if permission in user_permissions:
                return await func(*args, **kwargs)

            # Check RBAC hierarchy
            from eden.auth.rbac import default_rbac
            user_roles = getattr(user, "roles", [])
            if default_rbac.has_permission(user_roles, permission):
                return await func(*args, **kwargs)

            raise Forbidden(detail=f"Missing required permission: {permission}")

        return wrapper
    return decorator
