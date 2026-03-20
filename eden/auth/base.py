"""
Eden — Authentication Base

Defines the BaseUser model, AuthBackend interface, and core authentication dependencies.
"""

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, List, Optional, TypeVar

from eden.context import get_user
from eden.dependencies import Depends

if TYPE_CHECKING:
    from eden.requests import Request

U = TypeVar("U", bound="BaseUser")


class BaseUser:
    """
    Base class for user models.
    
    Extend this class in your application model:
    
    Example:
        class User(BaseUser):
            email: str
            password_hash: str
            is_active: bool = True
            is_staff: bool = False
            is_superuser: bool = False
            
            async def get_roles(self):
                return await self.roles.all()
    """
    
    id: Any  # Primary key (UUID or int)
    email: str
    password_hash: str
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    
    async def get_roles(self) -> List[str]:
        """Get all role names assigned to this user."""
        return []
    
    async def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        if self.is_superuser:
            return True
        return False
    
    async def has_role(self, role: str) -> bool:
        """Check if user belongs to a specific role."""
        if self.is_superuser and role == "superuser":
            return True
        roles = await self.get_roles()
        return role in roles
    
    def set_password(self, raw_password: str) -> None:
        """
        Set the user's password (hashes it automatically).
        Uses eden.auth.hashers.
        """
        from eden.auth.hashers import hash_password
        self.password_hash = hash_password(raw_password)
    
    def check_password(self, raw_password: str) -> bool:
        """
        Verify a password against the user's hash.
        Uses eden.auth.hashers.
        """
        from eden.auth.hashers import check_password
        return check_password(raw_password, self.password_hash)


class AuthBackend(ABC, Generic[U]):
    """
    Abstract base class for authentication backends.
    """

    @abstractmethod
    async def authenticate(self, request: "Request") -> U | None:
        """
        Authenticate the request and return the user if successful.
        """
        pass

    async def login(self, request: "Request", user: U) -> None:
        """
        Perform any necessary login actions (e.g. setting cookies, session data).
        """
        pass

    async def logout(self, request: "Request") -> None:
        """
        Perform any necessary logout actions.
        """
        pass


async def get_current_user(request: "Request") -> Optional[BaseUser]:
    """
    Dependency to get the current authenticated user.
    This is the primary way to access the user in view functions.
    """
    # 1. Check context (if middleware already ran)
    user = get_user()
    if user:
        return user

    # 2. If not in context, we check the request state (set by middleware)
    # Most backends will store the user in request.state.user
    return getattr(request.state, "user", None)


def current_user(required: bool = False) -> Any:
    """
    A helper to create a current_user dependency with optional requirement.

    Usage:
        @app.get("/profile")
        async def profile(user: User = Depends(current_user(required=True))):
            ...
    """
    from eden.exceptions import Unauthorized

    async def dependency(user: Optional[BaseUser] = Depends(get_current_user)) -> Optional[BaseUser]:
        if required and user is None:
            raise Unauthorized(detail="Authentication required.")
        return user

    return dependency
