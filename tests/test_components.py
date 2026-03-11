"""
Tests for the Eden Component System and expanded Widget Tweaks.
"""
import pytest
from eden.forms import FormField
from markupsafe import Markup


# ── Widget Tweaks: FormField method tests ────────────────────────────────────

class TestFormFieldWidgetTweaks:
    """Test all widget-tweaks methods on FormField."""

    def test_set_attr_alias(self):
        f = FormField("email", "test@eden.dev")
        result = f.set_attr("id", "email-field")
        assert 'id="email-field"' in str(result)

    def test_remove_class(self):
        f = FormField("name", "Joe").add_class("foo").add_class("bar")
        result = f.remove_class("foo")
        rendered = str(result)
        assert "bar" in rendered
        assert "foo" not in rendered.split("bar")[1]  # foo shouldn't be in extra classes

    def test_remove_attr(self):
        f = FormField("name", "Joe").attr("data-x", "1").attr("data-y", "2")
        result = f.remove_attr("data-x")
        rendered = str(result)
        assert 'data-y="2"' in rendered
        assert 'data-x' not in rendered

    def test_add_error_attr_with_error(self):
        f = FormField("name", "Joe", error="Required")
        result = f.add_error_attr("aria-invalid", "true")
        rendered = str(result)
        assert 'aria-invalid="true"' in rendered

    def test_add_error_attr_without_error(self):
        f = FormField("name", "Joe")
        result = f.add_error_attr("aria-invalid", "true")
        rendered = str(result)
        assert 'aria-invalid' not in rendered

    def test_field_type_property(self):
        f = FormField("email", "x", input_type="email")
        assert f.field_type == "email"

    def test_widget_type_property(self):
        f = FormField("bio", "x", widget="textarea")
        assert f.widget_type == "textarea"

    def test_as_textarea(self):
        f = FormField("bio", "Hello world")
        rendered = str(f.as_textarea())
        assert "<textarea" in rendered
        assert "Hello world" in rendered
        assert "</textarea>" in rendered

    def test_as_select(self):
        f = FormField("color", "red")
        rendered = str(f.as_select(choices=[("red", "Red"), ("blue", "Blue")]))
        assert "<select" in rendered
        assert '<option value="red" selected>Red</option>' in rendered
        assert '<option value="blue">Blue</option>' in rendered
        assert "</select>" in rendered

    def test_as_hidden(self):
        f = FormField("token", "abc123")
        rendered = str(f.as_hidden())
        assert '<input type="hidden"' in rendered
        assert 'value="abc123"' in rendered

    def test_immutable_chaining(self):
        """Ensure chaining creates new instances without mutating the original."""
        original = FormField("name", "test")
        modified = original.add_class("foo").attr("data-x", "1")
        assert "foo" not in str(original)
        assert "foo" in str(modified)


# ── Widget Tweaks: Jinja filter tests ────────────────────────────────────────

class TestWidgetTweaksFilters:

    def test_render_field_directive(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "form.html").write_text(
            '@render_field(field, class="custom-input", placeholder="Enter name")'
        )

        templates = EdenTemplates(directory=str(template_dir))
        field = FormField("username", "admin")
        rendered = templates.get_template("form.html").render(field=field)

        assert "custom-input" in rendered
        assert 'placeholder="Enter name"' in rendered

    def test_field_type_filter(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "type.html").write_text("{{ field | field_type }}")

        templates = EdenTemplates(directory=str(template_dir))
        field = FormField("email", "x", input_type="email")
        rendered = templates.get_template("type.html").render(field=field)
        assert rendered.strip() == "email"

    def test_widget_type_filter(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "wtype.html").write_text("{{ field | widget_type }}")

        templates = EdenTemplates(directory=str(template_dir))
        field = FormField("bio", "x", widget="textarea")
        rendered = templates.get_template("wtype.html").render(field=field)
        assert rendered.strip() == "textarea"


# ── Built-in Component tests ─────────────────────────────────────────────────

