from __future__ import annotations
"""
Eden Validator Library - Structured validation rules with error messaging.

Phase 3 of the field/form/model architecture provides a comprehensive
validator system that composes validation rules with context-aware
error messages, chainable validators, and support for custom rules.
"""


import importlib.util
import pathlib
from types import ModuleType

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


def _load_validators_module() -> ModuleType:
    module_path = pathlib.Path(__file__).parent.parent / "validators.py"
    spec = importlib.util.spec_from_file_location("eden.validators_module", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load the eden.validators module from validators.py")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

_validators_module = _load_validators_module()

validate_email = _validators_module.validate_email
validate_phone = _validators_module.validate_phone
validate_password = _validators_module.validate_password
validate_url = _validators_module.validate_url
validate_slug = _validators_module.validate_slug
validate_ip = _validators_module.validate_ip
validate_color = _validators_module.validate_color
validate_credit_card = _validators_module.validate_credit_card
validate_date = _validators_module.validate_date
validate_username = _validators_module.validate_username
validate_gps = _validators_module.validate_gps
validate_postcode = _validators_module.validate_postcode
validate_range = _validators_module.validate_range
validate_file_type = _validators_module.validate_file_type
validate_iban = _validators_module.validate_iban
validate_national_id = _validators_module.validate_national_id
EdenEmail = _validators_module.EdenEmail
EdenPhone = _validators_module.EdenPhone
EdenSlug = _validators_module.EdenSlug
EdenURL = _validators_module.EdenURL
EdenColor = _validators_module.EdenColor

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
    "validate_email",
    "validate_phone",
    "validate_password",
    "validate_url",
    "validate_slug",
    "validate_ip",
    "validate_color",
    "validate_credit_card",
    "validate_date",
    "validate_username",
    "validate_gps",
    "validate_postcode",
    "validate_range",
    "validate_file_type",
    "validate_iban",
    "validate_national_id",
    "EdenEmail",
    "EdenPhone",
    "EdenSlug",
    "EdenURL",
    "EdenColor",
]
