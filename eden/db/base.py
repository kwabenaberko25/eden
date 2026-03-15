import re
import uuid
import asyncio
import pydantic
import weakref
import contextlib
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar, Union, get_type_hints
from datetime import datetime
from .access import AccessControl
from .validation import ValidatorMixin

T = TypeVar("T", bound="Model")
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
)
from sqlalchemy.ext.asyncio import AsyncSession
Session = AsyncSession

# Internal sentinel for missing values
_MISSING = object()


def _camel_to_snake(name: str) -> str:
    """Helper to convert CamelCase to snake_case."""
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text


def _resolve_table_name(target_name: str) -> str:
    """Safely resolve table name for a target class name, respecting custom __tablename__."""
    try:
        # 1. Check if target_name refers to a class already in the registry
        reg = Base.registry._class_registry
        if target_name in reg:
            target_cls = reg[target_name]
            if hasattr(target_cls, "__tablename__"):
                return target_cls.__tablename__
            
        # 2. Search known Model subclasses if not in registry yet 
        # (common during early import phase or discovery)
        for sub in Model.__subclasses__():
            if sub.__name__ == target_name:
                if hasattr(sub, "__tablename__"):
                    return sub.__tablename__
                break
                
    except (KeyError, AttributeError, NameError):
        # NameError might occur if Model is not yet defined
        pass

    # Fallback to Eden convention: CamelCase -> camel_cases
    return _camel_to_snake(target_name) + "s"


class Base(DeclarativeBase):
    """SQLAlchemy Declarative Base."""

    __allow_unmapped__ = True
    type_annotation_map = {
        dict: JSON,
        list: JSON,
        uuid.UUID: Uuid,
        datetime: DateTime,
    }




