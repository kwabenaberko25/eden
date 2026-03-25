"""
Eden — Authentication & Authorization Access Control

Unified engine for RBAC, hierarchical roles, and Row-Level Security (RLS) filters.
"""

import logging
from typing import Any, Dict, List, Optional, Protocol, Set, Type, Union

from sqlalchemy import ColumnElement

from eden.auth.base import BaseUser

logger = logging.getLogger(__name__)

# ============================================================================
# ROLE HIERARCHY (RBAC)
# ============================================================================

class RoleHierarchy:
    """
    Role-Based Access Control system supporting hierarchical roles.
    """
    def __init__(self):
        # Maps a role to its parents (roles it inherits FROM).
        self._hierarchy: Dict[str, Set[str]] = {}
        # Maps a role to its direct permissions
        self._permissions: Dict[str, Set[str]] = {}

    def add_role(self, role: str, parents: Optional[List[str]] = None) -> None:
        """Register a new role and its parents (roles it inherits permissions from)."""
        if role not in self._hierarchy:
            self._hierarchy[role] = set()
        
        if parents:
            for parent in parents:
                self._hierarchy[role].add(parent)
                
    def add_permission(self, role: str, permission: str) -> None:
        """Grant a specific permission to a role."""
        if role not in self._permissions:
            self._permissions[role] = set()
        self._permissions[role].add(permission)

    def get_all_parents(self, role: str) -> Set[str]:
        """Recursively get all roles that this role inherits from."""
        parents = set()
        to_check = [role]
        
        while to_check:
            current = to_check.pop()
            direct_parents = self._hierarchy.get(current, set())
            for parent in direct_parents:
                if parent not in parents:
                    parents.add(parent)
                    to_check.append(parent)
                    
        return parents

    def get_all_permissions(self, role: str) -> Set[str]:
        """Get all permissions for a role, including inherited ones."""
        permissions = set(self._permissions.get(role, set()))
        
        for parent in self.get_all_parents(role):
            permissions.update(self._permissions.get(parent, set()))
            
        return permissions

    def has_permission(self, user_roles: List[str], permission: str) -> bool:
        """Check if any of the given roles grant the specific permission."""
        for role in user_roles:
            if permission in self.get_all_permissions(role):
                return True
        return False

# Global instance for typical simple usage
default_rbac = RoleHierarchy()


# ============================================================================
# DATABASE ACCESS RULES (RLS)
# ============================================================================

class PermissionRule:
    """
    Base class for row-level permission rules.
    """
    def resolve(self, model_cls: Type, user: Any) -> Union[bool, ColumnElement[bool]]:
        return False

class AllowPublic(PermissionRule):
    """Grants access to everyone, even unauthenticated users."""
    def resolve(self, model_cls, user):
        return True

class AllowAuthenticated(PermissionRule):
    """Grants access to all authenticated users."""
    def resolve(self, model_cls, user):
        return user is not None

class AllowOwner(PermissionRule):
    """Grants access only if the user is the owner of the record."""
    def __init__(self, field: str = "user_id"):
        self.field = field
    def resolve(self, model_cls, user):
        if not user:
            return False
        return getattr(model_cls, self.field) == user.id

class AllowRoles(PermissionRule):
    """Grants access if the user has any of the specified roles or their parents."""
    def __init__(self, *roles: str):
        self.roles = roles

    def _extract_role_names(self, user: Any) -> set[str]:
        """Deep resolution of user role names including hierarchy."""
        if not hasattr(user, "roles"):
            return set()
            
        role_list = getattr(user, "roles", [])
        names = set()
        
        # Relational roles with hierarchy support
        visited = set()
        for r in role_list:
            if hasattr(r, "name"):
                names.add(r.name)
                # Recursively add parents if available (sync traversal)
                if hasattr(r, "parents"):
                    names.update(self._traverse_parents(r, visited))
            else:
                names.add(str(r))
        
        # Legacy fallback
        if hasattr(user, "roles_json"):
            names.update(user.roles_json or [])
            
        return names

    def _traverse_parents(self, role: Any, visited: set) -> set[str]:
        if not hasattr(role, "id") or role.id in visited:
            return set()
        visited.add(role.id)
        
        results = set()
        for p in getattr(role, "parents", []):
            results.add(p.name)
            results.update(self._traverse_parents(p, visited))
        return results

    def resolve(self, model_cls, user):
        if not user:
            return False
        user_role_names = self._extract_role_names(user)
        return any(role in user_role_names for role in self.roles)

class AccessControl:
    """
    Mixin to enable Row-Level RBAC on a Model.
    """
    __rbac__: Dict[str, PermissionRule] = {}

    @classmethod
    def get_security_filters(cls, user: Any, action: str = "read") -> Union[bool, ColumnElement[bool]]:
        """
        Resolve the security rule for the given action and user.
        """
        rule = cls.__rbac__.get(action)
        logger.debug(f"Resolving RBAC for {cls.__name__} ({action}): rule={rule}")
        if not rule:
            return False  # Deny by default
        
        return rule.resolve(cls, user)


# ============================================================================
# HIGH-LEVEL API
# ============================================================================

async def check_permission(
    user: Optional[BaseUser],
    resource: str,
    action: str,
) -> bool:
    """
    Check if user has permission for an action on a resource.
    """
    if not user:
        return False
    
    if user.is_superuser:
        return True
    
    permission_code = f"{resource}:{action}"
    return await user.has_permission(permission_code)


async def require_permission(
    user: Optional[BaseUser],
    resource: str,
    action: str,
) -> None:
    """
    Require a permission or raise PermissionError.
    """
    if not await check_permission(user, resource, action):
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=403, detail=f"Permission denied: {resource}:{action}")

class RoleManager:
    """
    Manages role and permission assignments.
    """
    
    @staticmethod
    async def assign_role(user: BaseUser, role_name: str) -> None:
        """Assign a role to a user."""
        # This is a stub that should be implemented by the user model or a service
        logger.info(f"Role {role_name} assigned to user {user.id}")
    
    @staticmethod
    async def revoke_role(user: BaseUser, role_name: str) -> None:
        """Revoke a role from a user."""
        logger.info(f"Role {role_name} revoked from user {user.id}")
