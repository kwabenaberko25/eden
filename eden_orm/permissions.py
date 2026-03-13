"""
Eden ORM - Permissions & Access Control

Row-level security and attribute-based access control.
"""

from typing import Optional, Any, Callable
import logging

logger = logging.getLogger(__name__)


class AccessControl:
    """
    Mixin for row-level access control.
    
    Usage:
        class Post(Model, AccessControl):
            owner_id: UUID
            is_published: bool
            
            async def user_can(self, user, action: str) -> bool:
                if action == "edit":
                    return self.owner_id == user.id or user.is_staff
                return True
    """
    
    async def user_can(self, user: Any, action: str) -> bool:
        """Check if user can perform action on this record."""
        return True
    
    @classmethod
    async def filter_for_user(cls, user: Any):
        """Filter records accessible by user."""
        return cls.filter()


class Permission:
    """Represents a permission rule."""
    
    def __init__(self, name: str, rule: Callable):
        self.name = name
        self.rule = rule
    
    async def check(self, user: Any, obj: Any) -> bool:
        """Check if permission is granted."""
        if callable(self.rule):
            return await self.rule(user, obj)
        return False


class Role:
    """Represents a user role."""
    
    def __init__(self, name: str, permissions: list = None):
        self.name = name
        self.permissions = permissions or []