class Model(Base, AccessControl, ValidatorMixin):
    """
    Base model for all Eden database models.
    Combines SQLAlchemy Declarative with Pydantic-like serialization and RLS.
    """

    __abstract__ = True
    __allow_unmapped__ = True
    __reactive__: bool = False

    # Default RBAC rules (allow all by default, override in subclasses)
    from .access import AllowPublic
    __rbac__ = {
        "read": AllowPublic(),
        "create": AllowPublic(),
        "update": AllowPublic(),
        "delete": AllowPublic(),
    }

    # Track models for deferred relationship inference
    __pending_relationships__: List[Type["Model"]] = []
    __pending_m2m__: List[Dict[str, Any]] = []
    __m2m_registry__: Dict[str, Any] = {}

    # WeakKeyDictionary for relationship caching to prevent memory leaks
    _relationship_cache: ClassVar[weakref.WeakKeyDictionary] = weakref.WeakKeyDictionary()

    # Bound database instance
    _db: ClassVar[Optional[Any]] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Called when a subclass of Model is created.
        Automatically infers relationships from type hints to enable fluent ORM API.
        
        This ensures that relationships defined in a subclass are discovered and registered
        immediately when the class is defined, before any instances are created or queries run.
        """
        super().__init_subclass__(**kwargs)
        
        # Immediately infer relationships when subclass is defined
        # unless it's abstract (which shouldn't have concrete relationships)
        if not getattr(cls, "__abstract__", False):
            try:
                cls._infer_relationships_immediate()
            except Exception:
                # Log but don't fail class definition if inference has issues
                import logging
                logger = logging.getLogger("eden.db.base")
                logger.debug(f"Relationship inference skipped for {cls.__name__}", exc_info=True)

    # Standard primary key for all models
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=func.uuid_generate_v4() if False else None,
        default=uuid.uuid4,
    )

    # Timestamps (B1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Manual implementation of model serialization."""
        exclude = kwargs.get("exclude", set())
        include = kwargs.get("include", None)

        data = {}
        # Get columns from the table
        for column in self.__table__.columns:
            name = column.name
            if name in exclude:
                continue
            if include is not None and name not in include:
                continue

            value = getattr(self, name)
            if isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            data[name] = value
        return data

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert model instance to dictionary (utility)."""
        return self.model_dump(**kwargs)

    @classmethod
    def _infer_relationships_immediate(cls):
        """
        Introspect type hints to automatically define SQLAlchemy relationships.
        Supported patterns:
        - Mapped[List["OtherModel"]] -> one-to-many
        - Mapped["OtherModel"] -> many-to-one
        - Mapped[List["OtherModel"]] with ManyToManyField -> many-to-many
        """
        from sqlalchemy.orm import RelationshipProperty, relationship as sa_rel
        import re

        inferred_names = []
        annotations = getattr(cls, "__annotations__", {})

        for name, hint in list(annotations.items()):
            hint_str = str(hint)
            is_list = False

            # Detect List/Collection
            if "List[" in hint_str or "list[" in hint_str:
                is_list = True

            content = hint_str
            if "Mapped[" in content:
                # Be robust: find the innermost type in Mapped[...]
                try:
                    content = content.split("Mapped[", 1)[1].rsplit("]", 1)[0]
                except (IndexError, AttributeError):
                    pass

            # Handle potential Annotated or other wrappers that might still be in the string
            if "Annotated[" in content:
                try:
                    content = content.split("Annotated[", 1)[1].split(",", 1)[0].strip()
                except (IndexError, AttributeError):
                    pass

            # Extract name and check for basic types properly
            # Handle <class '...'> representations
            if "<class '" in content:
                content = content.split("<class '", 1)[1].split("'", 1)[0]

            match = re.search(r"['\"](\w+)['\"]", content)
            if match:
                target_name = match.group(1)
            else:
                # Robust extraction: "typing.Optional[Project]" -> "Project"
                # "typing.List['Task']" -> "Task"
                target_name = content
                if "[" in target_name:
                    target_name = target_name.split("[")[-1].split("]")[0]
                if "." in target_name:
                    target_name = target_name.split(".")[-1]
                target_name = target_name.strip("'\" >")

            # Skip basic types and lowercase names
            basic_types = (
                "str",
                "int",
                "float",
                "bool",
                "uuid.UUID",
                "UUID",
                "datetime",
                "dict",
                "list",
                "Any",
                "None",
                "uuid",
                "Decimal",
                "decimal",
            )
            if (
                not target_name
                or any(bt.lower() == target_name.lower() for bt in basic_types)
                or target_name[0].islower()
            ):
                continue

            if not target_name or not target_name[0].isupper() or "." in target_name:
                continue

            # Verify it's likely a model (starts with uppercase)
            # and is not in basic types
            if any(bt.lower() == target_name.lower() for bt in basic_types):
                continue

            inferred_names.append(name)

            # Detect Reference or M2M helper
            existing = cls.__dict__.get(name)
            is_ref = False
            is_m2m_explicit = False
            ref_info = {}
            if existing is not None:
                from sqlalchemy.orm import RelationshipProperty

                if isinstance(existing, RelationshipProperty) and hasattr(existing, "info"):
                    if existing.info.get("is_reference"):
                        is_ref = True
                        ref_info = existing.info
                    elif existing.info.get("is_m2m"):
                        is_m2m_explicit = True

            # Skip if already defined explicitly AND it's not a Reference helper AND not a M2M helper needing secondary
            if existing is not None and not is_ref and not is_m2m_explicit:
                if isinstance(existing, RelationshipProperty):
                    if getattr(existing, "argument", None) is None:
                        new_rel = sa_rel(
                            target_name,
                            back_populates=getattr(existing, "back_populates", None),
                            lazy=getattr(existing, "lazy", "selectin"),
                            overlaps="*",
                            uselist=False if not is_list else None,
                            foreign_keys=f"{cls.__name__}.{name}_id" if not is_list else None,
                        )
                        setattr(cls, name, new_rel)
                continue

            # Auto-infer relationship OR process Reference
            if is_list and is_m2m_explicit:
                cls._setup_m2m(name, target_name)
            elif is_list:
                # One-to-Many (One side)
                backref_name = _camel_to_snake(cls.__name__)
                _back_populates_val = ref_info.get("back_populates")

                kwargs = {
                    "back_populates": _back_populates_val,
                    "lazy": ref_info.get("lazy", "selectin"),
                    "overlaps": "*",
                }
                if not _back_populates_val:
                    kwargs["backref"] = backref_name + "s"

                setattr(cls, name, sa_rel(target_name, **kwargs))
            else:
                # Single relationship (Many side)
                fk_col = f"{name}_id"

                # Check for Reference metadata override
                on_delete = ref_info.get("on_delete", "CASCADE")
                is_required = (
                    ref_info.get("required", True) if is_ref else False
                )  # Default inferred rels are nullable
                fk_index = ref_info.get("index", True)
                fk_type_override = ref_info.get("fk_type")

                if not hasattr(cls, fk_col):
                    # Find the target class to correctly infer FK type and table name
                    target_cls = None
                    for sub in Model.__subclasses__():
                        if sub.__name__ == target_name:
                            target_cls = sub
                            break

                    target_table = (
                        target_cls.__tablename__
                        if target_cls and hasattr(target_cls, "__tablename__")
                        else _resolve_table_name(target_name)
                    )

                    if fk_type_override:
                        fk_type = fk_type_override
                    elif (
                        target_cls
                        and hasattr(target_cls, "id")
                        and hasattr(target_cls, "__table__")
                        and hasattr(target_cls.__table__.c.id, "type")
                    ):
                        # If table is already reflected/defined
                        fk_type = target_cls.__table__.c.id.type
                    elif (
                        target_cls and hasattr(target_cls, "id") and hasattr(target_cls.id, "type")
                    ):
                        fk_type = target_cls.id.type
                    else:
                        # Fallback heuristic
                        fk_type = Uuid if "user" not in target_table else Integer

                    # print(f"DEBUG: Setting {cls.__name__}.{fk_col} as FK to {target_table}.id (type={fk_type})")
                    col = mapped_column(
                        fk_type,
                        ForeignKey(f"{target_table}.id", ondelete=on_delete),
                        nullable=not is_required,
                        index=fk_index,
                    )
                    setattr(cls, fk_col, col)

                # In Eden, we default to singular backref for singular hints
                # and plural backref for list hints.
                backref_name = _camel_to_snake(cls.__name__)
                if is_list:
                    backref_name += "s"

                _back_populates_val = ref_info.get("back_populates")
                kwargs = {
                    "back_populates": _back_populates_val,
                    "overlaps": "*",
                    "uselist": False if not is_list else None,
                    "foreign_keys": f"{cls.__name__}.{fk_col}",
                }
                if not _back_populates_val:
                    kwargs["backref"] = backref_name

                setattr(cls, name, sa_rel(target_name, **kwargs))

        return inferred_names

    @classmethod
    def resolve_all_relationships(cls) -> None:
        """
        Force resolution of all pending relationships.
        Usually called during Database.connect() to ensure metadata is complete.
        """
        # Process deferred many-to-many tables
        while cls.__pending_m2m__:
            data = cls.__pending_m2m__.pop(0)
            cls._create_m2m_table(data)

    def __init_subclass__(cls, **kwargs):
        """Standard Eden model initialization."""
        # Auto-generate __tablename__ if not specified in this class direct dict
        if "__tablename__" not in cls.__dict__ and not cls.__dict__.get("__abstract__", False):
            cls.__tablename__ = _camel_to_snake(cls.__name__) + "s"

        # Inferred Relationships from Type Hints
        if not cls.__dict__.get("__abstract__", False):
            # Save original annotations
            original_annotations = dict(cls.__annotations__)

            # Run inference and get names of relationships to hide from SA mapping
            rel_names = cls._infer_relationships_immediate()

            # Stealth: Remove relationship annotations so SA doesn't try to resolve them
            # but keep column annotations so they are mapped correctly.
            for name in rel_names:
                if name in cls.__annotations__:
                    del cls.__annotations__[name]

            # Discover validation rules BEFORE SQLAlchemy consumes the mapped_column objects
            discovered_rules = []
            for name, attr in cls.__dict__.items():
                info = None
                if hasattr(attr, "info"):
                    info = attr.info
                elif hasattr(attr, "column") and hasattr(attr.column, "info"):
                    info = attr.column.info
                
                if info:
                    if "max" in info:
                        discovered_rules.append((cls.max_length, name, info["max"]))
                    if "min" in info:
                        discovered_rules.append((cls.min_length, name, info["min"]))
                    if "required" in info and info["required"]:
                        discovered_rules.append((cls.required, name, None))

            try:
                super().__init_subclass__(**kwargs)
            finally:
                # Restore original annotations for Pydantic/Forms
                cls.__annotations__.clear()
                cls.__annotations__.update(original_annotations)

            # Apply discovered rules AFTER super() has initialized _validation_rules
            for meth, name, val in discovered_rules:
                if val is not None:
                    meth(name, val)
                else:
                    meth(name)
        else:
            super().__init_subclass__(**kwargs)

    @classmethod
    def _setup_m2m(cls, name: str, target_name: str) -> None:
        """Sets up a many-to-many relationship with an implicit join table."""
        # Standardize join table name: rel_post_tags (sorted to be unique)
        cls_snake = _camel_to_snake(cls.__name__)
        names = sorted([cls_snake, _camel_to_snake(target_name)])
        table_name = f"rel_{names[0]}_{names[1]}"

        if table_name not in cls.__m2m_registry__:
            # Create the M2M table immediately in metadata
            cls._create_m2m_table(
                {
                    "table_name": table_name,
                    "cls": cls,
                    "target_name": target_name,
                    "cls_snake": cls_snake,
                }
            )
            cls.__m2m_registry__[table_name] = True

        # Setup the relationship
        existing = getattr(cls, name, None)
        is_sa_rel = hasattr(existing, "argument")

        if getattr(existing, "secondary", None) is None:
            # Find the target model class for back_populates check
            target_cls = None
            for sub in Model.__subclasses__():
                if sub.__name__ == target_name:
                    target_cls = sub
                    break

            # Check if it's a mutual relationship (both sides defined)
            backref_name = _camel_to_snake(cls.__name__) + "s"
            target_has_it = False
            if target_cls:
                target_annotations = getattr(target_cls, "__annotations__", {})
                target_has_it = any(backref_name == k for k in target_annotations.keys())

            # Use data from existing if present
            back_populates = getattr(existing, "back_populates", None)
            if not back_populates and target_has_it:
                back_populates = backref_name

            setattr(
                cls,
                name,
                relationship(
                    target_name,
                    secondary=table_name,
                    back_populates=back_populates,
                    backref=getattr(existing, "backref", None)
                    or (backref_name if not back_populates else None),
                    lazy=getattr(existing, "lazy", "selectin"),
                    overlaps=getattr(existing, "overlaps", name),
                ),
            )

    @classmethod
    def _create_m2m_table(cls, data: Dict[str, Any]) -> None:
        """Actually creates the M2M table in metadata."""
        table_name = data["table_name"]
        source_cls = data["cls"]
        target_name = data["target_name"]
        cls_snake = data["cls_snake"]

        target_cls = None
        for sub in Model.__subclasses__():
            if sub.__name__ == target_name:
                target_cls = sub
                break

        # Process M2M table
        existing = cls.registry.metadata.tables.get(table_name)
        if existing is not None:
            return

        try:
            if target_cls:
                target_table_name = (
                    target_cls.__tablename__
                    if hasattr(target_cls, "__tablename__")
                    else f"{_camel_to_snake(target_name)}s"
                )
                source_table_name = source_cls.__tablename__
                Table(
                    table_name,
                    cls.registry.metadata,
                    Column(
                        f"{cls_snake}_id",
                        source_cls.id.type,
                        ForeignKey(f"{source_table_name}.id", ondelete="CASCADE"),
                        primary_key=True,
                    ),
                    Column(
                        f"{_camel_to_snake(target_name)}_id",
                        target_cls.id.type,
                        ForeignKey(f"{target_table_name}.id", ondelete="CASCADE"),
                        primary_key=True,
                    ),
                    extend_existing=True,
                )
            else:
                # Final fallback
                source_table_name = source_cls.__tablename__
                Table(
                    table_name,
                    cls.registry.metadata,
                    Column(
                        f"{cls_snake}_id",
                        Uuid,
                        ForeignKey(f"{source_table_name}.id", ondelete="CASCADE"),
                        primary_key=True,
                    ),
                    Column(
                        f"{_camel_to_snake(target_name)}_id",
                        Uuid,
                        ForeignKey(f"{_camel_to_snake(target_name)}s.id", ondelete="CASCADE"),
                        primary_key=True,
                    ),
                    extend_existing=True,
                )
        except Exception as e:
            # Table probably already exists in this metadata instance or error
            import traceback

            traceback.print_exc()
            pass

    # ── Modern Type Mapping (SA 2.0) ──────────────────────────────────────

    type_annotation_map = {
        str: String(255),
        int: Integer,
        float: Float,
        bool: Boolean,
        datetime: DateTime(timezone=True),
        uuid.UUID: Uuid,
        dict: JSON,
        list: JSON,
    }

    # ── Database Binding (auto-session support) ───────────────────────────

    @classmethod
    def _bind_db(cls, db: Any) -> None:
        """Bind a Database instance so models can auto-acquire sessions."""
        Model._db = db

    @classmethod
    def _get_db(cls) -> Any:
        """Get the bound database instance."""
        if cls._db is None:
            raise RuntimeError("Model is not bound to a Database. Call db.connect() first.")
        return cls._db

    @classmethod
    @contextlib.asynccontextmanager
    async def _provide_session(cls):
        """
        Standard method to get a session, using the bound DB if available.
        Synchronizes with the current request context if active (B1).
        """
        from eden.context import get_request
        from sqlalchemy.ext.asyncio import AsyncSession

        # Check for context session first (async-safe contextvar)
        from eden.db.session import get_session
        context_session = get_session()
        if context_session:
            yield context_session
            return

        request = get_request()
        if request:
            # Check if there is an active session already attached to the request state
            session = getattr(request.state, "db_session", None) or getattr(
                request.state, "db", None
            )

            if isinstance(session, AsyncSession):
                yield session
                return

        # Fallback to creating a new session from the bound database
        if cls._db is None:
            raise RuntimeError("Model is not bound to a Database. Call db.connect() first.")

        async with cls._db.session() as session:
            yield session

    # Alias for backward compatibility
    _get_session = _provide_session

    # ── CRUD Operations ───────────────────────────────────────────────────

    @classmethod
    def _base_select(cls) -> Any:
        """Standard base select for this model."""
        from sqlalchemy import select

        stmt = select(cls)

        # Check for tenant isolation mixin (robust against MRO issues)
        if getattr(cls, "__eden_tenant_isolated__", False):
            # Call the mixin's hook if it exists, otherwise apply basic filter
            if hasattr(cls, "_apply_tenant_filter"):
                stmt = cls._apply_tenant_filter(stmt)
            else:
                # Fallback: Manual implementation to ensure it works even if mixin method isn't called
                from eden.tenancy.context import get_current_tenant_id

                tenant_id = get_current_tenant_id()
                if tenant_id is not None:
                    stmt = stmt.where(cls.tenant_id == tenant_id)
                # If tenant_id is None and isolation is enabled, we intentionally return nothing
                # (Fail-Secure) - unless it's a background task context, which should explicitly opt-out.

        return stmt

    @classmethod
    def query(cls, session: Optional[Any] = None) -> "QuerySet":
        """Returns a QuerySet for this model."""
        from .query import QuerySet

        return QuerySet(cls, session=session)

    @classmethod
    def accessible_by(cls, user: Any, action: str = "read", session: Optional[Any] = None) -> "QuerySet":
        """
        Returns a QuerySet pre-filtered for the given user and action.
        This provides a secure entry point for all model queries.
        """
        return cls.query(session=session).for_user(user, action=action)

    @classmethod
    async def get(
        cls, session: Optional[Any] = None, id: Union[uuid.UUID, str, None] = None
    ) -> Optional[T]:
        """Fetch a single record by primary key."""
        # Handle (id) or (session, id)
        if id is None and session is not None and not hasattr(session, "execute"):
            id = session
            session = None
        return await cls.query(session=session).filter(id=id).first()

    @classmethod
    async def all(cls, *args, **kwargs) -> List[T]:
        """Fetch all records."""
        session = kwargs.pop("session", None)
        if args and hasattr(args[0], "execute"):
            session = args[0]
            args = args[1:]

        qs = cls.query(session=session)
        prefetch = kwargs.pop("prefetch", None)
        if prefetch:
            qs = qs.prefetch(*prefetch)
        return await qs.all()

    @classmethod
    async def get_or_404(
        cls, session: Optional[Any] = None, id: Union[uuid.UUID, str, None] = None
    ) -> T:
        """Fetch a single record by primary key or raise NotFound."""
        record = await cls.get(session, id)
        if not record:
            from eden.exceptions import NotFound

            raise NotFound(detail=f"{cls.__name__} with ID {id} not found.")
        return record

    @classmethod
    def filter(cls, *args, **kwargs) -> "QuerySet":
        """Filter records."""
        session = kwargs.pop("session", None)
        if args and hasattr(args[0], "execute"):
            session = args[0]
            args = args[1:]

        qs = cls.query(session=session)
        prefetch = kwargs.pop("prefetch", None)
        if prefetch:
            qs = qs.prefetch(*prefetch)
        return qs.filter(*args, **kwargs)

    @classmethod
    def exclude(cls, *args, **kwargs) -> "QuerySet":
        """Exclude records matching the criteria."""
        session = kwargs.pop("session", None)
        if args and hasattr(args[0], "execute"):
            session = args[0]
            args = args[1:]

        qs = cls.query(session=session)
        prefetch = kwargs.pop("prefetch", None)
        if prefetch:
            qs = qs.prefetch(*prefetch)
        return qs.exclude(*args, **kwargs)

    @classmethod
    def order_by(cls, *args, **kwargs) -> "QuerySet":
        """Order records."""
        session = kwargs.pop("session", None)
        if args and hasattr(args[0], "execute"):
            session = args[0]
            args = args[1:]

        return cls.query(session=session).order_by(*args, **kwargs)

    @classmethod
    async def filter_one(cls, *args, **kwargs) -> Optional[T]:
        """Fetch a single record matching the criteria."""
        return await cls.filter(*args, **kwargs).first()

    @classmethod
    async def count(cls, *args, **kwargs) -> int:
        """Return the total number of records matching the criteria."""
        return await cls.filter(*args, **kwargs).count()

    @classmethod
    async def search(
        cls,
        query: Optional[str],
        fields: Optional[List[str]] = None,
        session: Optional[Any] = None,
    ) -> List[T]:
        """
        Search records by matching a query string across text columns.

        If ``fields`` is not specified, all String/Text columns are searched.
        Uses case-insensitive ``LIKE`` (icontains) matching.

        Args:
            query: The search term. Returns all records if empty/None.
            fields: Explicit list of column names to search.
            session: Optional database session.

        Returns:
            List of matching model instances.

        Usage::

            results = await Post.search("django")
            results = await Post.search("hello", fields=["title", "body"])
        """
        if not query or not query.strip():
            return await cls.all(session=session)

        from eden.db.lookups import Q

        # Determine searchable fields
        if fields:
            search_fields = fields
        else:
            from sqlalchemy import String as SAString, Text as SAText

            search_fields = []
            for col in cls.__table__.columns:
                if isinstance(col.type, (SAString, SAText)):
                    search_fields.append(col.name)

        if not search_fields:
            return []

        # Build OR query across all searchable fields
        q_obj = None
        for field_name in search_fields:
            lookup = Q(**{f"{field_name}__icontains": query.strip()})
            q_obj = lookup if q_obj is None else (q_obj | lookup)

        return await cls.filter(q_obj, session=session).all()

    @classmethod
    async def paginate(cls, *args, **kwargs) -> Any:
        """Paginate records."""
        session = kwargs.pop("session", None)
        if args and hasattr(args[0], "execute"):
            session = args[0]
            args = args[1:]

        page = kwargs.pop("page", 1)
        per_page = kwargs.pop("per_page", 20)

        if len(args) > 0:
            page = args[0]
        if len(args) > 1:
            per_page = args[1]

        return await cls.filter(session=session, **kwargs).paginate(page, per_page)

    async def _call_hook(self, hook_name: str, session: Any) -> None:
        """Call a lifecycle hook if it exists, supporting both sync and async implementations."""
        hook = getattr(self, hook_name, None)
        if hook and callable(hook):
            import inspect
            res = hook(session)
            if inspect.isawaitable(res):
                await res

    @classmethod
    async def create(cls, session: Optional[Any] = None, **kwargs) -> T:
        """Create a new record and save it to the database."""
        instance = cls(**kwargs)
        await instance.save(session)
        return instance

    @classmethod
    async def create_from(cls, source: Any, session: Optional[Any] = None) -> T:
        """
        Create a new model instance from a validated Form, Schema, or dict.
        Matches keys in the source against model field names.
        """
        # Data extraction
        if hasattr(source, "model_instance") and source.model_instance:
            # It's a bound Form
            data = source.model_instance.model_dump()
        elif hasattr(source, "model_dump"):
            # It's a Schema/BaseModel instance
            data = source.model_dump()
        elif isinstance(source, dict):
            data = source
        else:
            raise TypeError(f"Cannot create {cls.__name__} from {type(source)}")

        # Filter only valid fields
        from sqlalchemy import inspect

        mapper = inspect(cls)
        valid_keys = set(mapper.columns.keys()) | set(mapper.relationships.keys())

        filtered_data = {k: v for k, v in data.items() if k in valid_keys and k != "id"}

        return await cls.create(session=session, **filtered_data)

    async def update_from(self, source: Any, session: Optional[Any] = None) -> Any:
        """
        Update this model instance from a validated Form, Schema, or dict.
        Matches keys in the source against model field names.
        """
        # Data extraction
        if hasattr(source, "model_instance") and source.model_instance:
            data = source.model_instance.model_dump()
        elif hasattr(source, "model_dump"):
            data = source.model_dump()
        elif isinstance(source, dict):
            data = source
        else:
            raise TypeError(f"Cannot update {self.__class__.__name__} from {type(source)}")

        from sqlalchemy import inspect

        mapper = inspect(self.__class__)
        valid_keys = set(mapper.columns.keys()) | set(mapper.relationships.keys())

        for k, v in data.items():
            if k in valid_keys and k != "id":
                setattr(self, k, v)

        await self.save(session)
        return self

    @classmethod
    async def get_or_create(
        cls, session: Optional[Any] = None, defaults: Optional[Dict[str, Any]] = None, **kwargs
    ) -> tuple[T, bool]:
        """Fetch a record or create it if not found."""
        obj = await cls.filter_one(session=session, **kwargs)
        if obj:
            return obj, False

        params = {**kwargs, **(defaults or {})}
        return await cls.create(session=session, **params), True

    @classmethod
    async def bulk_create(
        cls,
        session_or_instances: Any = None,
        instances_or_session: Any = None,
        validate: bool = True,
    ) -> List[T]:
        """
        Create multiple records in a single operation.

        Args:
            session: Optional SQLAlchemy session.
            instances: List of model instances or dictionaries.
            validate: Whether to run full_clean() on each instance.
        """
        # Signature resolution: (session, instances) or (instances, session=None)
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

        # Convert dicts to instances if necessary
        actual_instances = [cls(**inst) if isinstance(inst, dict) else inst for inst in instances]

        if session:
            for inst in actual_instances:
                # Lifecycle hooks - Phase 1: Before
                await inst._call_hook("before_create", session)
                await inst._call_hook("before_save", session)

                if validate:
                    await inst.full_clean()

                session.add(inst)

            await session.flush()

            for inst in actual_instances:
                # Lifecycle hooks - Phase 2: After
                await inst._call_hook("after_create", session)
                await inst._call_hook("after_save", session)

            return actual_instances

        # No session provided, use context manager
        async with cls._provide_session() as sess:
            for inst in actual_instances:
                await inst._call_hook("before_create", sess)
                await inst._call_hook("before_save", sess)

                if validate:
                    await inst.full_clean()

                sess.add(inst)

            await sess.flush()

            for inst in actual_instances:
                await inst._call_hook("after_create", sess)
                await inst._call_hook("after_save", sess)

            await sess.commit()
            return actual_instances

    @classmethod
    async def bulk_update_mapping(
        cls, mappings: list[dict[str, Any]], id_field: str = "id", session: Optional[Any] = None
    ) -> int:
        """
        Efficiently update multiple records with different values in a single statement.
        Uses SQL CASE statements for high-performance batch updates.

        Args:
            mappings: List of dicts with id and fields to update.
            id_field: Name of the ID field (default: 'id').
            session: Optional database session.

        Example:
            await User.bulk_update_mapping([
                {"id": 1, "status": "active", "points": 100},
                {"id": 2, "status": "inactive", "points": 0},
            ])
        """
        if not mappings:
            return 0

        from sqlalchemy import case, update

        # Extract all field names that appear in the mappings (excluding ID)
        all_fields = {k for d in mappings for k in d.keys() if k != id_field}
        if not all_fields:
            return 0

        id_col = getattr(cls, id_field)
        ids = [m[id_field] for m in mappings]

        set_values = {}
        for field in all_fields:
            whens = []
            for m in mappings:
                if field in m:
                    whens.append((id_col == m[id_field], m[field]))

            if whens:
                # Build CASE WHEN id = 1 THEN 'val1' ... ELSE current_val END
                set_values[field] = case(*whens, else_=getattr(cls, field))

        stmt = update(cls).where(id_col.in_(ids)).values(set_values)

        if session:
            result = await session.execute(stmt)
            return result.rowcount

        async with cls._provide_session() as sess:
            result = await sess.execute(stmt)
            await sess.commit()
            return result.rowcount

    @classmethod
    async def checkpoint(cls, session: Optional[Any] = None) -> Any:
        """
        Start a nested transaction (SAVEPOINT).
        Returns a transaction object that acts as a context manager.
        """
        if session:
            return await session.begin_nested()

        # Savepoints require an explicit session context to be useful
        raise ValueError("checkpoint() requires an explicit session.")

    @classmethod
    async def rollback_to(self, savepoint: Any) -> None:
        """Rollback to a specific savepoint."""
        await savepoint.rollback()

    @classmethod
    def raw(cls, sql: str, params: Optional[List[Any]] = None) -> Any:
        """
        Execute raw SQL and map results to model instances.
        Example: users = await User.raw("SELECT * FROM users WHERE active = $1", [True])
        """
        from .raw_sql import RawQuery
        
        async def _execute():
            results = await RawQuery.execute(sql, params)
            if not results: return []
            
            instances = []
            for row in results:
                instance = cls()
                # Populate instance with row data
                for field in cls.__table__.columns.keys():
                    if field in row:
                        setattr(instance, field, row[field])
                instances.append(instance)
            return instances
            
        return _execute()

    async def save(self, session: Optional[Any] = None, validate: bool = True) -> None:
        """
        Save the current instance state to the database.

        Args:
            session: Optional SQLAlchemy session.
            validate: Whether to run full_clean() before saving (B2, B3).
        """
        from sqlalchemy.orm.attributes import instance_state

        # Determine if this is a new instance
        try:
            state = instance_state(self)
            is_new = state.key is None
        except Exception:
            is_new = True

        # Phase C.1: Change detection for Audit Log
        changes = {}
        if not is_new:
            from sqlalchemy import inspect as sa_inspect
            from sqlalchemy.orm import attributes
            try:
                insp = sa_inspect(self)
                for attr in insp.attrs:
                    history = attributes.get_history(self, attr.key)
                    if history.has_changes():
                        changes[attr.key] = {
                            "old": self._make_json_safe(history.deleted[0]) if history.deleted else None,
                            "new": self._make_json_safe(history.added[0]) if history.added else None
                        }
            except Exception:
                pass

        # Detect and flag JSON fields as modified to ensure they are saved
        # even if only nested values changed.
        if not is_new:
            from sqlalchemy import JSON
            from sqlalchemy.orm.attributes import flag_modified
            from sqlalchemy import inspect as sa_inspect

            mapper = sa_inspect(self.__class__)
            for column in mapper.columns:
                if isinstance(column.type, JSON):
                    # We check if the attribute has been accessed/modified
                    # or just flag it for safety in Eden.
                    flag_modified(self, column.key)

        # Handle Auto-Slugging
        await self._auto_slugify()

        if session:
            # Lifecycle hooks - Phase 1: Before
            if is_new:
                await self._call_hook("before_create", session)
            await self._call_hook("before_save", session)
            
            # Eden Validation Hooks & Rules (Discovery Phase 4)
            await self._trigger_hooks(self._pre_save_hooks)

            # Validation occurs AFTER 'before' hooks so they can populate required fields (e.g. tenant_id)
            if validate:
                errors = await self.validate()
                if errors:
                    from .validation import ValidationError as DBValidationError
                    from eden.exceptions import ValidationError
                    formatted_errors = [{"loc": [err.field or "__all__"], "msg": err.message, "type": "validation"} for err in errors]
                    raise ValidationError(detail="Model validation failed", errors=formatted_errors)
            
            is_new = self.id is None or not await session.get(self.__class__, self.id)

            # Sync to DB
            session.add(self)
            await session.flush()

            # Lifecycle hooks - Phase 2: After
            if is_new:
                await self._call_hook("after_create", session)
            await self._call_hook("after_save", session)
            await self._trigger_hooks(self._post_save_hooks)

            # Refresh to ensure database-generated fields are loaded
            await session.refresh(self)

            # Audit Trail Integration (Option C.1)
            await self._log_audit(is_new, self._make_json_safe(changes) if not is_new else None)
            return

        # No session provided, use context manager
        async with self._provide_session() as sess:
            # Lifecycle hooks - Phase 1: Before
            if is_new:
                await self._call_hook("before_create", sess)
            await self._call_hook("before_save", sess)
            
            # Eden Validation Hooks & Rules (Discovery Phase 4)
            await self._trigger_hooks(self._pre_save_hooks)

            if validate:
                errors = await self.validate()
                if errors:
                    from .validation import ValidationError as DBValidationError
                    from eden.exceptions import ValidationError
                    formatted_errors = [{"loc": [err.field or "__all__"], "msg": err.message, "type": "validation"} for err in errors]
                    raise ValidationError(detail="Model validation failed", errors=formatted_errors)

            sess.add(self)
            await sess.flush()

            # Lifecycle hooks - Phase 2: After
            if is_new:
                await self._call_hook("after_create", sess)
            await self._call_hook("after_save", sess)
            await self._trigger_hooks(self._post_save_hooks)

            await sess.commit()
            await sess.refresh(self)

        # Audit Trail Integration (Option C.1)
        # Call OUTSIDE the session block to ensure Project is committed and visible
        await self._log_audit(is_new, self._make_json_safe(changes) if not is_new else None)

    async def _auto_slugify(self) -> None:
        """Automatically generate slugs for fields marked as SlugField with populate_from."""
        from sqlalchemy import inspect as sa_inspect
        
        mapper = sa_inspect(self.__class__)
        for column in mapper.columns:
            if "populate_from" in column.info:
                current_val = getattr(self, column.key, None)
                # Only generate if current value is empty or hasn't been set
                if not current_val:
                    source_field = column.info["populate_from"]
                    source_val = getattr(self, source_field, None)
                    if source_val:
                        setattr(self, column.key, slugify(str(source_val)))

    async def full_clean(self) -> None:
        """
        Run comprehensive validation including Pydantic rules and custom hooks.
        Raises ValidationError on failure.
        """
        # 1. Internal Pydantic declarative cleaning
        self.clean()

        # 2. Custom logical cleaning (via ValidatorMixin)
        errors = await self.validate()
        if errors:
            from eden.exceptions import ValidationError
            formatted_errors = [{"loc": [err.field or "__all__"], "msg": err.message, "type": "validation"} for err in errors]
            raise ValidationError(detail="Model validation failed", errors=formatted_errors)

    async def update(self, session: Optional[Any] = None, **kwargs) -> None:
        """Update instance attributes and save."""
        from eden.db.lookups import F, _FExpr

        has_f_expressions = any(isinstance(v, (F, _FExpr)) for v in kwargs.values())
        if has_f_expressions:
            await self.__class__.query(session=session).filter(id=self.id).update(**kwargs)
            if session:
                # Flush the transaction first to ensure any other changes are visible
                await session.flush()
                await session.refresh(self)
            else:
                if not self._db:
                    raise RuntimeError(
                        f"Model {self.__class__.__name__} is not bound to a database."
                    )
                async with self._db.session() as sess:
                    # Attach to new session and refresh
                    sess.add(self)
                    await sess.refresh(self)
            return

        for k, v in kwargs.items():
            setattr(self, k, v)
        await self.save(session)

    async def delete(self, session: Optional[Any] = None, hard: bool = False) -> None:
        """
        Delete the current record.
        
        Automatically triggers file cleanup for linked files (Layer 2).
        If model has file references (via FileReference model), associated files
        are deleted from S3/Supabase/Local storage before the model instance is deleted.
        """
        # Trigger automatic file cleanup (Layer 2: Auto-cleanup on File Deletion)
        try:
            # Import here to avoid circular imports
            from eden.db.file_reference import FileReference
            await FileReference.cleanup_by_model(self.__class__, self.id)
        except Exception as exc:
            import logging
            logger = logging.getLogger("eden.db.base")
            logger.warning(f"File cleanup failed for {self.__class__.__name__}({self.id}): {exc}")
            # Continue with deletion even if file cleanup fails
        
        # Handle SoftDeleteMixin
        if hasattr(self, "deleted_at") and not hard:
            from datetime import datetime

            self.deleted_at = datetime.utcnow()
            await self.save(session)
            return

        if not hard:
            await self.hard_delete(session=session)
            return

        if session:
            await self._call_hook("before_delete", session)
            await session.delete(self)
            await session.flush()
            return

        if not self._db:
            raise RuntimeError(f"Model {self.__class__.__name__} is not bound to a database.")

        async with self._db.session() as sess:
            await self._call_hook("before_delete", sess)
            await sess.delete(self)
            await sess.flush()
            await sess.commit()

    async def hard_delete(self, session: Optional[Any] = None) -> None:
        """Permanently delete the record, bypassing soft delete (Layer 2)."""
        await self.delete(session=session, hard=True)

    async def _log_audit(self, is_new: bool, changes: dict | None = None) -> None:
        """Helper to record audit trail of changes."""
        # Avoid circular imports at module level
        try:
            from eden.admin.models import AuditLog
            from eden.context import get_user
        except Exception as e:
            return
        
        # Avoid auditing AuditLog itself (infinite loop)
        if isinstance(self, AuditLog):
            return

        try:
            user = get_user()
            user_id = str(getattr(user, "id", user)) if user else None
            action = "create" if is_new else "update"
            
            # For creation, if changes not provided, we can build a snapshot
            if is_new and not changes:
                changes = {}
                from sqlalchemy import inspect as sa_inspect
                insp = sa_inspect(self)
                for attr in insp.attrs:
                    val = getattr(self, attr.key)
                    if val is not None:
                        changes[attr.key] = {"old": None, "new": self._make_json_safe(val)}

            await AuditLog.log(
                user_id=user_id,
                action=action,
                model=self.__class__,
                record_id=str(self.id),
                changes=changes
            )
        except Exception as e:
            # Audit logging should never break the main transaction/save
            import logging
            logger = logging.getLogger("eden.db")
            logger.warning(f"Audit logging failed for {self.__class__.__name__}: {e}")

    def _make_json_safe(self, val: Any) -> Any:
        """Helper to recursively convert non-JSON types (UUID, datetime) to primitives."""
        import uuid
        from datetime import datetime
        
        if isinstance(val, (str, int, float, bool, type(None))):
            return val
        if isinstance(val, uuid.UUID):
            return str(val)
        if isinstance(val, datetime):
            return val.isoformat()
        if isinstance(val, dict):
            return {str(k): self._make_json_safe(v) for k, v in val.items()}
        if isinstance(val, (list, tuple, set)):
            return [self._make_json_safe(v) for v in val]
        
        # Fallback to string representation for complex objects
        return str(val)

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert model instance to dictionary (utility)."""
        return self.model_dump(**kwargs)

    def clean(self) -> None:
        """Run declarative validation rules via Pydantic over loaded attributes. Raises ValidationError on failure."""
        from sqlalchemy.orm.attributes import instance_state
        from pydantic import ValidationError as PydanticValidationError
        from eden.exceptions import ValidationError

        try:
            state = instance_state(self)
        except Exception:
            # Not a mapped instance yet
            return

        # D3: Use schema with only columns for internal validation to avoid relationship issues
        Schema = self.to_schema(only_columns=True)

        # Build dictionary of loaded attributes to validate
        data_to_validate = {}
        for col in self.__table__.columns:
            if col.name in state.dict:
                data_to_validate[col.name] = getattr(self, col.name)

        try:
            Schema.model_validate(data_to_validate)
        except PydanticValidationError as e:
            errors = []
            for err in e.errors():
                errors.append({"loc": err["loc"], "msg": err["msg"], "type": err["type"]})
            raise ValidationError(detail="ORM validation failed", errors=errors)

    @classmethod
    def to_schema(
        cls,
        include: Optional[List[str]] = None,
        exclude: Optional[set] = None,
        only_columns: bool = False,
    ) -> Type[pydantic.BaseModel]:
        """Automatically generate a Pydantic schema from the model definition (B2)."""
        from pydantic import create_model, ConfigDict, Field

        exclude = exclude or set()
        fields = {}
        try:
            annotations = get_type_hints(cls)
        except Exception:
            annotations = getattr(cls, "__annotations__", {})

        for name, hint in annotations.items():
            if name.startswith("_") or name in ("registry", "metadata") or name in exclude:
                continue

            if include is not None and name not in include:
                continue

            # Intelligently assign defaults based on column properties
            col = cls.__table__.columns.get(name)

            if only_columns and col is None:
                continue

            # Handle Mapped types
            origin = getattr(hint, "__origin__", None)
            if origin is Mapped:
                hint = hint.__args__[0] if hasattr(hint, "__args__") and hint.__args__ else hint

            is_nullable = col is not None and getattr(col, "nullable", False)
            has_default = col is not None and (
                getattr(col, "default", None) is not None
                or getattr(col, "server_default", None) is not None
            )

            field_kwargs = {}
            if col is not None:
                from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, Time, Text, Enum, Numeric

                # Extract constraints
                if isinstance(col.type, String) and col.type.length:
                    field_kwargs["max_length"] = col.type.length

                # Propagate Eden metadata (label, widget, etc.)
                info = dict(col.info) if col.info else {}

                # Auto-infer choices from Enum
                if isinstance(col.type, Enum) and "choices" not in info:
                    info["choices"] = [(v, v.title()) for v in col.type.enums]
                    if "widget" not in info:
                        info["widget"] = "select"

                # Numeric constraints
                if isinstance(col.type, (Integer, Float, Numeric)):
                    if "min" in info:
                        field_kwargs["ge"] = info["min"]
                    if "max" in info:
                        field_kwargs["le"] = info["max"]

                if "widget" not in info:
                    if isinstance(col.type, Text):
                        info["widget"] = "textarea"
                    elif isinstance(col.type, Boolean):
                        info["widget"] = "checkbox"
                    elif isinstance(col.type, Date):
                        info["widget"] = "date"
                    elif isinstance(col.type, DateTime):
                        info["widget"] = "datetime-local"
                    elif isinstance(col.type, Time):
                        info["widget"] = "time"
                    elif isinstance(col.type, (Integer, Float, Numeric)):
                        info["widget"] = "number"
                        if "step" not in info and isinstance(col.type, (Float, Numeric)):
                            info["step"] = "any"

                if info:
                    field_kwargs["json_schema_extra"] = info

            # Defaults and optionality
            # Internal fields are typically not wanted in forms unless explicitly included
            is_internal = name in ("id", "created_at", "updated_at", "deleted_at")
            if is_internal and include is None:
                continue

            if (
                col is None
                or is_internal
                or is_nullable
                or has_default
            ):
                default_val = None
            else:
                default_val = ...

            fields[name] = (hint, Field(default_val, **field_kwargs))

        config = ConfigDict(arbitrary_types_allowed=True)
        # Use dynamic type to avoid circular imports, but ensure it behaves like Eden Schema
        from eden.forms import Schema as EdenSchema

        dynamic_model = create_model(
            f"{cls.__name__}Schema", __config__=config, __base__=EdenSchema, **fields
        )
        return dynamic_model

    @classmethod
    def as_form(
        cls, 
        data: Optional[Dict[str, Any]] = None, 
        include: Optional[List[str]] = None, 
        exclude: Optional[set] = None
    ) -> Any:
        """
        Dynamically generate an Eden form directly from this ORM model.
        
        This utilizes `to_schema` to build a Pydantic schema with native UI
        metadata (extracted from SQLAlchemy types and columns), then wraps
        it in a standard `BaseForm` for rendering in templates.
        
        Args:
            data: Optional dictionary of data to bind to the form.
            include: Optional list of field names to include in the form.
            exclude: Optional set of field names to exclude from the form.
        """
        schema_cls = cls.to_schema(include=include, exclude=exclude, only_columns=True)
        return schema_cls.as_form(data=data)

