"""Tests for validation rules."""

from eden.validators.base import ValidationContext
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


def test_required_validator_empty_string():
    validator = required()
    result = validator.validate("")
    assert result.is_valid is False


def test_required_validator_none():
    validator = required()
    result = validator.validate(None)
    assert result.is_valid is False


def test_required_validator_valid():
    validator = required()
    result = validator.validate("test")
    assert result.is_valid is True


def test_min_length_validator():
    validator = min_length(3)
    assert validator.validate("ab").is_valid is False
    assert validator.validate("abc").is_valid is True
    assert validator.validate("abcd").is_valid is True


def test_max_length_validator():
    validator = max_length(5)
    assert validator.validate("abcdef").is_valid is False
    assert validator.validate("abcde").is_valid is True
    assert validator.validate("abc").is_valid is True


def test_pattern_validator():
    validator = pattern(r"^[a-z]+$")
    assert validator.validate("abc").is_valid is True
    assert validator.validate("ABC").is_valid is False
    assert validator.validate("abc123").is_valid is False


def test_email_validator():
    validator = email_validator()
    assert validator.validate("test@example.com").is_valid is True
    assert validator.validate("invalid-email").is_valid is False
    assert validator.validate("test@example").is_valid is False


def test_url_validator():
    validator = url_validator()
    assert validator.validate("https://example.com").is_valid is True
    assert validator.validate("http://example.com").is_valid is True
    assert validator.validate("not a url").is_valid is False


def test_min_value_validator():
    validator = min_value(10)
    assert validator.validate(5).is_valid is False
    assert validator.validate(10).is_valid is True
    assert validator.validate(15).is_valid is True


def test_max_value_validator():
    validator = max_value(100)
    assert validator.validate(101).is_valid is False
    assert validator.validate(100).is_valid is True
    assert validator.validate(50).is_valid is True


def test_custom_validator():
    def is_even(value, context):
        return value % 2 == 0

    validator = custom(is_even)
    assert validator.validate(4).is_valid is True
    assert validator.validate(5).is_valid is False


def test_error_message_with_context():
    validator = required(error_message="{field_label} cannot be empty")
    context = ValidationContext(field_name="username", field_label="Username")
    result = validator.validate("", context)
    assert result.is_valid is False
    assert "Username cannot be empty" in result.errors[0]


def test_error_messages_dict():
    validator = min_length(3, error_messages={"min_length": "Too short!"})
    result = validator.validate("ab")
    assert result.is_valid is False
    assert "Too short!" in result.errors[0]
