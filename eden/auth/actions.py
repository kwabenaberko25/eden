"""
Eden — Authentication Actions

Unified API for authentication, login, logout, and user creation.
"""

import logging
from typing import Any, Optional, Type, TYPE_CHECKING

from eden.auth.base import BaseUser
from eden.auth.hashers import hash_password, check_password

if TYPE_CHECKING:
    from eden.requests import Request

logger = logging.getLogger(__name__)


async def authenticate(
    email: str,
    password: str,
    user_model: Optional[Type[BaseUser]] = None,
) -> Optional[BaseUser]:
    """
    Authenticate a user by email and password.
    """
    if not email or not password:
        raise ValueError("Email and password required")
    
    # Auto-detect user model if not provided
    if user_model is None:
        from eden.db import get_models
        from eden.auth.models import User as DefaultUser
            
        models = get_models()
        
        # 1. Find the first model that extends BaseUser (excluding framework default)
        user_model = next(
            (m for m in models if issubclass(m, BaseUser) and m.__name__ != "User"),
            None
        )
        
        # 2. Fall back to framework's default User model
        if not user_model:
            user_model = DefaultUser
            
        if not user_model:
            raise ValueError(
                "No User model found. Ensure your User model inherits from "
                "eden.auth.BaseUser and is registered."
            )
    
    # Find user by email
    # Assuming the user model has a `.filter()` or similar from CrudMixin
    user = await user_model.filter(email=email.lower()).first()
    
    if not user or not user.is_active:
        logger.warning(f"Login failed for {email}: user not found or inactive")
        return None
    
    # Verify password using the unified hasher
    if not check_password(password, user.password_hash):
        logger.warning(f"Login failed for {email}: invalid password")
        return None
    
    logger.info(f"User {email} authenticated successfully")
    return user


async def login(request: "Request", user: BaseUser) -> None:
    """
    Log in a user by setting them on the request and in the session.
    """
    # 1. Set on request state
    request.state.user = user
    if hasattr(request, "user"):
        request.user = user

    # 2. Set in context
    from eden.context import set_user
    set_user(user)

    # 3. Persist in session
    if hasattr(request, "session"):
        from eden.auth.backends.session import SessionBackend
        request.session[SessionBackend.SESSION_KEY] = str(user.id)
    
    logger.info(f"User {user.email} logged in")


async def logout(request: "Request") -> None:
    """
    Log out the current user by clearing request state and session.
    """
    # 1. Clear request state
    if hasattr(request.state, "user"):
        request.state.user = None
    if hasattr(request, "user"):
        request.user = None

    # 2. Clear from context
    from eden.context import set_user
    set_user(None)

    # 3. Clear session
    if hasattr(request, "session"):
        from eden.auth.backends.session import SessionBackend
        request.session.pop(SessionBackend.SESSION_KEY, None)
    
    logger.info("User logged out")


async def create_user(
    email: str,
    password: str,
    **kwargs
) -> BaseUser:
    """
    Create a new user with email and password.
    """
    from eden.db import get_models
    from eden.validators import validate_email
    
    # Validate email
    result = validate_email(email)
    if not result:
        raise ValueError(f"Invalid email: {result.error}")
    
    email = result.value
    
    # Find user model
    models = get_models()
    user_model = next(
        (m for m in models if issubclass(m, BaseUser)),
        None
    )
    if not user_model:
        raise ValueError("No User model found. Define a model inheriting from BaseUser.")
    
    # Check email uniqueness
    existing = await user_model.filter(email=email).first()
    if existing:
        raise ValueError(f"Email {email} already in use")
    
    # Create user
    user = await user_model.objects.create(
        email=email,
        password_hash=hash_password(password),
        **kwargs
    )
    
    logger.info(f"User created: {email}")
    return user
