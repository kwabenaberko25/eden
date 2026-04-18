from __future__ import annotations
"""
Eden — Column Field Helpers

Clean, Django-style shorthand for defining SQLAlchemy columns.
Each helper returns a `mapped_column()` with sensible defaults.
"""


import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List, Union, Type, TypeVar, get_args, get_origin, Annotated

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Date,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    ARRAY,
    JSON,
    func,
)
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship as sa_relationship


_UNSET = object()

def _process_field_args(
    nullable_val: Any, required: bool | None, kwargs: dict[str, Any], default_nullable: Any = False
) -> tuple[dict[str, Any], Optional[Any], dict[str, Any]]:
    """Internal helper to handle the required/nullable logic and constraints."""
    # Check if both were provided explicitly
    if required is not None and nullable_val is not _UNSET:
        raise ValueError("Cannot specify both 'required' and 'nullable' simultaneously.")
    
    # Resolve the final nullable value
    if required is not None:
        resolved_nullable = not required
    elif nullable_val is not _UNSET:
        resolved_nullable = nullable_val
    else:
        resolved_nullable = default_nullable
        
    # Extract foreign_key if present
    fk_str = kwargs.pop("foreign_key", None)
    fk = ForeignKey(fk_str) if fk_str else None
    
    # Extract validation metadata from kwargs
    validation_meta = {}
    
    # Map common validation keywords
    if "min_length" in kwargs:
        validation_meta["min"] = kwargs.pop("min_length")
    if "max_length" in kwargs:
        validation_meta["max"] = kwargs.pop("max_length")
    if "min_value" in kwargs:
        validation_meta["min"] = kwargs.pop("min_value")
    if "max_value" in kwargs:
        validation_meta["max"] = kwargs.pop("max_value")
    if "choices" in kwargs:
        validation_meta["choices"] = kwargs.pop("choices")
    if "pattern" in kwargs:
        validation_meta["pattern"] = kwargs.pop("pattern")
        
    # Ensure we don't pass 'required' to mapped_column
    kwargs.pop("required", None)
    
    res = {**kwargs}
    if resolved_nullable is not _UNSET:
        res["nullable"] = resolved_nullable
        if not resolved_nullable:
            validation_meta["required"] = True
            
    return res, fk, validation_meta


def StringField(
    max_length: int = 255,
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    unique: bool = False,
    index: bool = False,
    default: Any = None,
    **kwargs: Any,
) -> Any:
    """
    String column with max length.

    Usage:
        name: Mapped[str] = StringField(required=True)
    """
    # Default for strings is nullable=False
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=False)
    kw.update({"unique": unique, "index": index})
    if default is not None:
        kw["default"] = default
    
    args = [String(max_length)]
    if fk: args.append(fk)
    
    # Store validation metadata for Model discovery
    meta = kw.get("info", {})
    if max_length:
        meta["max"] = max_length
    
    # Merge extracted validation metadata
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, **kw)



def SlugField(
    max_length: int = 255,
    *,
    populate_from: str | None = None,
    unique: bool = True,
    index: bool = True,
    **kwargs: Any,
) -> Any:
    """
    Field for storing URL-friendly strings (slugs).
    Automatically unique and indexed by default.

    Args:
        populate_from: Field name to auto-generate slug from (e.g. 'title')

    Usage:
        slug: Mapped[str] = SlugField(populate_from="title")
    """
    info = kwargs.get("info", {})
    if populate_from:
        info["populate_from"] = populate_from
    kwargs["info"] = info
    
    return StringField(max_length=max_length, unique=unique, index=index, **kwargs)


def TextField(
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    default: Any = None,
    **kwargs: Any,
) -> Any:
    """
    Unbounded text column.

    Usage:
        bio: Mapped[str] = TextField(required=True)
    """
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=False)
    if default is not None:
        kw["default"] = default
    
    args = [Text]
    if fk: args.append(fk)

    # Store validation metadata
    meta = kw.get("info", {})
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, **kw)


def IntField(
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    unique: bool = False,
    index: bool = False,
    default: Any = None,
    **kwargs: Any,
) -> Any:
    """
    Integer column.

    Usage:
        age: Mapped[int] = IntField(required=True)
    """
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=False)
    kw.update({"unique": unique, "index": index})
    if default is not None:
        kw["default"] = default
    
    args = [Integer]
    if fk: args.append(fk)

    # Store validation metadata
    meta = kw.get("info", {})
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, **kw)


# Alias for Django compatibility
IntegerField = IntField


def FloatField(
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    default: Any = None,
    **kwargs: Any,
) -> Any:
    """
    Float column.

    Usage:
        price: Mapped[float] = FloatField(required=True)
    """
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=False)
    if default is not None:
        kw["default"] = default
    
    args = [Float]
    if fk: args.append(fk)

    # Store validation metadata
    meta = kw.get("info", {})
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, **kw)


