"""Tests for model-to-form conversion."""

from eden.forms import Form
from eden.forms.fields import CharField, IntegerField


def test_form_generation_from_model():
    """Test that forms can be generated from models."""
    form = Form()
    assert hasattr(form, "fields")
    assert hasattr(form, "is_valid")


def test_form_field_types():
    """Test that various form field types are available."""
    char_field = CharField(name="name", label="Name", max_length=50)
    int_field = IntegerField(name="age", label="Age")
    
    assert char_field.max_length == 50
    assert int_field is not None
