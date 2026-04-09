from __future__ import annotations
"""Layout building for forms."""


from dataclasses import dataclass, field as dataclass_field
from typing import Any


@dataclass
class Section:
    """A section in a form layout."""

    title: str | None = None
    description: str | None = None
    fields: list[str] = dataclass_field(default_factory=list)
    css_class: str = "form-section"

    def render(self) -> str:
        """Render the section as HTML."""
        lines = []
        if self.title:
            lines.append(f'<div class="{self.css_class}">')
            lines.append(f"<h3>{self.title}</h3>")
            if self.description:
                lines.append(f"<p>{self.description}</p>")
        return "\n".join(lines)


@dataclass
class Row:
    """A row in a form layout containing multiple columns."""

    columns: list[Column] = dataclass_field(default_factory=list)
    css_class: str = "form-row"

    def render(self) -> str:
        """Render the row as HTML."""
        lines = [f'<div class="{self.css_class}">']
        for column in self.columns:
            lines.append(column.render())
        lines.append("</div>")
        return "\n".join(lines)


@dataclass
class Column:
    """A column in a form row."""

    fields: list[str] = dataclass_field(default_factory=list)
    width: int = 1  # Width in units
    css_class: str = "form-column"

    def render(self) -> str:
        """Render the column as HTML."""
        lines = [f'<div class="{self.css_class}" style="flex: {self.width};">']
        for field_name in self.fields:
            lines.append(f"<!-- field: {field_name} -->")
        lines.append("</div>")
        return "\n".join(lines)


@dataclass
class Layout:
    """Layout container for forms."""

    sections: list[Section] = dataclass_field(default_factory=list)
    rows: list[Row] = dataclass_field(default_factory=list)
    css_class: str = "form-layout"

    def add_section(self, section: Section) -> Layout:
        """Add a section to the layout."""
        self.sections.append(section)
        return self

    def add_row(self, row: Row) -> Layout:
        """Add a row to the layout."""
        self.rows.append(row)
        return self

    def render(self) -> str:
        """Render the layout as HTML."""
        lines = [f'<div class="{self.css_class}">']

        for section in self.sections:
            lines.append(section.render())

        for row in self.rows:
            lines.append(row.render())

        lines.append("</div>")
        return "\n".join(lines)


__all__ = ["Layout", "Row", "Column", "Section"]
