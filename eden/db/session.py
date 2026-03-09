import contextlib
import logging
from typing import Any, AsyncGenerator, Dict, Optional, Type, Union
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

logger = logging.getLogger("eden.db")

class Database:
    """
    Database manager for Eden applications.
    Wraps SQLAlchemy 2.0 Async Engine and Session management.
    """

    def __init__(self, url: str, **kwargs: Any) -> None:
        self.url = url
        # SQLite memory optimization
        if url.startswith("sqlite") and ":memory:" in url:
            kwargs.setdefault("poolclass", StaticPool)
            kwargs.setdefault("connect_args", {"check_same_thread": False})
        
        kwargs.setdefault("echo", False)
        self.engine = create_async_engine(url, **kwargs)
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self._connected = False

    async def connect(self, create_tables: bool = False) -> None:
        """Initialize the database connection and optionally create tables."""
        if self._connected:
            return

        from eden.db.base import Model
        Model._bind_db(self)

        if create_tables:
            async with self.engine.begin() as conn:
                await conn.run_sync(Model.metadata.create_all)
        
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

    async def set_schema(self, session: AsyncSession, schema_name: Optional[str]) -> None:
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

def get_db(request: Any) -> Database:
    """Dependency helper for route handlers."""
    return request.app.state.db

def init_db(url: str, app: Any = None, **kwargs: Any) -> Database:
    """Helper to initialize database and optionally attach to app state."""
    db = Database(url, **kwargs)
    if app:
        app.state.db = db
    return db
