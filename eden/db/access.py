from typing import Any, Dict, Optional, Type, Union
from sqlalchemy import ColumnElement

class PermissionRule:
    """
    Base class for RBAC permission rules.
    """
    def resolve(self, model_cls: Type, user: Any) -> Union[bool, ColumnElement[bool]]:
        return False

    def check_instance(self, instance: Any, user: Any) -> bool:
        """Evaluate if the user has access to the specific instance."""
        return False

    @property
    def is_restrictive(self) -> bool:
        """True if the rule restricts access beyond simple authentication."""
        return True

class AllowPublic(PermissionRule):
    """Grants access to everyone, even unauthenticated users."""
    def resolve(self, model_cls, user):
        return True
    
    def check_instance(self, instance, user):
        return True

    @property
    def is_restrictive(self) -> bool:
        return False

class AllowAuthenticated(PermissionRule):
    """Grants access to all authenticated users."""
    def resolve(self, model_cls, user):
        return user is not None
    
    def check_instance(self, instance, user):
        return user is not None

    @property
    def is_restrictive(self) -> bool:
        return False

class AllowOwner(PermissionRule):
    """Grants access only if the user is the owner of the record."""
    def __init__(self, field: str = "user_id"):
        self.field = field
    
    def resolve(self, model_cls, user):
        if not user:
            return False
        return getattr(model_cls, self.field) == user.id

    def check_instance(self, instance, user):
        if not user:
            return False
        return getattr(instance, self.field) == user.id

class AllowRoles(PermissionRule):
    """Grants access if the user has any of the specified roles or their parents."""
    def __init__(self, *roles: str):
        self.roles = roles
    
    def _extract_role_names(self, user: Any) -> set[str]:
        """Deep resolution of user role names for RLS filtering."""
        if not hasattr(user, "roles"):
            return set()
            
        role_list = getattr(user, "roles", [])
        names = set()
        
        # Check relational Role objects
        visited = set()
        for r in role_list:
            if hasattr(r, "name"):
                names.add(r.name)
                if hasattr(r, "parents"):
                    names.update(self._traverse_parents(r, visited))
            else:
                # Fallback for simple string roles (JSON)
                names.add(str(r))
        
        # Also check roles_json if present (legacy fallback)
        if hasattr(user, "roles_json"):
            names.update(user.roles_json or [])
            
        return names

    def _traverse_parents(self, role: Any, visited: set) -> set[str]:
        """Synchronous traversal for RLS filter generation."""
        if not hasattr(role, "id") or role.id in visited:
            return set()
        visited.add(role.id)
        
        results = set()
        # We rely on 'selectin' loading for Role.parents
        for p in getattr(role, "parents", []):
            results.add(p.name)
            results.update(self._traverse_parents(p, visited))
        return results

    def resolve(self, model_cls, user):
        if not user:
            return False
        
        names = self._extract_role_names(user)
        return any(role in names for role in self.roles)

    def check_instance(self, instance, user):
        if not user:
            return False
        
        names = self._extract_role_names(user)
        return any(role in names for role in self.roles)

class AccessControl:
    """
    Mixin to enable Row-Level RBAC on a Model.
    """
    __rbac__: Dict[str, PermissionRule] = {}
    
    def __init_subclass__(cls, **kwargs):
        """Isolate RBAC state per model but inherit and merge from parents."""
        super().__init_subclass__(**kwargs)
        
        # Find the first parent that has __rbac__ (other than cls itself)
        parent_rbac = {}
        for base in cls.__mro__[1:]:
            if hasattr(base, "__rbac__"):
                parent_rbac = getattr(base, "__rbac__", {})
                break
        
        # If the class itself defined __rbac__ in its body, we should merge with parent's
        if "__rbac__" in cls.__dict__:
            # Merge: parent rules first, then class rules (overriding parents)
            merged = parent_rbac.copy()
            merged.update(cls.__dict__["__rbac__"])
            cls.__rbac__ = merged
        else:
            # Not defined in body, just copy from parent to ensure isolation
            cls.__rbac__ = parent_rbac.copy()

    @classmethod
    def get_security_filters(cls, user: Any, action: str = "read") -> Union[bool, ColumnElement[bool]]:
        """
        Resolve the security rule for the given action and user.
        Ensures that Global Framework Admins (Superusers) bypass all RBAC.
        """
        # Global Superuser Bypass
        if user and getattr(user, "is_superuser", False):
            return True

        rule = cls.__rbac__.get(action)
        if not rule:
            # If no rules are defined at all for this model, we allow access by default.
            # This ensures that basic models don't require boilerplate RBAC to function,
            # while still allowing explicit 'Deny' or 'Owner' rules to be enforced.
            if not cls.__rbac__:
                return True
            return False
        
        return rule.resolve(cls, user)
