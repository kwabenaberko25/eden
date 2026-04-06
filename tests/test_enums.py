"""
Tests for Eden Enums and ChoiceField.
"""

import pytest

from eden.enums import ChoiceField, ChoiceEnum, choice_field


class TestStatus(ChoiceEnum):
    """Test status enum."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    @property
    def display_name(self) -> str:
        names = {
            "draft": "Draft",
            "published": "Published",
            "archived": "Archived",
        }
        return names.get(self.value, self.name)


def test_choice_enum_creation():
    """Test ChoiceEnum creation."""
    status = TestStatus.PUBLISHED

    assert status.value == "published"
    assert status.display_name == "Published"


def test_choice_enum_class_methods():
    """Test ChoiceEnum class methods."""
    # Test choices property
    choices = TestStatus.choices
    expected = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]
    assert choices == expected

    # Test values property
    values = TestStatus.values
    expected_values = ["draft", "published", "archived"]
    assert values == expected_values

    # Test display_names property
    display_names = TestStatus.display_names
    expected_names = ["Draft", "Published", "Archived"]
    assert display_names == expected_names


def test_choice_enum_get_display_name():
    """Test get_display_name method."""
    assert TestStatus.get_display_name("draft") == "Draft"
    assert TestStatus.get_display_name("published") == "Published"
    assert TestStatus.get_display_name("invalid") == "invalid"


def test_choice_enum_validate_choice():
    """Test validate_choice method."""
    assert TestStatus.validate_choice("draft") is True
    assert TestStatus.validate_choice("published") is True
    assert TestStatus.validate_choice("invalid") is False


def test_choice_field_creation():
    """Test ChoiceField creation."""
    field = ChoiceField(choices=TestStatus, default=TestStatus.DRAFT)

    assert field.choices == TestStatus
    assert field.default == TestStatus.DRAFT
    assert field.max_length == 50
    assert field.db_index is False


def test_choice_field_with_list_choices():
    """Test ChoiceField with list of tuples."""
    choices = [("small", "Small"), ("medium", "Medium"), ("large", "Large")]
    field = ChoiceField(choices=choices, default="medium")

    assert field._choice_dict == {"small": "Small", "medium": "Medium", "large": "Large"}
    assert field.default == "medium"


def test_choice_field_get_display_name():
    """Test ChoiceField get_display_name method."""
    field = ChoiceField(choices=TestStatus)

    assert field.get_display_name("draft") == "Draft"
    assert field.get_display_name("published") == "Published"
    assert field.get_display_name("invalid") == "invalid"


def test_choice_field_validation():
    """Test ChoiceField validation."""
    field = ChoiceField(choices=TestStatus)

    # Valid choices
    assert field.validate("draft") == []
    assert field.validate("published") == []
    assert field.validate("archived") == []

    # Invalid choice
    errors = field.validate("invalid")
    assert len(errors) == 1
    assert "not a valid choice" in errors[0]

    # None value (should be allowed if no default)
    assert field.validate(None) == []


def test_choice_field_properties():
    """Test ChoiceField properties."""
    field = ChoiceField(choices=TestStatus)

    # Test choice_list
    choices = field.choice_list
    expected = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]
    assert choices == expected

    # Test values_list
    values = field.values_list
    expected_values = ["draft", "published", "archived"]
    assert values == expected_values

    # Test display_names_list
    display_names = field.display_names_list
    expected_names = ["Draft", "Published", "Archived"]
    assert display_names == expected_names


def test_choice_field_with_validators():
    """Test ChoiceField with custom validators."""
    def custom_validator(value):
        if value == "archived":
            raise ValueError("Archived status not allowed")

    field = ChoiceField(
        choices=TestStatus,
        validators=[custom_validator]
    )

    # Valid choice
    assert field.validate("draft") == []

    # Invalid due to custom validator
    errors = field.validate("archived")
    assert len(errors) == 1
    assert "Archived status not allowed" in errors[0]


def test_choice_field_sqlalchemy_column():
    """Test ChoiceField SQLAlchemy column generation."""
    field = ChoiceField(choices=TestStatus, db_index=True)

    column = field.get_sqlalchemy_column("status")

    assert column.name == "status"
    assert column.nullable is True  # No default set
    assert column.index is True


def test_choice_field_with_default():
    """Test ChoiceField with default value."""
    field = ChoiceField(choices=TestStatus, default=TestStatus.DRAFT)

    assert field.default == TestStatus.DRAFT

    column = field.get_sqlalchemy_column("status")
    assert column.nullable is False  # Has default


def test_choice_field_invalid_choices():
    """Test ChoiceField with invalid choices parameter."""
    with pytest.raises(ValueError, match="Choices must be a list of tuples or an Enum class"):
        ChoiceField(choices="invalid")


def test_choice_field_convenience_function():
    """Test choice_field convenience function."""
    field = choice_field(
        choices=TestStatus,
        default=TestStatus.DRAFT,
        max_length=100,
        db_index=True,
        help_text="Status of the item"
    )

    assert field.choices == TestStatus
    assert field.default == TestStatus.DRAFT
    assert field.max_length == 100
    assert field.db_index is True
    assert field.help_text == "Status of the item"