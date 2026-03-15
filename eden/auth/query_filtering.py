"""
Eden — Query-Level RBAC Enforcement

Provides utilities for automatically filtering queries based on user roles and permissions.
Integrates with the ORM QuerySet to apply security filters at the database level.

Usage:
    from eden.auth.query_filtering import apply_rbac_filter
    from eden.db import QuerySet
    
    # In a route handler with authenticated user
    posts_query = Post.select()
    posts_query = apply_rbac_filter(request.user, posts_query, "view_posts")
    posts = await posts_query.all()  # Only posts user has permission to view
"""

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from eden.auth.models import BaseUser
    from eden.db import QuerySet


def apply_rbac_filter(
    user: "BaseUser",
    query: "QuerySet",
    required_permission: str,
    field_name: str = "owner_id",
) -> "QuerySet":
    """
    Apply RBAC filtering to a QuerySet based on user permissions.
    
    By default, users can only see records they own (owner_id == user.id).
    Users with admin permission can see everything.
    
    Args:
        user: Authenticated user object
        query: QuerySet to filter
        required_permission: Permission name required to bypass owner filtering
        field_name: Field name on the model that stores the owner reference (default: "owner_id")
    
    Returns:
        Filtered QuerySet
    
    Example:
        # Only see posts you own (or you're admin)
        user_posts = apply_rbac_filter(request.user, Post.select(), "view_all_posts")
        posts = await user_posts.all()
    """
    user_permissions = getattr(user, "permissions", [])
    
    # Admin users can see everything
    if "admin" in user_permissions or required_permission in user_permissions:
        return query
    
    # Regular users see only their own records
    if hasattr(query._model_cls, field_name):
        return query.filter(**{field_name: user.id})
    
    # Fallback: no filtering if model doesn't have the owner field
    return query


def user_has_permission(user: "BaseUser", permission: str) -> bool:
    """
    Check if a user has a specific permission.
    
    Args:
        user: User object
        permission: Permission name (e.g., "delete_users")
    
    Returns:
        True if user has permission or is superuser
    
    Example:
        if user_has_permission(request.user, "delete_users"):
            await user.delete()
    """
    if getattr(user, "is_superuser", False):
        return True
    
    user_permissions = getattr(user, "permissions", [])
    return permission in user_permissions


def user_has_role(user: "BaseUser", role: str) -> bool:
    """
    Check if a user has a specific role.
    
    Args:
        user: User object
        role: Role name (e.g., "admin", "editor")
    
    Returns:
        True if user has role or is superuser
    
    Example:
        if user_has_role(request.user, "editor"):
            # User is an editor
    """
    if getattr(user, "is_superuser", False):
        return True
    
    user_roles = getattr(user, "roles", [])
    return role in user_roles


def user_has_any_permission(user: "BaseUser", *permissions: str) -> bool:
    """
    Check if a user has at least ONE of the specified permissions.
    
    Args:
        user: User object
        *permissions: Permission names
    
    Returns:
        True if user has any of the permissions or is superuser
    """
    if getattr(user, "is_superuser", False):
        return True
    
    user_permissions = getattr(user, "permissions", [])
    return any(perm in user_permissions for perm in permissions)


def user_has_any_role(user: "BaseUser", *roles: str) -> bool:
    """
    Check if a user has at least ONE of the specified roles.
    
    Args:
        user: User object
        *roles: Role names
    
    Returns:
        True if user has any of the roles or is superuser
    """
    if getattr(user, "is_superuser", False):
        return True
    
    user_roles = getattr(user, "roles", [])
    return any(role in user_roles for role in roles)
