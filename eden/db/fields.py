"""
Eden — Column Field Helpers

Clean, Django-style shorthand for defining SQLAlchemy columns.
Each helper returns a `mapped_column()` with sensible defaults.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship as sa_relationship

_UNSET = object()


def _process_field_args(
    nullable_val: Any, required: bool | None, kwargs: dict[str, Any], default_nullable: bool = False
) -> dict[str, Any]:
    """Internal helper to handle the required/nullable logic."""
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
        
    # Ensure we don't pass 'required' to mapped_column
    kwargs.pop("required", None)
    
    return {"nullable": resolved_nullable, **kwargs}


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
    kw = _process_field_args(nullable, required, kwargs, default_nullable=False)
    kw.update({"unique": unique, "index": index})
    if default is not None:
        kw["default"] = default
    return mapped_column(String(max_length), **kw)


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
    kw = _process_field_args(nullable, required, kwargs, default_nullable=False)
    if default is not None:
        kw["default"] = default
    return mapped_column(Text, **kw)


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
    kw = _process_field_args(nullable, required, kwargs, default_nullable=False)
    kw.update({"unique": unique, "index": index})
    if default is not None:
        kw["default"] = default
    return mapped_column(Integer, **kw)


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
    kw = _process_field_args(nullable, required, kwargs, default_nullable=False)
    if default is not None:
        kw["default"] = default
    return mapped_column(Float, **kw)


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
    kw = _process_field_args(nullable, required, kwargs, default_nullable=False)
    return mapped_column(Boolean, default=default, **kw)


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

    Usage:
        published_at: Mapped[datetime] = DateTimeField(auto_now_add=True)
    """
    kw = _process_field_args(nullable, required, kwargs, default_nullable=False)

    if auto_now_add:
        kw["server_default"] = func.now()
        # Fallback for some DBs or drivers that don't auto-fetch server_default on insert
        if "default" not in kw:
            kw["default"] = datetime.now
            
    if auto_now:
        kw["onupdate"] = func.now()
        # If auto_now is true, but auto_now_add is not, we still want an initial value
        if not auto_now_add and "default" not in kw and "server_default" not in kw:
            kw["server_default"] = func.now()
            kw["default"] = datetime.now
    
    # Apply explicit default if provided and not overridden by auto_now_add
    if default is not None and "default" not in kw and "server_default" not in kw:
        kw["default"] = default

    return mapped_column(DateTime, **kw)


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
    kw = _process_field_args(nullable, required, kwargs, default_nullable=not primary_key)
    kw["primary_key"] = primary_key
    
    if default_factory is not None:
        kw["default"] = default_factory
    elif primary_key:
        kw["default"] = uuid.uuid4
    return mapped_column(Uuid, **kw)


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
    kw = _process_field_args(nullable, required, kwargs, default_nullable=False)
    kw.update({"index": index})
    return mapped_column(
        ForeignKey(target, ondelete=ondelete),
        **kw
    )


def Relationship(
    target_model: Any = None,
    *,
    back_populates: str | None = None,
    lazy: str = "selectin",
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
    lazy: str = "selectin",
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
    kw = _process_field_args(nullable, required, kwargs, default_nullable=True)
    meta = kw.get("info", {})
    meta.update({"widget": "file", "upload_to": upload_to})
    kw["info"] = meta
    return mapped_column(String(max_length), **kw)


# ── Zen Helper ─────────────────────────────────────────────────────────


def f(
    max_length: int | None = None,
    *,
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
    json: bool = False,
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
    kw = _process_field_args(nullable, required, kwargs, default_nullable=True)
    kw.update({"unique": unique, "index": index})
    if default is not None:
        kw["default"] = default
    
    # Store metadata for form generation/validation
    meta = {}
    if choices: meta["choices"] = choices
    if widget: meta["widget"] = widget
    if min is not None: meta["min"] = min
    if max is not None: meta["max"] = max
    if org_id: meta["org_id"] = True
    if upload_to:
        meta["upload_to"] = upload_to
        meta["widget"] = "file"
    
    if meta:
        kw["info"] = meta

    # If it looks like a relationship
    if back_populates:
        return Relationship(back_populates=back_populates, **kw)

    # Standard columns
    if json:
        return mapped_column(JSON, **kw)

    if max_length:
        return mapped_column(String(max_length), **kw)
    
    # Fallback to mapped_column - Eden's type_annotation_map in Model 
    # will handle the actual type inference from the hint.
    if foreign_key:
        return mapped_column(ForeignKey(foreign_key), **kw)
        
    return mapped_column(**kw)
