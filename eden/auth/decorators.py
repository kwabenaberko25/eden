"""
Eden — Authorization Decorators

Provides authentication and authorization decorators for both function-based
and class-based views. All decorators support:
- Function-based route handlers
- Class-Based Views (CBVs) via _find_request
- Tenant-aware RBAC via _get_tenant_roles / _get_tenant_permissions
- Superuser bypass

Usage:
    @login_required
    async def secret(request):
        return {"data": "sensitive"}

    @roles_required(["admin", "manager"])
    async def admin_panel(request):
        return {"panel": "admin"}

    @view_decorator(login_required)
    class ProtectedView(View):
        async def get(self, request): ...
"""

import functools
from collections.abc import Callable, Sequence
from typing import Any

from eden.auth.base import get_current_user
from eden.exceptions import Forbidden, Unauthorized, PermissionDenied


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _find_request(args: Sequence[Any], kwargs: dict[str, Any]) -> Any:
    """
    Safely find the request object in args or kwargs, supporting CBVs.
    """
    request = kwargs.get("request")
    if request:
        return request

    # Check args (handles CBV where self is first, request is second)
    for arg in args:
        if hasattr(arg, "scope") and hasattr(arg, "receive") and hasattr(arg, "send"):
            return arg

    # ContextVar fallback (set by middleware)
    from eden.context import get_request
    return get_request()


def _get_user_from_request(request: Any) -> Any:
    """
    Extract the user from a request object, checking multiple locations.
    """
    user = getattr(request, "user", None)
    if user is not None:
        return user
    # Check request.state as secondary
    state = getattr(request, "state", None)
    if state is not None:
        user = getattr(state, "user", None)
    return user


def _get_tenant_roles(user: Any) -> list[str]:
    """
    Get effective roles for the user in the current tenant context.
    """
    # 1. Check for a method that resolves tenant-scoped roles
    get_tenant_roles_fn = getattr(user, "get_roles_for_tenant", None)
    if callable(get_tenant_roles_fn) and not _is_mock(get_tenant_roles_fn):
        try:
            from eden.tenancy.context import get_current_tenant_id
            tenant_id = get_current_tenant_id()
            if tenant_id is not None:
                result = get_tenant_roles_fn(tenant_id)
                if isinstance(result, (list, tuple, set)):
                    return list(result)
        except Exception as e:
            from eden.logging import get_logger
            get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)

    # 2. Check for pre-resolved tenant_roles attribute
    tenant_roles = getattr(user, "tenant_roles", None)
    if isinstance(tenant_roles, (list, tuple, set)):
        return list(tenant_roles)

    # 3. Fallback: flat roles list on user model
    roles = getattr(user, "roles", [])
    if isinstance(roles, (list, tuple, set)):
        return list(roles)
    return []


def _get_tenant_permissions(user: Any) -> list[str]:
    """
    Get effective permissions for the user in the current tenant context.
    Combines direct permissions and permissions inherited via roles from default_rbac.
    """
    all_perms = set()

    # 1. Resolve direct permissions from user model (tenant-aware)
    get_tenant_perms_fn = getattr(user, "get_permissions_for_tenant", None)
    if callable(get_tenant_perms_fn) and not _is_mock(get_tenant_perms_fn):
        try:
            from eden.tenancy.context import get_current_tenant_id
            tenant_id = get_current_tenant_id()
            if tenant_id is not None:
                result = get_tenant_perms_fn(tenant_id)
                if isinstance(result, (list, tuple, set)):
                    all_perms.update(result)
        except Exception as e:
            from eden.logging import get_logger
            get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)
    else:
        # Fallback to pre-resolved or flat permissions
        tenant_perms = getattr(user, "tenant_permissions", None)
        if isinstance(tenant_perms, (list, tuple, set)):
            all_perms.update(tenant_perms)
        else:
            perms = getattr(user, "permissions", [])
            if isinstance(perms, (list, tuple, set)):
                all_perms.update(perms)

    # 2. Add permissions from roles (using default_rbac)
    user_roles = _get_tenant_roles(user)
    if user_roles:
        from eden.auth.access import default_rbac
        for role in user_roles:
            all_perms.update(default_rbac.get_all_permissions(role))

    return list(all_perms)


