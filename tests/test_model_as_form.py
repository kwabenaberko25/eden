import pytest
from datetime import datetime
from eden.orm import Model, f
from eden.forms import BaseForm

class UserProfileFormTest(Model):
    __tablename__ = "test_user_profiles_as_form"
    name: str = f(max_length=50)
    age: int = f()
    bio: str = f(widget="textarea")
    is_active: bool = f(default=True)
    joined_at: datetime = f(default=None, nullable=True)



@pytest.mark.asyncio
async def test_model_to_schema_extracts_widgets():
    schema = UserProfileFormTest.to_schema(only_columns=True)
    
    # "name" is a String -> text (default), max_length=50
    name_field = schema.model_fields["name"]
    assert name_field.json_schema_extra is None or "widget" not in name_field.json_schema_extra
    
    # "age" is an Integer -> number widget
    age_field = schema.model_fields["age"]
    assert age_field.json_schema_extra["widget"] == "number"

    # "bio" is Text -> textarea widget
    bio_field = schema.model_fields["bio"]
    assert bio_field.json_schema_extra["widget"] == "textarea"

    # "is_active" is Boolean -> checkbox widget
    active_field = schema.model_fields["is_active"]
    assert active_field.json_schema_extra["widget"] == "checkbox"

    # "joined_at" is DateTime -> datetime-local widget
    joined_field = schema.model_fields["joined_at"]
    assert joined_field.json_schema_extra["widget"] == "datetime-local"

@pytest.mark.asyncio
async def test_model_as_form_creates_baseform():
    form = UserProfileFormTest.as_form()
    
    assert isinstance(form, BaseForm)
    assert form.schema.__name__ == "UserProfileFormTestSchema"
    
    # Check that widgets correctly render in the form HTML fields
    assert form["name"].widget_type == "input"
    assert form["age"].widget_type == "number"
    assert form["bio"].widget_type == "textarea"
    assert form["is_active"].widget_type == "checkbox"
    assert form["joined_at"].widget_type == "datetime-local"

    # Test pre-filled data working
    form_with_data = UserProfileFormTest.as_form(data={"name": "John", "age": 30})
    assert form_with_data["name"].value == "John"
    assert form_with_data["age"].value == 30

@pytest.mark.asyncio
async def test_model_as_form_include_exclude():
    form = UserProfileFormTest.as_form(include=["name", "age"])
    assert "name" in form.schema.model_fields
    assert "age" in form.schema.model_fields
    assert "bio" not in form.schema.model_fields

    form_ex = UserProfileFormTest.as_form(exclude={"is_active", "joined_at"})
    assert "name" in form_ex.schema.model_fields
    assert "is_active" not in form_ex.schema.model_fields
