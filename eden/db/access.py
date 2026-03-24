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
    """Grants access if the user has any of the specified roles."""
    def __init__(self, *roles: str):
        self.roles = roles
    
    def resolve(self, model_cls, user):
        if not user or not hasattr(user, "roles"):
            return False
        return any(role in user.roles for role in self.roles)

    def check_instance(self, instance, user):
        if not user or not hasattr(user, "roles"):
            return False
        return any(role in user.roles for role in self.roles)

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
        """
        rule = cls.__rbac__.get(action)
        if not rule:
            return False  # Deny by default if AccessControl is implemented but action is not defined
        
        return rule.resolve(cls, user)
