"""
Eden — Authentication Actions

Unified API for authentication, login, logout, and user creation.
"""

import logging
from typing import Any, Optional, Type, TYPE_CHECKING

from eden.auth.base import BaseUser
from eden.auth.hashers import hash_password, check_password
from eden.db.context import BaseManager

if TYPE_CHECKING:
    from eden.requests import Request
    from eden.db.context import EdenDbContext

logger = logging.getLogger(__name__)


class AuthActions(BaseManager):
    """
    Manager for Authentication and User lifecycle.
    
    This class is auto-registered to EdenDbContext as 'auth'.
    """
    manager_name = "auth"

    async def authenticate(
        self,
        email: str,
        password: str,
        user_model: Optional[Type[BaseUser]] = None,
    ) -> Optional[BaseUser]:
        """
        Authenticate a user by email and password using the context session.
        """
        if not email or not password:
            raise ValueError("Email and password required")
        
        # Resolve user model
        user_model = self._get_user_model(user_model)
        
        # Find user by email using the session bound to this context
        user = await user_model.query(session=self.session).filter(email__iexact=email).first()
        
        if not user or not user.is_active:
            logger.warning(f"Login failed for {email}: user not found or inactive")
            return None
        
        # Verify password
        if not check_password(password, user.password_hash):
            logger.warning(f"Login failed for {email}: invalid password")
            return None
        
        logger.info(f"User {email} authenticated successfully")
        return user

    async def create_user(
        self,
        email: str,
        password: str,
        **kwargs
    ) -> BaseUser:
        """
        Create a new user with email and password using the context session.
        """
        from eden.validators import validate_email
        
        # Validate email
        result = validate_email(email)
        if not result:
            raise ValueError(f"Invalid email: {result.error}")
        
        email = result.value
        user_model = self._get_user_model()
        
        # Check email uniqueness via the context session
        existing = await user_model.query(session=self.session).filter(email=email.lower()).first()
        if existing:
            raise ValueError(f"Email {email} already in use")
        
        # Create user via CrudMixin API, explicitly passing the session
        user = await user_model.create(
            session=self.session,
            email=email.lower(),
            password_hash=hash_password(password),
            **kwargs
        )
        
        logger.info(f"User created: {email}")
        return user

    def _get_user_model(self, provided: Optional[Type[BaseUser]] = None) -> Type[BaseUser]:
        if provided:
            return provided
            
        from eden.db import get_models
        from eden.auth.models import User as DefaultUser
        
        models = get_models()
        user_model = next(
            (m for m in models if issubclass(m, BaseUser) and m.__name__ != "User"),
            None
        )
        return user_model or DefaultUser


async def authenticate(
    email: str,
    password: str,
    user_model: Optional[Type[BaseUser]] = None,
) -> Optional[BaseUser]:
    """
    Authenticate a user by email and password.
    
    Deprecated: Use ctx.auth.authenticate() instead.
    """
    from eden.db import get_db
    from eden.context import get_request
    
    # Try to resolve context from the current request
    req = get_request()
    if req and hasattr(req, "ctx"):
        return await req.ctx.auth.authenticate(email, password, user_model=user_model)
    
    # Fallback to magic context discovery
    db = get_db()
    async with db.context() as ctx:
        return await ctx.auth.authenticate(email, password, user_model=user_model)


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
    if "session" in request.scope:
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
    if "session" in request.scope:
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
    
    Deprecated: Use ctx.auth.create_user() instead.
    """
    from eden.db import get_db
    from eden.context import get_request
    
    # Try to resolve context from the current request
    req = get_request()
    if req and hasattr(req, "ctx"):
        return await req.ctx.auth.create_user(email, password, **kwargs)
    
    # Fallback to magic context discovery (if in a request)
    db = get_db()
    async with db.context() as ctx:
        return await ctx.auth.create_user(email, password, **kwargs)
