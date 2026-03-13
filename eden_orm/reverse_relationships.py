"""
Reverse Relationships - Many-to-One and One-to-Many reverse access

Allows accessing related objects in reverse direction. For example:
- If User has many Posts, access all posts by user: user.posts_set.all()
- Automatically created when ForeignKeyField references this model

Usage:
    class User(Model):
        name: str = StringField()
    
    class Post(Model):
        title: str = StringField()
        author: User = ForeignKeyField(User)
    
    # Reverse access:
    user = await User.get(id=1)
    posts = await user.post_set.all()
"""

from typing import List, Optional, Any
from dataclasses import dataclass, field as dc_field
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ReverseRelationshipManager:
    """Manager for accessing related objects in reverse direction."""
    
    model_class: Any  # Foreign key model class (e.g., Post)
    related_model_class: Any  # This model class (e.g., User)
    foreign_key_field_name: str  # Field name on related model (e.g., 'author')
    instance_id: Any  # ID of the related_model instance
    _cache: List[Any] = dc_field(default_factory=list)
    _cached: bool = False
    
    # Exponential backoff settings
    _backoff_initial_ms: int = 100      # Start with 100ms
    _backoff_max_ms: int = 10000        # Cap at 10 seconds
    _backoff_max_attempts: int = 5      # Try up to 5 times
    
    async def _execute_with_backoff(self, query: str, *params):
        """Execute query with exponential backoff retry logic."""
        from .connection import get_session
        
        last_error = None
        backoff_ms = self._backoff_initial_ms
        
        for attempt in range(self._backoff_max_attempts):
            try:
                async with await get_session() as session:
                    return await session.fetch(query, *params)
            except Exception as e:
                last_error = e
                if attempt < self._backoff_max_attempts - 1:
                    # Wait before retrying (exponential backoff)
                    wait_seconds = min(backoff_ms / 1000, self._backoff_max_ms / 1000)
                    logger.debug(f"Retry attempt {attempt + 1}/{self._backoff_max_attempts} after {wait_seconds}s: {e}")
                    await asyncio.sleep(wait_seconds)
                    backoff_ms *= 2  # Double wait time for next attempt
        
        # All retries exhausted
        logger.error(f"Failed after {self._backoff_max_attempts} attempts: {last_error}")
        raise last_error
    
    async def all(self) -> List[Any]:
        """Get all related objects with caching."""
        if self._cached:
            return self._cache
        
        # Build WHERE clause: field_name = instance_id
        table_name = self.model_class.__tablename__
        fk_field = self.foreign_key_field_name
        
        query = f"SELECT * FROM {table_name} WHERE {fk_field} = $1"
        
        try:
            rows = await self._execute_with_backoff(query, self.instance_id)
            
            # Map rows to model instances
            from .executor import ResultMapper
            self._cache = [
                ResultMapper.map_row(dict(row), self.model_class, self.model_class.__fields__)
                for row in rows
            ]
            self._cached = True
            
        except Exception as e:
            logger.error(f"Error fetching reverse relationships: {e}")
            return []
        
        return self._cache
    
    async def filter(self, **kwargs) -> List[Any]:
        """Get related objects matching filter criteria."""
        all_related = await self.all()
        
        # Filter in memory
        filtered = all_related
        for key, value in kwargs.items():
            filtered = [
                obj for obj in filtered
                if getattr(obj, key, None) == value
            ]
        
        return filtered
    
    async def count(self) -> int:
        """Count all related objects."""
        all_related = await self.all()
        return len(all_related)
    
    async def create(self, **kwargs) -> Any:
        """Create a new related object with FK automatically set."""
        kwargs[self.foreign_key_field_name] = self.instance_id
        
        instance = self.model_class(**kwargs)
        await instance.save()
        
        # Invalidate cache
        self._cached = False
        
        return instance
    
    async def delete_all(self) -> int:
        """Delete all related objects with exponential backoff."""
        from .connection import get_session
        
        table_name = self.model_class.__tablename__
        fk_field = self.foreign_key_field_name
        
        query = f"DELETE FROM {table_name} WHERE {fk_field} = $1"
        
        try:
            async with await get_session() as session:
                result = await session.execute(query, self.instance_id)
                # Invalidate cache
                self._cached = False
                # Result format depends on asyncpg, typically "DELETE N"
                return int(result.split()[-1]) if result else 0
        except Exception as e:
            logger.error(f"Error deleting related objects: {e}")
            return 0


@dataclass
class ReverseRelationshipDescriptor:
    """Descriptor for reverse relationship access on model instances."""
    
    related_model_class: Any  # Model that has the FK
    foreign_key_field_name: str  # Name of FK field
    manager_class: type = ReverseRelationshipManager
    
    def __set_name__(self, owner, name):
        """Called when descriptor is assigned to class attribute."""
        self.related_name = name
    
    def __get__(self, instance, owner):
        """Return ReverseRelationshipManager when accessed on instance."""
        if instance is None:
            return self
        
        return self.manager_class(
            model_class=self.related_model_class,
            related_model_class=owner,
            foreign_key_field_name=self.foreign_key_field_name,
            instance_id=instance.id,
            db_connection=getattr(instance, '_db_connection', None)
        )


def setup_reverse_relationships(model_class, field_name, fk_model_class):
    """
    Setup a reverse relationship on a model class.
    
    Called automatically by ForeignKeyField during model setup.
    
    Args:
        model_class: The model containing the foreign key (e.g., Post)
        field_name: Name of the foreign key field (e.g., 'author')
        fk_model_class: The model being referenced (e.g., User)
    """
    # Create reverse accessor name: post_set, comment_set, etc.
    related_name = f"{model_class.__tablename__.rstrip('s')}_set"
    
    # Create and attach the descriptor
    descriptor = ReverseRelationshipDescriptor(
        related_model_class=model_class,
        foreign_key_field_name=field_name
    )
    
    setattr(fk_model_class, related_name, descriptor)
    logger.debug(f"Setup reverse relationship: {fk_model_class.__name__}.{related_name} -> {model_class.__name__}")
