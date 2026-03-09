"""
Eden — Authentication Base

Defines the AuthBackend interface and core authentication dependencies.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar

from eden.context import get_user
from eden.dependencies import Depends

if TYPE_CHECKING:
    from eden.auth.models import BaseUser
    from eden.requests import Request

U = TypeVar("U", bound="BaseUser")

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

async def get_current_user(request: "Request") -> Optional["BaseUser"]:
    """
    Dependency to get the current authenticated user.
    This is the primary way to access the user in view functions.

    It checks if a user is already in the context, and if not,
    it could potentially trigger backends (though usually middleware handles this).
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

    async def dependency(user: Optional["BaseUser"] = Depends(get_current_user)) -> Optional["BaseUser"]:
        if required and user is None:
            raise Unauthorized(detail="Authentication required.")
        return user

    return dependency
