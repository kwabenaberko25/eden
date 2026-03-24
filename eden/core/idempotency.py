"""
Eden — Idempotency Support

Ensures that state-changing operations (like payments) are only executed once,
even if the request is retried.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional, TYPE_CHECKING, Callable
from datetime import timedelta

if TYPE_CHECKING:
    from eden.core.backends.base import DistributedBackend
    from typing_extensions import ParamSpec
    P = ParamSpec("P")

logger = logging.getLogger("eden.idempotency")


class IdempotencyManager:
    """
    Manages idempotency keys using the DistributedBackend.
    
    Features:
        - Result caching with configurable TTL (default 24h)
        - Distributed locking with unique identifiers per lock holder
        - Stale key cleanup support
        - Lock timeout recovery
    
    Example:
        >>> manager = IdempotencyManager(redis_backend, default_ttl=3600)
        >>> result = await with_idempotency(manager, "pay-123", process_payment, amount=50)
    """
    
    # Default TTL: 24 hours
    DEFAULT_TTL_SECONDS = 86400
    # Lock timeout: 30 seconds
    DEFAULT_LOCK_TIMEOUT = 30.0
    
    def __init__(
        self, 
        backend: DistributedBackend, 
        default_ttl: int = DEFAULT_TTL_SECONDS,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        self.backend = backend
        self.default_ttl = default_ttl
        self.lock_timeout = lock_timeout
        # Track lock identifiers for proper release
        self._lock_identifiers: dict[str, str] = {}

    async def get_result(self, key: str) -> Optional[Any]:
        """
        Retrieve the result of a previously executed operation.
        
        Args:
            key: The idempotency key to look up.
            
        Returns:
            The cached result, or None if no result is stored.
        """
        data = await self.backend.get(f"idempotency:{key}")
        if data:
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return data
        return None

    async def save_result(
        self, key: str, result: Any, ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Save the result of an operation for a given idempotency key.
        
        Args:
            key: The idempotency key.
            result: The result to cache. Must be JSON-serializable.
            ttl_seconds: Time-to-live in seconds. Defaults to self.default_ttl.
                After this time, the key is automatically cleaned up by the backend.
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        
        if isinstance(result, (dict, list)):
            data = json.dumps(result)
        else:
            data = json.dumps({"_value": result})
            
        await self.backend.set(f"idempotency:{key}", data, ttl=ttl)

    async def acquire_lock(self, key: str, timeout: Optional[float] = None) -> bool:
        """
        Acquire a lock for an idempotency key to prevent concurrent execution.
        
        Each lock acquisition generates a unique identifier, stored internally,
        so that only the holder can release it. This prevents accidental release
        by a different process or coroutine.
        
        Args:
            key: The idempotency key to lock.
            timeout: Lock expiration in seconds. Defaults to self.lock_timeout.
                If the lock holder crashes, it will auto-expire after this time.
        
        Returns:
            True if the lock was acquired, False if already held.
        """
        lock_timeout = timeout if timeout is not None else self.lock_timeout
        identifier = str(uuid.uuid4())
        lock_name = f"lock:idempotency:{key}"
        
        acquired = await self.backend.acquire_lock(
            lock_name, timeout=lock_timeout, identifier=identifier
        )
        
        if acquired:
            self._lock_identifiers[key] = identifier
            logger.debug(f"Lock acquired for key '{key}' with id '{identifier[:8]}...'")
        else:
            logger.debug(f"Failed to acquire lock for key '{key}'")
        
        return acquired

    async def release_lock(self, key: str) -> None:
        """
        Release the lock for an idempotency key.
        
        Uses the stored identifier from acquire_lock() to ensure only
        the holder can release the lock. If no identifier is found
        (e.g., after a crash/restart), the lock will auto-expire
        based on its timeout.
        
        Args:
            key: The idempotency key whose lock to release.
        """
        identifier = self._lock_identifiers.pop(key, None)
        if identifier is None:
            logger.warning(
                f"No lock identifier found for key '{key}'. "
                f"Lock may have already expired or been released."
            )
            return
        
        lock_name = f"lock:idempotency:{key}"
        released = await self.backend.release_lock(lock_name, identifier)
        
        if released:
            logger.debug(f"Lock released for key '{key}'")
        else:
            logger.warning(
                f"Lock release failed for key '{key}'. "
                f"Lock may have expired before release."
            )

    async def delete_key(self, key: str) -> None:
        """
        Delete a stored idempotency result, allowing re-execution.
        
        Args:
            key: The idempotency key to remove.
        """
        await self.backend.delete(f"idempotency:{key}")
        logger.debug(f"Deleted idempotency key '{key}'")

    async def has_result(self, key: str) -> bool:
        """
        Check if a result exists for the given idempotency key.
        
        Args:
            key: The idempotency key.
            
        Returns:
            True if a cached result exists.
        """
        return await self.get_result(key) is not None


# Helper to be used in services
async def with_idempotency(
    manager: Optional[IdempotencyManager],
    key: Optional[str],
    func: Callable[..., Any],
    *args: Any,
    ttl_seconds: Optional[int] = None,
    **kwargs: Any
) -> Any:
    """
    Wrap a function call with idempotency logic.
    
    If a result already exists for the key, return it immediately.
    Otherwise, acquire a lock, execute the function, cache the result,
    and release the lock.
    
    Args:
        manager: The IdempotencyManager instance. If None, executes directly.
        key: The idempotency key. If None, executes directly.
        func: The async function to execute.
        *args: Positional arguments for the function.
        ttl_seconds: Optional TTL override for result caching.
        **kwargs: Keyword arguments for the function.
        
    Returns:
        The function result (cached or freshly executed).
        
    Raises:
        RuntimeError: If a concurrent request with the same key is in progress.
    
    Example:
        >>> result = await with_idempotency(
        ...     manager, "payment-abc-123",
        ...     process_payment, amount=100, currency="USD"
        ... )
    """
    if not key or not manager:
        return await func(*args, **kwargs)
    
    # Assert for type narrowing
    assert isinstance(manager, IdempotencyManager)
    assert isinstance(key, str)
    
    m = manager
    k = key

    # 1. Check for existing result
    cached_result = await m.get_result(k)
    if cached_result is not None:
        logger.info(f"Idempotency cache hit for key '{k}'")
        return cached_result

    # 2. Acquire lock (prevent concurrent same-key requests)
    if not await m.acquire_lock(k):
        raise RuntimeError(
            f"Concurrent request with idempotency key '{k}' already in progress. "
            f"The lock will auto-expire after {m.lock_timeout}s if the holder crashes."
        )

    try:
        # Re-check cache after lock in case it finished while we waited
        final_cached = await m.get_result(k)
        if final_cached is not None:
            logger.info(f"Idempotency cache hit (post-lock) for key '{k}'")
            return final_cached

        # 3. Execute function
        execution_result = await func(*args, **kwargs)

        # 4. Save result with TTL
        await m.save_result(k, execution_result, ttl_seconds=ttl_seconds)
        return execution_result
    finally:
        await m.release_lock(k)
