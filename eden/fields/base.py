from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    ok: bool
    value: Any = None
    error: str | None = None

    def __bool__(self) -> bool:
        return self.ok


@dataclass
class ValidationContext:
    """Context passed to validators during validation."""

    field_name: str
    value: Any
    instance: Any = None
    form_data: dict | None = None
    request: Any = None


@dataclass
class FieldMetadata:
    """Complete field metadata for ORM, form, and validation."""

    name: str | None = None
    db_type: type = str
    unique: bool = False
    index: bool = False
    nullable: bool = False
    default: Any = None
    default_factory: Any = None
    primary_key: bool = False
    widget: str = "input"
    label: str | None = None
    placeholder: str | None = None
    help_text: str | None = None
    css_classes: list[str] | None = None
    validators: list[Validator] | None = None
    error_messages: dict[str, str] | None = None
    max_length: int | None = None
    min_length: int | None = None
    pattern: str | None = None
    min_value: Any = None
    max_value: Any = None
    choices: list[tuple] | None = None
    relation_type: str | None = None
    related_model: Any = None
    related_name: str | None = None
    on_delete: str | None = None
    through: Any = None

    def __post_init__(self) -> None:
        if self.css_classes is None:
            self.css_classes = []
        if self.validators is None:
            self.validators = []
        if self.error_messages is None:
            self.error_messages = {}


class Field:
    """A field wrapper that carries metadata and validator chaining."""

    def __init__(self, metadata: FieldMetadata | None = None) -> None:
        self.metadata = metadata or FieldMetadata()

    def __or__(self, validator: "Validator") -> Field:
        from eden.fields.validator import CompositeValidator

        if isinstance(validator, CompositeValidator):
            self.metadata.validators.extend(validator.validators)
        else:
            self.metadata.validators.append(validator)
        return self

    async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        if not self.metadata.validators:
            return ValidationResult(ok=True, value=value)

        from eden.fields.validator import CompositeValidator

        validator = CompositeValidator(self.metadata.validators)
        return await validator.validate(value, context)
