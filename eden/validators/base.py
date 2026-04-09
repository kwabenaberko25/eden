from __future__ import annotations
"""Base validator classes and validation context."""


from dataclasses import dataclass, field as dataclass_field
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    errors: list[str] = dataclass_field(default_factory=list)
    warnings: list[str] = dataclass_field(default_factory=list)
    data: Any = None

    def add_error(self, message: str) -> ValidationResult:
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False
        return self

    def add_warning(self, message: str) -> ValidationResult:
        """Add a warning message."""
        self.warnings.append(message)
        return self

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Merge another validation result."""
        self.is_valid = self.is_valid and other.is_valid
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        return self


@dataclass
class ValidationContext:
    """Context for validation operations."""

    field_name: str | None = None
    field_label: str | None = None
    value: Any = None
    obj: Any = None
    errors_dict: dict[str, list[str]] | None = dataclass_field(
        default_factory=dict
    )
    locale: str = "en"
    strict_mode: bool = False

    def error_message(
        self,
        template: str,
        **kwargs: Any,
    ) -> str:
        """Format an error message with context variables."""
        context_vars = {
            "field_name": self.field_name,
            "field_label": self.field_label or self.field_name,
            "value": self.value,
            "locale": self.locale,
        }
        context_vars.update(kwargs)
        try:
            return template.format(**context_vars)
        except KeyError:
            return template


class Validator(Generic[T]):
    """Base validator class for all validators."""

    def __init__(
        self,
        error_message: str | None = None,
        error_messages: dict[str, str] | None = None,
    ):
        self.error_message = error_message
        self.error_messages = error_messages or {}

    def validate(
        self,
        value: T,
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        """Validate a value and return a validation result."""
        if context is None:
            context = ValidationContext()

        try:
            self._validate(value, context)
            return ValidationResult(is_valid=True)
        except ValidationError as e:
            return ValidationResult(
                is_valid=False,
                errors=[str(e)],
            )

    def _validate(self, value: T, context: ValidationContext) -> None:
        """Internal validate method. Raise ValidationError on failure."""
        raise NotImplementedError

    def get_error_message(
        self,
        key: str,
        default: str,
        context: ValidationContext | None = None,
    ) -> str:
        """Get an error message by key."""
        if context is None:
            context = ValidationContext()

        message = self.error_messages.get(key, default)
        return context.error_message(message)


class ValidationError(Exception):
    """Raised when validation fails."""

    pass
