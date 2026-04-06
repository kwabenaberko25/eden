from __future__ import annotations

from datetime import date as DateType, datetime as DateTimeType, time as TimeType
from typing import Any

from eden.fields.base import Field, FieldMetadata
from eden.fields.registry import FieldRegistry


def _create_temporal_field(
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
    )
    return Field(metadata)


def datetime(
    *,
    unique: bool = False,
    index: bool = False,
    nullable: bool = False,
    default: DateTimeType | None = None,
    default_factory: Any = None,
    primary_key: bool = False,
    label: str | None = None,
    placeholder: str | None = None,
    help_text: str | None = None,
    css_classes: list[str] | None = None,
    validators: list | None = None,
    error_messages: dict[str, str] | None = None,
) -> Field:
    return _create_temporal_field(
        db_type=DateTimeType,
        widget="datetime-local",
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


def date(
    *,
    unique: bool = False,
    index: bool = False,
    nullable: bool = False,
    default: DateType | None = None,
    default_factory: Any = None,
    primary_key: bool = False,
    label: str | None = None,
    placeholder: str | None = None,
    help_text: str | None = None,
    css_classes: list[str] | None = None,
    validators: list | None = None,
    error_messages: dict[str, str] | None = None,
) -> Field:
    return _create_temporal_field(
        db_type=DateType,
        widget="date",
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


def time(
    *,
    unique: bool = False,
    index: bool = False,
    nullable: bool = False,
    default: TimeType | None = None,
    default_factory: Any = None,
    primary_key: bool = False,
    label: str | None = None,
    placeholder: str | None = None,
    help_text: str | None = None,
    css_classes: list[str] | None = None,
    validators: list | None = None,
    error_messages: dict[str, str] | None = None,
) -> Field:
    return _create_temporal_field(
        db_type=TimeType,
        widget="time",
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


def auto_now(**kwargs: Any) -> Field:
    from datetime import datetime

    return _create_temporal_field(
        db_type=DateTimeType,
        widget="datetime-local",
        default_factory=datetime.utcnow,
        **kwargs,
    )


def auto_now_update(**kwargs: Any) -> Field:
    from datetime import datetime

    return _create_temporal_field(
        db_type=DateTimeType,
        widget="datetime-local",
        default_factory=datetime.utcnow,
        **kwargs,
    )


FieldRegistry.register("datetime", datetime)
FieldRegistry.register("date", date)
FieldRegistry.register("time", time)
FieldRegistry.register("auto_now", auto_now)
FieldRegistry.register("auto_now_update", auto_now_update)

__all__ = ["datetime", "date", "time", "auto_now", "auto_now_update"]
