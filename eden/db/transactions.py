"""
Eden — Database Transaction & Isolation Support

Provides transaction decorators, isolation level management, and atomic operations.

**Features:**
- `@atomic` decorator for automatic transaction management
- `@read_only()` decorator for read-only transactions
- `@serializable()` for strict isolation
- Automatic rollback on exceptions
- Manual savepoint support

**Usage:**

    from eden.db import atomic, read_only
    
    @atomic
    async def transfer_funds(user_id: int, amount: float):
        user = await User.get(user_id)
        user.balance -= amount
        await user.save()
        # Auto-commits on success, rolls back on exception
    
    @read_only
    async def get_balance(user_id: int):
        user = await User.get(user_id)
        return user.balance
"""

import functools
import logging
from typing import Any, Callable, Optional, TypeVar, Union
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Supported isolation levels (PostgreSQL conventions, adapted for other DBs)
ISOLATION_LEVELS = {
    "READ_UNCOMMITTED": "READ UNCOMMITTED",
    "READ_COMMITTED": "READ COMMITTED",
    "REPEATABLE_READ": "REPEATABLE READ",
    "SERIALIZABLE": "SERIALIZABLE",
}


def atomic(
    func: Optional[Callable[..., Any]] = None,
    isolation_level: Optional[str] = None,
) -> Union[Callable, Callable[[Callable], Callable]]:
    """
    Decorator to execute an async function within a database transaction.
    
    Automatically commits on success, rolls back on any exception.
    
    Args:
        func: The async function to wrap
        isolation_level: Optional isolation level ('READ_UNCOMMITTED', 'READ_COMMITTED',
                        'REPEATABLE_READ', 'SERIALIZABLE'). Defaults to database default.
    
    Returns:
        Decorated async function
    
    Example:
        @atomic(isolation_level="SERIALIZABLE")
        async def create_user(email: str, password: str):
            user = await User.create(email=email, password_hash=hash_password(password))
            await UserProfile.create(user_id=user.id)
            return user
        
        # Usage:
        user = await create_user("alice@example.com", "secret123")
        # Transaction committed automatically if no exception
    """
    
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Import here to avoid circular imports
            from .session import Database
            
            # Try to get app from context
            from eden.context import get_app
            app = get_app()
            if app is None or not hasattr(app, "db"):
                raise RuntimeError(
                    f"@atomic decorator requires app.db. "
                    f"Call within request context or pass db as argument."
                )
            
            db: Database = app.db
            # db.transaction() now supports joining existing sessions and savepoint nesting
            async with db.transaction(isolation_level=isolation_level) as txn_session:
                return await fn(*args, **kwargs)
        
        return wrapper
    
    # Handle both @atomic and @atomic() syntax
    if func is not None:
        return decorator(func)
    return decorator


def read_only(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for read-only transactions.
    
    Reduces database locking overhead for queries that don't modify data.
    Uses 'READ_COMMITTED' isolation level by default.
    
    Example:
        @read_only
        async def get_user_stats(user_id: int):
            user = await User.get(user_id)
            orders = await user.orders.all()
            return {"user": user, "order_count": len(orders)}
    """
    return atomic(isolation_level="READ_COMMITTED")(func)


def serializable(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for strict SERIALIZABLE isolation.
    
    Prevents all concurrency anomalies (dirty reads, non-repeatable reads, phantom reads).
    Use when data consistency is more important than performance.
    
    Example:
        @serializable
        async def transfer_funds(from_user_id: int, to_user_id: int, amount: float):
            from_user = await User.get(from_user_id)
            to_user = await User.get(to_user_id)
            
            if from_user.balance < amount:
                raise ValueError("Insufficient funds")
            
            from_user.balance -= amount
            to_user.balance += amount
            
            await from_user.save()
            await to_user.save()
            # No race conditions possible
    """
    return atomic(isolation_level="SERIALIZABLE")(func)


@asynccontextmanager
async def transaction(
    db: Any, isolation_level: Optional[str] = None, name: Optional[str] = None
):
    """
    Context manager for explicit transaction control.
    
    Args:
        db: Database instance
        isolation_level: Transaction isolation level (see ISOLATION_LEVELS)
        name: Optional name for logging/debugging
    
    Usage:
        from eden.db import transaction
        
        async with transaction(app.db, isolation_level="SERIALIZABLE") as session:
            user = await User.create(session, email="alice@example.com")
            await UserProfile.create(session, user_id=user.id)
        # Auto-commits if no exception
    
    Raises:
        RuntimeError: If database is not properly initialized
        Any exception from operations: Transaction auto-rolls back
    """
    if not hasattr(db, "transaction"):
        raise RuntimeError("Invalid database object: missing transaction() method")
    
    async with db.transaction(isolation_level=isolation_level) as session:
        try:
            if name:
                logger.debug(f"Transaction started: {name}")
            yield session
            if name:
                logger.debug(f"Transaction committed: {name}")
        except Exception as e:
            if name:
                logger.debug(f"Transaction rolled back: {name} - {e}")
            raise


@asynccontextmanager
async def savepoint(db: Any, name: str = "sp1"):
    """
    Context manager for savepoints (nested transactions).
    
    Allows partial rollback within a larger transaction without affecting
    other operations in the transaction.
    
    Args:
        db: Database instance
        name: Unique identifier for this savepoint
    
    Usage:
        async with transaction(app.db) as session:
            user = await User.create(session, email="alice@example.com")
            
            try:
                async with savepoint(app.db, name="delete_sp") as sp:
                    # This operation might fail
                    await user.delete(sp)
            except SomeError:
                # user still exists because savepoint rolled back
                pass
            
            # Continue with other operations
            await UserProfile.create(session, user_id=user.id)
        # All remaining operations committed
    """
    if not hasattr(db, "savepoint"):
        raise RuntimeError("Invalid database object: missing savepoint() method")
    
    async with db.savepoint(name=name) as session:
        logger.debug(f"Savepoint created: {name}")
        try:
            yield session
            logger.debug(f"Savepoint committed: {name}")
        except Exception as e:
            logger.debug(f"Savepoint rolled back: {name} - {e}")
            raise


def get_isolation_level(name: str) -> str:
    """
    Get SQL representation of isolation level.
    
    Args:
        name: Isolation level constant ('SERIALIZABLE', 'READ_COMMITTED', etc.)
    
    Returns:
        SQL representation used by database
        
    Raises:
        ValueError: If isolation level not recognized
    """
    if name not in ISOLATION_LEVELS:
        raise ValueError(
            f"Unknown isolation level: {name}\n"
            f"Supported: {', '.join(ISOLATION_LEVELS.keys())}"
        )
    return ISOLATION_LEVELS[name]
