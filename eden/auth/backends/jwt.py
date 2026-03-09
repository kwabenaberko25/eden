"""
Eden — JWT Authentication Backend
"""

import datetime
from typing import Any

import jwt

from eden.auth.base import AuthBackend
from eden.auth.models import User
from eden.requests import Request


class JWTBackend(AuthBackend[User]):
    """
    Stateless JWT authentication.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    async def authenticate(self, request: Request) -> User | None:
        """
        Extract and verify the JWT from the Authorization header.
        Expected format: `Authorization: Bearer <token>`
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]
        try:
            payload = self.decode_token(token)
            user_id = payload.get("sub")
            if not user_id:
                return None

            # Use the ORM to fetch the user
            # Note: We need a session, which is usually provided via Depends(get_db)
            # but here we are in a backend. We might need to handle session lifecycle.
            # For now, let's assume the user info could be in the payload or we fetch it.
            # Real-world apps might use a cache or a quick DB lookup.

            # Get session from request state if available (set by db middleware)
            session = getattr(request.state, "db", None)
            if not session:
                # If db middleware hasn't run or is missing, we might have to create one
                # but it's better to ensure db middleware runs before auth.
                return None

            return await User.get(session, user_id)

        except (jwt.PyJWTError, ValueError):
            return None

    def create_access_token(self, data: dict[str, Any]) -> str:
        """Create a new access token."""
        to_encode = data.copy()
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            minutes=self.access_token_expire_minutes
        )
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: dict[str, Any]) -> str:
        """Create a new refresh token."""
        to_encode = data.copy()
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            days=self.refresh_token_expire_days
        )
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and verify a JWT."""
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
