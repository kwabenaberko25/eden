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
    get_type_hints,
    Annotated,
)
from datetime import datetime
from .access import AccessControl
from .validation import ValidatorMixin
from .metadata import MetadataToken

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
    declared_attr,
)
from sqlalchemy.ext.asyncio import AsyncSession
Session = AsyncSession

# Internal sentinel for missing values
_MISSING = object()


def _camel_to_snake(name: str) -> str:
    """Helper to convert CamelCase to snake_case."""
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


# Helper to map Python types to SQLAlchemy types for Annotated inference
_PYTHON_TO_SA = {
    str: String,
    int: Integer,
    float: Float,
    bool: Boolean,
    datetime: DateTime,
    uuid.UUID: Uuid,
    dict: JSON,
}


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


    # Standard primary key for all models
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        server_default=None,
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
        """
        from sqlalchemy.orm import RelationshipProperty, relationship as sa_rel
        from .metadata import parse_metadata, MetadataToken
        import typing

        inferred_names = []
        try:
            # We use globalns=None to delay resolution of string forward refs if possible,
            # but get_type_hints usually helps resolve them if the modules are imported.
            hints = get_type_hints(cls, include_extras=True)
        except Exception:
            # Fallback to manual annotation inspection if get_type_hints fails (e.g. circular)
            hints = getattr(cls, "__annotations__", {})

        for name, hint in hints.items():
            # Skip if name starts with _ or is a known internal attribute
            if name.startswith("_") or name in ("registry", "metadata", "type_annotation_map"):
                continue
            
            # Skip if defined in a parent class (mixins, abstract bases, etc.)
            # We allow processing if defined in the current cls.__dict__ to handle relationship helpers.
            already_defined_in_parent = False
            for base in cls.mro()[1:]:
                if base in (Model, Base, object):
                    continue
                if name in base.__dict__:
                    already_defined_in_parent = True
                    break
            
            if already_defined_in_parent:
                continue

            metadata = []
            final_type = hint
            
            # Extract from Annotated
            if typing.get_origin(hint) is typing.Annotated:
                metadata = getattr(hint, "__metadata__", ())
                final_type = typing.get_args(hint)[0]

            # Unwrap Mapped
            if typing.get_origin(final_type) is Mapped:
                final_type = typing.get_args(final_type)[0]

            # Detect List/Collection
            is_list = False
            origin = typing.get_origin(final_type)
            if origin in (list, List, typing.Sequence, typing.Collection):
                is_list = True
                final_type = typing.get_args(final_type)[0]

            # Unwrap Optional/Union
            origin = typing.get_origin(final_type)
            is_union = origin in (typing.Union, getattr(typing, "UnionType", None))
            if is_union:
                args = typing.get_args(final_type)
                # Filter out NoneType (None)
                args = [a for a in args if a is not type(None)]
                if args:
                    final_type = args[0]

            # Handle string forward refs
            target_name = None
            if isinstance(final_type, str):
                target_name = final_type
                # Clean up complex string hints like "Optional['User']" or "List[User]"
                if "[" in target_name:
                    target_name = target_name.split("[")[-1].split("]")[0]
                target_name = target_name.strip("'\" ")
            elif hasattr(final_type, "__name__"):
                target_name = final_type.__name__
            elif hasattr(final_type, "__forward_arg__"):
                target_name = final_type.__forward_arg__

            if not target_name:
                continue

            # Skip basic types
            basic_types = ("str", "int", "float", "bool", "uuid.UUID", "UUID", "datetime", "dict", "list", "Any", "None", "Decimal")
            if any(bt.lower() == target_name.lower() for bt in basic_types) or (target_name and target_name[0].islower()):
                continue

            # Process metadata
            sa_kwargs, sa_args, info = parse_metadata(metadata)

            # Detect Reference or M2M helper
            existing = cls.__dict__.get(name)
            is_m2m_explicit = False
            is_reference = False
            
            if existing is not None:
                is_reference = hasattr(existing, "info") and existing.info.get("is_reference")
                is_m2m_explicit = hasattr(existing, "info") and existing.info.get("is_m2m")
                
                # Check if it's already a relationship or a property that should be skipped
                # We skip if it's already fully defined (e.g. has 'direction' or 'argument' or 'column')
                # UNLESS it's a skeletal Reference or similar helper that needs FK inference.
                if not is_reference and not is_m2m_explicit:
                    if hasattr(existing, "column") or isinstance(existing, (property, declared_attr)) or hasattr(existing, "direction"):
                        continue
                
                # Also check for already defined relationships
                if not is_reference and not is_m2m_explicit:
                    if hasattr(existing, "argument") or hasattr(existing, "mapper") or hasattr(existing, "direction"):
                        continue

            if existing is not None:
                # Merge existing info into this field's info
                existing_info = getattr(existing, "info", {})
                for k, v in existing_info.items():
                    if k not in info:
                        info[k] = v
                
                # Extract relationship parameters if it's a skeletal relationship
                if is_reference:
                    if not info.get("back_populates") and hasattr(existing, "back_populates"):
                        info["back_populates"] = existing.back_populates
                    if not info.get("lazy") and hasattr(existing, "lazy"):
                        info["lazy"] = existing.lazy

                if not is_m2m_explicit:
                    # check for common relationship indicators again for safety if not a reference
                    if not is_reference and (hasattr(existing, "argument") or hasattr(existing, "mapper") or hasattr(existing, "direction")):
                        continue
                    if not is_reference:
                        # Some other member (column, property, etc.) - skip unless it's an annotated relationship
                        if name not in getattr(cls, "__annotations__", {}):
                            continue

            inferred_names.append(name)

            if is_list and is_m2m_explicit:
                cls._setup_m2m(name, target_name)
            elif is_list:
                # One-to-Many
                backref_name = _camel_to_snake(cls.__name__) + "s"
                kwargs = {
                    "lazy": info.get("lazy", "selectin"),
                    "overlaps": "*",
                    "back_populates": info.get("back_populates"),
                }
                if not kwargs["back_populates"]:
                    kwargs["backref"] = backref_name
                
                setattr(cls, name, sa_rel(target_name, **kwargs))
            else:
                # Many-to-One
                fk_col = f"{name}_id"
                if not hasattr(cls, fk_col):
                    # Guess target table if not found
                    target_table = _resolve_table_name(target_name)
                    
                    # Heuristic for FK Type: Default to Uuid for modern models. 
                    # Only use Integer for known legacy models (Role, etc.)
                    is_legacy = target_name in ("Role", "Permission")
                    fk_type = Uuid(native_uuid=True) if not is_legacy else Integer
                    
                    # Ensure FK info doesn't keep relationship-specific flags
                    fk_info = info.copy()
                    fk_info.pop("is_reference", None)
                    fk_info.pop("is_m2m", None)

                    col = mapped_column(
                        fk_type,
                        ForeignKey(f"{target_table}.id", ondelete=info.get("on_delete", "CASCADE")),
                        nullable=sa_kwargs.get("nullable", True),
                        index=sa_kwargs.get("index", True),
                        info=fk_info
                    )
                    setattr(cls, fk_col, col)

                backref_name = _camel_to_snake(cls.__name__)
                kwargs = {
                    "overlaps": "*",
                    "uselist": False,
                    "foreign_keys": f"{cls.__name__}.{fk_col}",
                    "back_populates": info.get("back_populates"),
                }
                if not kwargs["back_populates"]:
                    kwargs["backref"] = backref_name

                if not is_reference:
                    setattr(cls, name, sa_rel(target_name, **kwargs))
                else:
                    # If it's an existing Reference relationship, we don't overwrite it
                    # but we've ensured the FK column exists. Common in legacy code.
                    pass

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

            # Process Annotated Column Metadata (Modern Schema)
            from .metadata import parse_metadata
            import typing
            try:
                # include_extras=True is needed to see Annotated[...]
                hints = get_type_hints(cls, include_extras=True)
            except Exception:
                # Manual decomposition for circular/unresolvable hints
                hints = {
                    k: v for k, v in getattr(cls, "__annotations__", {}).items()
                }

            for name, hint in hints.items():
                if name.startswith("_") or name in rel_names:
                    continue
                
                # Check for Annotated in the hint (raw hint might be needed if hints resolution failed)
                raw_hint = getattr(cls, "__annotations__", {}).get(name, hint)
                
                # Support both resolved and raw Annotated
                is_annotated = typing.get_origin(hint) is typing.Annotated or typing.get_origin(raw_hint) is typing.Annotated
                if is_annotated:
                    effective_hint = hint if typing.get_origin(hint) is typing.Annotated else raw_hint
                    metadata = getattr(effective_hint, "__metadata__", ())
                    sa_kwargs, sa_args, info = parse_metadata(metadata)
                    
                    if sa_kwargs or sa_args or info:
                        # Capture default value if it exists on class
                        # We use __dict__ directly to avoid triggering descriptors or inheritance if not intended
                        default_val = cls.__dict__.get(name, _MISSING)
                        if default_val is not _MISSING and not hasattr(default_val, "__visit_name__"):
                            sa_kwargs.setdefault("default", default_val)

                        # We only handle it if it's NOT already a mapped property/column in a base
                        already_mapped = False
                        # Check if it's explicitly defined in the current class's __dict__
                        if name in cls.__dict__:
                            val = cls.__dict__[name]
                            # If it's a property, method, or already a SA mapped object, skip auto-mapping but keep for default
                            if hasattr(val, "column") or hasattr(val, "__visit_name__") or isinstance(val, (property, declared_attr)):
                                already_mapped = True
                        
                        # If not explicitly defined in current class, check parents
                        if not already_mapped:
                            for base in cls.mro()[1:]: # Check parents
                                if base in (Model, Base, object):
                                    continue
                                if name in base.__dict__:
                                    val = base.__dict__[name]
                                    if hasattr(val, "column") or hasattr(val, "__visit_name__") or isinstance(val, (property, declared_attr)):
                                        already_mapped = True
                                        break
                        
                        if already_mapped:
                            continue

                        # Auto-create mapped_column
                        args = typing.get_args(effective_hint)
                        if not args:
                            continue
                        
                        base_type = args[0]
                        if typing.get_origin(base_type) is Mapped:
                            base_type = typing.get_args(base_type)[0]
                        
                        # Unwrap Optional/Union
                        while typing.get_origin(base_type) in (typing.Union, getattr(typing, "UnionType", None)):
                            u_args = typing.get_args(base_type)
                            u_args = [a for a in u_args if a is not type(None)]
                            if u_args:
                                base_type = u_args[0]
                            else:
                                break

                        # Map Python primitive to SQLAlchemy type
                        sa_type = _PYTHON_TO_SA.get(base_type, base_type)

                        if not isinstance(sa_type, type) and not hasattr(sa_type, "__visit_name__"):
                            continue

                        # A1: Apply MaxLength constraints to String columns
                        if sa_type is String and "max" in info and not sa_args:
                            sa_type = String(info["max"])
                        elif isinstance(sa_type, type) and issubclass(sa_type, String) and "max" in info and not sa_args:
                            sa_type = sa_type(info["max"])

                        # A2: Handle Uuid instantiation with native_uuid=False for SQLite compatibility
                        if sa_type is Uuid:
                            sa_type = Uuid(native_uuid=False)

                        setattr(cls, name, mapped_column(sa_type, *sa_args, info=info, **sa_kwargs))

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
                        discovered_rules.append((cls.rule_max_length, name, info["max"]))
                    if "min" in info:
                        discovered_rules.append((cls.rule_min_length, name, info["min"]))
                    if "required" in info and info["required"]:
                        # Skip 'required' validation on relationships themselves (is_reference or is_m2m)
                        # as they are usually satisfied by providing the FK or being empty lists.
                        if not info.get("is_reference") and not info.get("is_m2m"):
                            discovered_rules.append((cls.rule_required, name, None))
                    if "choices" in info:
                        discovered_rules.append((cls.rule_choices, name, info["choices"]))
                    if "pattern" in info:
                        discovered_rules.append((cls.rule_pattern, name, info["pattern"]))

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

            # Apply EdenComparator to column properties AFTER SA mapping
            # (mapped_column doesn't accept comparator_factory; we attach it post-init)
            cls._apply_eden_comparators()
        else:
            super().__init_subclass__(**kwargs)

    @classmethod
    def _apply_eden_comparators(cls) -> None:
        """
        Attach EdenComparator to all ColumnProperty attributes on this class.

        SQLAlchemy 2.0's ``mapped_column()`` does NOT accept
        ``comparator_factory`` — that argument only works on ``column_property()``.
        Instead, we set it *after* the mapper processes the class by iterating
        over the class dict and patching each ``MappedColumn``'s
        ``_has_dataclass_arguments`` dict (or the property once resolved).

        This allows Django-style convenience methods like::

            User.name.icontains("alice")
        """
        from sqlalchemy.orm.properties import ColumnProperty
        from eden.db.lookups import EdenComparator

        for attr_name in list(cls.__dict__):
            attr = cls.__dict__[attr_name]
            # After __init_subclass__, column attrs may be MappedColumn descriptors.
            # The comparator_factory can be set on the ColumnProperty after it is
            # resolved, which happens lazily when the mapper is configured.
            # For now, we store the intent; SA will pick it up at configure time.
            if hasattr(attr, '_attribute_options'):
                # This is a MappedColumn; we can set comparator_factory via
                # the internal _has_dataclass_arguments or directly.
                try:
                    attr.comparator_factory = EdenComparator
                except (AttributeError, TypeError):
                    pass

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
                        Uuid(native_uuid=False),
                        ForeignKey(f"{source_table_name}.id", ondelete="CASCADE"),
                        primary_key=True,
                    ),
                    Column(
                        f"{_camel_to_snake(target_name)}_id",
                        Uuid(native_uuid=False),
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
        uuid.UUID: Uuid(native_uuid=True),
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
    def _base_select(cls, **kwargs) -> Any:
        """
        Cooperative base select for this model.
        Iterates through the MRO and applies all default filter hooks found.
        """
        from sqlalchemy import select
        stmt = select(cls)

        # Collect and apply filters from all classes in the MRO
        # This solves the shadowing issue between SoftDelete, Tenancy, etc.
        for base in cls.mro():
            if hasattr(base, "_apply_default_filters") and base is not Model:
                # We use __dict__ to avoid calling the same method multiple times 
                # if it's inherited but not overridden, but MRO already handles hierarchy.
                # However, to ensure we only call it ONCE even if multiple mixins share a base,
                # we just check if the method is defined on THIS specific base class.
                if "_apply_default_filters" in base.__dict__:
                    stmt = base._apply_default_filters(cls, stmt, **kwargs)

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
            from sqlalchemy import String as SA_String, Text as SA_Text
            from sqlalchemy import ForeignKey as SA_ForeignKey, DateTime as SA_DateTime, func as SA_func, JSON as SA_JSON

            search_fields = []
            for col in cls.__table__.columns:
                if isinstance(col.type, (SA_String, SA_Text)):
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
    @classmethod
    def to_schema(
        cls,
        include: Optional[List[str]] = None,
        exclude: Optional[set] = None,
        only_columns: bool = False,
    ) -> Type[pydantic.BaseModel]:
        """Automatically generate a Pydantic schema from the model definition."""
        # Check cache for efficiency (Maximum Capacity)
        if not hasattr(cls, "_schema_cache"):
            cls._schema_cache = {}
        
        cache_key = f"{include}:{exclude}:{only_columns}"
        if cache_key in cls._schema_cache:
            return cls._schema_cache[cache_key]

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
        cls._schema_cache[cache_key] = dynamic_model
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