# ── Real-time Sync Listeners ──────────────────────────────────────────

def _get_reactive_channels(target: Any) -> list[str]:
    """Determine which channels to broadcast to for a given model instance."""
    table_name = target.__tablename__
    channels = [table_name, f"{table_name}:{target.id}"]
    
    # If the model has a custom method for extra channels, call it
    if hasattr(target, "get_sync_channels"):
        channels.extend(target.get_sync_channels())
        
    return channels

async def _async_broadcast(channels: list[str], event_type: str, data: dict):
    """Bridge to the unified ConnectionManager."""
    from eden.websocket import connection_manager
    for channel in channels:
        await connection_manager.broadcast({
            "event": event_type,
            "data": data
        }, channel=channel)

def _trigger_broadcast(mapper, connection, target, event_type: str):
    """Sync listener that triggers the async broadcast."""
    if not getattr(target, "__reactive__", False):
        return
        
    channels = _get_reactive_channels(target)
    data = target.model_dump()
    
    # Use the current event loop if it exists to run the broadcast
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.create_task(_async_broadcast(channels, event_type, data))
    except (RuntimeError, NameError):
        # Fallback if no loop is running (unlikely in ASGI context)
        pass

@event.listens_for(Model, "after_insert", propagate=True)
def after_insert(mapper, connection, target):
    _trigger_broadcast(mapper, connection, target, "created")

@event.listens_for(Model, "after_update", propagate=True)
def after_update(mapper, connection, target):
    _trigger_broadcast(mapper, connection, target, "updated")

@event.listens_for(Model, "after_delete", propagate=True)
def after_delete(mapper, connection, target):
    _trigger_broadcast(mapper, connection, target, "deleted")
