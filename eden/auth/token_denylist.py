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

# Global singleton for default usage
denylist = TokenDenylist()
