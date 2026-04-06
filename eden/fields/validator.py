from __future__ import annotations

from typing import Any

from eden.fields.base import ValidationContext, ValidationResult


class Validator:
    """Base validator interface."""

    def __init__(self, name: str, async_mode: bool = False) -> None:
        self.name = name
        self.async_mode = async_mode
        self.error_message: str | None = None

    async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        raise NotImplementedError(f"{self.__class__.__name__} must implement validate()")

    def with_message(self, message: str) -> Validator:
        self.error_message = message
        return self

    def __or__(self, other: Validator) -> CompositeValidator:
        if isinstance(self, CompositeValidator):
            return CompositeValidator(self.validators + [other])
        if isinstance(other, CompositeValidator):
            return CompositeValidator([self] + other.validators)
        return CompositeValidator([self, other])


class CompositeValidator(Validator):
    """Chains multiple validators with AND logic."""

    def __init__(self, validators: list[Validator]) -> None:
        super().__init__("composite", async_mode=True)
        self.validators = validators

    async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        for validator in self.validators:
            result = await validator.validate(value, context)
            if not result.ok:
                error_msg = self.error_message or result.error or f"Validation failed: {validator.name}"
                return ValidationResult(ok=False, error=error_msg)
        return ValidationResult(ok=True, value=value)
