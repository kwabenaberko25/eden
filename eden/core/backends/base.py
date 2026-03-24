"""
Eden — Distributed Backend Base
"""

from __future__ import annotations

import abc
import asyncio
from typing import Any, Protocol, runtime_checkable

@runtime_checkable
class DistributedBackend(Protocol):
    """
    Protocol for distributed backends providing locking, pub/sub, and storage.
    """
    
    @abc.abstractmethod
    async def connect(self) -> None:
        """Establish connection to the backend."""
        ...

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Close the backend connection."""
        ...

    # -- Locking --
    @abc.abstractmethod
    async def acquire_lock(self, name: str, timeout: float = 10.0, identifier: str | None = None) -> bool:
        """
        Acquire a distributed lock.
        
        Args:
            name: Lock name
            timeout: Lock expiration in seconds
            identifier: Unique identifier for the lock holder
            
        Returns:
            True if acquired, False otherwise
        """
        ...

    @abc.abstractmethod
    async def release_lock(self, name: str, identifier: str) -> bool:
        """
        Release a distributed lock.
        
        Args:
            name: Lock name
            identifier: Unique identifier used during acquisition
            
        Returns:
            True if released, False if not held or expired
        """
        ...

    # -- Pub/Sub --
    @abc.abstractmethod
    async def publish(self, channel: str, message: Any) -> int:
        """
        Publish a message to a channel.
        
        Args:
            channel: Channel name
            message: Message payload (should be serializable)
            
        Returns:
            Number of subscribers who received the message
        """
        ...

    @abc.abstractmethod
    async def subscribe(self, channel: str, callback: asyncio.Future | Any) -> None:
        """
        Subscribe to a channel with a callback or listener.
        """
        ...

    # -- Storage --
    @abc.abstractmethod
    async def get(self, key: str) -> Any:
        """Retrieve a value from distributed storage."""
        ...

    @abc.abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in distributed storage."""
        ...

    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value from distributed storage."""
        ...

    @abc.abstractmethod
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a value in distributed storage."""
        ...
