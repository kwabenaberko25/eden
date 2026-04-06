from __future__ import annotations

from decimal import Decimal
from enum import Enum
from uuid import UUID
from typing import Any

from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, JSON, Numeric, String, Time, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey

from eden.fields.base import FieldMetadata


TYPE_MAP = {
    str: String,
    int: Integer,
    float: Float,
    bool: Boolean,
    dict: JSON,
    list: JSON,
    Decimal: Numeric,
    UUID: String,
}


def get_sqlalchemy_type(metadata: FieldMetadata) -> Any:
    db_type = metadata.db_type
    if db_type in TYPE_MAP:
        type_cls = TYPE_MAP[db_type]
        if db_type is str and metadata.max_length:
            return type_cls(metadata.max_length)
        if db_type is UUID:
            return type_cls(36)
        return type_cls()

    if isinstance(db_type, type) and issubclass(db_type, Enum):
        return SAEnum(db_type)

    return Text()


def field_to_column(metadata: FieldMetadata) -> Column:
    if metadata.name is None:
        raise ValueError("FieldMetadata.name is required for SQLAlchemy column creation")

    column_type = get_sqlalchemy_type(metadata)
    kwargs: dict[str, Any] = {
        "primary_key": metadata.primary_key,
        "unique": metadata.unique,
        "index": metadata.index,
        "nullable": metadata.nullable,
    }

    if metadata.default_factory is not None:
        kwargs["default"] = metadata.default_factory
    elif metadata.default is not None:
        kwargs["default"] = metadata.default

    if metadata.pattern and metadata.choices:
        kwargs["info"] = {"choices": metadata.choices}

    if metadata.pattern and isinstance(metadata.pattern, str) and metadata.pattern.startswith("foreign_key:"):
        # Legacy support for relationship-style metadata
        ref_table = metadata.pattern.split(":", 1)[1]
        return Column(ForeignKey(ref_table), **kwargs)

    return Column(metadata.name, column_type, **kwargs)
