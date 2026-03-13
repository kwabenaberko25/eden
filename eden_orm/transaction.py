"""
Eden ORM - Transactions

Async transaction support with rollback and savepoints.
"""

import logging
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class Transaction:
    """Represents a database transaction."""
    
    def __init__(self, session, savepoint: Optional[str] = None):
        self.session = session
        self.savepoint = savepoint
        self.started = False
    
    async def __aenter__(self):
        """Start transaction."""
        try:
            if self.savepoint:
                await self.session.execute(f"SAVEPOINT {self.savepoint}")
            else:
                await self.session.execute("BEGIN")
            self.started = True
            logger.info("Transaction started")
            return self
        except Exception as e:
            logger.error(f"Failed to start transaction: {e}")
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Commit or rollback transaction."""
        try:
            if exc_type is not None:
                # Error occurred - rollback
                if self.savepoint:
                    await self.session.execute(f"ROLLBACK TO {self.savepoint}")
                else:
                    await self.session.execute("ROLLBACK")
                logger.warning(f"Transaction rolled back due to {exc_type.__name__}")
            else:
                # No error - commit
                if not self.savepoint:
                    await self.session.execute("COMMIT")
                logger.info("Transaction committed")
            
            self.started = False
        except Exception as e:
            logger.error(f"Error during transaction cleanup: {e}")
            raise
        
        return False  # Don't suppress exceptions


@asynccontextmanager
async def transaction(savepoint: Optional[str] = None):
    """
    Context manager for database transactions.
    
    Usage:
        async with transaction():
            user = await User.create(email="john@example.com")
            await Post.create(title="...", author_id=user.id)
        # Auto-commit on success, rollback on error
    """
    from .connection import get_session
    
    session = await get_session()
    trans = Transaction(session, savepoint)
    
    async with trans:
        yield trans


async def atomic_transaction(func, *args, **kwargs):
    """
    Decorator-like transaction wrapper.
    
    Usage:
        async def create_user_and_post():
            user = await User.create(...)
            await Post.create(...)
        
        result = await atomic_transaction(create_user_and_post)
    """
    async with transaction():
        return await func(*args, **kwargs)
