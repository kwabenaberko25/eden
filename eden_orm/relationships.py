"""
Eden ORM - Relationships

Foreign key relationships and eager loading.
"""

from typing import Optional, Type, List, Dict, Any
import logging
import weakref
from asyncio import iscoroutine

logger = logging.getLogger(__name__)


class Relationship:
    """
    Represents a relationship between models.
    
    Supports:
    - ForeignKey (many-to-one)
    - Reverse relationships (one-to-many)
    """
    
    def __init__(
        self,
        to_model: Type,
        back_populates: Optional[str] = None,
        foreign_key_field: Optional[str] = None,
    ):
        self.to_model = to_model
        self.back_populates = back_populates
        self.foreign_key_field = foreign_key_field
    
    async def get_related(self, instance, fk_value):
        """
        Load related object for the given FK value.
        
        Args:
            instance: The model instance (for context)
            fk_value: The foreign key value to load
        
        Returns:
            Related object instance or None
        """
        if fk_value is None:
            return None
        
        try:
            from .connection import get_session
            from .executor import ResultMapper
            
            table_name = self.to_model.__tablename__
            query = f"SELECT * FROM {table_name} WHERE id = $1"
            
            async with await get_session() as session:
                row = await session.fetchrow(query, fk_value)
            
            if not row:
                return None
            
            # Map the row to model instance
            related_obj = ResultMapper.map_row(
                dict(row),
                self.to_model,
                self.to_model.__fields__
            )
            return related_obj
            
        except Exception as e:
            logger.error(f"Failed to load related {self.to_model.__name__}: {e}")
            raise


class Reference:
    """
    Descriptor for foreign key relationships with lazy loading support.
    
    Supports both eager loading (from select_related) and lazy loading.
    
    Usage:
        class Post(Model):
            author_id: UUID = ForeignKeyField("users")
            author: Reference["User"] = Reference(to_model=User, back_populates="posts")
        
        # Eager loading (from select_related query):
        post = await Post.select_related('author').first()
        print(post.author.name)  # Already loaded
        
        # Lazy loading:
        post = await Post.get(id=1)
        author = await post.author.load()  # Fetches from DB
        
        # Or via direct FK reference:
        author_id = post.author_id  # FK value
    """
    
    # Weak reference cache to avoid memory leaks: {instance -> {attr_name -> related_obj}}
    _cache = weakref.WeakKeyDictionary()
    
    def __init__(
        self,
        to_model: Optional[Type] = None,
        back_populates: Optional[str] = None,
    ):
        self.to_model = to_model
        self.back_populates = back_populates
        self.attr_name: Optional[str] = None
        self.fk_field_name: Optional[str] = None
    
    def __set_name__(self, owner, name):
        """Called when descriptor is assigned to class."""
        self.attr_name = name
        # Derive FK field name: 'author' -> 'author_id'
        self.fk_field_name = f"{name}_id"
    
    def __get__(self, obj, objtype=None):
        """
        Get related object on access.
        
        Returns:
        - descriptor class itself if accessed on class (obj is None)
        - cached related object if already loaded
        - coroutine for lazy loading if not cached
        """
        if obj is None:
            return self
        
        if not self.attr_name:
            return None
        
        # Check eager-loaded cache (from select_related)
        eager_cache_key = f"_cached_{self.attr_name}"
        if eager_cache_key in obj.__dict__:
            return obj.__dict__[eager_cache_key]
        
        # Check weak reference cache
        if obj in self._cache and self.attr_name in self._cache[obj]:
            return self._cache[obj][self.attr_name]
        
        # Return lazy-loading coroutine
        return self._load_related_async(obj)
    
    async def _load_related_async(self, obj):
        """Lazy-load the related object from the database."""
        # Get FK value from instance
        if not self.fk_field_name:
            return None
        
        fk_value = getattr(obj, self.fk_field_name, None)
        if fk_value is None:
            return None
        
        # Check cache again before querying
        if obj in self._cache and self.attr_name in self._cache[obj]:
            return self._cache[obj][self.attr_name]
        
        # Fetch related object using to_model.get()
        if not self.to_model:
            logger.error(f"Reference.to_model not set for {self.attr_name}")
            return None
        
        try:
            from .connection import get_session
            
            # Use the model's get() method if available
            if hasattr(self.to_model, 'get'):
                related_obj = await self.to_model.get(id=fk_value)
            else:
                # Fallback: query directly
                table_name = self.to_model.__tablename__
                query = f"SELECT * FROM {table_name} WHERE id = $1"
                
                async with await get_session() as session:
                    row = await session.fetchrow(query, fk_value)
                
                if not row:
                    return None
                
                # Instantiate related model
                from .executor import ResultMapper
                related_obj = ResultMapper.map_row(
                    dict(row),
                    self.to_model,
                    self.to_model.__fields__
                )
            
            # Cache the result
            if obj not in self._cache:
                self._cache[obj] = {}
            self._cache[obj][self.attr_name] = related_obj
            
            return related_obj
            
        except Exception as e:
            logger.error(f"Failed to lazy-load {self.attr_name}: {e}")
            raise
    
    def __set__(self, obj, value):
        """Set related object and update cache."""
        if self.attr_name:
            # Set in eager-loaded cache (from direct assignment)
            cache_key = f"_cached_{self.attr_name}"
            obj.__dict__[cache_key] = value
            
            # Also update weak reference cache
            if obj not in self._cache:
                self._cache[obj] = {}
            self._cache[obj][self.attr_name] = value


class RelationshipManager:
    """Manages relationship loading and caching."""
    
    def __init__(self, model_class: Type):
        self.model_class = model_class
        self.cache: Dict[str, Any] = {}
    
    async def load_related(
        self,
        instance: Any,
        relation_name: str,
        session = None,
    ) -> Any:
        """Load related object via lazy loading."""
        if not session:
            from .connection import get_session
            session = await get_session()
        
        # Find the ForeignKey field
        fk_field_name = None
        for field_name, field in self.model_class.__fields__.items():
            if field_name.endswith(f"_{relation_name}_id") or field_name == f"{relation_name}_id":
                fk_field_name = field_name
                break
        
        if not fk_field_name:
            return None
        
        # Get the foreign key value
        fk_value = getattr(instance, fk_field_name, None)
        if not fk_value:
            return None
        
        # Query the related model
        # (Will be implemented when we know the related model)
        logger.debug(f"Lazy loading {relation_name} for {self.model_class.__name__}")
        
        return None


class RelationshipPath:
    """
    Represents a path through relationships.
    
    Used for eager loading with select_related.
    """
    
    def __init__(self, *path: str):
        self.path = path
    
    def get_sql_join(self, base_table: str, base_model: Type) -> str:
        """Generate SQL JOIN for this relationship path."""
        joins = []
        current_model = base_model
        current_table = base_table
        
        for i, relation in enumerate(self.path):
            # Find FK field for this relation
            fk_field = None
            for field_name, field in current_model.__fields__.items():
                if field_name == f"{relation}_id":
                    fk_field = field
                    break
            
            if not fk_field or not hasattr(fk_field, "to_model"):
                continue
            
            # Get the target model
            target_model = fk_field.to_model
            if not target_model:
                continue
            
            target_table = target_model.__tablename__
            join = (
                f"LEFT JOIN {target_table} ON "
                f"{current_table}.{relation}_id = {target_table}.id"
            )
            joins.append(join)
            
            current_model = target_model
            current_table = target_table
        
        return " ".join(joins)
