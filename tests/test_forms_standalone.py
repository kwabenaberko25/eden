"""Tests for standalone form usage."""

from eden.forms import Form
from eden.forms.fields import CharField, IntegerField


def test_form_as_standalone():
    """Verify form can be used standalone."""
    form = Form(data={"name": "John", "age": "25"})
    form.fields["name"] = CharField(name="name", label="Name")
    form.fields["age"] = IntegerField(name="age", label="Age")
    
    form.fields["name"].value = form.data.get("name")
    form.fields["age"].value = form.data.get("age")
    
    assert form.fields["name"].value == "John"
    assert form.fields["age"].value == "25"

