"""Tests for validator base classes."""

from eden.validators.base import (
    ValidationContext,
    ValidationError,
    ValidationResult,
    Validator,
)


def test_validation_result_creation():
    result = ValidationResult(is_valid=True)
    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []


def test_validation_result_add_error():
    result = ValidationResult(is_valid=True)
    result.add_error("Test error")
    assert result.is_valid is False
    assert "Test error" in result.errors


def test_validation_result_add_warning():
    result = ValidationResult(is_valid=True)
    result.add_warning("Test warning")
    assert result.is_valid is True
    assert "Test warning" in result.warnings


def test_validation_result_merge():
    result1 = ValidationResult(is_valid=True)
    result2 = ValidationResult(is_valid=False, errors=["Error 1"])
    result1.merge(result2)
    assert result1.is_valid is False
    assert "Error 1" in result1.errors


def test_validation_context_error_message():
    context = ValidationContext(field_name="email", field_label="Email Address")
    msg = context.error_message("{field_label} is required")
    assert msg == "Email Address is required"


def test_validation_context_error_message_with_kwargs():
    context = ValidationContext(field_name="password", field_label="Password")
    msg = context.error_message(
        "{field_label} must be at least {min_length} characters",
        min_length=8,
    )
    assert msg == "Password must be at least 8 characters"


class SimpleValidator(Validator):
    """Simple test validator that checks if value is not None."""

    def _validate(self, value, context):
        if value is None:
            raise ValidationError("Value is required")


def test_simple_validator_success():
    validator = SimpleValidator()
    result = validator.validate("test")
    assert result.is_valid is True
    assert result.errors == []


def test_simple_validator_failure():
    validator = SimpleValidator()
    result = validator.validate(None)
    assert result.is_valid is False
    assert len(result.errors) > 0


def test_validator_with_context():
    validator = SimpleValidator()
    context = ValidationContext(field_name="name", field_label="Full Name")
    result = validator.validate(None, context)
    assert result.is_valid is False
