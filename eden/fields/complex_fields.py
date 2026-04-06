from __future__ import annotations

from typing import Any

from eden.fields.base import Field, FieldMetadata
from eden.fields.registry import FieldRegistry


def _create_complex_field(
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
    choices: list[tuple] | None = None,
    item_type: type | None = None,
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
        choices=choices,
    )
    if item_type is not None:
        metadata.pattern = getattr(item_type, "__name__", str(item_type))
    return Field(metadata)


def json(**kwargs: Any) -> Field:
    return _create_complex_field(
        db_type=dict,
        widget="textarea",
        **kwargs,
    )


def array(item_type: type = str, **kwargs: Any) -> Field:
    return _create_complex_field(
        db_type=list,
        widget="textarea",
        item_type=item_type,
        **kwargs,
    )


def enum(choices: list[tuple], **kwargs: Any) -> Field:
    return _create_complex_field(
        db_type=str,
        widget="select",
        choices=choices,
        **kwargs,
    )


def file(**kwargs: Any) -> Field:
    return _create_complex_field(
        db_type=bytes,
        widget="file",
        **kwargs,
    )


def image(**kwargs: Any) -> Field:
    metadata = _create_complex_field(
        db_type=bytes,
        widget="file",
        **kwargs,
    )
    metadata.metadata.widget = "image"
    return metadata


FieldRegistry.register("json", json)
FieldRegistry.register("array", array)
FieldRegistry.register("enum", enum)
FieldRegistry.register("file", file)
FieldRegistry.register("image", image)

__all__ = ["json", "array", "enum", "file", "image"]
