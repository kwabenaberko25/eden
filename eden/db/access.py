from typing import Any, Dict, Optional, Type, Union
from sqlalchemy import ColumnElement

class PermissionRule:
    """
    Base class for RBAC permission rules.
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
        # Return a boolean or a SQL expression
        return getattr(model_cls, self.field) == user.id

class AllowRoles(PermissionRule):
    """Grants access if the user has any of the specified roles."""
    def __init__(self, *roles: str):
        self.roles = roles
    def resolve(self, model_cls, user):
        if not user or not hasattr(user, "roles"):
            return False
        return any(role in user.roles for role in self.roles)

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
        if not rule:
            return False  # Deny by default if AccessControl is implemented but action is not defined
        
        return rule.resolve(cls, user)
