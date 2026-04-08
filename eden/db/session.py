import asyncio
import contextlib
import contextvars
import logging
from collections import OrderedDict
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from typing import (
    TYPE_CHECKING,
    Any,
    cast,
)

if TYPE_CHECKING:
    from starlette.requests import Request
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool, Pool
logger = logging.getLogger("eden.db")

@event.listens_for(Pool, "reset")
def _reset_postgres_search_path(dbapi_connection, connection_record, reset_state):
    """
    Harden schema boundaries. Whenever a connection is returned to the pool (reset),
    forcefully reset the PostgreSQL search_path to public to prevent connection leakage.
    We safely catch exceptions and ignore non-PostgreSQL drivers.
    """
    try:
        # DBAPI objects like asyncpg Connection or psycopg have `execute` or `cursor().execute()`
        # Not all standard DBAPIs implement this exactly the same, but `search_path` is Postgres-only
        if hasattr(dbapi_connection, "cursor"):  # psycopg2/sync or similar
            cursor = dbapi_connection.cursor()
            cursor.execute('SET search_path TO "public"')
            cursor.close()
        elif hasattr(dbapi_connection, "execute"):  # asyncpg sync fallback wrapper
            dbapi_connection.execute('SET search_path TO "public"')
    except Exception:
        pass

# Context variable for per-request session storage (async-safe)
_session_context: contextvars.ContextVar[AsyncSession | None] = contextvars.ContextVar(
    "db_session", default=None
)

class DatabaseError(Exception):
    """Base exception for all Eden database errors."""
    pass

class SessionResolutionError(DatabaseError):
    """Raised when a database session cannot be resolved for a query."""


class SecurityIsolationError(DatabaseError):
    """
    Raised when a database operation is attempted without a resolved tenant context.

    This is a fail-closed guard: if tenant isolation is enforced and no tenant
    has been set in the current execution context, operations are rejected rather
    than silently proceeding against a default/public schema.

    Common causes:
        - Background task spawned without ``spawn_safe_task()``
        - Request reached a handler before ``TenantMiddleware`` executed
        - Missing tenant context in CLI/script environments

    Resolution:
        - Use ``spawn_safe_task(coro)`` for background tasks to propagate context
        - Ensure ``TenantMiddleware`` is installed in the middleware stack
        - Add the route to ``exempt_paths`` if it genuinely doesn't need tenancy
    """
    pass

class TransactionRequiredError(DatabaseError):
    """Raised when an operation requires an active transaction context."""
    pass


