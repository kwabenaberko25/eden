"""Tests for form builder."""

from eden.builder.form_factory import FormBuilder
from eden.forms.fields import CharField, IntegerField, EmailField


def test_form_builder_creation():
    builder = FormBuilder()
    assert isinstance(builder, FormBuilder)
    assert builder.name == "DynamicForm"


def test_form_builder_add_field():
    builder = FormBuilder()
    field = CharField(name="username", label="Username")
    builder.add_field("username", field)
    assert "username" in builder.fields


def test_form_builder_add_char_field():
    builder = FormBuilder()
    builder.add_char_field("username", label="Username", required=True)
    assert "username" in builder.fields


def test_form_builder_add_int_field():
    builder = FormBuilder()
    builder.add_int_field("age", label="Age", required=True)
    assert "age" in builder.fields


def test_form_builder_add_email_field():
    builder = FormBuilder()
    builder.add_email_field("email", label="Email", required=True)
    assert "email" in builder.fields


def test_form_builder_add_choice_field():
    builder = FormBuilder()
    choices = [("admin", "Administrator"), ("user", "User")]
    builder.add_choice_field("role", choices=choices, label="Role")
    assert "role" in builder.fields


def test_form_builder_set_name():
    builder = FormBuilder().set_name("LoginForm")
    assert builder.name == "LoginForm"


def test_form_builder_fluent_api():
    builder = (
        FormBuilder()
        .set_name("UserForm")
        .add_char_field("username", label="Username")
        .add_email_field("email", label="Email")
        .add_int_field("age", label="Age")
    )
    assert builder.name == "UserForm"
    assert len(builder.fields) == 3


def test_form_builder_build():
    builder = (
        FormBuilder()
        .add_char_field("username", label="Username")
        .add_email_field("email", label="Email")
    )
    form_class = builder.build()
    assert form_class is not None
    # Verify it can be instantiated
    form = form_class()
    assert hasattr(form, "fields")
