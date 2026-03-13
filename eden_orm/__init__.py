"""
Eden ORM - Production-Ready Async ORM for PostgreSQL

A clean, Django-inspired ORM built from scratch with pure asyncio support.

Features:
- Async-first design (asyncpg driver)
- Lazy-evaluated queries (QuerySet)
- Automatic primary keys (UUID v4)
- Timestamps (created_at, updated_at)
- Relationships (ForeignKey, eager loading)
- Query filtering with lookups
- Pagination support
- Transaction management
- Type safety with Python type hints

Example:
    import asyncio
    from eden_orm import Model, StringField, DateTimeField, initialize
    
    class User(Model):
        __tablename__ = "users"
        email: str = StringField(unique=True)
        name: str = StringField()
    
    async def main():
        await initialize("postgresql+asyncpg://user:pass@localhost/db")
        
        # Create
        user = await User.create(email="john@example.com", name="John")
        
        # Query
        users = await User.filter(name="John").all()
        
        # Update
        user.name = "Jane"
        await user.save()
        
        # Delete
        await user.delete()
    
    asyncio.run(main())
"""

# Core exports
from .connection import (
    initialize,
    close,
    get_session,
    get_pool,
    ConnectionPool,
    Session,
)

from .fields import (
    Field,
    ForeignKeyField,
    StringField,
    TextField,
    IntField,
    BigIntField,
    FloatField,
    BooleanField,
    DateField,
    TimeField,
    DateTimeField,
    UUIDField,
    JSONField,
    ArrayField,
)

from .base import Model, add_timestamps

from .query import (
    QuerySet,
    FilterChain,
    Query,
    add_queryset_methods,
)

from .pagination import Page

from .executor import (
    QueryExecutor,
    SQLBuilder,
    ResultMapper,
    QueryProfiler,
)

from .nested_prefetch import (
    NestedPrefetchDescriptor,
    NestedPrefetchQuerySet,
)

from .raw_sql import (
    RawQuery,
    ModelRawQuery,
    raw_select,
    raw_count,
    raw_insert,
    raw_update,
    raw_delete,
)

__version__ = "0.1.0"

__all__ = [
    # Connection
    "initialize",
    "close",
    "get_session",
    "get_pool",
    "ConnectionPool",
    "Session",
    # Fields
    "Field",
    "ForeignKeyField",
    "StringField",
    "TextField",
    "IntField",
    "BigIntField",
    "FloatField",
    "BooleanField",
    "DateField",
    "TimeField",
    "DateTimeField",
    "UUIDField",
    "JSONField",
    "ArrayField",
    # Model
    "Model",
    "add_timestamps",
    # Query
    "QuerySet",
    "FilterChain",
    "Query",
    "add_queryset_methods",
    # Pagination
    "Page",
    # Executor
    "QueryExecutor",
    "SQLBuilder",
    "ResultMapper",
    "QueryProfiler",
    # Nested Prefetch
    "NestedPrefetchDescriptor",
    "NestedPrefetchQuerySet",
    # Raw SQL
    "RawQuery",
    "ModelRawQuery",
    "raw_select",
    "raw_count",
    "raw_insert",
    "raw_update",
    "raw_delete",
]
