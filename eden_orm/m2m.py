"""
Eden ORM - Many-to-Many Relationships

Support for many-to-many relationships via through tables.
"""

import logging
from typing import List, Type, Optional, Any, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ManyToManyField:
    """
    Field representing many-to-many relationship.
    
    Usage:
        class Student(Model):
            courses = ManyToManyField(Course, through='enrollments')
        
        class Course(Model):
            students = ManyToManyField(Student, through='enrollments')
    """
    
    to_model: Type
    through: Optional[str] = None
    related_name: Optional[str] = None
    field_name: Optional[str] = None
    owner_model: Optional[Type] = None
    
    def __post_init__(self):
        # Don't generate through table name here - wait for __set_name__
        # when we have access to owner_model
        pass
    
    def get_through_table(self) -> str:
        """Get through table name."""
        if self.through:
            return self.through
        # If not explicitly set, generate from owner and target model names
        if self.owner_model and self.to_model:
            owner_name = self.owner_model.__tablename__ or self.owner_model.__name__.lower()
            target_name = self.to_model.__tablename__ or self.to_model.__name__.lower()
            # Sort alphabetically for consistent naming
            names = sorted([owner_name, target_name])
            return f"{names[0]}_{names[1]}_through"
        return self.through or "unknown_through_table"
    
    def __set_name__(self, owner, name):
        """Called when descriptor is assigned to class."""
        self.field_name = name
        self.owner_model = owner
        # Generate through table name if not explicitly provided
        if not self.through:
            self.through = self.get_through_table()


class ManyToManyManager:
    """Manager for many-to-many relationships."""
    
    def __init__(
        self,
        from_model: Type,
        to_model: Type,
        through_table: str,
        from_pk: Any,
        field_name: str
    ):
        self.from_model = from_model
        self.to_model = to_model
        self.through_table = through_table
        self.from_pk = from_pk
        self.field_name = field_name
        self._cache: Optional[List[Any]] = None
    
    async def all(self) -> List[Any]:
        """Get all related objects."""
        if self._cache is not None:
            return self._cache
        
        from .connection import get_session
        
        session = await get_session()
        
        # SQL: SELECT * FROM to_model
        # INNER JOIN through_table ON to_model.id = through_table.to_model_id
        # WHERE through_table.from_model_id = ?
        
        from_table = self.from_model.__tablename__
        to_table = self.to_model.__tablename__
        
        sql = f"""
        SELECT {to_table}.* FROM {to_table}
        INNER JOIN {self.through_table} 
        ON {to_table}.id = {self.through_table}.{self.to_model.__tablename__}_id
        WHERE {self.through_table}.{from_table}_id = $1
        """
        
        try:
            rows = await session.fetch(sql, self.from_pk)
            self._cache = [self.to_model(**dict(row)) for row in rows]
            return self._cache
        except Exception as e:
            logger.error(f"Failed to fetch M2M related objects: {e}")
            return []
    
    async def add(self, *objects) -> int:
        """Add objects to this relationship."""
        if not objects:
            return 0
        
        from .connection import get_session
        
        session = await get_session()
        from_table = self.from_model.__tablename__
        to_table = self.to_model.__tablename__
        
        added_count = 0
        
        for obj in objects:
            to_pk = obj.id if hasattr(obj, 'id') else obj
            
            # INSERT INTO through_table (from_model_id, to_model_id) VALUES (?, ?)
            sql = f"""
            INSERT INTO {self.through_table} ({from_table}_id, {to_table}_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """
            
            try:
                await session.execute(sql, self.from_pk, to_pk)
                added_count += 1
                self._cache = None  # Invalidate cache
            except Exception as e:
                logger.warning(f"Failed to add M2M relationship: {e}")
        
        logger.info(f"Added {added_count} relationships to {self.field_name}")
        return added_count
    
    async def remove(self, *objects) -> int:
        """Remove objects from this relationship."""
        if not objects:
            return 0
        
        from .connection import get_session
        
        session = await get_session()
        from_table = self.from_model.__tablename__
        to_table = self.to_model.__tablename__
        
        removed_count = 0
        
        for obj in objects:
            to_pk = obj.id if hasattr(obj, 'id') else obj
            
            sql = f"""
            DELETE FROM {self.through_table}
            WHERE {from_table}_id = $1 AND {to_table}_id = $2
            """
            
            try:
                await session.execute(sql, self.from_pk, to_pk)
                removed_count += 1
                self._cache = None  # Invalidate cache
            except Exception as e:
                logger.warning(f"Failed to remove M2M relationship: {e}")
        
        logger.info(f"Removed {removed_count} relationships from {self.field_name}")
        return removed_count
    
    async def clear(self) -> int:
        """Clear all relationships."""
        from .connection import get_session
        
        session = await get_session()
        from_table = self.from_model.__tablename__
        
        sql = f"""
        DELETE FROM {self.through_table}
        WHERE {from_table}_id = $1
        """
        
        try:
            result = await session.execute(sql, self.from_pk)
            self._cache = None  # Invalidate cache
            logger.info(f"Cleared all {self.field_name} relationships")
            return 1
        except Exception as e:
            logger.error(f"Failed to clear M2M relationships: {e}")
            return 0
    
    async def count(self) -> int:
        """Count related objects."""
        from .connection import get_session
        
        session = await get_session()
        from_table = self.from_model.__tablename__
        
        sql = f"""
        SELECT COUNT(*) FROM {self.through_table}
        WHERE {from_table}_id = $1
        """
        
        try:
            result = await session.fetchval(sql, self.from_pk)
            return result or 0
        except Exception as e:
            logger.error(f"Failed to count M2M relationships: {e}")
            return 0


class ManyToManyDescriptor:
    """Descriptor for accessing many-to-many relationships."""
    
    def __init__(self, field: ManyToManyField):
        self.field = field
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.field
        
        # Return ManyToManyManager instance
        return ManyToManyManager(
            from_model=objtype,
            to_model=self.field.to_model,
            through_table=self.field.through,
            from_pk=obj.id,
            field_name=self.field.field_name
        )
