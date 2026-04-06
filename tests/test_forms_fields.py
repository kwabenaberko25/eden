"""Tests for form fields."""

from eden.forms.fields import CharField, IntegerField, EmailField, ChoiceField


def test_char_field_creation():
    field = CharField(name="username", label="Username", required=True)
    assert field.name == "username"
    assert field.label == "Username"
    assert field.required is True


def test_char_field_with_length_constraints():
    field = CharField(name="username", min_length=3, max_length=20)
    field.value = "ab"
    result = field.validate()
    assert result.is_valid is False


def test_char_field_valid():
    field = CharField(name="username", min_length=3, max_length=20)
    field.value = "john"
    result = field.validate()
    assert result.is_valid is True


def test_integer_field_creation():
    field = IntegerField(name="age", label="Age", required=True)
    assert field.name == "age"
    assert field.label == "Age"


def test_integer_field_with_range():
    field = IntegerField(name="age", min_value=0, max_value=150)
    field.value = 200
    result = field.validate()
    assert result.is_valid is False


def test_integer_field_valid():
    field = IntegerField(name="age", min_value=0, max_value=150)
    field.value = 25
    result = field.validate()
    assert result.is_valid is True


def test_email_field_creation():
    field = EmailField(name="email", label="Email Address", required=True)
    assert field.name == "email"
    assert field.label == "Email Address"


def test_email_field_invalid():
    field = EmailField(name="email")
    field.value = "invalid-email"
    result = field.validate()
    assert result.is_valid is False


def test_email_field_valid():
    field = EmailField(name="email")
    field.value = "john@example.com"
    result = field.validate()
    assert result.is_valid is True


def test_choice_field_creation():
    field = ChoiceField(
        name="role",
        choices=[("admin", "Administrator"), ("user", "User")],
    )
    assert field.name == "role"
    assert len(field.choices) == 2


def test_choice_field_widget():
    field = ChoiceField(
        name="role",
        choices=[("admin", "Administrator"), ("user", "User")],
    )
    html = field.widget.render("role", "admin")
    assert "option" in html
    assert "Administrator" in html
    assert "selected" in html
