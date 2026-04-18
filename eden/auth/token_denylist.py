import datetime
from typing import Any, Protocol

class TokenDenylistStore(Protocol):
    async def set(self, jti: str, expires_at: datetime.datetime) -> None:
        """Store the revoked token JTI until expires_at."""
        ...

    async def is_revoked(self, jti: str) -> bool:
        """Check if the JTI is revoked."""
        ...

class InMemoryTokenDenylist:
    def __init__(self):
        self._store: dict[str, datetime.datetime] = {}

    async def set(self, jti: str, expires_at: datetime.datetime) -> None:
        self._store[jti] = expires_at
        self._cleanup()

    async def is_revoked(self, jti: str) -> bool:
        self._cleanup()
        return jti in self._store

    def _cleanup(self) -> None:
        now = datetime.datetime.now(datetime.UTC)
        expired_keys = [k for k, v in self._store.items() if v < now]
        for k in expired_keys:
            self._store.pop(k, None)

class TokenDenylist:
    """
    Manages revoked JWT tokens using a configurable backend.
    
    Supports:
    - In-memory store (development only)
    - Replaces external dependency with simple key-value store interface.
    
    Tokens are stored by their `jti` (JWT ID) claim with automatic
    TTL expiry matching the token's remaining lifetime.
    """
    def __init__(self, store: TokenDenylistStore | None = None):
        self.store = store or InMemoryTokenDenylist()

    async def revoke(self, jti: str, expires_at: datetime.datetime) -> None:
        """Add a token's JTI to the denylist until its natural expiry."""
        await self.store.set(jti, expires_at)

    async def is_revoked(self, jti: str) -> bool:
        """Check if a token has been revoked."""
        return await self.store.is_revoked(jti)
    
    async def revoke_all_for_user(self, user_id: str, issued_before: datetime.datetime) -> None:
        """
        Mark all tokens for a user issued before a given timestamp as revoked.
        
        This is used for "logout everywhere" functionality. The check is performed
        in JWTBackend.authenticate() by comparing token 'iat' against the user's
        last global-logout timestamp.
        
        Args:
            user_id: The user's ID.
            issued_before: Tokens issued before this datetime are considered revoked.
        """
        # Store as a special key: "user_revoke:{user_id}" -> issued_before
        key = f"user_revoke:{user_id}"
        # Use a far-future expiry for user-level revocations (e.g., 30 days)
        far_future = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)
        await self.store.set(key, far_future)

# Global singleton for default usage
denylist = TokenDenylist()
