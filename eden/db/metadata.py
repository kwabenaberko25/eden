"""
Eden — Database Metadata Tokens

This module defines the metadata classes used with `typing.Annotated`
to specify schema constraints and column properties in a type-safe way.
"""

from typing import Any, Optional, Union, Callable
from dataclasses import dataclass


class MetadataToken:
    """Base class for all Eden database metadata tokens."""
    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"


class MaxLength(MetadataToken):
    """Specifies the maximum length for a string column."""
    def __init__(self, value: int):
        self.value = value


class MinLength(MetadataToken):
    """Specifies the minimum length for a string column."""
    def __init__(self, value: int):
        self.value = value


class MinValue(MetadataToken):
    """Specifies the minimum value for a numeric column."""
    def __init__(self, value: Any):
        self.value = value


class MaxValue(MetadataToken):
    """Specifies the maximum value for a numeric column."""
    def __init__(self, value: Any):
        self.value = value


class Indexed(MetadataToken):
    """Specifies that a column should be indexed."""
    def __init__(self, value: bool = True):
        self.value = value


class Unique(MetadataToken):
    """Specifies that a column must be unique."""
    def __init__(self, value: bool = True):
        self.value = value


class PrimaryKey(MetadataToken):
    """Specifies that a column is a primary key."""
    def __init__(self, value: bool = True):
        self.value = value


class Required(MetadataToken):
    """Specifies that a column is not nullable."""
    def __init__(self, value: bool = True):
        self.value = value


class Default(MetadataToken):
    """Specifies a default value for a column."""
    def __init__(self, value: Any):
        self.value = value


class ServerDefault(MetadataToken):
    """Specifies a server-side default value for a column."""
    def __init__(self, value: Any):
        self.value = value


class ForeignKey(MetadataToken):
    """Specifies a foreign key constraint."""
    def __init__(self, target: str, on_delete: str = "CASCADE", **kwargs: Any):
        self.target = target
        self.on_delete = on_delete
        self.kwargs = kwargs


class Choices(MetadataToken):
    """Specifies allowed values for a column."""
    def __init__(self, values: list[Any]):
        self.values = values


class Label(MetadataToken):
    """Specifies a human-readable label for the field."""
    def __init__(self, text: str):
        self.text = text


class HelpText(MetadataToken):
    """Specifies help text for the field."""
    def __init__(self, text: str):
        self.text = text


class Placeholder(MetadataToken):
    """Specifies a placeholder for the field."""
    def __init__(self, text: str):
        self.text = text


class UploadTo(MetadataToken):
    """Specifies the directory for uploaded files."""
    def __init__(self, path: str):
        self.path = path


class CustomWidget(MetadataToken):
    """Specifies a custom widget for the field in the admin/forms."""
    def __init__(self, name: str):
        self.name = name


class AutoNow(MetadataToken):
    """Update current time on every save."""
    def __init__(self, value: bool = True):
        self.value = value


class AutoNowAdd(MetadataToken):
    """Set current time on creation."""
    def __init__(self, value: bool = True):
        self.value = value

class JSON(MetadataToken):
    """Flag for JSON storage."""
    def __init__(self, value: bool = True):
        self.value = value

class OrganizationID(MetadataToken):
    """Flag for multi-tenant isolation."""
    def __init__(self, value: bool = True):
        self.value = value


@dataclass(frozen=True)
class Collation(MetadataToken):
    """Database-level collation for the column."""
    value: str

@dataclass(frozen=True)
class CheckConstraint(MetadataToken):
    """SQL Check constraint."""
    sql: str
    name: str | None = None

@dataclass(frozen=True)
class Comment(MetadataToken):
    """Database comment for the column."""
    text: str

@dataclass(frozen=True)
class Immutable(MetadataToken):
    """Prevents updating the column after initial creation."""
    pass

@dataclass(frozen=True)
class Encrypted(MetadataToken):
    """Flags the column for transparent encryption."""
    pass

@dataclass(frozen=True)
class Searchable(MetadataToken):
    """Flags the column for inclusion in full-text search index."""
    pass


def parse_metadata(metadata: list[Any]) -> tuple[dict[str, Any], list[Any], dict[str, Any]]:
    """
    Parse a list of metadata tokens into:
    1. sa_kwargs: Keyword arguments for mapped_column or relationship
    2. sa_args: Positional arguments for mapped_column (like String(50))
    3. info: Dictionary for the 'info' parameter (Eden-specific metadata)
    """
    from sqlalchemy import String as SA_String, ForeignKey as SA_ForeignKey, DateTime as SA_DateTime, func as SA_func, JSON as SA_JSON

    sa_kwargs = {}
    sa_args = []
    info = {}

    for token in metadata:
        # Support both instances and classes
        if isinstance(token, type) and issubclass(token, MetadataToken):
            token = token()
        
        # If it's already a SQLAlchemy object, we might want to pass it through to sa_args
        if not isinstance(token, MetadataToken):
            # Pass through common SA constructs if they are in metadata
            if hasattr(token, "__visit_name__"):
                 sa_args.append(token)
            continue

        if isinstance(token, MaxLength):
            info["max"] = token.value
            # We don't automatically add String(value) here to avoid conflicts,
            # but we could if no type is provided.
        elif isinstance(token, MinLength):
            info["min"] = token.value
        elif isinstance(token, MinValue):
            info["min_val"] = token.value
        elif isinstance(token, MaxValue):
            info["max_val"] = token.value
        elif isinstance(token, Indexed):
            sa_kwargs["index"] = token.value
        elif isinstance(token, Unique):
            sa_kwargs["unique"] = token.value
        elif isinstance(token, PrimaryKey):
            sa_kwargs["primary_key"] = token.value
        elif isinstance(token, Required):
            sa_kwargs["nullable"] = not token.value
            info["required"] = token.value
        elif isinstance(token, Default):
            sa_kwargs["default"] = token.value
        elif isinstance(token, ServerDefault):
            sa_kwargs["server_default"] = token.value
        elif isinstance(token, ForeignKey):
            sa_args.append(SA_ForeignKey(token.target, ondelete=token.on_delete, **token.kwargs))
        elif isinstance(token, Choices):
            info["choices"] = token.values
        elif isinstance(token, Label):
            info["label"] = token.text
        elif isinstance(token, HelpText):
            info["help_text"] = token.text
        elif isinstance(token, Placeholder):
            info["placeholder"] = token.text
        elif isinstance(token, UploadTo):
            info["upload_to"] = token.path
        elif isinstance(token, CustomWidget):
            info["widget"] = token.name
        elif isinstance(token, AutoNow):
            sa_kwargs["onupdate"] = SA_func.now()
        elif isinstance(token, AutoNowAdd):
            sa_kwargs["server_default"] = SA_func.now()
        elif isinstance(token, JSON):
            sa_args.append(SA_JSON)
        elif isinstance(token, OrganizationID):
            info["org_id"] = token.value
        elif isinstance(token, Collation):
            sa_kwargs["collation"] = token.value
        elif isinstance(token, CheckConstraint):
            from sqlalchemy import CheckConstraint as SA_CheckConstraint
            sa_args.append(SA_CheckConstraint(token.sql, name=token.name))
        elif isinstance(token, Comment):
            sa_kwargs["comment"] = token.text
        elif isinstance(token, Immutable):
            info["immutable"] = True
        elif isinstance(token, Encrypted):
            info["encrypted"] = True
        elif isinstance(token, Searchable):
            info["searchable"] = True

    return sa_kwargs, sa_args, info
