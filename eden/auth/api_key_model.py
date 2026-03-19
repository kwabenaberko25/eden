"""
Eden — API Key Model

Persistent, revocable API keys for programmatic access.
Keys are stored as SHA-256 hashes; the raw key is only shown once at creation.
"""

import datetime
import hashlib
import secrets
import uuid
from typing import Optional

from sqlalchemy import JSON
from sqlalchemy.orm import mapped_column

from eden.db import Model, f


class APIKey(Model):
    """
    Persistent API key for programmatic authentication.

    Usage:
        # Create a new key (returns instance + raw key)
        api_key, raw_key = await APIKey.generate(
            session, user=user, name="My CI Key", scopes=["read", "write"]
        )
        # raw_key is shown once: "eden_a1b2c3d4e5f6..."

        # Revoke a key by prefix
        await APIKey.revoke(session, prefix="a1b2c3d4")
    """

    __tablename__ = "eden_api_keys"

    # Human-readable label ("My CI Key", "GitHub Actions", etc.)
    name: str = f(max_length=255)

    # First 8 chars of the raw key, stored in cleartext for identification
    prefix: str = f(max_length=8, index=True)

    # SHA-256 hash of the full raw key
    key_hash: str = f(unique=True, index=True)

    # Owner
    user_id: uuid.UUID = f(foreign_key="eden_users.id")

    # Optional permission scopes (e.g., ["read", "write", "admin"])
    scopes: list[str] = mapped_column(JSON, default=list)

    # Optional expiry
    expires_at: datetime.datetime | None = f(nullable=True)

    # Tracking
    last_used_at: datetime.datetime | None = f(nullable=True)

    # Revocation flag
    is_active: bool = f(default=True)

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        """Check if this key has expired."""
        if self.expires_at is None:
            return False
        # SQLAlchemy DateTime by default is naive. Comparison must match.
        now = datetime.datetime.utcnow()
        return now >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if this key is active and not expired."""
        return self.is_active and not self.is_expired

    # ── Class Methods ─────────────────────────────────────────────────

    @classmethod
    async def generate(
        cls,
        session,
        user,
        name: str = "Default",
        scopes: list[str] | None = None,
        expires_in: datetime.timedelta | None = None,
    ) -> tuple["APIKey", str]:
        """
        Generate a new API key for a user.

        Returns:
            Tuple of (APIKey instance, raw key string).
            The raw key is only available at creation time.
        """
        # Generate a cryptographically secure random key
        raw_key = f"eden_{secrets.token_hex(32)}"
        prefix = raw_key[5:13]  # 8 chars after "eden_"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        expires_at = None
        if expires_in:
            expires_at = datetime.datetime.utcnow() + expires_in

        db = cls._get_db()
        async with db.transaction(session=session) as tx_session:
            api_key = cls(
                name=name,
                prefix=prefix,
                key_hash=key_hash,
                user_id=user.id,
                scopes=scopes or [],
                expires_at=expires_at,
            )

            tx_session.add(api_key)
            await tx_session.flush()
            await tx_session.refresh(api_key)

        return api_key, raw_key

    @classmethod
    async def revoke(cls, session, prefix: str) -> bool:
        """
        Revoke an API key by its prefix.

        Returns:
            True if a key was found and revoked, False otherwise.
        """
        from sqlalchemy import update

        db = cls._get_db()
        async with db.transaction(session=session) as tx_session:
            stmt = (
                update(cls)
                .where(cls.prefix == prefix, cls.is_active)
                .values(is_active=False)
            )
            result = await tx_session.execute(stmt)
            await tx_session.flush()
            return result.rowcount > 0

    @classmethod
    async def find_by_raw_key(cls, session, raw_key: str) -> Optional["APIKey"]:
        """
        Look up an API key by its raw key string.

        Returns:
            The APIKey instance if found and valid, None otherwise.
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        # Use QuerySet to handle session resolution and RBAC
        # We also filter for is_active and manually check expires_at
        api_key = await cls.query(session).filter(key_hash=key_hash, is_active=True).first()

        if api_key and api_key.is_expired:
            return None

        return api_key

    @classmethod
    async def list_for_user(cls, session, user_id: uuid.UUID) -> list["APIKey"]:
        """List all active API keys for a user."""
        from sqlalchemy import select

        stmt = (
            select(cls)
            .where(cls.user_id == user_id, cls.is_active)
            .order_by(cls.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def __repr__(self) -> str:
        return f"<APIKey(name='{self.name}', prefix='{self.prefix}', active={self.is_active})>"
