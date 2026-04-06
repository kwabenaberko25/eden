"""
Eden Validator Library - Structured validation rules with error messaging.

Phase 3 of the field/form/model architecture provides a comprehensive
validator system that composes validation rules with context-aware
error messages, chainable validators, and support for custom rules.
"""

from __future__ import annotations

from eden.validators.base import Validator, ValidationContext, ValidationResult
from eden.validators.rules import (
    required,
    min_length,
    max_length,
    pattern,
    email_validator,
    url_validator,
    min_value,
    max_value,
    custom,
)
from eden.validators.composite import chain, any_of, all_of
from eden.validators.registry import ValidatorRegistry

__all__ = [
    "Validator",
    "ValidationContext",
    "ValidationResult",
    "required",
    "min_length",
    "max_length",
    "pattern",
    "email_validator",
    "url_validator",
    "min_value",
    "max_value",
    "custom",
    "chain",
    "any_of",
    "all_of",
    "ValidatorRegistry",
]
