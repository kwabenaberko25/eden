from __future__ import annotations

from typing import Any, Type
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from eden.db import Model
from eden.db.base import _camel_to_snake
from eden.fields.base import Field
from eden.fields.sqlalchemy_mapping import get_sqlalchemy_type


def is_model(obj: Any) -> bool:
    """Check if an object is an Eden model class."""
    try:
        return isinstance(obj, type) and issubclass(obj, Model)
    except TypeError:
        return False


def _create_mapped_column(name: str, field_wrapper: Field) -> tuple[Any, Any]:
    metadata = field_wrapper.metadata
    sa_type = get_sqlalchemy_type(metadata)
    kwargs: dict[str, Any] = {
        "primary_key": metadata.primary_key,
        "unique": metadata.unique,
        "index": metadata.index,
        "nullable": metadata.nullable,
    }

    if metadata.default_factory is not None:
        kwargs["default"] = metadata.default_factory
    elif metadata.default is not None:
        kwargs["default"] = metadata.default

    info = {"eden": {"field": metadata}}
    kwargs["info"] = info

    if metadata.relation_type == "foreign_key" and metadata.related_model is not None:
        target = metadata.related_model
        target_name = getattr(target, "__tablename__", None)
        if target_name is None and isinstance(target, type):
            target_name = _camel_to_snake(target.__name__) + "s"
        if target_name is None:
            raise ValueError("Unable to resolve foreign key target table name")
        fk = ForeignKey(f"{target_name}.id")
        return mapped_column(fk, sa_type, **kwargs), Mapped[metadata.db_type]

    if metadata.relation_type in ("one_to_one", "many_to_many"):
        # Relationship support will be handled later by relationship-aware decorators
        # For now, store a standard mapped column for the underlying type.
        return mapped_column(sa_type, **kwargs), Mapped[metadata.db_type]

    return mapped_column(sa_type, **kwargs), Mapped[metadata.db_type]


def define(model_cls: Type[Any]) -> Type[Any]:
    """Decorator to define Eden models with Field wrappers."""
    original_annotations = dict(getattr(model_cls, "__annotations__", {}))
    transformed_annotations = original_annotations.copy()
    namespace: dict[str, Any] = {}

    for key, value in vars(model_cls).items():
        if key in {"__dict__", "__weakref__", "__module__", "__doc__"}:
            continue
        if isinstance(value, Field):
            mapped_value, annotation = _create_mapped_column(key, value)
            namespace[key] = mapped_value
            transformed_annotations[key] = annotation
        else:
            namespace[key] = value

    class _DeferredModel(Model):
        __abstract__ = True

        def __init_subclass__(cls, **kwargs: Any) -> None:
            return None

    bases = model_cls.__bases__
    if Model not in bases:
        bases = (Model, *bases)

    if Model in bases:
        bases = tuple(b for b in bases if b is not Model)
    bases = (_DeferredModel, *bases)

    new_cls = type(model_cls.__name__, bases, namespace)
    new_cls.__module__ = model_cls.__module__
    new_cls.__annotations__ = transformed_annotations

    if "__tablename__" not in vars(new_cls) and not getattr(new_cls, "__abstract__", False):
        new_cls.__tablename__ = _camel_to_snake(new_cls.__name__) + "s"

    # Store the original field definitions for form building
    new_cls._eden_fields = {}
    for key, value in vars(model_cls).items():
        if isinstance(value, Field):
            new_cls._eden_fields[key] = value

    Model.__init_subclass__.__func__(new_cls)
    return new_cls
