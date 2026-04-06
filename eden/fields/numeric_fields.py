from __future__ import annotations

import builtins
from decimal import Decimal
from typing import Any

from eden.fields.base import Field, FieldMetadata
from eden.fields.registry import FieldRegistry


def _create_numeric_field(
    db_type: type,
    widget: str,
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
    min_value: Any = None,
    max_value: Any = None,
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
        min_value=min_value,
        max_value=max_value,
    )
    return Field(metadata)


def int(
    *,
    unique: bool = False,
    index: bool = False,
    nullable: bool = False,
    default: int | None = None,
    default_factory: Any = None,
    primary_key: bool = False,
    label: str | None = None,
    placeholder: str | None = None,
    help_text: str | None = None,
    css_classes: list[str] | None = None,
    validators: list | None = None,
    error_messages: dict[str, str] | None = None,
    min_value: int | None = None,
    max_value: int | None = None,
) -> Field:
    return _create_numeric_field(
        db_type=builtins.int,
        widget="number",
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
        min_value=min_value,
        max_value=max_value,
    )


def float(
    *,
    unique: bool = False,
    index: bool = False,
    nullable: bool = False,
    default: float | None = None,
    default_factory: Any = None,
    primary_key: bool = False,
    label: str | None = None,
    placeholder: str | None = None,
    help_text: str | None = None,
    css_classes: list[str] | None = None,
    validators: list | None = None,
    error_messages: dict[str, str] | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
) -> Field:
    return _create_numeric_field(
        db_type=builtins.float,
        widget="number",
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
        min_value=min_value,
        max_value=max_value,
    )


def decimal(
    *,
    unique: bool = False,
    index: bool = False,
    nullable: bool = False,
    default: Decimal | None = None,
    default_factory: Any = None,
    primary_key: bool = False,
    label: str | None = None,
    placeholder: str | None = None,
    help_text: str | None = None,
    css_classes: list[str] | None = None,
    validators: list | None = None,
    error_messages: dict[str, str] | None = None,
    min_value: Decimal | None = None,
    max_value: Decimal | None = None,
) -> Field:
    return _create_numeric_field(
        db_type=Decimal,
        widget="number",
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
        min_value=min_value,
        max_value=max_value,
    )


def bool(
    *,
    unique: bool = False,
    index: bool = False,
    nullable: bool = False,
    default: bool | None = None,
    default_factory: Any = None,
    primary_key: bool = False,
    label: str | None = None,
    placeholder: str | None = None,
    help_text: str | None = None,
    css_classes: list[str] | None = None,
    validators: list | None = None,
    error_messages: dict[str, str] | None = None,
) -> Field:
    return _create_numeric_field(
        db_type=builtins.bool,
        widget="checkbox",
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
    )


FieldRegistry.register("int", int)
FieldRegistry.register("float", float)
FieldRegistry.register("decimal", decimal)
FieldRegistry.register("bool", bool)

__all__ = ["int", "float", "decimal", "bool"]
