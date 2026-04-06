from __future__ import annotations

from typing import Any

from eden.fields.base import Field, FieldMetadata
from eden.fields.registry import FieldRegistry


def _create_relationship_field(
    relation_type: str,
    target_model: Any,
    *,
    name: str | None = None,
    nullable: bool = False,
    related_name: str | None = None,
    through: Any = None,
    on_delete: str | None = None,
    label: str | None = None,
    help_text: str | None = None,
    validators: list | None = None,
    error_messages: dict[str, str] | None = None,
) -> Field:
    css_classes: list[str] = []
    if related_name:
        css_classes.append(f"related_name:{related_name}")
    if through:
        css_classes.append(f"through:{through}")
    if on_delete:
        css_classes.append(f"on_delete:{on_delete}")

    metadata = FieldMetadata(
        name=name,
        db_type=target_model,
        widget="relationship",
        nullable=nullable,
        label=label,
        help_text=help_text,
        validators=validators,
        error_messages=error_messages,
        relation_type=relation_type,
        related_model=target_model,
        related_name=related_name,
        on_delete=on_delete,
        through=through,
        css_classes=css_classes,
    )
    metadata.pattern = relation_type
    metadata.choices = [
        ("target", getattr(target_model, "__name__", str(target_model)))
    ]
    return Field(metadata)


def foreign_key(target_model: Any, **kwargs: Any) -> Field:
    return _create_relationship_field("foreign_key", target_model, **kwargs)


def one_to_one(target_model: Any, **kwargs: Any) -> Field:
    return _create_relationship_field("one_to_one", target_model, **kwargs)


def many_to_many(target_model: Any, **kwargs: Any) -> Field:
    return _create_relationship_field("many_to_many", target_model, **kwargs)


FieldRegistry.register("foreign_key", foreign_key)
FieldRegistry.register("one_to_one", one_to_one)
FieldRegistry.register("many_to_many", many_to_many)

__all__ = ["foreign_key", "one_to_one", "many_to_many"]
