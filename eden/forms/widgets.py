from __future__ import annotations
"""Form widgets for rendering input elements."""


from typing import Any
from html import escape


class Widget:
    """Base widget class for rendering form inputs."""

    widget_type: str = "input"
    input_type: str = "text"

    def __init__(self, attrs: dict[str, str] | None = None):
        self.attrs = attrs or {}

    def render(self, name: str, value: Any | None = None) -> str:
        """Render the widget as HTML."""
        raise NotImplementedError

    def _build_attrs(self, **kwargs: str) -> dict[str, str]:
        """Build HTML attributes."""
        attrs = self.attrs.copy()
        attrs.update(kwargs)
        return attrs

    def _attrs_to_html(self, attrs: dict[str, str]) -> str:
        """Convert attributes dict to HTML string."""
        parts = []
        for key, value in attrs.items():
            if value is not None:
                parts.append(f'{key}="{escape(str(value))}"')
        return " ".join(parts)


class TextInput(Widget):
    """Text input widget."""

    input_type = "text"

    def render(self, name: str, value: Any | None = None) -> str:
        """Render text input."""
        attrs = self._build_attrs(
            type="text",
            name=name,
            value=escape(str(value)) if value is not None else "",
        )
        html = self._attrs_to_html(attrs)
        return f"<input {html}>"


class NumberInput(Widget):
    """Number input widget."""

    input_type = "number"

    def render(self, name: str, value: Any | None = None) -> str:
        """Render number input."""
        attrs = self._build_attrs(
            type="number",
            name=name,
            value=escape(str(value)) if value is not None else "",
        )
        html = self._attrs_to_html(attrs)
        return f"<input {html}>"


class EmailInput(Widget):
    """Email input widget."""

    input_type = "email"

    def render(self, name: str, value: Any | None = None) -> str:
        """Render email input."""
        attrs = self._build_attrs(
            type="email",
            name=name,
            value=escape(str(value)) if value is not None else "",
        )
        html = self._attrs_to_html(attrs)
        return f"<input {html}>"


class Textarea(Widget):
    """Textarea widget."""

    widget_type = "textarea"

    def render(self, name: str, value: Any | None = None) -> str:
        """Render textarea."""
        attrs = self._build_attrs(name=name)
        html = self._attrs_to_html(attrs)
        content = escape(str(value)) if value is not None else ""
        return f"<textarea {html}>{content}</textarea>"


class Select(Widget):
    """Select/dropdown widget."""

    widget_type = "select"

    def __init__(
        self,
        choices: list[tuple[str, str]] | None = None,
        attrs: dict[str, str] | None = None,
    ):
        super().__init__(attrs)
        self.choices = choices or []

    def render(self, name: str, value: Any | None = None) -> str:
        """Render select."""
        attrs = self._build_attrs(name=name)
        html = self._attrs_to_html(attrs)

        options = []
        for option_value, option_label in self.choices:
            selected = " selected" if str(value) == str(option_value) else ""
            options.append(
                f'<option value="{escape(str(option_value))}"{selected}>'
                f"{escape(str(option_label))}"
                f"</option>"
            )

        options_html = "\n".join(options)
        return f"<select {html}>\n{options_html}\n</select>"


class Checkbox(Widget):
    """Checkbox widget."""

    input_type = "checkbox"

    def render(self, name: str, value: Any | None = None) -> str:
        """Render checkbox."""
        checked = " checked" if value else ""
        attrs = self._build_attrs(type="checkbox", name=name, value="on")
        html = self._attrs_to_html(attrs)
        return f"<input {html}{checked}>"
