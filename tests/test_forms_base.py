"""Tests for form base classes."""

from eden.forms.base import Form, FormField, BoundForm
from eden.validators.rules import required, min_length


def test_form_field_creation():
    field = FormField(name="username", label="Username", required=True)
    assert field.name == "username"
    assert field.label == "Username"
    assert field.required is True


def test_form_init():
    class TestForm(Form):
        pass

    form = TestForm()
    assert isinstance(form, Form)
    assert form.data == {}
    assert form.errors == {}


def test_form_bind_data():
    form = Form(data={"name": "John", "email": "john@example.com"})
    assert form.data["name"] == "John"
    assert form.data["email"] == "john@example.com"


def test_form_field_validate():
    field = FormField(name="username", validators=[required()])
    field.value = ""
    result = field.validate()
    assert result.is_valid is False
    assert len(field.errors) > 0


def test_form_field_validate_success():
    field = FormField(name="username", validators=[required()])
    field.value = "john"
    result = field.validate()
    assert result.is_valid is True
    assert len(field.errors) == 0


def test_form_is_valid_empty():
    form = Form()
    assert form.is_valid() is False


def test_bound_form_creation():
    form = Form()
    bound = form.bind({"name": "John"})
    assert isinstance(bound, BoundForm)
    assert bound.data["name"] == "John"


def test_bound_form_with_validation():
    form = Form()
    form.fields["name"] = FormField(name="name", validators=[required()])
    bound = form.bind({"name": ""})
    assert bound.is_valid() is False


def test_bound_form_valid_data():
    form = Form()
    form.fields["name"] = FormField(name="name", validators=[required()])
    bound = form.bind({"name": "John"})
    assert bound.is_valid() is True
