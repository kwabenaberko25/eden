"""
Eden — API Key Authentication Backend

Authenticates requests using persistent API keys.
Reads from `Authorization: Bearer eden_...` or `X-API-Key` header.
"""

import datetime

from eden.auth.base import AuthBackend
from eden.auth.models import User
from eden.requests import Request


class APIKeyBackend(AuthBackend[User]):
    """
    API key authentication backend.

    Looks for an API key in the following locations:
    1. `Authorization: Bearer eden_...` header
    2. `X-API-Key: eden_...` header

    The raw key is hashed with SHA-256 and looked up in the `eden_api_keys` table.

    Usage:
        from eden.auth.backends.api_key import APIKeyBackend

        app = Eden()
        app.add_middleware("auth", backends=[
            APIKeyBackend(),
            SessionBackend(),
        ])
    """

    HEADER_NAME = "X-API-Key"
    BEARER_PREFIX = "eden_"

    def __init__(self, header_name: str = "X-API-Key"):
        self.header_name = header_name

    async def authenticate(self, request: Request) -> User | None:
        """
        Extract and verify the API key from request headers.
        """
        raw_key = self._extract_key(request)
        if not raw_key:
            return None

        # Get DB session from request state (set by DB middleware)
        session = getattr(request.state, "db", None)
        if not session:
            return None

        # Look up the key
        from eden.auth.api_key_model import APIKey

        api_key = await APIKey.find_by_raw_key(session, raw_key)
        if not api_key:
            return None

        # Update last_used_at
        from eden.auth.api_key_model import APIKey
        db = APIKey._get_db()
        async with db.transaction(session=session) as tx_session:
            api_key.last_used_at = datetime.datetime.now(datetime.UTC)
            await tx_session.flush()

        # Store scopes on request state for downstream use
        request.state.api_key_scopes = api_key.scopes

        # Fetch and return the user
        user = await User.get(session, api_key.user_id)
        return user

    def _extract_key(self, request: Request) -> str | None:
        """
        Extract the raw API key from the request headers.
        Checks both Authorization Bearer and X-API-Key.
        """
        # 1. Check Authorization: Bearer eden_...
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            if token.startswith(self.BEARER_PREFIX):
                return token

        # 2. Check X-API-Key header
        api_key_header = request.headers.get(self.header_name)
        if api_key_header and api_key_header.startswith(self.BEARER_PREFIX):
            return api_key_header

        return None
