"""
Eden ORM - Field Types and Column Definitions

Defines the mapping between Python types and PostgreSQL column types.
"""

from typing import Any, Optional, Type, Union, List, Dict
from dataclasses import dataclass
from enum import Enum
import uuid
from datetime import datetime, date, time
import json


class ColumnType(Enum):
    """PostgreSQL column type mappings."""
    
    # Basic types
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    SMALLINT = "SMALLINT"
    FLOAT = "FLOAT"
    DECIMAL = "DECIMAL"
    
    # String types
    VARCHAR = "VARCHAR"
    TEXT = "TEXT"
    CHAR = "CHAR"
    
    # UUID
    UUID = "UUID"
    
    # Date/Time
    DATE = "DATE"
    TIME = "TIME"
    TIMESTAMP = "TIMESTAMP"
    TIMESTAMP_TZ = "TIMESTAMP WITH TIME ZONE"
    
    # JSON
    JSON = "JSON"
    JSONB = "JSONB"
    
    # Array types
    INTEGER_ARRAY = "INTEGER[]"
    TEXT_ARRAY = "TEXT[]"
    
    # Custom
    BYTEA = "BYTEA"


@dataclass
class ColumnConstraint:
    """Column constraints."""
    
    primary_key: bool = False
    unique: bool = False
    not_null: bool = False
    index: bool = False
    default: Any = None
    check: Optional[str] = None


class Field:
    """Base field descriptor for model columns."""
    
    def __init__(
        self,
        column_type: ColumnType,
        python_type: Type,
        *,
        primary_key: bool = False,
        unique: bool = False,
        nullable: bool = True,
        index: bool = False,
        default: Any = None,
        default_factory: Optional[callable] = None,
        check: Optional[str] = None,
        on_delete: Optional[str] = None,  # For ForeignKey
        on_update: Optional[str] = None,  # For ForeignKey
    ):
        self.column_type = column_type
        self.python_type = python_type
        self.primary_key = primary_key
        self.unique = unique
        self.nullable = nullable
        self.index = index
        self.default = default
        self.default_factory = default_factory
        self.check = check
        self.on_delete = on_delete
        self.on_update = on_update
        self.name: Optional[str] = None  # Set by metaclass
        self.model: Optional[Type] = None  # Set by metaclass
    
    def get_default(self) -> Any:
        """Get default value for this field."""
        if self.default_factory:
            return self.default_factory()
        return self.default
    
    def __get__(self, obj, objtype=None):
        """Descriptor get."""
        if obj is None:
            return self
        return obj.__dict__.get(self.name)
    
    def __set__(self, obj, value):
        """Descriptor set."""
        obj.__dict__[self.name] = value
    
    def sql_definition(self) -> str:
        """Generate SQL column definition."""
        parts = [self.column_type.value]
        
        if self.primary_key:
            parts.append("PRIMARY KEY")
        elif not self.nullable:
            parts.append("NOT NULL")
        
        if self.unique:
            parts.append("UNIQUE")
        
        if self.default is not None:
            if isinstance(self.default, str):
                parts.append(f"DEFAULT '{self.default}'")
            elif isinstance(self.default, bool):
                parts.append(f"DEFAULT {str(self.default).upper()}")
            else:
                parts.append(f"DEFAULT {self.default}")
        
        if self.check:
            parts.append(f"CHECK ({self.check})")
        
        return " ".join(parts)


# Convenience constructors

def StringField(
    max_length: int = 255,
    **kwargs
) -> Field:
    """String column (VARCHAR)."""
    field = Field(ColumnType.VARCHAR, str, **kwargs)
    field.max_length = max_length
    return field


def TextField(**kwargs) -> Field:
    """Text column (unlimited length)."""
    return Field(ColumnType.TEXT, str, **kwargs)


def IntField(**kwargs) -> Field:
    """Integer column."""
    return Field(ColumnType.INTEGER, int, **kwargs)


def BigIntField(**kwargs) -> Field:
    """Big integer column (64-bit)."""
    return Field(ColumnType.BIGINT, int, **kwargs)


def FloatField(**kwargs) -> Field:
    """Float column."""
    return Field(ColumnType.FLOAT, float, **kwargs)


def BooleanField(default: bool = False, **kwargs) -> Field:
    """Boolean column."""
    return Field(ColumnType.BOOLEAN, bool, default=default, **kwargs)


def DateField(**kwargs) -> Field:
    """Date column."""
    return Field(ColumnType.DATE, date, **kwargs)


def TimeField(**kwargs) -> Field:
    """Time column."""
    return Field(ColumnType.TIME, time, **kwargs)


def DateTimeField(
    auto_now_add: bool = False,
    auto_now: bool = False,
    **kwargs
) -> Field:
    """DateTime column with timezone support."""
    
    if auto_now_add or auto_now:
        kwargs.setdefault("default_factory", lambda: datetime.utcnow())
        kwargs["nullable"] = False
    
    field = Field(ColumnType.TIMESTAMP_TZ, datetime, **kwargs)
    field.auto_now_add = auto_now_add
    field.auto_now = auto_now
    return field


def UUIDField(primary_key: bool = False, **kwargs) -> Field:
    """UUID column."""
    if primary_key:
        kwargs.setdefault("default_factory", uuid.uuid4)
    return Field(ColumnType.UUID, uuid.UUID, primary_key=primary_key, **kwargs)


def JSONField(**kwargs) -> Field:
    """JSONB column (native JSON in PostgreSQL)."""
    return Field(ColumnType.JSONB, dict, **kwargs)


def ArrayField(item_type: Type = str, **kwargs) -> Field:
    """Array column."""
    if item_type == int:
        col_type = ColumnType.INTEGER_ARRAY
    elif item_type == str:
        col_type = ColumnType.TEXT_ARRAY
    else:
        raise ValueError(f"Unsupported array type: {item_type}")
    
    return Field(col_type, List[item_type], **kwargs)


class ForeignKeyField(Field):
    """Foreign key relationship field."""
    
    def __init__(
        self,
        to: str,  # "TableName" or "app.TableName"
        *,
        on_delete: str = "CASCADE",
        on_update: str = "CASCADE",
        **kwargs
    ):
        self.to = to
        self.to_model: Optional[Type] = None  # Set later
        
        kwargs["on_delete"] = on_delete
        kwargs["on_update"] = on_update
        
        # Foreign keys are usually not nullable unless explicitly set
        kwargs.setdefault("nullable", False)
        
        super().__init__(ColumnType.UUID, uuid.UUID, **kwargs)
    
    def sql_definition(self) -> str:
        """Generate SQL foreign key definition."""
        base = super().sql_definition()
        
        if self.to_model:
            table_name = self.to_model.__tablename__
            fk_constraint = (
                f"REFERENCES {table_name}(id) "
                f"ON DELETE {self.on_delete} ON UPDATE {self.on_update}"
            )
            return f"{base} {fk_constraint}"
        
        return base


class Index:
    """Database index definition."""
    
    def __init__(self, *fields: str, unique: bool = False, name: Optional[str] = None):
        self.fields = fields
        self.unique = unique
        self.name = name
    
    def sql_definition(self, table_name: str) -> str:
        """Generate SQL index definition."""
        unique_kw = "UNIQUE" if self.unique else ""
        fields_str = ", ".join(self.fields)
        index_name = self.name or f"{table_name}_{'_'.join(self.fields)}_idx"
        return f"CREATE {unique_kw} INDEX {index_name} ON {table_name}({fields_str})"
