"""
Eden — Redis Distributed Backend
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None  # type: ignore[assignment]

from eden.core.backends.base import DistributedBackend

logger = logging.getLogger("eden.core.backends")

class RedisBackend(DistributedBackend):
    """
    Redis-based implementation of DistributedBackend.
    
    Provides:
    - Distributed locking via SET NX PX
    - Pub/Sub for cross-process communication
    - Key-value storage with TTL
    """
    
    def __init__(self, url: str = "redis://localhost:6379/0", prefix: str = "eden:", **kwargs: Any) -> None:
        if aioredis is None:
            raise ImportError("redis[async] is required for RedisBackend. Install it: pip install redis[async]")
            
        self.url = url
        self.prefix = prefix
        self.redis: aioredis.Redis | None = None
        self._pubsub: aioredis.PubSub | None = None
        self._subscriptions: Dict[str, Set[Callable]] = {}
        self._listener_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if not self.redis:
            self.redis = aioredis.from_url(self.url, decode_responses=False)
            logger.info(f"Connected to Redis distributed backend at {self.url}")

    async def disconnect(self) -> None:
        """Close Redis connection and stop listeners."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
            
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
            
        if self.redis:
            await self.redis.aclose()
            self.redis = None
            logger.info("Disconnected from Redis distributed backend")

    def _key(self, key: str) -> str:
        """Apply prefix to key."""
        return f"{self.prefix}{key}"

    # -- Locking --
    async def acquire_lock(self, name: str, timeout: float = 10.0, identifier: str | None = None) -> bool:
        """Acquire a lock using SET NX PX."""
        if not self.redis:
            await self.connect()
            
        identifier = identifier or str(uuid.uuid4())
        key = self._key(f"lock:{name}")
        # px = milliseconds
        px = int(timeout * 1000)
        
        result = await self.redis.set(key, identifier, px=px, nx=True)
        return bool(result)

    async def release_lock(self, name: str, identifier: str) -> bool:
        """Release a lock safely using Lua script."""
        if not self.redis:
            await self.connect()
            
        key = self._key(f"lock:{name}")
        
        # Lua script to ensure we only release our own lock
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self.redis.eval(script, 1, key, identifier)
        return bool(result)

    # -- Pub/Sub --
    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to Redis channel."""
        if not self.redis:
            await self.connect()
            
        full_channel = self._key(f"pubsub:{channel}")
        if not isinstance(message, (str, bytes)):
            payload = json.dumps(message).encode("utf-8")
        else:
            payload = message if isinstance(message, bytes) else message.encode("utf-8")
            
        return await self.redis.publish(full_channel, payload)

    async def subscribe(self, channel: str, callback: Callable) -> None:
        """Subscribe to a Redis channel."""
        if not self.redis:
            await self.connect()
            
        full_channel = self._key(f"pubsub:{channel}")
        
        if full_channel not in self._subscriptions:
            self._subscriptions[full_channel] = set()
            
        self._subscriptions[full_channel].add(callback)
        
        if not self._pubsub:
            self._pubsub = self.redis.pubsub()
            await self._pubsub.subscribe(full_channel)
            
            if not self._listener_task:
                self._listener_task = asyncio.create_task(self._listen_forever())
        else:
            await self._pubsub.subscribe(full_channel)

    async def _listen_forever(self) -> None:
        """Background task to listen for messages."""
        try:
            while self._pubsub:
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode("utf-8")
                        
                    data = message["data"]
                    # Try to parse JSON
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        pass
                        
                    callbacks = self._subscriptions.get(channel, set())
                    for cb in callbacks:
                        try:
                            if asyncio.iscoroutinefunction(cb):
                                await cb(data)
                            else:
                                cb(data)
                        except Exception as e:
                            logger.error(f"Error in pubsub callback: {e}")
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in pubsub listener: {e}")

    # -- Storage --
    async def get(self, key: str) -> Any:
        """Get value from Redis."""
        if not self.redis:
            await self.connect()
            
        raw = await self.redis.get(self._key(f"store:{key}"))
        if raw is None:
            return None
            
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in Redis with optional TTL."""
        if not self.redis:
            await self.connect()
            
        full_key = self._key(f"store:{key}")
        if isinstance(value, (dict, list, tuple)):
            payload = json.dumps(value)
        else:
            payload = value
            
        await self.redis.set(full_key, payload, ex=ttl)

    async def delete(self, key: str) -> None:
        """Delete value from Redis."""
        if not self.redis:
            await self.connect()
        await self.redis.delete(self._key(f"store:{key}"))