def DecimalField(
    precision: int = 10,
    scale: int = 2,
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    default: Any = None,
    **kwargs: Any,
) -> Any:
    """
    Fixed-point decimal column.

    Usage:
        balance: Mapped[Decimal] = DecimalField(precision=12, scale=4)
    """
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=False)
    if default is not None:
        kw["default"] = default
    
    args = [Numeric(precision, scale)]
    if fk: args.append(fk)

    # Store validation metadata
    meta = kw.get("info", {})
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, **kw)


def BoolField(
    *,
    default: bool = False,
    nullable: Any = _UNSET,
    required: bool | None = None,
    **kwargs: Any,
) -> Any:
    """
    Boolean column.

    Usage:
        is_active: Mapped[bool] = BoolField(required=True)
    """
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=False)
    args = [Boolean]
    if fk: args.append(fk)

    # Store validation metadata
    meta = kw.get("info", {})
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, default=default, **kw)


def DateTimeField(
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    auto_now: bool = False,
    auto_now_add: bool = False,
    default: Any = None,
    **kwargs: Any,
) -> Any:
    """
    DateTime column with optional auto-timestamps.
    
    ⏰ TIMEZONE AWARENESS:
    
    All datetime fields should store UTC in the database. The application should:
    1. Always store UTC timestamps in the database
    2. Convert to user's local timezone on display
    3. Accept input in any timezone but normalize to UTC before saving
    
    Example:
        from datetime import datetime, timezone
        
        # Always use UTC for storage
        created_at: Mapped[datetime] = DateTimeField(auto_now_add=True)
        
        # On display, convert to user timezone:
        user_tz = pytz.timezone('America/New_York')
        local_time = created.created_at.replace(tzinfo=timezone.utc).astimezone(user_tz)
        
        # On input, normalize to UTC:
        user_input = datetime.fromisoformat("2025-01-20T10:30:00-05:00")  # New York time
        utc_time = user_input.astimezone(timezone.utc)
    
    Args:
        auto_now: Auto-update to current time on every save
        auto_now_add: Set to current time on creation only
        default: Static default value or callable
        nullable: Column allows NULL or not
        required: Alias for nullable (required=True means nullable=False)
    
    Returns:
        Mapped column configured with DateTime type
    
    Usage:
        # Automatically set on creation
        created_at: Mapped[datetime] = DateTimeField(auto_now_add=True)
        
        # Automatically update on every change
        updated_at: Mapped[datetime] = DateTimeField(auto_now=True)
        
        # Optional publish date (can be NULL until published)
        published_at: Mapped[datetime | None] = DateTimeField(nullable=True)
    
    Note:
        Both auto_now and auto_now_add can be True simultaneously:
        - auto_now_add sets initial value
        - auto_now updates it on every save
    """
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=False)

    # Helper to get current UTC time
    # We use naive UTC for standard DateTime columns to avoid asyncpg mismatch
    utc_now = lambda: datetime.now(timezone.utc).replace(tzinfo=None).replace(tzinfo=None)

    if auto_now_add:
        kw["server_default"] = func.now()
        # Fallback for some DBs or drivers that don't auto-fetch server_default on insert
        if "default" not in kw:
            kw["default"] = utc_now
            
    if auto_now:
        kw["onupdate"] = func.now()
        # If auto_now is true, but auto_now_add is not, we still want an initial value
        if not auto_now_add and "default" not in kw and "server_default" not in kw:
            kw["server_default"] = func.now()
            kw["default"] = utc_now
    
    # Apply explicit default if provided and not overridden by auto_now_add
    if default is not None and "default" not in kw and "server_default" not in kw:
        kw["default"] = default

    args = [DateTime]
    if fk: args.append(fk)

    # Store validation metadata
    meta = kw.get("info", {})
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, **kw)


def JSONField(
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    default: Any = None,
    **kwargs: Any,
) -> Any:
    """
    JSON column for storing structured data.

    Usage:
        data: Mapped[dict] = JSONField(required=True)
    """
    from sqlalchemy import JSON
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=True)
    if default is not None:
        kw["default"] = default
    
    args = [JSON]
    if fk: args.append(fk)

    # Store validation metadata
    meta = kw.get("info", {})
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, **kw)


def JSONBField(
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    default: Any = None,
    **kwargs: Any,
) -> Any:
    """
    PostgreSQL-optimized JSONB column. Falls back to standard JSON on other DBs.
    """
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=True)
    if default is not None:
        kw["default"] = default
    
    # SQLAlchemy's JSON type has no 'none_as_null' by default, 
    # but we can pass it through kwargs if needed.
    # Note: JSON(none_as_null=True) is the default in some drivers.
    
    # We use JSON since it maps to JSONB on PostgreSQL automatically if supported.
    args = [JSON]
    if fk: args.append(fk)

    # Store validation metadata
    meta = kw.get("info", {})
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, **kw)