class EdenAsyncSession(AsyncSession):
    """
    Standard SQLAlchemy AsyncSession enhanced with concurrency safety.
    
    AsyncSession is not thread-safe or task-safe for concurrent calls.
    If multiple async tasks share a session (common in Eden's request context),
    this class ensures they execute sequentially rather than raising IllegalStateError.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._eden_lock = asyncio.Lock()

    async def execute(self, *args, **kwargs):
        async with self._eden_lock:
            return await super().execute(*args, **kwargs)

    async def commit(self, *args, **kwargs):
        async with self._eden_lock:
            return await super().commit(*args, **kwargs)

    async def rollback(self, *args, **kwargs):
        async with self._eden_lock:
            return await super().rollback(*args, **kwargs)

    async def flush(self, *args, **kwargs):
        async with self._eden_lock:
            return await super().flush(*args, **kwargs)

    async def refresh(self, *args, **kwargs):
        async with self._eden_lock:
            return await super().refresh(*args, **kwargs)

    async def scalar(self, *args, **kwargs):
        async with self._eden_lock:
            return await super().scalar(*args, **kwargs)

    async def scalars(self, *args, **kwargs):
        async with self._eden_lock:
            return await super().scalars(*args, **kwargs)

    async def stream(self, *args, **kwargs):
        async with self._eden_lock:
            return await super().stream(*args, **kwargs)


class Database:
    """
    Database manager for Eden applications.
    Wraps SQLAlchemy 2.0 Async Engine and Session management.
    """

    def __init__(self, url: str, **kwargs: Any) -> None:
        self.url = url
        # SQLite connection optimization
        if url.startswith("sqlite"):
            if ":memory:" in url:
                kwargs.setdefault("poolclass", StaticPool)

            # File or memory SQLite via async needs check_same_thread=False
            if "connect_args" not in kwargs:
                kwargs["connect_args"] = {}
            kwargs["connect_args"].setdefault("check_same_thread", False)

        # Set safe defaults for connection pooling when not explicitly provided.
        # This helps prevent resource exhaustion in production.
        poolclass = kwargs.get("poolclass")
        if poolclass not in (StaticPool, NullPool):
            kwargs.setdefault("pool_size", 10)
            kwargs.setdefault("max_overflow", 20)
            kwargs.setdefault("pool_recycle", 3600)

        kwargs.setdefault("pool_pre_ping", True)
        kwargs.setdefault("echo", False)

        self.engine = create_async_engine(url, **kwargs)
        self.session_factory = async_sessionmaker(
            self.engine, class_=EdenAsyncSession, expire_on_commit=False
        )
        self._connected = False
        # Bound the number of distinct isolation level engines cached to avoid unbounded growth
        self._engine_cache: OrderedDict[str, Any] = OrderedDict()
        self._engine_cache_limit = 8

    async def connect(self, create_tables: bool = False) -> None:
        """Initialize the database connection and optionally create tables."""
        from eden.db.base import Model
        Model._bind_db(self)

        if self._connected:
            if create_tables:
                async with self.engine.begin() as conn:
                    try:
                        await conn.run_sync(Model.metadata.create_all)
                    except Exception as exc:
                        message = str(exc).lower()
                        if self.engine.dialect.name == "sqlite" and "already exists" in message:
                            logger.warning(
                                "Ignoring SQLite 'already exists' error during create_all: %s",
                                exc,
                            )
                        else:
                            raise
            return

        if create_tables:
            async with self.engine.begin() as conn:
                try:
                    await conn.run_sync(Model.metadata.create_all)
                except Exception as exc:
                    message = str(exc).lower()
                    if self.engine.dialect.name == "sqlite" and "already exists" in message:
                        logger.warning(
                            "Ignoring SQLite 'already exists' error during create_all: %s",
                            exc,
                        )
                    else:
                        raise

        self._connected = True
        logger.info(f"Database connected to {self.url}")

    async def disconnect(self) -> None:
        """Close all database connections."""
        await self.engine.dispose()
        self._connected = False
        logger.info("Database disconnected")

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async context manager for database sessions."""
        async with self.session_factory() as session:
            try:
                yield session
                # COMMIT is handled by Model.save/create or manually by user
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def set_schema(self, session: AsyncSession, schema_name: str | None) -> None:
        """
        Sets the PostgreSQL search_path for the current session.
        If schema_name is None, resets to 'public'.
        """
        if self.engine.dialect.name != "postgresql":
            # For non-PostgreSQL databases (like SQLite), schema isolation
            # is typically not supported via search_path.
            return

        from sqlalchemy import text
        target = schema_name or "public"
        # Sanitize schema name: allow only alphanumeric and underscores
        safe_schema = "".join(c for c in target if c.isalnum() or c == "_")

        await session.execute(text(f'SET search_path TO "{safe_schema}", public'))

    def __getattr__(self, name: str) -> Any:
        """Proxy to SQLAlchemy engine if needed."""
        return getattr(self.engine, name)

    @contextlib.asynccontextmanager
    async def transaction(
        self, isolation_level: str | None = None, session: AsyncSession | None = None, commit: bool = True
    ) -> AsyncIterator[AsyncSession]:
        """
        Context manager for database transactions with concurrency safety and nesting.
        """
        # 1. Try to join provided or existing session if no isolation level is required
        target_session = session or get_session()
        if target_session and not isolation_level:
            if target_session.in_transaction():
                # Use a savepoint (nested transaction)
                async with target_session.begin_nested():
                    try:
                        yield target_session
                        # Flush to ensure errors are caught within the savepoint
                        await target_session.flush()
                    except Exception:
                        # begin_nested() handles rollback automatically on exception
                        raise
                return
            
            # Start a top-level transaction on the existing session
            await target_session.begin()
            try:
                yield target_session
                await target_session.flush()
                if commit:
                    await target_session.commit()
            except Exception:
                await target_session.rollback()
                raise
            return

        # 2. Handle explicit isolation level (requires separate connection/session)
        if isolation_level:
            if isolation_level not in self._engine_cache:
                if len(self._engine_cache) >= self._engine_cache_limit:
                    # Evict oldest entry to keep cache bounded
                    self._engine_cache.popitem(last=False)
                self._engine_cache[isolation_level] = self.engine.execution_options(
                    isolation_level=isolation_level
                )
            else:
                # Move to end to mark recently used
                self._engine_cache.move_to_end(isolation_level)

            engine = self._engine_cache[isolation_level]
            new_session = EdenAsyncSession(engine, expire_on_commit=False)

            token = set_session(new_session)
            try:
                async with new_session:
                    await new_session.begin() # Start the transaction explicitly
                    try:
                        yield new_session
                        if commit:
                            await new_session.commit()
                    except Exception:
                        await new_session.rollback()
                        raise
            finally:
                await new_session.close()
                reset_session(token)
            return

        # 3. Standard case: New session and transaction
        async with self.session() as session:
            # We also need to set this session in context so nested calls can find it
            token = set_session(session)
            try:
                await session.begin()
                try:
                    yield session
                    if commit:
                        await session.commit()
                except Exception:
                    await session.rollback()
                    raise
            except Exception:
                # SQLAlchemy's async with session.begin() handles rollback
                raise
            finally:
                reset_session(token)

    @contextlib.asynccontextmanager
    async def savepoint(
        self, name: str | None = None, session: AsyncSession | None = None
    ) -> AsyncIterator[AsyncSession]:
        """
        Creates a savepoint within the current transaction.
        """
        target_session = session or get_session()
        if not target_session:
            raise RuntimeError(
                "Savepoint requires an active transaction context. "
                "Use: async with db.transaction() as session: ... await db.savepoint() ..."
            )

        # Explicit begin_nested for savepoints
        async with target_session.begin_nested():
            yield target_session
            # Ensure it flushes before exit to capture changes in identifiers/counts
            await target_session.flush()

    async def atomic(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a function atomically (within a transaction).
        """
        async with self.transaction() as session:
            token = set_session(session)
            try:
                return await func(*args, **kwargs)
            finally:
                reset_session(token)


def set_session(session: AsyncSession) -> contextvars.Token:
    """
    Set the current session in async context.
    """
    return _session_context.set(session)


def get_session() -> AsyncSession | None:
    """
    Get the current session from async context, if available.
    """
    return _session_context.get()


def reset_session(token: contextvars.Token | None = None) -> None:
    """
    Reset the session context.
    """
    if token is not None:
        _session_context.reset(token)
    else:
        _session_context.set(None)


# ── @atomic Decorator ────────────────────────────────────────────────────

import functools
from typing import Any as TypingAny
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def atomic(func: F) -> F:
    """
    Decorator for route handlers to automatically wrap execution in a transaction.
    """
    @functools.wraps(func)  # type: ignore[misc]
    async def wrapper(request: "Request", *args: TypingAny, **kwargs: TypingAny) -> TypingAny:
        # Get database from app state
        db = getattr(request.app, "state", None)
        if db is None or not hasattr(db, "db"):
            raise RuntimeError(
                "@atomic requires app.state.db to be configured. "
                "Example: app.state.db = Database(...)"
            )

        db_inst = db.db

        # Execute handler within a transaction
        async with db_inst.transaction() as session:
            # Set session in context for QuerySet._resolve_session()
            token = set_session(session)

            # Also store in request.state for direct access
            request.state.session = session

            try:
                # Inject session into handler if it has a 'session' parameter
                sig = __inspect_signature(cast(Callable[..., Any], func))
                if "session" in sig.parameters and "session" not in kwargs:
                    result = await cast(Callable[..., Any], func)(request, *args, session=session, **kwargs)
                else:
                    result = await cast(Callable[..., Any], func)(request, *args, **kwargs)

                return result
            finally:
                # Always clean up context
                reset_session(token)
                if hasattr(request.state, "session"):
                    delattr(request.state, "session")

    return cast(F, wrapper)


def __inspect_signature(func: Callable[..., Any]) -> Any:
    """Helper to get function signature safely."""
    import inspect
    try:
        return inspect.signature(func)
    except (ValueError, TypeError):
        # Fallback: pretend it accepts any parameter
        class AnySignature:
            parameters = {}
        return AnySignature()

def get_db(request: Any) -> Database:
    """Dependency helper for route handlers."""
    return request.app.state.db

def init_db(url: str, app: Any = None, **kwargs: Any) -> Database:
    """Helper to initialize database and optionally attach to app state."""
    try:
        from eden.config import get_config
        config = get_config()
        # Merge config engine arguments with explicit kwargs (explicit wins)
        engine_kwargs = config.get_database_engine_kwargs()
        engine_kwargs.update(kwargs)
        kwargs = engine_kwargs
    except Exception:
        pass

    db = Database(url, **kwargs)
    if app:
        app.state.db = db
    return db
