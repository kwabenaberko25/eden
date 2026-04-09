from __future__ import annotations
"""Model form generation."""


from typing import Any, Type

from eden.forms.base import Form


def model_form(
    model: Any,
    fields: list[str] | None = None,
    exclude: list[str] | None = None,
    form_class: Type[Form] = Form,
    name: str | None = None,
) -> Type[Form]:
    """Generate a form from a model class."""
    from eden.builder.form_factory import FormFactory

    form_name = name or f"{model.__name__}Form"

    # Filter fields
    model_fields = getattr(model, "_eden_fields", {})

    if exclude:
        model_fields = {
            k: v for k, v in model_fields.items() if k not in exclude
        }

    if fields:
        model_fields = {
            k: v for k, v in model_fields.items() if k in fields
        }

    return FormFactory.from_fields(model_fields, name=form_name)


__all__ = ["model_form"]
