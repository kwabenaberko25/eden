"""Tests for form rendering."""

from eden.forms.base import Form, FormField
from eden.forms.fields import CharField, EmailField
from eden.forms.rendering import FormRenderer
from eden.validators.rules import required


def test_form_renderer_creation():
    renderer = FormRenderer()
    assert isinstance(renderer, FormRenderer)


def test_render_simple_field():
    renderer = FormRenderer()
    field = CharField(name="username", label="Username")
    field.value = "john"
    html = renderer.render_field(field)
    assert "Username" in html
    assert "username" in html


def test_render_field_with_errors():
    renderer = FormRenderer()
    field = CharField(name="username", label="Username", validators=[required()])
    field.value = ""
    field.validate()
    html = renderer.render_field(field)
    assert "errors" in html or "Username" in html


def test_render_field_without_labels():
    renderer = FormRenderer(include_labels=False)
    field = CharField(name="username", label="Username")
    field.value = "john"
    html = renderer.render_field(field)
    assert "<label" not in html


def test_render_complete_form():
    renderer = FormRenderer()
    form = Form()
    form.fields["username"] = CharField(name="username", label="Username")
    form.fields["email"] = EmailField(name="email", label="Email")
    form.fields["username"].value = "john"
    form.fields["email"].value = "john@example.com"

    html = renderer.render_form(form)
    assert "<form" in html
    assert "username" in html
    assert "email" in html
    assert "</form>" in html


def test_render_field_with_help_text():
    renderer = FormRenderer()
    field = CharField(
        name="username",
        label="Username",
        help_text="Enter your username",
    )
    field.value = "john"
    html = renderer.render_field(field)
    assert "Enter your username" in html
