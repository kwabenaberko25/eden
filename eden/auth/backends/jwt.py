"""
Eden — JWT Authentication Backend
"""

import datetime
import uuid
from typing import Any

import jwt

from eden.auth.base import AuthBackend
from eden.auth.models import User
from eden.auth.token_denylist import denylist
from eden.requests import Request


class JWTBackend(AuthBackend[User]):
    """
    Stateless JWT authentication.

    Usage::

        from eden.auth.providers import JWTProvider

        provider = JWTProvider(secret="top-secret", algorithm="HS256")

        # Create a token
        token = provider.encode({"sub": user.id, "scope": "admin"}, expires_in=3600)

        # Verify a token
        payload = provider.decode(token)
    """

    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        *,
        secret: str | None = None,
    ):
        # Support both 'secret_key' and 'secret' param names for convenience
        resolved_key = secret_key or secret
        if not resolved_key:
            raise ValueError("Either 'secret_key' or 'secret' must be provided.")
        self.secret_key = resolved_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    async def authenticate(self, request: Request) -> User | None:
        """
        Extract and verify the JWT from the Authorization header or cookies.
        """
        token = None

        # 1. Try Authorization header (standard API approach)
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token_parts = auth_header.split()
            if len(token_parts) >= 2 and token_parts[0].lower() == "bearer":
                token = token_parts[1]

        # 2. Try cookies (browser/SPA approach)
        if not token:
            token = request.cookies.get("access_token")

        if not token:
            return None
        try:
            payload = self.decode_token(token)
            user_id = payload.get("sub")
            jti = payload.get("jti")
            if not user_id or not jti:
                return None

            # Check if token is revoked
            is_revoked = await denylist.is_revoked(jti)
            if is_revoked:
                return None

            # Use the ORM to fetch the user
            # Note: We need a session, which is usually provided via Depends(get_db)
            # but here we are in a backend. We might need to handle session lifecycle.
            # For now, let's assume the user info could be in the payload or we fetch it.
            # Real-world apps might use a cache or a quick DB lookup.

            # Special handling for EdenTestClient mock users
            if payload.get("test") is True:
                return User(
                    id=payload.get("sub"),
                    email=payload.get("email"),
                    is_staff=payload.get("is_staff", False),
                    is_superuser=payload.get("is_superuser", False)
                )

            # Get session from request state if available (set by db middleware)
            # Fall back to app-level database
            session = getattr(request.state, "db", None) or getattr(request.app.state, "db", None)
            
            return await User.get(id=user_id, session=session)

        except (jwt.PyJWTError, ValueError):
            return None

    def create_access_token(self, data: dict[str, Any]) -> str:
        """Create a new access token."""
        to_encode = data.copy()
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            minutes=self.access_token_expire_minutes
        )
        to_encode.update({"exp": expire, "type": "access", "jti": str(uuid.uuid4())})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: dict[str, Any]) -> str:
        """Create a new refresh token."""
        to_encode = data.copy()
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            days=self.refresh_token_expire_days
        )
        to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid.uuid4())})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and verify a JWT."""
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

    async def revoke_token(self, token: str) -> None:
        """Revoke a token by adding its jti to the denylist."""
        try:
            payload = self.decode_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                dt_exp = datetime.datetime.fromtimestamp(exp, tz=datetime.UTC)
                await denylist.revoke(jti, dt_exp)
        except (jwt.PyJWTError, ValueError):
            pass

    # ── Documented Aliases ────────────────────────────────────────────────

    def encode(
        self,
        data: dict[str, Any],
        expires_in: int | None = None,
        token_type: str = "access",
    ) -> str:
        """
        Encode a payload into a JWT.

        This is the documented convenience method. Use ``create_access_token``
        or ``create_refresh_token`` if you prefer explicit control.

        Args:
            data: Payload dictionary (must contain ``sub``).
            expires_in: Override expiry in seconds. Defaults to
                ``access_token_expire_minutes * 60``.
            token_type: ``"access"`` or ``"refresh"``.

        Returns:
            Encoded JWT string.
        """
        to_encode = data.copy()
        if expires_in is not None:
            expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
                seconds=expires_in
            )
        elif token_type == "refresh":
            expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
                days=self.refresh_token_expire_days
            )
        else:
            expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
                minutes=self.access_token_expire_minutes
            )
        to_encode.update({"exp": expire, "type": token_type})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode(self, token: str) -> dict[str, Any]:
        """
        Decode and verify a JWT.

        Alias for ``decode_token``. This is the documented convenience method.
        """
        return self.decode_token(token)
