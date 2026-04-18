"""
Eden — User Session Tracker

Tracks active sessions per user and enforces concurrent session limits.
Uses the cache backend (Redis or in-memory) for storage.

Usage:
    tracker = SessionTracker(max_sessions=3)
    await tracker.register(user_id, session_id)
    
    if await tracker.is_valid(user_id, session_id):
        # Session is active
        ...
"""

import datetime
import logging
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


class SessionTrackerStore(Protocol):
    """Interface for session tracking storage."""
    async def get_sessions(self, user_id: str) -> list[dict]:
        """Get all active sessions for a user."""
        ...
    
    async def add_session(self, user_id: str, session_id: str, metadata: dict) -> None:
        """Register a new session."""
        ...
    
    async def remove_session(self, user_id: str, session_id: str) -> None:
        """Remove a specific session."""
        ...
    
    async def remove_all_sessions(self, user_id: str) -> None:
        """Remove all sessions for a user."""
        ...


class InMemorySessionTrackerStore:
    """In-memory session tracker (single-process only)."""
    
    def __init__(self):
        self._store: dict[str, list[dict]] = {}
    
    async def get_sessions(self, user_id: str) -> list[dict]:
        return self._store.get(user_id, [])
    
    async def add_session(self, user_id: str, session_id: str, metadata: dict) -> None:
        if user_id not in self._store:
            self._store[user_id] = []
        self._store[user_id].append({"session_id": session_id, **metadata})
    
    async def remove_session(self, user_id: str, session_id: str) -> None:
        if user_id in self._store:
            self._store[user_id] = [
                s for s in self._store[user_id] if s["session_id"] != session_id
            ]
    
    async def remove_all_sessions(self, user_id: str) -> None:
        self._store.pop(user_id, None)


class SessionTracker:
    """
    Manages concurrent session limits per user.
    
    When max_sessions is exceeded, the oldest session is evicted (FIFO).
    Set max_sessions=0 for unlimited (default).
    """
    
    def __init__(
        self,
        max_sessions: int = 0,
        store: Optional[SessionTrackerStore] = None,
    ):
        self.max_sessions = max_sessions
        self.store = store or InMemorySessionTrackerStore()
    
    async def register(
        self,
        user_id: str,
        session_id: str,
        *,
        ip_address: str = "",
        user_agent: str = "",
    ) -> list[str]:
        """
        Register a new session. Returns list of evicted session IDs.
        
        Args:
            user_id: The user's ID.
            session_id: Unique session identifier.
            ip_address: Client IP for audit purposes.
            user_agent: Client user agent for display.
        
        Returns:
            List of session IDs that were evicted due to limit enforcement.
        """
        evicted = []
        
        if self.max_sessions > 0:
            sessions = await self.store.get_sessions(user_id)
            
            # Evict oldest sessions if at capacity
            while len(sessions) >= self.max_sessions:
                oldest = sessions.pop(0)
                await self.store.remove_session(user_id, oldest["session_id"])
                evicted.append(oldest["session_id"])
                logger.info(
                    "Evicted session %s for user %s (max_sessions=%d)",
                    oldest["session_id"], user_id, self.max_sessions,
                )
        
        await self.store.add_session(user_id, session_id, {
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        })
        
        return evicted
    
    async def is_valid(self, user_id: str, session_id: str) -> bool:
        """Check if a session is still active."""
        sessions = await self.store.get_sessions(user_id)
        return any(s["session_id"] == session_id for s in sessions)
    
    async def revoke_all(self, user_id: str) -> int:
        """
        Revoke all sessions for a user. Returns count of revoked sessions.
        Used for "Logout Everywhere" functionality.
        """
        sessions = await self.store.get_sessions(user_id)
        count = len(sessions)
        await self.store.remove_all_sessions(user_id)
        logger.info("Revoked all %d sessions for user %s", count, user_id)
        return count
