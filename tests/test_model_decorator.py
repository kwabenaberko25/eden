from sqlalchemy import Integer, inspect

from eden.db import Model
from eden.models import define
from eden.fields import email, int as int_field


@define
class DefinedUser:
    email: str = email(unique=True)
    age: int = int_field(default=21)


def test_model_define_sets_tablename():
    assert DefinedUser.__tablename__ == "defined_users"


def test_model_define_creates_columns():
    columns = DefinedUser.__table__.columns
    assert "email" in columns
    assert "age" in columns
    assert columns["email"].unique is True
    assert isinstance(columns["age"].type, Integer)


def test_model_define_inherits_model_when_missing_base():
    @define
    class Tag:
        name: str = email(default="tag@example.com")

    assert issubclass(Tag, Model)
    assert Tag.__tablename__ == "tags"
    assert "name" in Tag.__table__.columns


def test_duplicate_tablename_does_not_duplicate_indexes():
    table_name = "duplicate_index_test_users"

    @define
    class DuplicateIndexUserA:
        __tablename__ = table_name
        email: str = email(unique=True)

    class DuplicateIndexUserB(Model):
        __tablename__ = table_name
        email: str = email(unique=True)

    table = Model.metadata.tables[table_name]
    index_names = [index.name for index in table.indexes]

    assert len(index_names) == len(set(index_names))
    assert "ix_duplicate_index_test_users_created_at" in index_names
    assert "ix_duplicate_index_test_users_updated_at" in index_names
