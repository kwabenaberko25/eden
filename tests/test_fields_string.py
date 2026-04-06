import pytest

from eden.fields import FieldRegistry, email, password, slug, phone, string, text, url, uuid


def test_string_field_metadata_defaults():
    field_obj = string()
    assert field_obj.metadata.db_type is str
    assert field_obj.metadata.widget == "input"
    assert field_obj.metadata.nullable is False
    assert field_obj.metadata.validators == []


def test_email_field_pattern_and_widget():
    field_obj = email(unique=True, index=True, label="Email")
    assert field_obj.metadata.widget == "email"
    assert field_obj.metadata.pattern.startswith("^[^@")
    assert field_obj.metadata.unique is True
    assert field_obj.metadata.index is True
    assert field_obj.metadata.label == "Email"


def test_password_and_text_fields():
    assert password().metadata.widget == "password"
    assert text().metadata.widget == "textarea"


def test_registry_has_string_helpers():
    assert FieldRegistry.get("email") is not None
    assert FieldRegistry.get("url") is not None
    assert FieldRegistry.get("password") is not None
    assert FieldRegistry.get("uuid") is not None


def test_uuid_field_type():
    field_obj = uuid()
    assert field_obj.metadata.db_type.__name__ == "UUID"
    assert field_obj.metadata.widget == "text"
