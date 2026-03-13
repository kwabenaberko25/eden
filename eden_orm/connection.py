"""
Eden ORM - Connection Pool Management

Handles asyncpg connection pooling, session management, and transaction lifecycle.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
import logging
from uuid import UUID

# Optional asyncpg import for better error messages
try:
    import asyncpg
except ImportError:
    asyncpg = None

logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    Manages asyncpg connection pool for PostgreSQL.
    
    Features:
    - Auto-creates pool on demand
    - Connection health checks (pre-ping)
    - Automatic cleanup
    - Transaction management
    """
    
    def __init__(
        self,
        dsn: str,
        min_size: int = 5,
        max_size: int = 20,
        timeout: float = 10.0,
        echo: bool = False,
    ):
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self.echo = echo
        self.pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        async with self._lock:
            if self.pool is not None:
                return
            
            try:
                self.pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    timeout=self.timeout,
                    command_timeout=self.timeout,
                )
                logger.info(
                    f"Connection pool initialized: {self.min_size}-{self.max_size} "
                    f"connections"
                )
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                raise
    
    async def close(self) -> None:
        """Close all connections in the pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Connection pool closed")
    
    async def get_connection(self) -> asyncpg.Connection:
        """Get a connection from the pool."""
        if not self.pool:
            await self.initialize()
        
        conn = await self.pool.acquire()
        
        # Pre-ping: verify connection is alive
        try:
            await conn.fetchval("SELECT 1")
        except Exception as e:
            await self.pool.release(conn, broken=True)
            logger.warning(f"Connection health check failed: {e}, retrying...")
            return await self.get_connection()
        
        return conn
    
    @asynccontextmanager
    async def connection(self):
        """Context manager for connection borrowing."""
        if not self.pool:
            await self.initialize()
        
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for transaction handling."""
        if not self.pool:
            await self.initialize()
        
        conn = await self.pool.acquire()
        try:
            async with conn.transaction():
                yield conn
        finally:
            await self.pool.release(conn)
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool statistics."""
        if not self.pool:
            return {"status": "not_initialized"}
        
        return {
            "size": self.pool.get_size(),
            "available": self.pool.get_idle_size(),
            "min_size": self.min_size,
            "max_size": self.max_size,
        }


class Session:
    """
    Database session for executing queries.
    
    Wraps a connection and provides query execution methods.
    Supports async context manager for automatic connection release.
    """
    
    def __init__(self, connection: asyncpg.Connection, pool: ConnectionPool):
        self.connection = connection
        self.pool = pool
        self._in_transaction = False
    
    async def __aenter__(self):
        """Enter async context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager and release connection."""
        # Rollback transaction if error occurred
        if exc_type is not None and self._in_transaction:
            await self.rollback()
        
        # Release connection back to pool
        await self.pool.pool.release(self.connection)
        return False
    
    async def execute(self, query: str, *args) -> None:
        """Execute a query without returning results (INSERT, UPDATE, DELETE)."""
        if self.pool.echo:
            logger.debug(f"EXECUTE: {query} | Args: {args}")
        
        await self.connection.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> list:
        """Fetch multiple rows."""
        if self.pool.echo:
            logger.debug(f"FETCH: {query} | Args: {args}")
        
        return await self.connection.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict]:
        """Fetch a single row."""
        if self.pool.echo:
            logger.debug(f"FETCHROW: {query} | Args: {args}")
        
        return await self.connection.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single scalar value."""
        if self.pool.echo:
            logger.debug(f"FETCHVAL: {query} | Args: {args}")
        
        return await self.connection.fetchval(query, *args)
    
    async def begin(self) -> None:
        """Begin a transaction."""
        await self.connection.execute("BEGIN")
        self._in_transaction = True
    
    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._in_transaction:
            await self.connection.execute("COMMIT")
            self._in_transaction = False
    
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._in_transaction:
            await self.connection.execute("ROLLBACK")
            self._in_transaction = False


# Global connection pool instance
_pool: Optional[ConnectionPool] = None


async def initialize(dsn: str, min_size: int = 5, max_size: int = 20) -> None:
    """Initialize the global connection pool."""
    global _pool
    _pool = ConnectionPool(dsn, min_size=min_size, max_size=max_size)
    await _pool.initialize()


async def close() -> None:
    """Close the global connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_session() -> Session:
    """Get a new database session."""
    global _pool
    if not _pool:
        raise RuntimeError("Connection pool not initialized. Call initialize() first.")
    
    conn = await _pool.get_connection()
    return Session(conn, _pool)


def get_pool() -> ConnectionPool:
    """Get the global connection pool."""
    global _pool
    if not _pool:
        raise RuntimeError("Connection pool not initialized. Call initialize() first.")
    return _pool
