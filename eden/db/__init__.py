"""
Eden — Database ORM Package

Provides the data layer: Model base class, Field helpers,
Database session management, and Alembic migration integration.

✨ CANONICAL IMPORT PATH FOR ORM FEATURES

This is the recommended way to import database and ORM functionality:

    from eden.db import (
        Model,                    # Base class for your models
        Database,                 # Database connection manager
        QuerySet, Q, F,          # Query interface
        StringField, IntField,   # Field definitions
        ForeignKeyField,         # Relationships
        Page,                    # Pagination
        SoftDeleteMixin,         # Soft delete behavior
        MigrationManager,        # Database migrations
    )

    # Also available: SQLAlchemy utilities
    from eden.db import select, insert, update, delete, func
    from eden.db import and_, or_, not_, desc, asc
    from eden.db import JSON, Mapped, relationship

BACKWARD COMPATIBILITY:
    from eden import Model  # Still works, but imports from here internally
    from eden.orm import Model  # Deprecated but works until v1.0.0

KEY EXPORTS (230+ items total):
    - Model base class and ORM utilities (Mapped, relationship, etc.)
    - Field types: StringField, IntField, FloatField, BoolField, etc.
    - Query helpers: Q (queries), F (field references), QuerySet
    - SQLAlchemy re-exports: select, insert, update, delete, and more
    - Aggregation: Sum, Avg, Count, Min, Max
    - Pagination: Page class for result sets
    - Soft deletes: SoftDeleteMixin
    - Row-level security: AccessControl, PermissionRule, AllowRoles, etc.
    - AI/Vector support: VectorModel, VectorField for pgvector
"""

from eden.db.base import Model
from eden.db.fields import (
    BoolField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntField,
    ManyToManyField,
    Relationship,
    Reference,
    StringField,
    TextField,
    UUIDField,
    FileField,
    f,
)
from sqlalchemy import (
    select,
    update,
    delete,
    insert,
    func,
    text,
    inspect,
    event,
    MetaData,
    Table,
    Column,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
    PrimaryKeyConstraint,
    ForeignKeyConstraint,
    Sequence,
    Identity,
    Computed,
    DefaultClause,
    String,
    Integer,
    SmallInteger,
    BigInteger,
    Numeric,
    Float,
    Boolean,
    DateTime,
    Date,
    Time,
    Interval,
    Uuid,
    JSON,
    Enum,
    ARRAY,
    Unicode,
    UnicodeText,
    LargeBinary,
    TypeDecorator,
    and_,
    or_,
    not_,
    desc,
    asc,
    union,
    union_all,
    exists,
    distinct,
    between,
    case,
    cast,
    extract,
    null,
    true,
    false,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    selectinload,
    joinedload,
    subqueryload,
    contains_eager,
    aliased,
    column_property,
    validates,
)
from sqlalchemy.ext.asyncio import AsyncSession

from eden.db.aggregates import Sum, Avg, Count, Min, Max
from eden.db.lookups import F, Q
from eden.db.mixins import SoftDeleteMixin
from eden.db.pagination import Page
from eden.db.query import QuerySet
from eden.db.session import Database, get_db, init_db
from eden.db.migrations import MigrationManager
from eden.context import request, user
from eden.db.ai import VectorModel, VectorField


__all__ = [
    "Model",
    "Database",
    "get_db",
    "init_db",
    "Q",
    "F",
    "f",
    "Sum",
    "Avg",
    "Count",
    "Min",
    "Max",
    "Page",
    "SoftDeleteMixin",
    "StringField",
    "IntField",
    "TextField",
    "BoolField",
    "FloatField",
    "DateTimeField",
    "UUIDField",
    "ForeignKeyField",
    "Relationship",
    "Reference",
    "ManyToManyField",
    "FileField",
    "QuerySet",
    "MigrationManager",
    "Mapped",
    "mapped_column",
    "relationship",
    "selectinload",
    "joinedload",
    "select",
    "update",
    "delete",
    "insert",
    "func",
    "text",
    "inspect",
    "event",
    "MetaData",
    "Table",
    "Column",
    "ForeignKey",
    "Index",
    "UniqueConstraint",
    "CheckConstraint",
    "PrimaryKeyConstraint",
    "ForeignKeyConstraint",
    "Sequence",
    "Identity",
    "Computed",
    "DefaultClause",
    "AsyncSession",
    "String",
    "Integer",
    "SmallInteger",
    "BigInteger",
    "Numeric",
    "Float",
    "Boolean",
    "DateTime",
    "Date",
    "Time",
    "Interval",
    "Uuid",
    "JSON",
    "Enum",
    "ARRAY",
    "Unicode",
    "UnicodeText",
    "LargeBinary",
    "TypeDecorator",
    "and_",
    "or_",
    "not_",
    "desc",
    "asc",
    "union",
    "union_all",
    "exists",
    "distinct",
    "between",
    "case",
    "cast",
    "extract",
    "null",
    "true",
    "false",
    "subqueryload",
    "contains_eager",
    "aliased",
    "column_property",
    "validates",
    "request",
    "user",
    "VectorModel",
    "VectorField",
]