def ArrayField(
    item_type: Any = String,
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    default: Any = None,
    **kwargs: Any,
) -> Any:
    """
    Array column (PostgreSQL specific but safe with ARRAY fallback).

    Usage:
        tags: Mapped[list[str]] = ArrayField(String)
    """
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=True)
    if default is not None:
        kw["default"] = default
    
    args = [ARRAY(item_type)]
    if fk: args.append(fk)

    # Store validation metadata
    meta = kw.get("info", {})
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, **kw)


def EnumField(
    enum_type: Any,
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    default: Any = None,
    native_enum: bool = True,
    **kwargs: Any,
) -> Any:
    """
    Enumerated type column.

    Usage:
        status: Mapped[Status] = EnumField(Status)
    """
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=False)
    if default is not None:
        kw["default"] = default
    
    args = [SAEnum(enum_type, native_enum=native_enum)]
    if fk: args.append(fk)
    
    # Add choices to meta for forms
    meta = kw.get("info", {})
    if hasattr(enum_type, "__members__"):
        meta["choices"] = [(m.value, m.name) for m in enum_type]
    
    # Merge extracted validation metadata
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, **kw)


def UUIDField(
    *,
    primary_key: bool = False,
    nullable: Any = _UNSET,
    required: bool | None = None,
    default_factory: Any = None,
    **kwargs: Any,
) -> Any:
    """
    UUID column, often used as primary key.

    Usage:
        id: Mapped[uuid.UUID] = UUIDField(primary_key=True)
    """
    # Primary keys are not nullable by default
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=not primary_key)
    kw["primary_key"] = primary_key
    
    if default_factory is not None:
        kw["default"] = default_factory
    elif primary_key:
        kw["default"] = uuid.uuid4
        
    args = [Uuid]
    if fk: args.append(fk)

    # Store validation metadata
    meta = kw.get("info", {})
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(*args, **kw)


def ForeignKeyField(
    target: str,
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    index: bool = True,
    ondelete: str = "CASCADE",
    **kwargs: Any,
) -> Any:
    """
    Foreign key column.

    Usage:
        user_id: Mapped[uuid.UUID] = ForeignKeyField("users.id", required=True)
    """
    kw, _, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=False)
    kw.update({"index": index})

    # Store validation metadata
    meta = kw.get("info", {})
    meta.update(v_meta)
    kw["info"] = meta

    return mapped_column(
        ForeignKey(target, ondelete=ondelete),
        **kw
    )


def Relationship(
    target_model: Any = None,
    *,
    back_populates: str | None = None,
    lazy: str = "raise",
    **kwargs: Any,
) -> Any:
    """
    Relationship helper with async-friendly defaults.

    Usage:
        posts: Mapped[list["Post"]] = Relationship("Post", back_populates="author")
    """
    kw: dict[str, Any] = {"lazy": lazy, **kwargs}
    if back_populates is not None:
        kw["back_populates"] = back_populates
    
    from .lookups import EdenRelationshipComparator
    kw.setdefault("comparator_factory", EdenRelationshipComparator)
    return sa_relationship(target_model, **kw)


def Reference(
    target: str | Any | None = None,
    *,
    on_delete: str = "CASCADE",
    back_populates: str | None = None,
    required: bool = True,
    index: bool = True,
    fk_type: Any | None = None,
    **kwargs: Any,
) -> Any:
    """
    The ultimate one-liner for Foreign Keys + Relationships.
    
    Usage:
        user: Mapped["User"] = Reference(back_populates="social_accounts")
        
    This automatically creates 'user_id' with the correct ForeignKey constraint.
    """
    info = kwargs.get("info", {})
    info.update({
        "is_reference": True,
        "on_delete": on_delete,
        "required": required,
        "index": index,
        "fk_type": fk_type
    })
    kwargs["info"] = info
    return Relationship(target, back_populates=back_populates, **kwargs)


def ManyToManyField(
    target_model: str,
    through: str | Any | None = None,
    *,
    back_populates: str | None = None,
    lazy: str = "raise",
    **kwargs: Any,
) -> Any:
    """
    Many-to-Many relationship helper.

    Args:
        target_model: The related model name.
        through: Association table name. If omitted, auto-inferred.

    Usage:
        tags: Mapped[list["Tag"]] = ManyToManyField("Tag", through="post_tags", back_populates="posts")
        # Or auto-inferred:
        tags: Mapped[list["Tag"]] = ManyToManyField("Tag")
    """
    secondary = through  # Will be resolved during relationship init if None
    kw: dict[str, Any] = {
        "lazy": lazy,
        **kwargs,
    }
    
    info = kw.get("info", {})
    info.update({
        "is_m2m": True,
        "through": through
    })
    kw["info"] = info

    if secondary is not None:
        kw["secondary"] = secondary
    if back_populates is not None:
        kw["back_populates"] = back_populates
    return Relationship(target_model, **kw)


