from __future__ import annotations
"""
Eden Enums - Type-safe choice fields with enum support.

Provides ChoiceField for database columns with predefined options,
enum validation, and display name support.
"""


from enum import Enum, EnumMeta
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints
import sqlalchemy as sa
from sqlalchemy import Column, String, Integer, Enum as SAEnum

from ..db import Model, mapped_column


class classproperty:
    """Descriptor for class-level read-only computed attributes."""

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, objtype=None):
        return self.func(objtype)


class ChoiceMeta(EnumMeta):
    """Metaclass for choice enums to provide additional functionality."""

    def __new__(cls, name, bases, attrs):
        # Create the enum class
        enum_class = super().__new__(cls, name, bases, attrs)

        # Add choice helpers for class-level access
        if hasattr(enum_class, '__members__'):
            enum_class.choices = classproperty(lambda cls: [
                (member.value, member.display_name)
                for member in cls.__members__.values()
            ])

            enum_class.values = classproperty(lambda cls: [
                member.value for member in cls.__members__.values()
            ])

            enum_class.display_names = classproperty(lambda cls: [
                member.display_name for member in cls.__members__.values()
            ])

        return enum_class

class ChoiceEnum(str, Enum, metaclass=ChoiceMeta):
    """
    Base enum class for model choices.

    Provides display names and choice utilities.
    """

    @property
    def display_name(self) -> str:
        """Get the display name for this choice."""
        # Try to get from _display_names_ class attribute
        if hasattr(self.__class__, '_display_names_'):
            return self.__class__._display_names_.get(self.value, self.name.replace('_', ' ').title())

        # Default: convert name to title case
        return self.name.replace('_', ' ').title()

    @classmethod
    def get_display_name(cls, value: str) -> str:
        """Get display name for a value."""
        try:
            member = cls(value)
            return member.display_name
        except ValueError:
            return value

    @classmethod
    def validate_choice(cls, value: str) -> bool:
        """Validate that a value is a valid choice."""
        return value in [member.value for member in cls]

class ChoiceField:
    """
    Database field for choices with enum support.

    Provides type-safe choice validation and display names.
    """

    def __init__(
        self,
        choices: Union[List[tuple], Type[Enum], Type[ChoiceEnum]],
        default: Any = None,
        max_length: int = 50,
        db_index: bool = False,
        help_text: str = "",
        validators: Optional[List[callable]] = None,
    ):
        self.choices = choices
        self.default = default
        self.max_length = max_length
        self.db_index = db_index
        self.help_text = help_text
        self.validators = validators or []

        # Process choices into different formats
        self._choice_dict = self._process_choices()
        self._enum_class = self._get_enum_class()

    def _process_choices(self) -> Dict[str, str]:
        """Process choices into value -> display_name mapping."""
        if isinstance(self.choices, list):
            # List of tuples: [('value', 'Display Name'), ...]
            return {value: display for value, display in self.choices}
        elif hasattr(self.choices, '__members__'):
            # Enum class
            return {member.value: getattr(member, 'display_name', member.name.replace('_', ' ').title())
                   for member in self.choices.__members__.values()}
        else:
            raise ValueError("Choices must be a list of tuples or an Enum class")

    def _get_enum_class(self) -> Optional[Type[Enum]]:
        """Get the enum class if choices is an enum."""
        if hasattr(self.choices, '__members__'):
            return self.choices
        return None

    def get_display_name(self, value: str) -> str:
        """Get the display name for a choice value."""
        return self._choice_dict.get(value, value)

    def validate(self, value: Any) -> List[str]:
        """Validate a value against the choices."""
        errors = []

        if value is None and self.default is None:
            return errors  # Allow None if no default

        if value is not None:
            if isinstance(value, str):
                if value not in self._choice_dict:
                    errors.append(f"'{value}' is not a valid choice. Valid choices are: {list(self._choice_dict.keys())}")
            else:
                errors.append("Choice value must be a string")

        # Run custom validators
        for validator in self.validators:
            try:
                validator(value)
            except Exception as e:
                errors.append(str(e))

        return errors

    def get_sqlalchemy_column(self, name: str) -> Column:
        """Get the SQLAlchemy column definition."""
        # Create the column with appropriate type
        column_type = String(self.max_length)

        # Add enum constraint if using enum
        if self._enum_class:
            column_type = SAEnum(self._enum_class, native_enum=False)

        # Create column
        default_value = None
        if self.default is not None:
            default_value = self.default.value if isinstance(self.default, Enum) else self.default

        column = Column(
            name,
            column_type,
            nullable=default_value is None,
            default=default_value,
        )

        # Add index if requested
        if self.db_index:
            column.index = True

        return column

    @property
    def choice_list(self) -> List[tuple]:
        """Get choices as list of (value, display_name) tuples."""
        return [(value, display) for value, display in self._choice_dict.items()]

    @property
    def values_list(self) -> List[str]:
        """Get list of valid values."""
        return list(self._choice_dict.keys())

    @property
    def display_names_list(self) -> List[str]:
        """Get list of display names."""
        return list(self._choice_dict.values())

# Convenience function for creating choice fields
def choice_field(
    choices: Union[List[tuple], Type[Enum], Type[ChoiceEnum]],
    default: Any = None,
    max_length: int = 50,
    db_index: bool = False,
    help_text: str = "",
) -> ChoiceField:
    """Create a ChoiceField instance."""
    return ChoiceField(
        choices=choices,
        default=default,
        max_length=max_length,
        db_index=db_index,
        help_text=help_text,
    )

# Example usage patterns
class Status(ChoiceEnum):
    """Example status enum."""
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
        return names.get(self.value, self.name.title())

class Priority(ChoiceEnum):
    """Example priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

# Usage in models
def create_choice_field_for_model(
    model_cls: Type[Model],
    field_name: str,
    choices: Union[List[tuple], Type[Enum], Type[ChoiceEnum]],
    **kwargs
) -> ChoiceField:
    """
    Create a choice field and dynamically add it to a model.

    This function demonstrates how choice fields integrate with Eden models.
    """
    choice_field = ChoiceField(choices, **kwargs)

    # Add the field to the model class
    setattr(model_cls, field_name, choice_field)

    # You would also need to add the SQLAlchemy column to the model's table
    # This is a simplified example - in practice, this would be handled
    # by Eden's schema generation system

    return choice_field

# Validation helpers
def validate_choice(choices: List[str]):
    """Validator function for choice fields."""
    def validator(value: str) -> None:
        if value not in choices:
            raise ValueError(f"Must be one of: {choices}")
    return validator

# Example model usage (conceptual)
"""
class Article(Model):
    title: Mapped[str]
    status: Mapped[str] = ChoiceField(choices=Status, default=Status.DRAFT, db_index=True)
    priority: Mapped[str] = ChoiceField(choices=Priority, default=Priority.MEDIUM)

    # Usage
    article = Article(title="My Article", status=Status.PUBLISHED)
    print(article.status_display)  # "Published"

    # Validation
    article.status = "invalid"  # Raises ValidationError
"""