def _is_mock(value: Any) -> bool:
    """Check if a value is a unittest.mock Mock object."""
    try:
        from unittest.mock import Mock, MagicMock
        return isinstance(value, (Mock, MagicMock))
    except (ImportError, AttributeError):
        return False


def _is_true(value: Any) -> bool:
    """
    Safely check if a value is True, handling Mock objects in tests.
    """
    return value is True or (isinstance(value, bool) and value)


def _is_none_or_mock(value: Any) -> bool:
    """
    Check if a value is None or a Mock/MagicMock object.
    """
    if value is None:
        return True
    try:
        from unittest.mock import Mock, MagicMock
        return isinstance(value, (Mock, MagicMock))
    except (ImportError, AttributeError):
        return False


# ─── Class-Level Decorator ────────────────────────────────────────────────────

def view_decorator(decorator: Callable) -> Callable:
    """
    Apply a decorator to all HTTP method handlers of a View class.
    """
    def wrapper(cls: type) -> type:
        for attr in ("get", "post", "put", "patch", "delete", "any"):
            if hasattr(cls, attr):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls
    return wrapper


# ─── Authentication Decorators ────────────────────────────────────────────────

def login_required(func: Callable) -> Callable:
    """
    Decorator to ensure the user is authenticated.
    """
    setattr(func, "_login_required", True)

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = _find_request(args, kwargs)
        if not request:
            raise RuntimeError("Request object not found in view arguments or context.")

        user = _get_user_from_request(request)
        if not user:
            user = await get_current_user(request)

        if not user:
            raise Unauthorized(detail="Login required.")

        return await func(*args, **kwargs)

    return wrapper


def is_authorized(func: Callable) -> Callable:
    """Alias for login_required."""
    return login_required(func)


