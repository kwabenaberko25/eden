from sqlalchemy import Integer, inspect

from eden.db import Model
from eden.models import define
from eden.fields import email, int as int_field


@define
class User:
    email: str = email(unique=True)
    age: int = int_field(default=21)


def test_model_define_sets_tablename():
    assert User.__tablename__ == "users"


def test_model_define_creates_columns():
    columns = User.__table__.columns
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
