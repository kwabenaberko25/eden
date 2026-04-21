from __future__ import annotations
"""Typed form fields."""


from typing import Any

from eden.forms.base import BasicFormField
from eden.forms.widgets import TextInput, NumberInput, EmailInput, Select
from eden.validators import rules


class CharField(BasicFormField):
    """Text input field."""

    def __init__(
        self,
        name: str,
        label: str | None = None,
        required: bool = False,
        max_length: int | None = None,
        min_length: int | None = None,
        help_text: str | None = None,
        **kwargs: Any,
    ):
        validators = []
        if min_length is not None:
            validators.append(rules.min_length(min_length))
        if max_length is not None:
            validators.append(rules.max_length(max_length))

        super().__init__(
            name=name,
            label=label,
            required=required,
            help_text=help_text,
            validators=validators,
        )
        self.widget = TextInput()
        self.max_length = max_length
        self.min_length = min_length


class IntegerField(BasicFormField):
    """Integer input field."""

    def __init__(
        self,
        name: str,
        label: str | None = None,
        required: bool = False,
        min_value: int | None = None,
        max_value: int | None = None,
        help_text: str | None = None,
        **kwargs: Any,
    ):
        validators = []
        if min_value is not None:
            validators.append(rules.min_value(min_value))
        if max_value is not None:
            validators.append(rules.max_value(max_value))

        super().__init__(
            name=name,
            label=label,
            required=required,
            help_text=help_text,
            validators=validators,
        )
        self.widget = NumberInput()
        self.min_value = min_value
        self.max_value = max_value


class EmailField(BasicFormField):
    """Email input field."""

    def __init__(
        self,
        name: str,
        label: str | None = None,
        required: bool = False,
        help_text: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            name=name,
            label=label,
            required=required,
            help_text=help_text,
            validators=[rules.email_validator()],
        )
        self.widget = EmailInput()


class ChoiceField(BasicFormField):
    """Select/choice field."""

    def __init__(
        self,
        name: str,
        choices: list[tuple[str, str]] | None = None,
        label: str | None = None,
        required: bool = False,
        help_text: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            name=name,
            label=label,
            required=required,
            help_text=help_text,
        )
        self.widget = Select(choices or [])
        self.choices = choices or []
