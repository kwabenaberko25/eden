from __future__ import annotations

from typing import Any
from uuid import UUID

from eden.fields.base import Field, FieldMetadata
from eden.fields.registry import FieldRegistry


def _create_string_field(
    widget: str = "input",
    db_type: type = str,
    *,
    name: str | None = None,
    unique: bool = False,
    index: bool = False,
    nullable: bool = False,
    default: Any = None,
    default_factory: Any = None,
    primary_key: bool = False,
    label: str | None = None,
    placeholder: str | None = None,
    help_text: str | None = None,
    css_classes: list[str] | None = None,
    validators: list | None = None,
    error_messages: dict[str, str] | None = None,
    max_length: int | None = None,
    min_length: int | None = None,
    pattern: str | None = None,
    choices: list[tuple] | None = None,
) -> Field:
    metadata = FieldMetadata(
        name=name,
        db_type=db_type,
        widget=widget,
        unique=unique,
        index=index,
        nullable=nullable,
        default=default,
        default_factory=default_factory,
        primary_key=primary_key,
        label=label,
        placeholder=placeholder,
        help_text=help_text,
        css_classes=css_classes,
        validators=validators,
        error_messages=error_messages,
        max_length=max_length,
        min_length=min_length,
        pattern=pattern,
        choices=choices,
    )
    return Field(metadata)


def string(
    *,
    unique: bool = False,
    index: bool = False,
    nullable: bool = False,
    default: Any = None,
    default_factory: Any = None,
    primary_key: bool = False,
    label: str | None = None,
    placeholder: str | None = None,
    help_text: str | None = None,
    css_classes: list[str] | None = None,
    validators: list | None = None,
    error_messages: dict[str, str] | None = None,
    max_length: int | None = None,
    min_length: int | None = None,
    pattern: str | None = None,
    choices: list[tuple] | None = None,
) -> Field:
    return _create_string_field(
        widget="input",
        db_type=str,
        unique=unique,
        index=index,
        nullable=nullable,
        default=default,
        default_factory=default_factory,
        primary_key=primary_key,
        label=label,
        placeholder=placeholder,
        help_text=help_text,
        css_classes=css_classes,
        validators=validators,
        error_messages=error_messages,
        max_length=max_length,
        min_length=min_length,
        pattern=pattern,
        choices=choices,
    )


def email(**kwargs: Any) -> Field:
    return _create_string_field(
        widget="email",
        db_type=str,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        **kwargs,
    )


def url(**kwargs: Any) -> Field:
    return _create_string_field(
        widget="url",
        db_type=str,
        pattern=r"^https?://.+$",
        **kwargs,
    )


def slug(**kwargs: Any) -> Field:
    return _create_string_field(
        widget="text",
        db_type=str,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        **kwargs,
    )


def phone(**kwargs: Any) -> Field:
    return _create_string_field(
        widget="tel",
        db_type=str,
        pattern=r"^\+?[0-9\-\s()]+$",
        **kwargs,
    )


def text(**kwargs: Any) -> Field:
    return _create_string_field(
        widget="textarea",
        db_type=str,
        **kwargs,
    )


def password(**kwargs: Any) -> Field:
    return _create_string_field(
        widget="password",
        db_type=str,
        **kwargs,
    )


def uuid(**kwargs: Any) -> Field:
    return _create_string_field(
        widget="text",
        db_type=UUID,
        **kwargs,
    )


FieldRegistry.register("string", string)
FieldRegistry.register("email", email)
FieldRegistry.register("url", url)
FieldRegistry.register("slug", slug)
FieldRegistry.register("phone", phone)
FieldRegistry.register("text", text)
FieldRegistry.register("password", password)
FieldRegistry.register("uuid", uuid)

__all__ = [
    "string",
    "email",
    "url",
    "slug",
    "phone",
    "text",
    "password",
    "uuid",
]
