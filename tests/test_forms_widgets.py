"""Tests for form widgets."""

from eden.forms.widgets import (
    TextInput,
    NumberInput,
    EmailInput,
    Select,
    Textarea,
    Checkbox,
)


def test_text_input_render():
    widget = TextInput()
    html = widget.render("username", "john")
    assert 'type="text"' in html
    assert 'name="username"' in html
    assert 'value="john"' in html
    assert "<input" in html


def test_text_input_render_empty():
    widget = TextInput()
    html = widget.render("username")
    assert 'value=""' in html


def test_number_input_render():
    widget = NumberInput()
    html = widget.render("age", 25)
    assert 'type="number"' in html
    assert 'value="25"' in html


def test_email_input_render():
    widget = EmailInput()
    html = widget.render("email", "john@example.com")
    assert 'type="email"' in html
    assert 'john@example.com' in html


def test_textarea_render():
    widget = Textarea()
    html = widget.render("message", "Hello")
    assert "<textarea" in html
    assert "Hello" in html


def test_select_render():
    widget = Select(
        choices=[("admin", "Administrator"), ("user", "User")]
    )
    html = widget.render("role", "admin")
    assert "<select" in html
    assert "<option" in html
    assert "Administrator" in html
    assert "selected" in html


def test_select_render_no_selection():
    widget = Select(
        choices=[("admin", "Administrator"), ("user", "User")]
    )
    html = widget.render("role")
    assert "<select" in html
    assert "selected" not in html


def test_checkbox_render_checked():
    widget = Checkbox()
    html = widget.render("accept_terms", True)
    assert 'type="checkbox"' in html
    assert "checked" in html


def test_checkbox_render_unchecked():
    widget = Checkbox()
    html = widget.render("accept_terms", False)
    assert 'type="checkbox"' in html
    assert "checked" not in html


def test_widget_with_custom_attrs():
    widget = TextInput(attrs={"class": "form-control", "placeholder": "Name"})
    html = widget.render("name", "John")
    assert 'class="form-control"' in html
    assert 'placeholder="Name"' in html
