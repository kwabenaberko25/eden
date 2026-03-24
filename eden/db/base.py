import re
import uuid
import asyncio
import pydantic
import weakref
import contextlib
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    Annotated,
)
from datetime import datetime
from sqlalchemy import event
from .access import AccessControl
from .validation import ValidatorMixin
from .metadata import MetadataToken
from .mixins.crud import CrudMixin
from .mixins.serialization import SerializationMixin
from .mixins.lifecycle import LifecycleMixin
# from eden.tenancy.registry import tenancy_registry (moved to local imports)

T = TypeVar("T", bound="Model")


def reactive(cls: Type[T]) -> Type[T]:
    """
    Decorator to enable real-time WebSocket broadcasting for a Model.
    When an instance is created, updated, or deleted, an event will be broadcast
    to the corresponding WebSocket channels.
    """
    cls.__reactive__ = True
    return cls


from sqlalchemy import (
    event,
    Column,
    ForeignKey,
    Table,
    MetaData,
    select,
    update,
    delete,
    func,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Uuid,
    JSON,
    inspect,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    selectinload,
    joinedload,
    declared_attr,
)
from sqlalchemy.ext.asyncio import AsyncSession
Session = AsyncSession

from .utils import _MISSING


# These are now imported from .schema
from .schema import _camel_to_snake, _PYTHON_TO_SA, _resolve_table_name


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text


class Base(DeclarativeBase):
    """SQLAlchemy Declarative Base."""

    __allow_unmapped__ = True
    type_annotation_map = {
        dict: JSON,
        list: JSON,
        uuid.UUID: Uuid,
        datetime: DateTime,
    }


