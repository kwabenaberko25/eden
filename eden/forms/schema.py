from __future__ import annotations

"""
Eden Schema system — Pydantic-based validation with ORM model integration.

This module provides:
- Schema: A Pydantic BaseModel subclass with Eden form rendering integration
- SchemaMeta: Metaclass that enables declarative `class Meta: model = ...` injection
- field() / v / f: Helper function for defining form fields with UI metadata
"""

from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field as PydanticField, EmailStr, AnyUrl


def field(
    default: Any = ...,
    *,
    label: str | None = None,
    placeholder: str | None = None,
    help_text: str | None = None,
    widget: str | None = None,
    choices: list[Any] | None = None,
    min: Any = None,
    max: Any = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
    required: bool | None = None,
    **kwargs: Any,
) -> Any:
    """
    Form-specific field helper. Returns a Pydantic Field with Eden UI metadata.

    Usage:
        from eden.forms import Schema, field

        class LoginSchema(Schema):
            email: str = field(widget="email", label="Email")
            password: str = field(widget="password", min_length=8)
    """
    from pydantic import Field

    # Map to json_schema_extra for Eden's form rendering
    metadata = kwargs.get("json_schema_extra", {})
    if not isinstance(metadata, dict):
        metadata = {}

    if label:
        metadata["label"] = label
    if placeholder:
        metadata["placeholder"] = placeholder
    if help_text:
        metadata["help_text"] = help_text
    if choices:
        metadata["choices"] = choices
    if widget:
        metadata["widget"] = widget
    if min is not None:
        metadata["min"] = min
    if max is not None:
        metadata["max"] = max
    if pattern:
        metadata["pattern"] = pattern

    # Handle required/default logic
    if required is True:
        if default is ...:
            default = ...
    elif required is False and default is ...:
        default = None

    # Handle ge/le for min/max if they are numeric
    if min is not None and isinstance(min, (int, float)):
        kwargs["ge"] = min
    if max is not None and isinstance(max, (int, float)):
        kwargs["le"] = max

    return Field(
        default=default,
        max_length=max_length,
        min_length=min_length,
        pattern=pattern,
        json_schema_extra=metadata if metadata else None,
        **kwargs,
    )


# Convenience aliases
v = field
f = field


try:
    from pydantic._internal._model_construction import ModelMetaclass
except ImportError:
    ModelMetaclass = type(BaseModel)


class SchemaMeta(ModelMetaclass):
    """
    Metaclass for Schema that enables seamless integration with ORM models
    via 'class Meta: model = MyModel'.

    This metaclass injects fields and annotations during class creation so that
    Pydantic's core schema generator correctly incorporates all validation
    constraints (like max_length, gt, etc.).
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        # Skip logic for the base Schema class itself
        if name == "Schema" and not any(isinstance(b, mcs) for b in bases):
            return super().__new__(mcs, name, bases, namespace, **kwargs)

        # 1. Handle explicit annotations and 'f()' helper attributes
        annotations = namespace.get("__annotations__", {})
        from pydantic import Field

        for fname in list(annotations.keys()):
            val = namespace.get(fname, ...)
            if hasattr(val, "column") and hasattr(val.column, "info"):
                meta = val.column.info
                field_kwargs = {"json_schema_extra": meta}
                if "label" in meta:
                    field_kwargs["description"] = meta["label"]
                namespace[fname] = Field(**field_kwargs)

        # 2. Declarative Model Integration (Meta.model)
        meta = namespace.get("Meta", None)
        if meta and hasattr(meta, "model"):
            try:
                model = meta.model
                include = getattr(meta, "include", None)
                exclude = getattr(meta, "exclude", None)
                if exclude is not None:
                    exclude = list(exclude)

                dynamic_schema = model.to_schema(include=include, exclude=exclude)

                from pydantic_core import PydanticUndefined
                if "__annotations__" not in namespace:
                    namespace["__annotations__"] = {}
                target_annotations = namespace["__annotations__"]

                for f_name, f_info in dynamic_schema.model_fields.items():
                    if f_name not in target_annotations and f_name not in namespace:
                        target_annotations[f_name] = f_info.annotation

                        fdef = f_info.default
                        if fdef is not None and (
                            hasattr(fdef, "column") or
                            hasattr(fdef, "mapper") or
                            hasattr(fdef, "prop")
                        ):
                            f_info.default = PydanticUndefined
                        namespace[f_name] = f_info
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Schema Meta injection for {name} failed: {e}")

                import os
                if os.environ.get("EDEN_ENV", "development") != "production":
                    raise RuntimeError(
                        f"Schema Meta injection for '{name}' failed. "
                        f"The resulting schema will have NO model-derived fields, "
                        f"which means it will validate nothing. "
                        f"Original error: {e}"
                    ) from e
                else:
                    logger.critical(
                        f"DEGRADED SCHEMA: {name} has no model fields due to injection failure. "
                        f"All data will pass validation for this schema. Error: {e}"
                    )

        return super().__new__(mcs, name, bases, namespace, **kwargs)


class Schema(BaseModel, metaclass=SchemaMeta):
    """
    Unified Schema for Eden.
    Combines Pydantic validation with Eden Form rendering.

    Usage:
        class SignupSchema(Schema):
            email: str = f(max_length=255, widget="email")
            ...

        form = SignupSchema.as_form(data)

    Declarative Model Integration:
        class ProductSchema(Schema):
            class Meta:
                model = Product
                include = ["title", "price"]
    """

    model_config = {"extra": "ignore", "arbitrary_types_allowed": True}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @classmethod
    def as_form(cls, data: Optional[Dict[str, Any]] = None):
        """Create a BaseForm instance from this schema."""
        from eden.forms.base import BaseForm
        return BaseForm(schema=cls, data=data)

    @classmethod
    async def from_request(cls, request: Any):
        """Create a bound form directly from a request."""
        from eden.forms.base import BaseForm
        return await BaseForm.from_request(cls, request)

    @classmethod
    def from_model(cls, instance: Any):
        """Creates a form instance populated with data from a model record."""
        from eden.forms.base import BaseForm
        return BaseForm.from_model(instance)
