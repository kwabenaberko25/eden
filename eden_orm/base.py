"""
Eden ORM - Base Model Class

Core model implementation with metaclass for field registration and table mapping.
"""

from typing import Any, Type, Dict, Optional, List, ClassVar
from datetime import datetime
from uuid import UUID, uuid4
import logging

from .fields import Field, ForeignKeyField, DateTimeField, UUIDField
from .connection import get_session, get_pool
from .executor import QueryExecutor, SQLBuilder

logger = logging.getLogger(__name__)


# Import here to avoid circular dependency
def _add_queryset_methods(model_class):
    """Add QuerySet methods to model class."""
    from .query import FilterChain
    
    @classmethod
    def filter(cls, **kwargs) -> FilterChain:
        chain = FilterChain(model_class=cls)
        return chain.filter(**kwargs)
    
    @classmethod
    def exclude(cls, **kwargs) -> FilterChain:
        chain = FilterChain(model_class=cls)
        return chain.exclude(**kwargs)
    
    model_class.filter = filter
    model_class.exclude = exclude


class ModelMetaclass(type):
    """
    Metaclass for Model.
    
    Handles:
    - Field registration and discovery
    - Table name mapping
    - Primary key detection
    - Relationship tracking
    """
    
    def __new__(mcs, name, bases, namespace, **kwargs):
        # Don't process abstract models
        if namespace.get("__abstract__"):
            return super().__new__(mcs, name, bases, namespace)
        
        # Collect fields from namespace
        fields: Dict[str, Field] = {}
        primary_key: Optional[str] = None
        
        for attr_name, attr_value in list(namespace.items()):
            if isinstance(attr_value, Field):
                attr_value.name = attr_name
                fields[attr_name] = attr_value
                
                if attr_value.primary_key:
                    if primary_key:
                        raise ValueError(f"Multiple primary keys in {name}")
                    primary_key = attr_name
        
        # Inherit fields from parent
        for base in bases:
            if hasattr(base, "__fields__"):
                fields = {**base.__fields__, **fields}
            if hasattr(base, "__primary_key__") and not primary_key:
                primary_key = base.__primary_key__
        
        # Ensure primary key exists
        if not primary_key and name != "Model":
            # Auto-add UUID primary key
            id_field = UUIDField(primary_key=True, default_factory=uuid4)
            id_field.name = "id"
            fields["id"] = id_field
            namespace["id"] = id_field
            primary_key = "id"
        
        # Ensure table name
        table_name = namespace.get("__tablename__")
        if not table_name:
            table_name = name.lower() + "s"
        
        # Create the class
        cls = super().__new__(mcs, name, bases, namespace)
        
        # Attach metadata
        cls.__fields__ = fields
        cls.__primary_key__ = primary_key
        cls.__tablename__ = table_name
        cls.__new_fields = {}
        cls.__relationships__ = {}
        cls._reverse_relationships = {}  # For reverse relationship access
        
        # Add field descriptors to class
        for field_name, field in fields.items():
            if field_name not in cls.__dict__:
                setattr(cls, field_name, field)
        
        # Add QuerySet methods (filter, exclude)
        if name != "Model":  # Don't add to abstract base
            _add_queryset_methods(cls)
        
        logger.debug(
            f"Registered model: {name} (table={table_name}, pk={primary_key}, "
            f"fields={list(fields.keys())})"
        )
        
        return cls


