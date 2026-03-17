"""
Eden — Idempotency Support

Ensures that state-changing operations (like payments) are only executed once,
even if the request is retried.
"""

from __future__ import annotations

import json
import logging
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
    """
    def __init__(self, backend: DistributedBackend) -> None:
        self.backend = backend

    async def get_result(self, key: str) -> Optional[Any]:
        """Retrieve the result of a previously executed operation."""
        data = await self.backend.get(f"idempotency:{key}")
        if data:
            try:
                return json.loads(data)
            except Exception:
                return data
        return None

    async def save_result(self, key: str, result: Any, ttl_seconds: int = 86400) -> None:
        """Save the result of an operation for a given idempotency key."""
        if isinstance(result, (dict, list)):
            data = json.dumps(result)
        else:
            data = str(result)
            
        await self.backend.set(f"idempotency:{key}", data, ttl=ttl_seconds)

    async def acquire_lock(self, key: str, timeout: float = 30.0) -> bool:
        """
        Acquire a lock for an idempotency key to prevent concurrent execution.
        """
        # We reuse the distributed lock mechanism
        return await self.backend.acquire_lock(f"lock:idempotency:{key}", timeout=timeout)

    async def release_lock(self, key: str) -> None:
        """Release the lock for an idempotency key."""
        # Use a dummy identifier since we don't track it here (simple release)
        await self.backend.release_lock(f"lock:idempotency:{key}", "")

# Helper to be used in services
async def with_idempotency(
    manager: Optional[IdempotencyManager],
    key: Optional[str],
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any
) -> Any:
    """
    Wrap a function call with idempotency logic.
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
    if cached_result:
        return cached_result

    # 2. Acquire lock (prevent concurrent same-key requests)
    if not await m.acquire_lock(k):
        raise RuntimeError(f"Concurrent request with idempotency key '{k}' already in progress.")

    try:
        # Re-check cache after lock in case it finished while we waited
        final_cached = await m.get_result(k)
        if final_cached:
            return final_cached

        # 3. Execute function
        execution_result = await func(*args, **kwargs)

        # 4. Save result
        await m.save_result(k, execution_result)
        return execution_result
    finally:
        await m.release_lock(k)
