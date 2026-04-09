from __future__ import annotations
"""Form factory and builder for creating forms programmatically."""


from typing import Any, Callable, Generic, Type, TypeVar

from eden.fields.base import Field
from eden.forms.base import Form, FormField
from eden.forms.fields import CharField, IntegerField, EmailField, ChoiceField
from eden.forms.widgets import TextInput
from eden.builder.field_converters import FieldConverter

T = TypeVar("T")


class FormBuilder:
    """Builder for constructing forms programmatically."""

    def __init__(self):
        self.form_class = None
        self.fields: dict[str, FormField] = {}
        self.name = "DynamicForm"

    def set_name(self, name: str) -> FormBuilder:
        """Set the form name."""
        self.name = name
        return self

    def add_field(self, name: str, field: FormField) -> FormBuilder:
        """Add a field to the form."""
        self.fields[name] = field
        return self

    def add_char_field(
        self,
        name: str,
        label: str | None = None,
        required: bool = False,
        **kwargs: Any,
    ) -> FormBuilder:
        """Add a CharField."""
        field = CharField(name=name, label=label, required=required, **kwargs)
        return self.add_field(name, field)

    def add_int_field(
        self,
        name: str,
        label: str | None = None,
        required: bool = False,
        **kwargs: Any,
    ) -> FormBuilder:
        """Add an IntegerField."""
        field = IntegerField(name=name, label=label, required=required, **kwargs)
        return self.add_field(name, field)

    def add_email_field(
        self,
        name: str,
        label: str | None = None,
        required: bool = False,
        **kwargs: Any,
    ) -> FormBuilder:
        """Add an EmailField."""
        field = EmailField(name=name, label=label, required=required, **kwargs)
        return self.add_field(name, field)

    def add_choice_field(
        self,
        name: str,
        choices: list[tuple[str, str]],
        label: str | None = None,
        required: bool = False,
        **kwargs: Any,
    ) -> FormBuilder:
        """Add a ChoiceField."""
        field = ChoiceField(
            name=name,
            label=label,
            required=required,
            choices=choices,
            **kwargs,
        )
        return self.add_field(name, field)

    def build(self) -> Type[Form]:
        """Build and return the form class."""
        form_fields = self.fields

        class DynamicForm(Form):
            def __init__(self, data: dict[str, Any] | None = None):
                super().__init__(data or {})
                # Initialize fields from the captured form_fields
                for name, field in form_fields.items():
                    self.fields[name] = field

        return DynamicForm


class FormFactory:
    """Factory for creating forms from various sources."""

    @staticmethod
    def from_fields(
        fields: dict[str, Field],
        name: str = "DynamicForm",
    ) -> Type[Form]:
        """Create a form from a dictionary of fields."""
        builder = FormBuilder().set_name(name)

        for field_name, field in fields.items():
            form_field = FieldConverter.convert(field_name, field)
            builder.add_field(field_name, form_field)

        return builder.build()

    @staticmethod
    def from_model(
        model: Any,
        fields: list[str] | None = None,
        name: str | None = None,
    ) -> Type[Form]:
        """Create a form from a model class."""
        from eden.models.decorator import is_model

        if not is_model(model):
            raise ValueError(f"{model} is not a valid model")

        form_name = name or f"{model.__name__}Form"
        builder = FormBuilder().set_name(form_name)

        # Get model fields
        model_fields = getattr(model, "_eden_fields", {})

        for field_name, field in model_fields.items():
            if fields is None or field_name in fields:
                form_field = FieldConverter.convert(field_name, field)
                builder.add_field(field_name, form_field)

        return builder.build()
