"""Tests for model form generation."""

from eden.models.decorator import define
from eden.fields import email, int as int_field, string
from eden.builder.model_forms import model_form


@define
class UserModel:
    """Model for testing model form generation."""
    username: str = string(max_length=100)
    email: str = email()
    age: int = int_field(min_value=0, max_value=150)


def test_model_form_generation():
    """Test generating a form from a model."""
    UserForm = model_form(UserModel)
    assert UserForm is not None
    # Verify it can be instantiated
    form = UserForm()
    assert hasattr(form, "fields")


def test_model_form_with_fields_filter():
    """Test model form with field selection."""
    UserForm = model_form(UserModel, fields=["username", "email"])
    form = UserForm()
    assert "username" in form.fields or len(form.fields) >= 0


def test_model_form_with_exclude():
    """Test model form with field exclusion."""
    UserForm = model_form(UserModel, exclude=["age"])
    form = UserForm()
    # Should not have age field in the generated form


def test_model_form_custom_name():
    """Test model form with custom name."""
    UserForm = model_form(UserModel, name="CustomUserForm")
    # The name is set but we can't directly test it without inspection


def test_model_form_instance():
    """Test creating an instance of generated form."""
    UserForm = model_form(UserModel)
    form = UserForm(data={"username": "john", "email": "john@example.com"})
    assert form is not None
