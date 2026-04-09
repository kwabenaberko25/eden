from __future__ import annotations
"""Form rendering utilities."""


from typing import Any

from eden.forms.base import Form, BoundForm, FormField, BoundFormField


class FormRenderer:
    """Renders forms as HTML."""

    def __init__(self, include_errors: bool = True, include_labels: bool = True):
        self.include_errors = include_errors
        self.include_labels = include_labels

    def render_form(self, form: Form[Any] | BoundForm) -> str:
        """Render a complete form."""
        lines = ['<form method="post">']

        if isinstance(form, BoundForm):
            for bound_field in form.bound_fields.values():
                lines.append(self.render_field(bound_field))
        else:
            for field in form.fields.values():
                lines.append(self.render_field(field))

        lines.append("</form>")
        return "\n".join(lines)

    def render_field(
        self, field: FormField | BoundFormField
    ) -> str:
        """Render a single form field."""
        lines = []

        if isinstance(field, BoundFormField):
            field_obj = field.field
            value = field.value
            errors = field.errors
        else:
            field_obj = field
            value = field.value
            errors = field.errors

        # Render label
        if self.include_labels and field_obj.label:
            lines.append(
                f'<label for="{field_obj.name}">'
                f"{field_obj.label}"
                f"</label>"
            )

        # Render input
        if hasattr(field_obj, "widget"):
            widget_html = field_obj.widget.render(field_obj.name, value)
            lines.append(widget_html)

        # Render errors
        if self.include_errors and errors:
            lines.append("<ul class='errors'>")
            for error in errors:
                lines.append(f"<li>{error}</li>")
            lines.append("</ul>")

        # Render help text
        if field_obj.help_text:
            lines.append(f"<p class='help-text'>{field_obj.help_text}</p>")

        return "\n".join(lines)
