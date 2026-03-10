import re
import uuid
import pydantic
import contextlib
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar, Union, get_type_hints
from datetime import datetime
from eden.db.access import AccessControl

T = TypeVar("T", bound="Model")
from sqlalchemy import (
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

# Internal sentinel for missing values
_MISSING = object()

def _camel_to_snake(name: str) -> str:
    """Helper to convert CamelCase to snake_case."""
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def _resolve_table_name(target_name: str) -> str:
    """Safely resolve table name for a target class name, respecting custom __tablename__."""
    try:
        # Check if target_name refers to a class already in the registry
        reg = Base.registry._class_registry
        if target_name in reg:
            target_cls = reg[target_name]
            #reg can contain strings or the actual class
            if hasattr(target_cls, "__tablename__"):
                return target_cls.__tablename__
            elif hasattr(target_cls, "name"): # it might be a descriptor/etc.
                pass
    except Exception:
        pass
            
    # Fallback to Eden convention: CamelCase -> camel_cases
    return _camel_to_snake(target_name) + "s"

class Base(DeclarativeBase):
    """SQLAlchemy Declarative Base."""
    __allow_unmapped__ = True

class Model(Base, AccessControl):
    """
    Base model for all Eden database models.
    Combines SQLAlchemy Declarative with Pydantic-like serialization and RLS.
    """
    __abstract__ = True
    __allow_unmapped__ = True
    
    # Track models for deferred relationship inference
    __pending_relationships__: List[Type["Model"]] = []
    __pending_m2m__: List[Dict[str, Any]] = []
    __m2m_registry__: Dict[str, Any] = {}
    
    # Bound database instance
    _db: ClassVar[Optional[Any]] = None

    # Multi-tenancy isolation marker
    __eden_tenant_isolated__: ClassVar[bool] = False
    __allow_unmapped__ = True

    # Standard primary key for all models
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=func.uuid_generate_v4() if False else None, default=uuid.uuid4)
    
    # Timestamps (B1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

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
        """Infers relationships from type hints before mapping. Returns list of inferred names."""
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
                target_name = target_name.strip("'\" ")

            # Skip basic types and lowercase names
            basic_types = ("str", "int", "float", "bool", "uuid.UUID", "datetime", "dict", "list", "Any", "None", "uuid")
            if not target_name or any(bt.lower() == target_name.lower() for bt in basic_types) or target_name[0].islower():
                continue
            
            if not target_name or not target_name[0].isupper() or "." in target_name:
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
                            foreign_keys=f"{cls.__name__}.{name}_id" if not is_list else None
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
                    "overlaps": "*"
                }
                if not _back_populates_val:
                    kwargs["backref"] = backref_name + "s"
                
                setattr(cls, name, sa_rel(target_name, **kwargs))
            else:
                # Single relationship (Many side)
                fk_col = f"{name}_id"
                
                # Check for Reference metadata override
                on_delete = ref_info.get("on_delete", "CASCADE")
                is_required = ref_info.get("required", True) if is_ref else False # Default inferred rels are nullable
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
                    elif target_cls and hasattr(target_cls, "id") and hasattr(target_cls, "__table__") and hasattr(target_cls.__table__.c.id, "type"):
                        # If table is already reflected/defined
                        fk_type = target_cls.__table__.c.id.type
                    elif target_cls and hasattr(target_cls, "id") and hasattr(target_cls.id, "type"):
                        fk_type = target_cls.id.type
                    else:
                        # Fallback heuristic
                        fk_type = Uuid if "user" not in target_table else Integer
                    
                    # print(f"DEBUG: Setting {cls.__name__}.{fk_col} as FK to {target_table}.id (type={fk_type})")
                    col = mapped_column(
                        fk_type, 
                        ForeignKey(f"{target_table}.id", ondelete=on_delete), 
                        nullable=not is_required,
                        index=fk_index
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
                    "foreign_keys": f"{cls.__name__}.{fk_col}"
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

            try:
                super().__init_subclass__(**kwargs)
            finally:
                # Restore original annotations for Pydantic/Forms
                cls.__annotations__.clear()
                cls.__annotations__.update(original_annotations)
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
            cls._create_m2m_table({
                "table_name": table_name,
                "cls": cls,
                "target_name": target_name,
                "cls_snake": cls_snake
            })
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

            setattr(cls, name, relationship(
                target_name, 
                secondary=table_name, 
                back_populates=back_populates,
                backref=getattr(existing, "backref", None) or (backref_name if not back_populates else None),
                lazy=getattr(existing, "lazy", "selectin"),
                overlaps=getattr(existing, "overlaps", name)
            ))

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
                target_table_name = target_cls.__tablename__ if hasattr(target_cls, '__tablename__') else f"{_camel_to_snake(target_name)}s"
                source_table_name = source_cls.__tablename__
                Table(
                    table_name,
                    cls.registry.metadata,
                    Column(f"{cls_snake}_id", source_cls.id.type, ForeignKey(f"{source_table_name}.id", ondelete="CASCADE"), primary_key=True),
                    Column(f"{_camel_to_snake(target_name)}_id", target_cls.id.type, ForeignKey(f"{target_table_name}.id", ondelete="CASCADE"), primary_key=True),
                    extend_existing=True
                )
            else:
                # Final fallback
                source_table_name = source_cls.__tablename__
                Table(
                    table_name,
                    cls.registry.metadata,
                    Column(f"{cls_snake}_id", Uuid, ForeignKey(f"{source_table_name}.id", ondelete="CASCADE"), primary_key=True),
                    Column(f"{_camel_to_snake(target_name)}_id", Uuid, ForeignKey(f"{_camel_to_snake(target_name)}s.id", ondelete="CASCADE"), primary_key=True),
                    extend_existing=True
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

    # We use Type[Database] | None to avoid circular imports during type checking
    _db: ClassVar[Any | None] = None  # Bound Database instance

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
    async def _get_session(cls):
        """
        Standard method to get a session, using the bound DB if available.
        Synchronizes with the current request context if active (B1).
        """
        from eden.context import get_request
        from sqlalchemy.ext.asyncio import AsyncSession
        
        request = get_request()
        if request:
            # Check if there is an active session already attached to the request state
            # We look for 'db_session' first, then 'db'
            session = getattr(request.state, "db_session", None) or getattr(request.state, "db", None)
            
            if isinstance(session, AsyncSession):
                yield session
                return

        # Fallback to creating a new session from the bound database
        if cls._db is None:
            raise RuntimeError("Model is not bound to a Database. Call db.connect() first.")
        
        async with cls._db.session() as session:
            yield session

    # ── CRUD Operations ───────────────────────────────────────────────────

    @classmethod
    def _base_select(cls) -> Any:
        """Standard base select for this model."""
        from sqlalchemy import select
        return select(cls)

    @classmethod
    def query(cls, session: Optional[Any] = None) -> "QuerySet":
        """Returns a QuerySet for this model."""
        from .query import QuerySet
        return QuerySet(cls, session=session)

    @classmethod
    async def get(cls, session: Optional[Any] = None, id: Union[uuid.UUID, str, None] = None) -> Optional[T]:
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
    async def get_or_404(cls, session: Optional[Any] = None, id: Union[uuid.UUID, str, None] = None) -> T:
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
        if hasattr(self, hook_name) and callable(getattr(self, hook_name)):
            await getattr(self, hook_name)(session)

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
    async def get_or_create(cls, session: Optional[Any] = None, defaults: Optional[Dict[str, Any]] = None, **kwargs) -> tuple[T, bool]:
        """Fetch a record or create it if not found."""
        obj = await cls.filter_one(session=session, **kwargs)
        if obj:
            return obj, False
        
        params = {**kwargs, **(defaults or {})}
        return await cls.create(session=session, **params), True

    @classmethod
    async def bulk_create(cls, session_or_instances: Any = None, instances_or_session: Any = None, validate: bool = True) -> List[T]:
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
                    inst.full_clean()
                    
                session.add(inst)
            
            await session.flush()
                
            for inst in actual_instances:
                # Lifecycle hooks - Phase 2: After
                await inst._call_hook("after_create", session)
                await inst._call_hook("after_save", session)

            return actual_instances
        
        # No session provided, use context manager
        async with cls._get_session() as sess:
            for inst in actual_instances:
                await inst._call_hook("before_create", sess)
                await inst._call_hook("before_save", sess)
                
                if validate:
                    inst.full_clean()
                    
                sess.add(inst)
            
            await sess.commit()
                
            for inst in actual_instances:
                await inst._call_hook("after_create", sess)
                await inst._call_hook("after_save", sess)

            return actual_instances

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

        if session:
            # Lifecycle hooks - Phase 1: Before
            if is_new:
                await self._call_hook("before_create", session)
            await self._call_hook("before_save", session)

            # Validation occurs AFTER 'before' hooks so they can populate required fields (e.g. tenant_id)
            if validate:
                self.full_clean()
            
            # Sync to DB
            session.add(self)
            await session.flush()
            
            # Lifecycle hooks - Phase 2: After
            if is_new:
                await self._call_hook("after_create", session)
            await self._call_hook("after_save", session)
            
            # Refresh to ensure database-generated fields are loaded
            await session.refresh(self)
            return

        # No session provided, use context manager
        async with self._get_session() as sess:
            # Lifecycle hooks - Phase 1: Before
            if is_new:
                await self._call_hook("before_create", sess)
            await self._call_hook("before_save", sess)

            if validate:
                self.full_clean()
            
            sess.add(self)
            await sess.commit()
            
            # Lifecycle hooks - Phase 2: After
            if is_new:
                await self._call_hook("after_create", sess)
            await self._call_hook("after_save", sess)
            
            await sess.refresh(self)

    def full_clean(self) -> None:
        """
        Run comprehensive validation including Pydantic rules and custom hooks.
        Raises ValidationError on failure.
        """
        # 1. Internal Pydantic declarative cleaning
        self.clean()
        
        # 2. Custom logical cleaning (can be overridden)
        self.validate()

    def validate(self) -> None:
        """
        Custom validation hook. Override this in your model to add
        complex logical validation. Raise eden.exceptions.ValidationError on failure.
        """
        pass

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
                    raise RuntimeError(f"Model {self.__class__.__name__} is not bound to a database.")
                async with self._db.session() as sess:
                     # Attach to new session and refresh
                     sess.add(self)
                     await sess.refresh(self)
            return

        for k, v in kwargs.items():
            setattr(self, k, v)
        await self.save(session)

    async def delete(self, session: Optional[Any] = None, hard: bool = False) -> None:
        """Delete the current record."""
        # Handle SoftDeleteMixin
        if hasattr(self, "deleted_at") and not hard:
            from datetime import datetime
            self.deleted_at = datetime.utcnow()
            await self.save(session)
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
            await sess.commit()

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
                errors.append({
                    "loc": err["loc"],
                    "msg": err["msg"],
                    "type": err["type"]
                })
            raise ValidationError(detail="ORM validation failed", errors=errors)

    @classmethod
    def to_schema(cls, include: Optional[List[str]] = None, exclude: Optional[set] = None, only_columns: bool = False) -> Type[pydantic.BaseModel]:
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
                hint = hint.__args__[0] if hasattr(hint, '__args__') and hint.__args__ else hint
                
            is_nullable = col is not None and getattr(col, "nullable", False)
            has_default = col is not None and (getattr(col, "default", None) is not None or getattr(col, "server_default", None) is not None)
            
            field_kwargs = {}
            if col is not None:
                if isinstance(col.type, String) and col.type.length:
                    field_kwargs["max_length"] = col.type.length
                
                # Propagate Eden metadata (label, widget, etc.)
                if col.info:
                    field_kwargs["json_schema_extra"] = col.info

            # If not a database column (e.g., relationship), make it optional
            if col is None or name in ("id", "created_at", "updated_at") or is_nullable or has_default:
                default_val = None
            else:
                default_val = ...
                
            fields[name] = (hint, Field(default_val, **field_kwargs))
            
        config = ConfigDict(arbitrary_types_allowed=True)
        # Use dynamic type to avoid circular imports, but ensure it behaves like Eden Schema
        from eden.forms import Schema as EdenSchema
        
        dynamic_model = create_model(f"{cls.__name__}Schema", __config__=config, __base__=EdenSchema, **fields)
        return dynamic_model
