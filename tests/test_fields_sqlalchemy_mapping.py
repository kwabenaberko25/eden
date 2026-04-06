from decimal import Decimal
from uuid import UUID

from sqlalchemy import Integer, String

from eden.fields import FieldMetadata, field_to_column, get_sqlalchemy_type


def test_get_sqlalchemy_type_string_length():
    metadata = FieldMetadata(name="name", db_type=str, max_length=100)
    sa_type = get_sqlalchemy_type(metadata)
    assert isinstance(sa_type, String)
    assert sa_type.length == 100


def test_get_sqlalchemy_type_uuid():
    metadata = FieldMetadata(name="uuid", db_type=UUID)
    sa_type = get_sqlalchemy_type(metadata)
    assert isinstance(sa_type, String)
    assert sa_type.length == 36


def test_field_to_column_basic():
    metadata = FieldMetadata(name="count", db_type=int, nullable=False, unique=True)
    column = field_to_column(metadata)
    assert column.name == "count"
    assert isinstance(column.type, Integer)
    assert column.unique is True
    assert column.nullable is False


def test_field_to_column_default_factory():
    metadata = FieldMetadata(name="created_at", db_type=str, default_factory=lambda: "now")
    column = field_to_column(metadata)
    assert column.default is not None