def FileField(
    *,
    nullable: Any = _UNSET,
    required: bool | None = None,
    upload_to: str = "uploads",
    max_length: int = 500,
    **kwargs: Any,
) -> Any:
    """
    Field for file uploads. Stores the relative path/URL as a string.

    Usage:
        avatar: Mapped[str] = FileField(upload_to="avatars")
    """
    kw, fk, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=True)
    meta = kw.get("info", {})
    meta.update({"widget": "file", "upload_to": upload_to})
    
    # Merge extracted validation metadata
    meta.update(v_meta)
    kw["info"] = meta
    
    args = [String(max_length)]
    if fk: args.append(fk)
    return mapped_column(*args, **kw)


# ── Zen Helper ─────────────────────────────────────────────────────────


def f(
    type_or_length: Any | int | None = None,
    *,
    max_length: int | None = None,
    label: str | None = None,

    placeholder: str | None = None,
    help_text: str | None = None,
    nullable: Any = _UNSET,
    required: bool | None = None,
    unique: bool = False,
    index: bool = False,
    default: Any = None,
    choices: list[Any] | None = None,
    widget: str | None = None,
    back_populates: str | None = None,
    org_id: bool = False,
    upload_to: str | None = None,
    min: Any = None,
    max: Any = None,
    foreign_key: str | None = None,
    on_delete: str = "CASCADE",
    json: bool = False,
    reference: bool = False,
    **kwargs: Any,
) -> Any:
    """
    The ultimate Zen helper. Automatically chooses the right SQLAlchemy 
    column type based on the input or relationship context.
    
    Usage:
        title: str = f(max_length=100)
        payload: dict = f(json=True)
    """
    from sqlalchemy import JSON
    # Ensure reference is not passed to mapped_column
    if reference:
        kwargs.setdefault("index", True)
        
    kw, fk_from_kw, v_meta = _process_field_args(nullable, required, kwargs, default_nullable=_UNSET)
    kw.update({"unique": unique, "index": index})
    if default is not None:
        kw["default"] = default
    
    # Store metadata for form generation/validation
    meta: Dict[str, Any] = {}
    if reference:
        meta["is_reference"] = True
    if label: meta["label"] = label
    if placeholder: meta["placeholder"] = placeholder
    if help_text: meta["help_text"] = help_text
    if choices: meta["choices"] = choices
    if widget: meta["widget"] = widget
    if min is not None: meta["min"] = min
    if max is not None: meta["max"] = max
    if org_id: meta["org_id"] = True
    if upload_to:
        meta["upload_to"] = upload_to
        meta["widget"] = "file"
    
    if meta:
        # Merge existing info if present in kwargs via _process_field_args
        if "info" in kw:
            kw["info"].update(meta)
        else:
            kw["info"] = meta
    
    # Merge validation metadata extracted by _process_field_args from kwargs
    if v_meta:
        if "info" in kw:
            kw["info"].update(v_meta)
        else:
            kw["info"] = v_meta

    # If it looks like a relationship (one-liner support)
    if back_populates or "backref" in kwargs:
        # If it's a relationship, we flag it as a reference so Model auto-creates the _id column.
        # This allows: organization: Mapped["Organization"] = f(back_populates="members")
        meta["is_reference"] = True
        meta["on_delete"] = on_delete
        meta["required"] = not kw.get("nullable", True)
        
        # We only pass info and any other non-column kwargs to Relationship
        rel_kw = {"info": meta}
        for k in ["lazy", "overlaps", "uselist", "secondary", "order_by"]:
            if k in kwargs:
                rel_kw[k] = kwargs[k]
        
        return Relationship(back_populates=back_populates, **rel_kw)

    # Prioritize the explicit 'foreign_key' parameter
    final_fk = None
    if foreign_key:
        final_fk = ForeignKey(foreign_key, ondelete=on_delete)
    elif fk_from_kw:
        final_fk = fk_from_kw

    # Standard columns
    final_type = type_or_length
    if isinstance(type_or_length, int):
        final_type = String(type_or_length)
    elif max_length:
        final_type = String(max_length)
    
    if json:
        from sqlalchemy.ext.mutable import MutableDict, MutableList
        if default is not None and isinstance(default, list):
            final_type = MutableList.as_mutable(JSON)
        else:
            final_type = MutableDict.as_mutable(JSON)

    args = []
    if final_type is not None:
        args.append(final_type)
    if final_fk:
        args.append(final_fk)
        
    if args:
        return mapped_column(*args, **kw)
        
    return mapped_column(**kw)
