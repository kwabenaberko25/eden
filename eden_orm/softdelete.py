"""
Eden ORM - Soft Deletes

Soft delete support with automatic filtering and restoration.
"""

import logging
from datetime import datetime
from typing import Type, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class SoftDeleteMixin:
    """
    Mixin for soft delete support.
    
    Usage:
        class User(Model, SoftDeleteMixin):
            email: str = StringField()
            deleted_at: datetime = DateTimeField(nullable=True)
        
        user = await User.create(email="john@example.com")
        await user.soft_delete()  # Soft delete
        
        # Queries auto-exclude soft-deleted
        users = await User.all()  # Excludes soft-deleted
        
        # Restore
        await user.restore()
    """
    
    deleted_at: Optional[datetime] = None
    
    async def soft_delete(self):
        """Mark record as deleted without removing."""
        self.deleted_at = datetime.now()
        await self.save()
        logger.info(f"Soft deleted {self.__class__.__tablename__} {self.id}")
    
    async def restore(self):
        """Restore soft-deleted record."""
        if self.deleted_at is None:
            logger.warning(f"Record {self.id} is not soft-deleted")
            return False
        
        self.deleted_at = None
        await self.save()
        logger.info(f"Restored {self.__class__.__tablename__} {self.id}")
        return True
    
    @classmethod
    def _filter_soft_deleted(cls, query):
        """Auto-filter soft-deleted records."""
        # This should be called automatically by FilterChain
        return query.filter(deleted_at__isnull=True)
    
    @classmethod
    async def with_deleted(cls):
        """Include soft-deleted records in query."""
        # Override for specific query
        from .query import FilterChain
        return FilterChain(model_class=cls)
    
    @classmethod
    async def only_deleted(cls):
        """Get only soft-deleted records."""
        from .query import FilterChain
        return FilterChain(model_class=cls).filter(deleted_at__isnull=False)


def soft_delete_model(cls: Type) -> Type:
    """
    Decorator to add soft delete to model.
    
    Usage:
        @soft_delete_model
        class User(Model):
            email: str = StringField()
    """
    # Add deleted_at field if not present
    if not hasattr(cls, 'deleted_at'):
        from .fields import DateTimeField
        cls.deleted_at = DateTimeField(nullable=True)
    
    # Add mixin methods if not present
    if not hasattr(cls, 'soft_delete'):
        cls = type(cls.__name__, (SoftDeleteMixin, cls), dict(cls.__dict__))
    
    return cls
