from __future__ import annotations
"""Common validation rules."""


import re
from typing import Any, Callable

from eden.validators.base import (
    ValidationContext,
    ValidationError,
    Validator,
)
from eden.validators.registry import ValidatorRegistry


class RequiredValidator(Validator[Any]):
    """Validates that a value is not empty."""

    def _validate(self, value: Any, context: ValidationContext) -> None:
        if value is None or (isinstance(value, str) and not value.strip()):
            if self.error_message:
                msg = context.error_message(self.error_message)
            else:
                msg = self.get_error_message(
                    "required",
                    "{field_label} is required",
                    context,
                )
            raise ValidationError(msg)


class MinLengthValidator(Validator[str]):
    """Validates minimum string length."""

    def __init__(self, min_length: int, **kwargs: Any):
        super().__init__(**kwargs)
        self.min_length = min_length

    def _validate(self, value: str, context: ValidationContext) -> None:
        if value is not None and len(str(value)) < self.min_length:
            msg = self.get_error_message(
                "min_length",
                "{field_label} must be at least {min_length} characters",
                context,
            )
            raise ValidationError(
                context.error_message(msg, min_length=self.min_length)
            )


class MaxLengthValidator(Validator[str]):
    """Validates maximum string length."""

    def __init__(self, max_length: int, **kwargs: Any):
        super().__init__(**kwargs)
        self.max_length = max_length

    def _validate(self, value: str, context: ValidationContext) -> None:
        if value is not None and len(str(value)) > self.max_length:
            msg = self.get_error_message(
                "max_length",
                "{field_label} must be at most {max_length} characters",
                context,
            )
            raise ValidationError(
                context.error_message(msg, max_length=self.max_length)
            )


class PatternValidator(Validator[str]):
    """Validates string against a regex pattern."""

    def __init__(self, pattern: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.pattern = re.compile(pattern)

    def _validate(self, value: str, context: ValidationContext) -> None:
        if value is not None and not self.pattern.match(str(value)):
            msg = self.get_error_message(
                "pattern",
                "{field_label} format is invalid",
                context,
            )
            raise ValidationError(msg)


class EmailValidator(Validator[str]):
    """Validates email addresses."""

    EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

    def _validate(self, value: str, context: ValidationContext) -> None:
        if value is not None:
            if not re.match(self.EMAIL_PATTERN, str(value)):
                msg = self.get_error_message(
                    "email",
                    "{field_label} must be a valid email address",
                    context,
                )
                raise ValidationError(msg)


class URLValidator(Validator[str]):
    """Validates URLs."""

    URL_PATTERN = r"^https?://.+\..+$"

    def _validate(self, value: str, context: ValidationContext) -> None:
        if value is not None:
            if not re.match(self.URL_PATTERN, str(value)):
                msg = self.get_error_message(
                    "url",
                    "{field_label} must be a valid URL",
                    context,
                )
                raise ValidationError(msg)


class MinValueValidator(Validator[int | float]):
    """Validates minimum numeric value."""

    def __init__(self, min_value: int | float, **kwargs: Any):
        super().__init__(**kwargs)
        self.min_value = min_value

    def _validate(
        self, value: int | float, context: ValidationContext
    ) -> None:
        if value is not None and value < self.min_value:
            msg = self.get_error_message(
                "min_value",
                "{field_label} must be at least {min_value}",
                context,
            )
            raise ValidationError(
                context.error_message(msg, min_value=self.min_value)
            )


class MaxValueValidator(Validator[int | float]):
    """Validates maximum numeric value."""

    def __init__(self, max_value: int | float, **kwargs: Any):
        super().__init__(**kwargs)
        self.max_value = max_value

    def _validate(
        self, value: int | float, context: ValidationContext
    ) -> None:
        if value is not None and value > self.max_value:
            msg = self.get_error_message(
                "max_value",
                "{field_label} must be at most {max_value}",
                context,
            )
            raise ValidationError(
                context.error_message(msg, max_value=self.max_value)
            )


class CustomValidator(Validator[Any]):
    """Custom validator using a callable."""

    def __init__(
        self,
        func: Callable[[Any, ValidationContext], bool],
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.func = func

    def _validate(self, value: Any, context: ValidationContext) -> None:
        if not self.func(value, context):
            msg = self.get_error_message(
                "custom",
                "{field_label} validation failed",
                context,
            )
            raise ValidationError(msg)


def required(**kwargs: Any) -> RequiredValidator:
    """Create a required validator."""
    return RequiredValidator(**kwargs)


def min_length(length: int, **kwargs: Any) -> MinLengthValidator:
    """Create a minimum length validator."""
    return MinLengthValidator(length, **kwargs)


def max_length(length: int, **kwargs: Any) -> MaxLengthValidator:
    """Create a maximum length validator."""
    return MaxLengthValidator(length, **kwargs)


def pattern(regex: str, **kwargs: Any) -> PatternValidator:
    """Create a pattern validator."""
    return PatternValidator(regex, **kwargs)


def email_validator(**kwargs: Any) -> EmailValidator:
    """Create an email validator."""
    return EmailValidator(**kwargs)


def url_validator(**kwargs: Any) -> URLValidator:
    """Create a URL validator."""
    return URLValidator(**kwargs)


def min_value(value: int | float, **kwargs: Any) -> MinValueValidator:
    """Create a minimum value validator."""
    return MinValueValidator(value, **kwargs)


def max_value(value: int | float, **kwargs: Any) -> MaxValueValidator:
    """Create a maximum value validator."""
    return MaxValueValidator(value, **kwargs)


def custom(
    func: Callable[[Any, ValidationContext], bool],
    **kwargs: Any,
) -> CustomValidator:
    """Create a custom validator."""
    return CustomValidator(func, **kwargs)


# Register validators
ValidatorRegistry.register("required", required)
ValidatorRegistry.register("min_length", min_length)
ValidatorRegistry.register("max_length", max_length)
ValidatorRegistry.register("pattern", pattern)
ValidatorRegistry.register("email", email_validator)
ValidatorRegistry.register("url", url_validator)
ValidatorRegistry.register("min_value", min_value)
ValidatorRegistry.register("max_value", max_value)
ValidatorRegistry.register("custom", custom)

__all__ = [
    "required",
    "min_length",
    "max_length",
    "pattern",
    "email_validator",
    "url_validator",
    "min_value",
    "max_value",
    "custom",
]
