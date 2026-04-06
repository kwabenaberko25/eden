"""Tests for form layout builder."""

from eden.builder.layout import Layout, Row, Column, Section


def test_section_creation():
    section = Section(
        title="Personal Info",
        description="Enter your personal information",
        fields=["name", "email"],
    )
    assert section.title == "Personal Info"
    assert len(section.fields) == 2


def test_section_render():
    section = Section(title="Personal Info")
    html = section.render()
    assert "Personal Info" in html
    assert "form-section" in html


def test_column_creation():
    column = Column(fields=["name", "email"], width=2)
    assert len(column.fields) == 2
    assert column.width == 2


def test_column_render():
    column = Column(fields=["name", "email"])
    html = column.render()
    assert "form-column" in html
    assert "name" in html
    assert "email" in html


def test_row_creation():
    col1 = Column(fields=["name"], width=1)
    col2 = Column(fields=["email"], width=1)
    row = Row(columns=[col1, col2])
    assert len(row.columns) == 2


def test_row_render():
    col1 = Column(fields=["name"])
    col2 = Column(fields=["email"])
    row = Row(columns=[col1, col2])
    html = row.render()
    assert "form-row" in html
    assert "form-column" in html


def test_layout_creation():
    layout = Layout()
    assert isinstance(layout, Layout)
    assert len(layout.sections) == 0
    assert len(layout.rows) == 0


def test_layout_add_section():
    layout = Layout()
    section = Section(title="Info", fields=["name"])
    layout.add_section(section)
    assert len(layout.sections) == 1


def test_layout_add_row():
    layout = Layout()
    col = Column(fields=["name"])
    row = Row(columns=[col])
    layout.add_row(row)
    assert len(layout.rows) == 1


def test_layout_fluent_api():
    layout = (
        Layout()
        .add_section(Section(title="Personal", fields=["name"]))
        .add_row(Row(columns=[Column(fields=["email"])]))
    )
    assert len(layout.sections) == 1
    assert len(layout.rows) == 1


def test_layout_render():
    layout = (
        Layout()
        .add_section(Section(title="Personal"))
    )
    html = layout.render()
    assert "form-layout" in html
    assert "Personal" in html