class TestBuiltinComponents:

    def test_alert_renders(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '@component("alert", variant="danger") {\n'
            '  Something went wrong!\n'
            '}\n'
        )

        templates = EdenTemplates(directory=str(template_dir))
        rendered = templates.get_template("page.html").render()
        assert "Something went wrong!" in rendered
        assert "bg-red-900/40" in rendered
        assert "❌" in rendered

    def test_card_renders(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '@component("card", title="Dashboard") {\n'
            '  Card body content\n'
            '  @slot("footer") {\n'
            '    <button>Save</button>\n'
            '  }\n'
            '}\n'
        )

        templates = EdenTemplates(directory=str(template_dir))
        rendered = templates.get_template("page.html").render()
        assert "Dashboard" in rendered
        assert "Card body content" in rendered
        assert "<button>Save</button>" in rendered

    def test_badge_renders(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '@component("badge", text="New", variant="success") {\n'
            '}\n'
        )

        templates = EdenTemplates(directory=str(template_dir))
        rendered = templates.get_template("page.html").render()
        assert "New" in rendered
        assert "bg-emerald-600" in rendered

    def test_avatar_renders(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '@component("avatar", alt="John Doe", size="lg") {\n'
            '}\n'
        )

        templates = EdenTemplates(directory=str(template_dir))
        rendered = templates.get_template("page.html").render()
        assert "JD" in rendered  # initials
        assert "w-14 h-14" in rendered  # lg size

    def test_breadcrumb_renders(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '{{ breadcrumb_html }}'
        )

        # Use the component directly since breadcrumb takes a list
        from eden.components import get_component
        comp_cls = get_component("breadcrumb")
        assert comp_cls is not None

        inst = comp_cls()
        ctx = inst.get_context_data(items=[
            {"label": "Home", "href": "/"},
            {"label": "Products", "href": "/products"},
            {"label": "Widget"},
        ])
        assert len(ctx["items"]) == 3

    def test_tooltip_renders(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '@component("tooltip", text="Help info") {\n'
            '  <button>?</button>\n'
            '}\n'
        )

        templates = EdenTemplates(directory=str(template_dir))
        rendered = templates.get_template("page.html").render()
        assert "Help info" in rendered
        assert "<button>?</button>" in rendered

    def test_pagination_renders(self, tmp_path):
        from eden.templating import EdenTemplates
        from eden.orm import Page

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '@component("pagination", page=page_obj, url_param="p") {\n'
            '}\n'
        )

        templates = EdenTemplates(directory=str(template_dir))
        page_obj = Page(items=[1, 2], total=10, page=2, per_page=2)
        rendered = templates.get_template("page.html").render(page_obj=page_obj)
        assert "Page <span" in rendered
        assert "of <span" in rendered
        assert "Next →" in rendered

    def test_progress_renders(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '@component("progress", value=75, label="Uploading") {\n'
            '}\n'
        )

        templates = EdenTemplates(directory=str(template_dir))
        rendered = templates.get_template("page.html").render()
        assert "Uploading" in rendered
        assert "75%" in rendered
        assert "width: 75%" in rendered

    def test_stat_renders(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '@component("stat", label="Revenue", value="$5K", change="10%") {\n'
            '}\n'
        )

        templates = EdenTemplates(directory=str(template_dir))
        rendered = templates.get_template("page.html").render()
        assert "Revenue" in rendered
        assert "$5K" in rendered
        assert "10%" in rendered

    def test_spinner_renders(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '@component("spinner", label="Please wait...") {\n'
            '}\n'
        )

        templates = EdenTemplates(directory=str(template_dir))
        rendered = templates.get_template("page.html").render()
        assert "Please wait..." in rendered
        assert "animate-spin" in rendered

    def test_empty_state_renders(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '@component("empty_state", title="No Users", description="Add one.") {\n'
            '  <div>Custom content</div>\n'
            '}\n'
        )

        templates = EdenTemplates(directory=str(template_dir))
        rendered = templates.get_template("page.html").render()
        assert "No Users" in rendered
        assert "Add one." in rendered
        assert "<div>Custom content</div>" in rendered

    def test_data_table_renders(self, tmp_path):
        from eden.templating import EdenTemplates

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "page.html").write_text(
            '@component("data_table", headers=["ID", "Name"], rows=[[1, "Alice"], [2, "Bob"]]) {\n'
            '}\n'
        )

        templates = EdenTemplates(directory=str(template_dir))
        rendered = templates.get_template("page.html").render()
        assert "Name" in rendered
        assert "Alice" in rendered
        assert "Bob" in rendered
