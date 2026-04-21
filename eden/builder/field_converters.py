from __future__ import annotations
"""Field type converters for form building."""


from typing import Any

from eden.fields.base import Field
from eden.forms.fields import CharField, IntegerField, EmailField, ChoiceField
from eden.forms.base import BasicFormField


class FieldConverter:
    """Converts field definitions to form fields."""

    @staticmethod
    def convert(name: str, field: Field) -> BasicFormField:
        """Convert a Field to a FormField."""
        metadata = field.metadata

        # Determine field type from db_type
        if metadata.db_type is str:
            form_field = CharField(
                name=name,
                label=metadata.label or name.replace("_", " ").title(),
                required=not metadata.nullable,
                max_length=metadata.max_length,
                min_length=metadata.min_length,
                help_text=metadata.help_text,
            )
        elif metadata.db_type is int:
            form_field = IntegerField(
                name=name,
                label=metadata.label or name.replace("_", " ").title(),
                required=not metadata.nullable,
                min_value=metadata.min_value,
                max_value=metadata.max_value,
                help_text=metadata.help_text,
            )
        elif metadata.widget == "email":
            form_field = EmailField(
                name=name,
                label=metadata.label or name.replace("_", " ").title(),
                required=not metadata.nullable,
                help_text=metadata.help_text,
            )
        elif metadata.widget == "choice" or metadata.choices:
            form_field = ChoiceField(
                name=name,
                label=metadata.label or name.replace("_", " ").title(),
                required=not metadata.nullable,
                choices=metadata.choices or [],
                help_text=metadata.help_text,
            )
        else:
            # Default to CharField
            form_field = CharField(
                name=name,
                label=metadata.label or name.replace("_", " ").title(),
                required=not metadata.nullable,
                help_text=metadata.help_text,
            )

        # Add validators
        if metadata.validators:
            form_field.validators.extend(metadata.validators)

        return form_field


__all__ = ["FieldConverter"]
