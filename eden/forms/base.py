"""Base form classes."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import Any, Generic, TypeVar, get_type_hints

from eden.validators.base import ValidationContext, ValidationResult

T = TypeVar("T")


@dataclass
class FormField:
    """A field in a form."""

    name: str
    label: str | None = None
    required: bool = False
    help_text: str | None = None
    error_messages: dict[str, str] = dataclass_field(default_factory=dict)
    validators: list = dataclass_field(default_factory=list)
    value: Any = None
    errors: list[str] = dataclass_field(default_factory=list)

    def validate(self) -> ValidationResult:
        """Validate the field value."""
        context = ValidationContext(
            field_name=self.name,
            field_label=self.label or self.name,
            value=self.value,
        )

        result = ValidationResult(is_valid=True)

        for validator in self.validators:
            sub_result = validator.validate(self.value, context)
            result.merge(sub_result)

        self.errors = result.errors
        return result


class Form(Generic[T]):
    """Base typed form class."""

    def __init__(self, data: dict[str, Any] | None = None):
        self.data = data or {}
        self.fields: dict[str, FormField] = {}
        self.errors: dict[str, list[str]] = {}
        self._init_fields()

    def _init_fields(self) -> None:
        """Initialize form fields from type hints."""
        hints = get_type_hints(self.__class__)
        for name, type_hint in hints.items():
            if not name.startswith("_"):
                self.fields[name] = FormField(name=name)

    def bind(self, data: dict[str, Any]) -> BoundForm:
        """Bind data to the form."""
        return BoundForm(self, data)

    def is_valid(self) -> bool:
        """Check if form is valid."""
        if not self.data:
            return False

        for name, field in self.fields.items():
            field.value = self.data.get(name)
            result = field.validate()
            if not result.is_valid:
                self.errors[name] = result.errors

        return len(self.errors) == 0

    def get_field(self, name: str) -> FormField | None:
        """Get a form field by name."""
        return self.fields.get(name)


class BoundForm:
    """A form bound to data."""

    def __init__(self, form: Form[Any], data: dict[str, Any]):
        self.form = form
        self.data = data
        self.errors: dict[str, list[str]] = {}
        self.bound_fields: dict[str, BoundFormField] = {}
        self._bind_fields()

    def _bind_fields(self) -> None:
        """Bind each field to data."""
        for name, field in self.form.fields.items():
            field.value = self.data.get(name)
            result = field.validate()
            if not result.is_valid:
                self.errors[name] = result.errors

            self.bound_fields[name] = BoundFormField(field, result)

    def is_valid(self) -> bool:
        """Check if bound form is valid."""
        return len(self.errors) == 0

    def get_field(self, name: str) -> BoundFormField | None:
        """Get a bound field by name."""
        return self.bound_fields.get(name)


@dataclass
class BoundFormField:
    """A form field bound to a form and data."""

    field: FormField
    validation_result: ValidationResult

    @property
    def value(self) -> Any:
        """Get the field value."""
        return self.field.value

    @property
    def errors(self) -> list[str]:
        """Get field errors."""
        return self.validation_result.errors

    @property
    def is_valid(self) -> bool:
        """Check if field is valid."""
        return self.validation_result.is_valid
