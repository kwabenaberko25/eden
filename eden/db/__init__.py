"""
Eden — Database ORM Package

Provides the data layer: Model base class, Field helpers,
Database session management, and Alembic migration integration.

✨ CANONICAL IMPORT PATH FOR ORM FEATURES

This is the recommended way to import database and ORM functionality:

    from eden.db import (
        Model,                    # Base class for your models
        Database,                 # Database connection manager
        QuerySet, Q, F, q,       # Query interface (three syntaxes)
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

from eden.db.base import Model, _MISSING
from eden.db.file_reference import FileReference
from eden.db.fields import (
    BoolField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntField,
    IntegerField,
    ManyToManyField,
    Relationship,
    Reference,
    StringField,
    SlugField,
    TextField,
    UUIDField,
    JSONField,
    JSONBField,
    ArrayField,
    EnumField,
    DecimalField,
    FileField,
    f,
)
from eden.db.validation import (
    ValidatorMixin,
    ValidationError,
    ValidationErrors,
    ValidationRule,
    ValidationResult,
)
from eden.db.metadata import (
    MaxLength,
    MinLength,
    MinValue,
    MaxValue,
    Indexed,
    Unique,
    PrimaryKey,
    Required,
    Default,
    ServerDefault,
    ForeignKey as ForeignKeyToken,
    Choices,
    Label,
    HelpText,
    Placeholder,
    UploadTo,
    CustomWidget,
    AutoNow,
    AutoNowAdd,
    JSON as JSONToken,
    OrganizationID,
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
from eden.db.lookups import F, Q, parse_lookups, q
from eden.db.mixins import SoftDeleteMixin
from eden.db.pagination import Page, PaginationLinks
from eden.db.query import QuerySet
from eden.db.session import Database, get_db, init_db, get_session, set_session, reset_session
from eden.db.session import atomic as _session_atomic
from eden.db.transactions import atomic, read_only, serializable, transaction, savepoint
from eden.db.cache import QueryCache, InMemoryCache, RedisCache, generate_cache_key
from eden.db.slugs import SlugMixin, slugify, auto_slugify_field
from eden.db.migrations import MigrationManager
from eden.context import request, user
from eden.db.ai import VectorModel, VectorField
from eden.db.discovery import discover_models
from eden.db.access import (
    AccessControl,
    PermissionRule,
    AllowRoles,
    AllowOwner,
    AllowPublic,
    AllowAuthenticated,
)


def get_models():
    """Return all registered (non-abstract) Model subclasses."""
    def _all_subclasses(cls):
        result = []
        for sub in cls.__subclasses__():
            if not getattr(sub, '__abstract__', False):
                result.append(sub)
            result.extend(_all_subclasses(sub))
        return result
    return _all_subclasses(Model)


def get_engine():
    """Return the SQLAlchemy engine from the bound database, if available."""
    db = getattr(Model, '_db', None)
    if db is None:
        raise RuntimeError("No database bound. Call db.connect() first.")
    return db.engine


__all__ = [
    "Model",
    "_MISSING",
    "FileReference",
    "Database",
    "get_db",
    "init_db",
    "discover_models",
    # Session context & transactions
    "get_session",
    "set_session",
    "reset_session",
    "atomic",
    "read_only",
    "serializable",
    "transaction",
    "savepoint",
    # Utilities
    "get_models",
    "get_engine",
    # Access Control
    "AccessControl",
    "PermissionRule",
    "AllowRoles",
    "AllowOwner",
    "AllowPublic",
    "AllowAuthenticated",
    # Lookups
    "Q",
    "F",
    "f",
    "q",
    "parse_lookups",
    "Sum",
    "Avg",
    "Count",
    "Min",
    "Max",
    "Page",
    "SoftDeleteMixin",
    "StringField",
    "SlugField",
    "IntField",
    "IntegerField",
    "TextField",
    "BoolField",
    "FloatField",
    "DateTimeField",
    "UUIDField",
    "ForeignKeyField",
    "Relationship",
    "Reference",
    "ManyToManyField",
    "JSONField",
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


# Ensure core admin models are registered for migrations/create_all
try:
    from eden.admin import models as _admin_models
except ImportError:
    pass

