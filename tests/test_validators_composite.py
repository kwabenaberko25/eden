"""Tests for composite validators."""

from eden.validators.composite import chain, any_of, all_of
from eden.validators.rules import min_length, max_length, pattern, required


def test_chain_validator_all_pass():
    validator = chain(required(), min_length(3), max_length(10))
    result = validator.validate("test")
    assert result.is_valid is True


def test_chain_validator_first_fails():
    validator = chain(required(), min_length(10))
    result = validator.validate("")
    assert result.is_valid is False


def test_chain_validator_second_fails():
    validator = chain(required(), min_length(10))
    result = validator.validate("ab")
    assert result.is_valid is False


def test_chain_validator_stops_at_first_failure():
    validator = chain(required(), min_length(10), max_length(5))
    result = validator.validate("ab")
    # Should fail at min_length, not reach max_length
    assert result.is_valid is False


def test_any_of_validator_first_passes():
    validator = any_of(
        pattern(r"^[0-9]+$"),
        pattern(r"^[a-z]+$"),
    )
    assert validator.validate("123").is_valid is True


def test_any_of_validator_second_passes():
    validator = any_of(
        pattern(r"^[0-9]+$"),
        pattern(r"^[a-z]+$"),
    )
    assert validator.validate("abc").is_valid is True


def test_any_of_validator_none_pass():
    validator = any_of(
        pattern(r"^[0-9]+$"),
        pattern(r"^[a-z]+$"),
    )
    assert validator.validate("ABC").is_valid is False


def test_all_of_validator_all_pass():
    validator = all_of(required(), min_length(3), max_length(10))
    result = validator.validate("test")
    assert result.is_valid is True


def test_all_of_validator_one_fails():
    validator = all_of(required(), min_length(3), max_length(5))
    result = validator.validate("toolongstring")
    assert result.is_valid is False


def test_all_of_validator_multiple_failures():
    validator = all_of(
        required(),
        min_length(5),
        max_length(10),
        pattern(r"^[a-z]+$"),
    )
    result = validator.validate("ABC")
    # Multiple errors: too short and wrong pattern
    assert result.is_valid is False
    assert len(result.errors) >= 2


def test_nested_validators():
    # Chain of any_of validators
    validator = chain(
        required(),
        any_of(
            min_length(3),
            pattern(r"^[0-9]+$"),
        ),
    )
    assert validator.validate("12").is_valid is True  # matches pattern
    assert validator.validate("ab").is_valid is False  # too short and no pattern
    assert validator.validate("abc").is_valid is True  # long enough