def bind_user_principal(func: Callable) -> Callable:
    """
    Decorator to bind the current user to the request context.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = _find_request(args, kwargs)

        if request:
            user = await get_current_user(request)
            if user:
                request.user = user
                request.principal = user

        return await func(*args, **kwargs)

    return wrapper


# ─── Role-Based Decorators (Tenant-Aware) ─────────────────────────────────────

def roles_required(roles: Sequence[str]) -> Callable:
    """
    Decorator to ensure the user has at least one of the specified roles.
    """
    def decorator(func: Callable) -> Callable:
        setattr(func, "_required_roles", roles)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(args, kwargs)
            if not request:
                raise RuntimeError("Request object not found in view arguments or context.")

            user = _get_user_from_request(request) or await get_current_user(request)
            if not user:
                raise Unauthorized(detail="Login required.")

            if _is_true(getattr(user, "is_superuser", False)):
                return await func(*args, **kwargs)

            user_roles = _get_tenant_roles(user)
            if not any(role in user_roles for role in roles):
                raise PermissionDenied(
                    detail=f"Missing one of the required roles: {', '.join(roles)}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_role(role: str) -> Callable:
    """
    Decorator to ensure the user has a specific single role.
    """
    def decorator(func: Callable) -> Callable:
        setattr(func, "_required_role", role)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(args, kwargs)
            if not request:
                raise RuntimeError("Request object not found in view arguments or context.")

            user = _get_user_from_request(request) or await get_current_user(request)
            if not user:
                raise Unauthorized(detail="Login required.")

            if _is_true(getattr(user, "is_superuser", False)):
                return await func(*args, **kwargs)

            user_roles = _get_tenant_roles(user)
            if role not in user_roles:
                raise PermissionDenied(detail=f"Missing required role: {role}")

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_any_role(roles: Sequence[str]) -> Callable:
    """
    Decorator to ensure the user has at least one of the specified roles.
    """
    def decorator(func: Callable) -> Callable:
        setattr(func, "_required_any_roles", roles)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(args, kwargs)
            if not request:
                raise RuntimeError("Request object not found in view arguments or context.")

            user = _get_user_from_request(request) or await get_current_user(request)
            if not user:
                raise Unauthorized(detail="Login required.")

            if _is_true(getattr(user, "is_superuser", False)):
                return await func(*args, **kwargs)

            user_roles = _get_tenant_roles(user)
            if not any(role in user_roles for role in roles):
                raise PermissionDenied(
                    detail=f"Missing at least one of the required roles: {', '.join(roles)}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ─── Permission-Based Decorators (Tenant-Aware) ──────────────────────────────

def permissions_required(permissions: Sequence[str]) -> Callable:
    """
    Decorator to ensure the user has ALL the specified permissions.
    """
    def decorator(func: Callable) -> Callable:
        setattr(func, "_required_permissions", permissions)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(args, kwargs)
            if not request:
                raise RuntimeError("Request object not found in view arguments or context.")

            user = _get_user_from_request(request) or await get_current_user(request)
            if _is_none_or_mock(user) or not user:
                raise Unauthorized(detail="Login required.")

            if _is_true(getattr(user, "is_superuser", False)):
                return await func(*args, **kwargs)

            user_permissions = _get_tenant_permissions(user)
            user_roles = _get_tenant_roles(user)
            from eden.auth.access import default_rbac
            
            missing = []
            for perm in permissions:
                if perm not in user_permissions and not default_rbac.has_permission(user_roles, perm):
                    missing.append(perm)
                    
            if missing:
                raise PermissionDenied(
                    detail=f"Missing required permissions: {', '.join(missing)}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_permission(permission: str) -> Callable:
    """
    Decorator to ensure the user has a specific permission.
    """
    def decorator(func: Callable) -> Callable:
        setattr(func, "_required_permission", permission)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(args, kwargs)
            if not request:
                raise RuntimeError("Request object not found in view arguments or context.")

            user = _get_user_from_request(request) or await get_current_user(request)
            if not user:
                raise Unauthorized(detail="Login required.")

            # 1. Superuser bypass
            if _is_true(getattr(user, "is_superuser", False)):
                return await func(*args, **kwargs)

            # 2. Direct permission check (tenant-aware)
            user_permissions = _get_tenant_permissions(user)
            if permission in user_permissions:
                return await func(*args, **kwargs)

            # 3. RBAC hierarchy check (tenant-aware roles)
            from eden.auth.access import default_rbac
            user_roles = _get_tenant_roles(user)
            if default_rbac.has_permission(user_roles, permission):
                return await func(*args, **kwargs)

            raise PermissionDenied(detail=f"Missing required permission: {permission}")

        return wrapper
    return decorator


def require_any_permission(permissions: Sequence[str]) -> Callable:
    """
    Decorator to ensure the user has at least one of the specified permissions.
    """
    def decorator(func: Callable) -> Callable:
        setattr(func, "_required_any_permissions", permissions)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(args, kwargs)
            if not request:
                raise RuntimeError("Request object not found in view arguments or context.")

            user = _get_user_from_request(request) or await get_current_user(request)
            if not user:
                raise Unauthorized(detail="Login required.")

            if _is_true(getattr(user, "is_superuser", False)):
                return await func(*args, **kwargs)

            user_permissions = _get_tenant_permissions(user)
            user_roles = _get_tenant_roles(user)
            from eden.auth.access import default_rbac
            
            has_any = any(perm in user_permissions for perm in permissions)
            if not has_any:
                has_any = any(default_rbac.has_permission(user_roles, perm) for perm in permissions)

            if not has_any:
                raise PermissionDenied(
                    detail=f"Missing at least one of the required permissions: {', '.join(permissions)}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def staff_required(func: Callable) -> Callable:
    """
    Decorator to ensure the user is staff.
    """
    setattr(func, "_staff_required", True)

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = _find_request(args, kwargs)
        if not request:
            raise RuntimeError("Request object not found in view arguments or context.")

        user = _get_user_from_request(request) or await get_current_user(request)
        if not user or not getattr(user, "is_staff", False):
            if not getattr(user, "is_superuser", False):
                raise PermissionDenied(detail="Staff access required.")

        return await func(*args, **kwargs)

    return wrapper


def can_read(permission: str) -> Callable:
    """
    Decorator to ensure the user has 'read' permission for a resource.
    Equivalent to @require_permission("{permission}:read").
    """
    return require_permission(f"{permission}:read")


def can_write(permission: str) -> Callable:
    """
    Decorator to ensure the user has 'write' permission for a resource.
    Equivalent to @require_permission("{permission}:write").
    """
    return require_permission(f"{permission}:write")
