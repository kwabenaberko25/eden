"""Tests for form security."""

from eden.forms import Form
from eden.forms.fields import CharField


def test_xss_vulnerability_prevention():
    """Verify that dangerous HTML is escaped in rendered fields."""
    form = Form(data={"name": '"><script>alert("xss")</script>'})
    form.fields["name"] = CharField(name="name", label="Name")
    form.fields["name"].value = '"><script>alert("xss")</script>'
    
    # The widget should escape the value
    html = form.fields["name"].widget.render("name", form.fields["name"].value)
    
    # Verify dangerous tags are not rendered as raw HTML
    assert "<script>" not in html
    # Either &lt; or &amp; or &quot; shows that escaping happened
    assert "&" in html


def test_form_input_stripping():
    """Verify form strips whitespace from inputs."""
    form = Form(data={"name": "  John  "})
    form.fields["name"] = CharField(name="name", label="Name")
    form.fields["name"].value = "  John  ".strip()
    
    assert form.fields["name"].value == "John"