class Model(metaclass=ModelMetaclass):
    """
    Base class for all models.
    
    Usage:
        class User(Model):
            __tablename__ = "users"
            
            id: UUID = UUIDField(primary_key=True)
            email: str = StringField(unique=True)
            name: str = StringField()
            created_at: datetime = DateTimeField(auto_now_add=True)
    """
    
    __abstract__ = True
    __fields__: ClassVar[Dict[str, Field]] = {}
    __primary_key__: ClassVar[str] = "id"
    __tablename__: ClassVar[str] = ""
    __relationships__: ClassVar[Dict] = {}
    
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    def __init__(self, **kwargs):
        """Initialize model instance with provided values."""
        # Set provided values
        for key, value in kwargs.items():
            if key in self.__fields__:
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown field: {key}")
        
        # Set defaults for missing fields
        for field_name, field in self.__fields__.items():
            if field_name not in kwargs:
                if field.default_factory:
                    setattr(self, field_name, field.get_default())
                elif field.default is not None:
                    setattr(self, field_name, field.default)
    
    def __repr__(self) -> str:
        pk_value = getattr(self, self.__primary_key__, None)
        return f"<{self.__class__.__name__} {self.__primary_key__}={pk_value}>"
    
    def __getattr__(self, name: str):
        """
        Support dynamic access to reverse relationships.
        
        When accessing a relationship that hasn't been loaded yet,
        return a ReverseRelationshipManager for querying.
        
        Example:
            user = await User.get(id=1)
            posts = await user.posts.all()
        """
        # Avoid infinite recursion for special attributes
        if name.startswith('_') or name in ('__class__', '__dict__'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
        # Check if this is a registered reverse relationship
        reverse_rels = getattr(self.__class__, '_reverse_relationships', {})
        
        if name in reverse_rels:
            from .reverse_relationships import ReverseRelationshipManager
            
            rel_info = reverse_rels[name]
            return ReverseRelationshipManager(
                model_class=rel_info['model'],
                related_model_class=self.__class__,
                foreign_key_field_name=rel_info['fk_field'],
                instance_id=getattr(self, 'id', None)
            )
        
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        result = {}
        for field_name in self.__fields__:
            value = getattr(self, field_name, None)
            
            # Convert special types
            if isinstance(value, UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            
            result[field_name] = value
        
        return result
    
    async def save(self) -> "Model":
        """
        Save the model to database.
        
        Performs INSERT if new, UPDATE if existing.
        """
        async with await get_session() as session:
            executor = QueryExecutor(session)
            
            # Check if this is an insert or update
            pk_value = getattr(self, self.__primary_key__, None)
            
            if pk_value is None:
                # INSERT
                return await self._insert(executor, session)
            else:
                # UPDATE
                return await self._update(executor, session)
    
    async def _insert(self, executor: QueryExecutor, session) -> "Model":
        """Insert new record into database."""
        # Collect values
        values = {}
        columns = []
        
        for field_name, field in self.__fields__.items():
            value = getattr(self, field_name, None)
            
            # Skip None values unless not nullable
            if value is None and field.nullable:
                continue
            
            # Generate default if needed
            if value is None and field.default_factory:
                value = field.get_default()
                setattr(self, field_name, value)
            
            if value is not None:
                values[field_name] = value
                columns.append(field_name)
        
        # Build INSERT query
        builder = SQLBuilder()
        placeholders = ", ".join([f"${i}" for i in range(1, len(columns) + 1)])
        cols_str = ", ".join(columns)
        
        query = f"INSERT INTO {self.__tablename__} ({cols_str}) VALUES ({placeholders}) RETURNING *"
        params = tuple(values[col] for col in columns)
        
        logger.debug(f"INSERT: {query} | Params: {params}")
        
        # Execute
        row = await session.fetchrow(query, *params)
        
        if row:
            # Update instance with DB-generated values (id, timestamps, etc)
            from .executor import ResultMapper
            mapped = ResultMapper.map_row(dict(row), self.__class__, self.__fields__)
            self.__dict__.update(mapped.__dict__)
        
        return self
    
    async def _update(self, executor: QueryExecutor, session) -> "Model":
        """Update existing record in database."""
        # Collect changed values
        values = {}
        for field_name, field in self.__fields__.items():
            value = getattr(self, field_name, None)
            values[field_name] = value
        
        # Build UPDATE query
        pk_value = getattr(self, self.__primary_key__)
        set_parts = []
        params = []
        
        for i, (col, val) in enumerate(values.items(), 1):
            set_parts.append(f"{col} = ${i}")
            params.append(val)
        
        # Add WHERE clause
        where_idx = len(params) + 1
        set_str = ", ".join(set_parts)
        query = (
            f"UPDATE {self.__tablename__} SET {set_str} "
            f"WHERE {self.__primary_key__} = ${where_idx} "
            f"RETURNING *"
        )
        params.append(pk_value)
        
        logger.debug(f"UPDATE: {query} | Params: {params}")
        
        # Execute
        row = await session.fetchrow(query, *tuple(params))
        
        if row:
            from .executor import ResultMapper
            mapped = ResultMapper.map_row(dict(row), self.__class__, self.__fields__)
            self.__dict__.update(mapped.__dict__)
        
        return self
    
    async def delete(self) -> None:
        """Delete this record from database."""
        async with await get_session() as session:
            pk_value = getattr(self, self.__primary_key__)
            query = f"DELETE FROM {self.__tablename__} WHERE {self.__primary_key__} = $1"
            
            logger.debug(f"DELETE: {query} | Params: ({pk_value})")
            
            await session.execute(query, pk_value)
    
    @classmethod
    async def create(cls, **kwargs) -> "Model":
        """Create and save a new instance."""
        instance = cls(**kwargs)
        return await instance.save()
    
    @classmethod
    async def get_by_pk(cls, pk_value: Any) -> Optional["Model"]:
        """Get record by primary key."""
        async with await get_session() as session:
            query = f"SELECT * FROM {cls.__tablename__} WHERE {cls.__primary_key__} = $1"
            row = await session.fetchrow(query, pk_value)
            
            if row:
                from .executor import ResultMapper
                return ResultMapper.map_row(dict(row), cls, cls.__fields__)
            
            return None
    
    @classmethod
    async def all(cls) -> List["Model"]:
        """Get all records."""
        async with await get_session() as session:
            query = f"SELECT * FROM {cls.__tablename__}"
            rows = await session.fetch(query)
            
            from .executor import ResultMapper
            return [
                ResultMapper.map_row(dict(row), cls, cls.__fields__)
                for row in rows
            ]
    
    @classmethod
    async def count(cls) -> int:
        """Get total record count."""
        async with await get_session() as session:
            query = f"SELECT COUNT(*) as count FROM {cls.__tablename__}"
            result = await session.fetchval(query)
            return result
    
    @classmethod
    async def exists(cls, **filters) -> bool:
        """Check if record matching filters exists."""
        async with await get_session() as session:
            where_parts = []
            params = []
            
            for i, (key, value) in enumerate(filters.items(), 1):
                where_parts.append(f"{key} = ${i}")
                params.append(value)
            
            where_clause = " AND ".join(where_parts)
            query = f"SELECT 1 FROM {cls.__tablename__} WHERE {where_clause} LIMIT 1"
            
            result = await session.fetchval(query, *params)
            return result is not None
    
    @classmethod
    def raw(cls, sql: str, params: Optional[List[Any]] = None):
        """
        Execute raw SQL query and map results to model instances.
        
        Usage:
            users = await User.raw(
                "SELECT * FROM users WHERE email LIKE $1",
                ["%@example.com"]
            )
        """
        from .raw_sql import RawQuery
        
        async def _execute_raw():
            results = await RawQuery.execute(sql, params, fetch_one=False)
            
            # Convert dict results to model instances
            instances = []
            for row in results:
                instance = cls()
                for field_name in cls.__fields__:
                    if field_name in row:
                        setattr(instance, field_name, row[field_name])
                instances.append(instance)
            
            return instances
        
        return _execute_raw()
    
    @classmethod
    def prefetch_nested(cls, *paths: str):
        """
        Create a query with nested prefetch support.
        
        Usage:
            posts = await Post.prefetch_nested(
                "author",
                "comments__author"
            ).all()
        
        Args:
            paths: Relationship paths with dot notation for nesting
        """
        from .nested_prefetch import NestedPrefetchQuerySet
        from .query import FilterChain
        
        chain = FilterChain(model_class=cls)
        qs = NestedPrefetchQuerySet(chain)
        qs.nested_prefetch_fields.extend(paths)
        
        return qs


# Auto-add timestamps
def add_timestamps(model_class):
    """Add created_at and updated_at fields to model."""
    if "created_at" not in model_class.__fields__:
        field = DateTimeField(auto_now_add=True, nullable=False)
        field.name = "created_at"
        model_class.__fields__["created_at"] = field
    
    if "updated_at" not in model_class.__fields__:
        field = DateTimeField(auto_now=True, nullable=False)
        field.name = "updated_at"
        model_class.__fields__["updated_at"] = field