class Model(Base, AccessControl, ValidatorMixin, LifecycleMixin, SerializationMixin, CrudMixin):
    """
    Base model for all Eden database models.
    Combines SQLAlchemy Declarative with Pydantic-like serialization, RLS, and ActiveRecord CRUD.
    """

    __abstract__ = True
    __allow_unmapped__ = True
    __reactive__: bool = False

    # Default RBAC rules
    from .access import AllowPublic
    __rbac__ = {
        "read": AllowPublic(),
        "create": AllowPublic(),
        "update": AllowPublic(),
        "delete": AllowPublic(),
    }

    # Tracking for schema engine
    __pending_relationships__: List[Type["Model"]] = []
    __pending_m2m__: List[Dict[str, Any]] = []
    __m2m_registry__: Dict[str, Any] = {}

    # WeakKeyDictionary for relationship caching
    _relationship_cache: ClassVar[weakref.WeakKeyDictionary] = weakref.WeakKeyDictionary()

    # Bound database instance
    _db: ClassVar[Optional[Any]] = None

    # Standard primary key for all models
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __init_subclass__(cls, **kwargs):
        """Standard Eden model initialization."""
        if "__tablename__" not in cls.__dict__ and not cls.__dict__.get("__abstract__", False):
            cls.__tablename__ = _camel_to_snake(cls.__name__) + "s"

        if not cls.__dict__.get("__abstract__", False):
            from eden.db.schema import SchemaInferenceEngine, ValidationScanner
            
            # 1. Process schema via the Engine
            SchemaInferenceEngine.process_class(cls)

            # 2. Discover validation rules
            discovered_rules = ValidationScanner.discover_rules(cls)

            super().__init_subclass__(**kwargs)

            # Apply validation rules
            for meth, name, val in discovered_rules:
                if val is not None: meth(name, val)
                else: meth(name)

            # Apply comparators
            SchemaInferenceEngine.apply_comparators(cls)

            # 3. Tenancy Auto-Discovery
            # If a model has 'tenant_id' but doesn't explicitly inherit from TenantMixin,
            # we register it for isolation anyway (Secure-by-Default).
            if hasattr(cls, "tenant_id") or "tenant_id" in cls.__annotations__:
                if not cls.__dict__.get("__abstract__", False):
                    from eden.tenancy.registry import tenancy_registry
                    tenancy_registry.register(cls)
            
            # Register event listeners for timestamp management
            @event.listens_for(cls, "before_update", propagate=True)
            def set_updated_at(mapper, connection, target):
                if hasattr(target, 'updated_at'):
                    target.updated_at = datetime.now()
        else:
            super().__init_subclass__(**kwargs)

    @classmethod
    def _bind_db(cls, db: Any) -> None:
        """Bind a Database instance so models can auto-acquire sessions."""
        Model._db = db

    @classmethod
    def to_schema(
        cls,
        include: Optional[List[str]] = None,
        exclude: Optional[set] = None,
        only_columns: bool = False,
    ) -> Type[pydantic.BaseModel]:
        """
        Convert this model class to a Pydantic schema (BaseModel representation).
        Used by the form system and OpenAPI generator.
        """
        from .schema import SchemaInferenceEngine
        return SchemaInferenceEngine.generate_pydantic_schema(
            cls, include=include, exclude=exclude, only_columns=only_columns
        )

    @classmethod
    def as_form(cls, data: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        """
        Create an Eden BaseForm instance from this model's schema.
        Accepts include/exclude as keyword arguments to filter fields.
        """
        from eden.forms import BaseForm
        schema = cls.to_schema(**kwargs)
        return BaseForm(schema=schema, data=data)

    @classmethod
    def _get_db(cls) -> Any:
        """Get the bound database instance."""
        if cls._db is None:
            raise RuntimeError("Model is not bound to a Database. Call db.connect() first.")
        return cls._db

    @classmethod
    @contextlib.asynccontextmanager
    async def _provide_session(cls):
        """Standard method to get a session."""
        from eden.db.session import get_session
        context_session = get_session()
        if context_session:
            yield context_session
            return

        from eden.context import get_request
        request = get_request()
        if request:
            session = getattr(request.state, "db_session", None) or getattr(
                request.state, "db", None
            )
            if isinstance(session, AsyncSession):
                yield session
                return

        if cls._db is None:
            raise RuntimeError("Model is not bound to a Database. Call db.connect() first.")

        async with cls._db.session() as session:
            yield session

    # Alias for legacy compatibility across the framework
    _get_session = _provide_session

    @classmethod
    def _base_select(cls, **kwargs) -> Any:
        """Cooperative base select for this model."""
        stmt = select(cls)
        applied_isolation = False
        
        # 1. Apply default filters from mixins (e.g. TenantMixin, SoftDeleteMixin)
        for base in cls.mro():
            if hasattr(base, "_apply_default_filters") and base is not Model:
                if "_apply_default_filters" in base.__dict__:
                    stmt = base._apply_default_filters(cls, stmt, **kwargs)
                    if getattr(base, "__eden_tenant_isolated__", False):
                        applied_isolation = True
        
        # 2. Secure-by-Default: If model is isolated but no mixin applied the filter, apply it now.
        from eden.tenancy.registry import tenancy_registry
        if not applied_isolation and tenancy_registry.is_isolated(cls):
            from eden.tenancy.mixins import TenantMixin
            stmt = TenantMixin._apply_tenant_filter(cls, stmt, **kwargs)
            
        return stmt

    # ── Bulk Operations ───────────────────────────────────────────────────

    @classmethod
    async def bulk_create(
        cls,
        session_or_instances: Any = None,
        instances_or_session: Any = None,
        validate: bool = True,
        batch_size: Optional[int] = None,
    ) -> List[T]:
        """
        Create multiple records efficiently.
        Triggers signals and hooks for each instance.
        """
        session = None
        instances = None

        if isinstance(session_or_instances, list):
            instances = session_or_instances
            session = instances_or_session
        elif isinstance(instances_or_session, list):
            session = session_or_instances
            instances = instances_or_session
        elif session_or_instances is not None and not hasattr(session_or_instances, "execute"):
            instances = session_or_instances
            session = None
        else:
            session = session_or_instances
            instances = instances_or_session

        if not instances:
            return []

        from .signals import pre_save, post_save
        actual_instances = [cls(**inst) if isinstance(inst, dict) else inst for inst in instances]

        async def _internal_save(inst, sess):
            is_new = inst.id is None
            await pre_save.send(sender=cls, instance=inst, is_new=is_new, session=sess)
            if is_new:
                await inst._call_hook("before_create", sess)
            await inst._call_hook("before_save", sess)
            if validate:
                await inst.full_clean()
            sess.add(inst)

        async def _internal_after(inst, sess):
            is_new = True # Bulk create is always new conceptually, but let's be safe
            if inst.id is not None:
                await inst._call_hook("after_create", sess)
            await inst._call_hook("after_save", sess)
            await post_save.send(sender=cls, instance=inst, is_new=True, session=sess)

        db = cls._get_db()
        async with db.transaction(session=session) as sess:
            for i, inst in enumerate(actual_instances):
                await _internal_save(inst, sess)
                if batch_size and (batch_size > 0) and (i + 1) % batch_size == 0:
                    await sess.flush()
            
            await sess.flush()
            for inst in actual_instances:
                await _internal_after(inst, sess)
            return actual_instances

    @classmethod
    async def bulk_update_mapping(
        cls, mappings: list[dict[str, Any]], id_field: str = "id", session: Optional[Any] = None
    ) -> int:
        """Batch update."""
        if not mappings: return 0
        from sqlalchemy import case, update
        all_fields = {k for d in mappings for k in d.keys() if k != id_field}
        if not all_fields: return 0
        id_col = getattr(cls, id_field)
        ids = [m[id_field] for m in mappings]
        set_values = {}
        for field in all_fields:
            whens = []
            for m in mappings:
                if field in m:
                    whens.append((id_col == m[id_field], m[field]))
            if whens:
                set_values[field] = case(*whens, else_=getattr(cls, field))
        stmt = update(cls).where(id_col.in_(ids)).values(set_values)
        db = cls._get_db()
        async with db.transaction(session=session) as sess:
            result = await sess.execute(stmt)
            await sess.flush()
            return result.rowcount

    @classmethod
    async def checkpoint(cls, session: Optional[Any] = None) -> Any:
        """SAVEPOINT."""
        if session: return await session.begin_nested()
        raise ValueError("checkpoint() requires an explicit session.")

    @classmethod
    async def rollback_to(cls, savepoint: Any) -> None:
        """Rollback to savepoint."""
        await savepoint.rollback()

    @classmethod
    def raw(cls, sql: str, params: Optional[List[Any]] = None) -> Any:
        """Raw SQL query."""
        from .raw_sql import RawQuery
        async def _execute():
            results = await RawQuery.execute(sql, params)
            if not results: return []
            instances = []
            for row in results:
                instance = cls()
                for field in cls.__table__.columns.keys():
                    if field in row: setattr(instance, field, row[field])
                instances.append(instance)
            return instances
        return _execute()

# Register listeners
from .listeners import register_listeners
register_listeners(Model)
