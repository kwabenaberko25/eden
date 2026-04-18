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

# Pre-computed dummy hash for constant-time authentication flow.
# This ensures that authentication takes the same time whether or not
# the user exists, preventing timing-based user enumeration.
_DUMMY_HASH: str | None = None


def _perform_dummy_hash(password: str) -> None:
    """
    Perform a password hash check against a dummy value to ensure
    constant-time behavior regardless of user existence.
    """
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("eden-dummy-password-for-timing-safety")
    check_password(password, _DUMMY_HASH)


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
        
        .. warning::
            This method does NOT enforce rate limiting. Callers MUST apply
            rate limiting at the route level (e.g., ``@rate_limit("5/minute")``)
            to prevent brute-force attacks.
        
        Security:
            This method performs a constant-time flow regardless of whether the
            user exists, to prevent user enumeration via timing side-channels.
        """
        if not email or not password:
            raise ValueError("Email and password required")
        
        # Resolve user model
        user_model = self._get_user_model(user_model)
        
        # Find user by email using the session bound to this context
        user = await user_model.query(session=self.session).filter(email__iexact=email).first()
        
        if not user or not user.is_active:
            # SECURITY: Perform a dummy password hash to prevent timing-based
            # user enumeration. Without this, "user not found" returns faster
            # than "wrong password" (because Argon2 hashing is intentionally slow).
            _perform_dummy_hash(password)
            logger.warning("Login failed for %s: user not found or inactive", email)
            return None
        
        # Verify password
        if not check_password(password, user.password_hash):
            logger.warning("Login failed for %s: invalid password", email)
            return None
        
        logger.info("User %s authenticated successfully", email)
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


async def login(request: "Request", user: BaseUser, *, remember: bool = False) -> None:
    """
    Log in a user by setting them on the request and in the session.
    
    Args:
        request: The current request object.
        user: The authenticated user instance.
        remember: If True, extend session lifetime (default: 30 days).
                  If False, session expires when the browser closes.
    
    Security: The session ID is rotated after authentication to prevent
    session fixation attacks (where an attacker pre-sets a session ID
    before the user logs in).
    """
    import datetime
    
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
        
        # Store authentication timestamp for absolute expiry enforcement
        request.session["_auth_authenticated_at"] = datetime.datetime.now(
            datetime.UTC
        ).isoformat()
        
        # Store remember-me preference for session middleware to honor
        request.session["_auth_remember"] = remember
        
        # SECURITY: Rotate session ID to prevent session fixation attacks.
        # Copy existing session data into a new session with a fresh ID.
        if hasattr(request.session, "regenerate"):
            # If the session backend supports explicit regeneration
            await request.session.regenerate()
        else:
            # Starlette's SessionMiddleware stores data in a signed cookie,
            # so clearing and re-setting effectively rotates the session.
            # Copy current data, clear, then restore.
            session_data = dict(request.session)
            request.session.clear()
            request.session.update(session_data)
    
    logger.info("User %s logged in (remember=%s)", user.email, remember)
    
    # 4. Emit audit log
    from eden.auth.audit import auth_audit
    auth_audit.login_success(request, user)


async def logout(request: "Request", *, revoke_tokens: bool = True) -> None:
    """
    Log out the current user by clearing request state, session, and
    optionally revoking JWT tokens via the token denylist.

    Args:
        request: The current request object.
        revoke_tokens: If True, add the current access/refresh JWT tokens
                       to the denylist so they cannot be reused. Defaults to True.
    """
    # Get user before it's cleared for audit logging
    user_for_audit = getattr(request.state, "user", None) or getattr(request, "user", None)
    
    # 1. Revoke JWT tokens (MUST happen before clearing state)
    if revoke_tokens:
        from eden.auth.token_denylist import denylist
        import jwt as pyjwt

        # Attempt to revoke from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token_str = auth_header.split(" ", 1)[1]
            try:
                # Decode without verification to extract jti and exp
                payload = pyjwt.decode(token_str, options={"verify_signature": False})
                jti = payload.get("jti")
                exp = payload.get("exp")
                if jti and exp:
                    import datetime
                    dt_exp = datetime.datetime.fromtimestamp(exp, tz=datetime.UTC)
                    await denylist.revoke(jti, dt_exp)
                    logger.info("JWT access token revoked (jti=%s)", jti)
            except Exception as e:
                logger.warning("Failed to revoke JWT token on logout: %s", e)

        # Attempt to revoke from cookies (if JWTs stored as cookies)
        for cookie_name in ("access_token", "refresh_token"):
            cookie_val = request.cookies.get(cookie_name)
            if cookie_val:
                try:
                    payload = pyjwt.decode(cookie_val, options={"verify_signature": False})
                    jti = payload.get("jti")
                    exp = payload.get("exp")
                    if jti and exp:
                        import datetime
                        dt_exp = datetime.datetime.fromtimestamp(exp, tz=datetime.UTC)
                        await denylist.revoke(jti, dt_exp)
                        logger.info("JWT cookie '%s' revoked (jti=%s)", cookie_name, jti)
                except Exception as e:
                    logger.warning("Failed to revoke JWT cookie '%s': %s", cookie_name, e)

    # 2. Clear request state
    if hasattr(request.state, "user"):
        request.state.user = None
    if hasattr(request, "user"):
        request.user = None

    # 3. Clear from context
    from eden.context import set_user
    set_user(None)

    # 4. Clear session
    if "session" in request.scope:
        from eden.auth.backends.session import SessionBackend
        request.session.pop(SessionBackend.SESSION_KEY, None)
    
    logger.info("User logged out")
    
    # 5. Emit audit log
    from eden.auth.audit import auth_audit
    auth_audit.logout(request, user_for_audit)


async def logout_all(user: BaseUser) -> None:
    """
    Invalidate all active sessions and tokens for a user.
    
    This should be called after security-sensitive events like:
    - Password change
    - Account compromise detection
    - User-initiated "sign out everywhere"
    
    Args:
        user: The user whose sessions should be invalidated.
    """
    user_id = str(user.id)
    
    # 1. Revoke all JWT tokens by setting a user-level revocation timestamp
    from eden.auth.token_denylist import denylist
    import datetime
    await denylist.revoke_all_for_user(user_id, datetime.datetime.now(datetime.UTC))
    
    # 2. Revoke all tracked sessions (if session tracker is configured)
    try:
        from eden.auth.session_tracker import SessionTracker
        tracker = SessionTracker()  # Uses global default
        await tracker.revoke_all(user_id)
    except ImportError:
        pass
    
    logger.info("All sessions revoked for user %s", user.email)
    
    # 3. Emit audit log
    from eden.auth.audit import auth_audit
    auth_audit.logout_all(user)


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
