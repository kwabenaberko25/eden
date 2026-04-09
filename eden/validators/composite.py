from __future__ import annotations
"""Composite validators for combining multiple validators."""


from typing import Any

from eden.validators.base import (
    ValidationContext,
    ValidationError,
    ValidationResult,
    Validator,
)


class ChainValidator(Validator[Any]):
    """Chains multiple validators in sequence."""

    def __init__(self, *validators: Validator[Any]):
        super().__init__()
        self.validators = validators

    def validate(
        self,
        value: Any,
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        """Validate through all validators in chain."""
        if context is None:
            context = ValidationContext()

        result = ValidationResult(is_valid=True)

        for validator in self.validators:
            sub_result = validator.validate(value, context)
            result.merge(sub_result)
            if not sub_result.is_valid:
                break

        return result

    def _validate(self, value: Any, context: ValidationContext) -> None:
        """Not used in ChainValidator."""
        pass


class AnyOfValidator(Validator[Any]):
    """Validates if any one of the validators passes."""

    def __init__(self, *validators: Validator[Any]):
        super().__init__()
        self.validators = validators

    def validate(
        self,
        value: Any,
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        """Validate that at least one validator passes."""
        if context is None:
            context = ValidationContext()

        all_errors: list[str] = []

        for validator in self.validators:
            sub_result = validator.validate(value, context)
            if sub_result.is_valid:
                return ValidationResult(is_valid=True)
            all_errors.extend(sub_result.errors)

        return ValidationResult(
            is_valid=False,
            errors=all_errors or ["No validators matched"],
        )

    def _validate(self, value: Any, context: ValidationContext) -> None:
        """Not used in AnyOfValidator."""
        pass


class AllOfValidator(Validator[Any]):
    """Validates if all validators pass."""

    def __init__(self, *validators: Validator[Any]):
        super().__init__()
        self.validators = validators

    def validate(
        self,
        value: Any,
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        """Validate that all validators pass."""
        if context is None:
            context = ValidationContext()

        result = ValidationResult(is_valid=True)

        for validator in self.validators:
            sub_result = validator.validate(value, context)
            result.merge(sub_result)

        return result

    def _validate(self, value: Any, context: ValidationContext) -> None:
        """Not used in AllOfValidator."""
        pass


def chain(*validators: Validator[Any]) -> ChainValidator:
    """Create a chain validator."""
    return ChainValidator(*validators)


def any_of(*validators: Validator[Any]) -> AnyOfValidator:
    """Create an any-of validator."""
    return AnyOfValidator(*validators)


def all_of(*validators: Validator[Any]) -> AllOfValidator:
    """Create an all-of validator."""
    return AllOfValidator(*validators)


__all__ = ["chain", "any_of", "all_of"]
