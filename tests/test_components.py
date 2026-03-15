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
        from eden.db import Page

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


# ── Component System: State Management and Actions ──────────────────────────

class TestComponentStateManagement:
    """Test component state initialization, context data, and state persistence."""

    def test_component_init_with_state(self):
        """Components should accept arbitrary state via kwargs."""
        from eden.components import Component, register
        
        @register("test_state_init")
        class TestComp(Component):
            template_name = "test.html"
        
        comp = TestComp(count=5, title="Test", enabled=True)
        assert comp.count == 5
        assert comp.title == "Test"
        assert comp.enabled is True

    def test_component_init_with_defaults(self):
        """Components with __init__ defaults should preserve them."""
        from eden.components import Component, register
        
        @register("test_defaults")
        class TestComp(Component):
            template_name = "test.html"
            
            def __init__(self, count=0, title="Default", **kwargs):
                self.count = count
                self.title = title
                super().__init__(**kwargs)
        
        comp_default = TestComp()
        assert comp_default.count == 0
        assert comp_default.title == "Default"
        
        comp_custom = TestComp(count=10, title="Custom")
        assert comp_custom.count == 10
        assert comp_custom.title == "Custom"

    def test_get_context_data_includes_state(self):
        """get_context_data should include all instance attributes."""
        from eden.components import Component, register
        
        @register("test_context_state")
        class TestComp(Component):
            template_name = "test.html"
        
        comp = TestComp(count=5, name="test", visible=True)
        ctx = comp.get_context_data()
        
        assert ctx["count"] == 5
        assert ctx["name"] == "test"
        assert ctx["visible"] is True

    def test_get_context_data_includes_helpers(self):
        """get_context_data should include action_url and component_attrs."""
        from eden.components import Component, register
        
        @register("test_helpers")
        class TestComp(Component):
            template_name = "test.html"
        
        comp = TestComp()
        ctx = comp.get_context_data()
        
        assert "action_url" in ctx
        assert callable(ctx["action_url"])
        assert "component_attrs" in ctx
        assert isinstance(ctx["component_attrs"], Markup)
        assert "component" in ctx
        assert ctx["component"] is comp

    def test_get_context_data_override_with_kwargs(self):
        """get_context_data kwargs should override state."""
        from eden.components import Component, register
        
        @register("test_context_override")
        class TestComp(Component):
            template_name = "test.html"
        
        comp = TestComp(count=5)
        ctx = comp.get_context_data(count=100, extra="value")
        
        assert ctx["count"] == 100  # Override takes precedence
        assert ctx["extra"] == "value"

    def test_get_state_simple_types(self):
        """get_state should include str, int, bool, float, list, dict, None."""
        from eden.components import Component, register
        
        @register("test_state_types")
        class TestComp(Component):
            template_name = "test.html"
        
        comp = TestComp(
            text="hello",
            num=42,
            flag=True,
            price=9.99,
            items=[1, 2, 3],
            data={"key": "val"},
            nothing=None
        )
        
        state = comp.get_state()
        assert state["text"] == "hello"
        assert state["num"] == 42
        assert state["flag"] is True
        assert state["price"] == 9.99
        assert state["items"] == [1, 2, 3]
        assert state["data"] == {"key": "val"}
        assert state["nothing"] is None

    def test_get_state_excludes_complex_types(self):
        """get_state should exclude complex objects and callables."""
        from eden.components import Component, register
        from unittest.mock import Mock
        
        @register("test_exclude_complex")
        class TestComp(Component):
            template_name = "test.html"
        
        comp = TestComp(
            name="test",
            method=lambda x: x,
            obj=object()
        )
        
        state = comp.get_state()
        assert "name" in state
        assert "method" not in state
        assert "obj" not in state

    def test_get_state_excludes_private_attributes(self):
        """get_state should exclude attributes starting with underscore."""
        from eden.components import Component, register
        
        @register("test_exclude_private")
        class TestComp(Component):
            template_name = "test.html"
        
        comp = TestComp(count=5)
        comp._internal = "hidden"
        comp._private = "also_hidden"
        
        state = comp.get_state()
        assert "count" in state
        assert "_internal" not in state
        assert "_private" not in state

    def test_get_hx_attrs_json_encoding(self):
        """get_hx_attrs should return JSON-encoded hx-vals."""
        from eden.components import Component, register
        
        @register("test_hx_attrs")
        class TestComp(Component):
            template_name = "test.html"
        
        comp = TestComp(count=5, title="test")
        attrs = comp.get_hx_attrs()
        
        assert isinstance(attrs, Markup)
        assert "hx-vals=" in attrs
        # JSON should be in the output (ignoring whitespace variations)
        assert '"count"' in attrs or '"count' in attrs
        assert '"5"' in attrs or ': 5' in attrs or ':5' in attrs


class TestComponentActions:
    """Test @action decorator and action dispatch."""

    def test_action_marks_function(self):
        """@action should mark functions with _is_eden_action flag."""
        from eden.components import Component, register, action
        
        @register("test_action_mark")
        class TestComp(Component):
            template_name = "test.html"
            
            @action
            async def my_action(self, request):
                return "result"
        
        assert hasattr(TestComp.my_action, "_is_eden_action")
        assert TestComp.my_action._is_eden_action is True

    def test_action_default_slug(self):
        """@action without args should use method name as slug."""
        from eden.components import Component, register, action
        
        @register("test_action_slug")
        class TestComp(Component):
            template_name = "test.html"
            
            @action
            async def increment(self, request):
                pass
        
        assert TestComp.increment._action_slug == "increment"

    def test_action_custom_slug(self):
        """@action with string should use that as slug."""
        from eden.components import Component, register, action
        
        @register("test_custom_slug")
        class TestComp(Component):
            template_name = "test.html"
            
            @action("custom")
            async def my_method(self, request):
                pass
        
        assert TestComp.my_method._action_slug == "custom"

    def test_action_url_generation(self):
        """action_url should generate correct HTMX endpoint."""
        from eden.components import Component, register
        
        @register("counter")
        class TestComp(Component):
            template_name = "test.html"
        
        comp = TestComp()
        assert comp.action_url("increment") == "/_eden/component/counter/increment"
        assert comp.action_url("decrement") == "/_eden/component/counter/decrement"
        assert comp.action_url("reset") == "/_eden/component/counter/reset"

    def test_register_auto_discovers_actions(self):
        """@register should auto-discover @action methods."""
        from eden.components import Component, register, action, _action_registry
        
        @register("test_discovery")
        class TestComp(Component):
            template_name = "test.html"
            
            @action
            async def my_action(self, request):
                pass
        
        # Should be in global action registry
        assert "my_action" in _action_registry
        comp_cls, method_name = _action_registry["my_action"]
        assert comp_cls is TestComp
        assert method_name == "my_action"


class TestComponentIntegration:
    """Integration tests combining multiple component features."""

    def test_counter_component_example(self):
        """Test a complete Counter component (like the example)."""
        from eden.components import Component, register, action
        
        @register("counter_test")
        class CounterComponent(Component):
            template_name = "test.html"
            
            def __init__(self, count=0, step=1, **kwargs):
                self.count = count
                self.step = step
                super().__init__(**kwargs)
            
            @action
            async def increment(self, request):
                self.count += self.step
                return await self.render()
            
            @action
            async def decrement(self, request):
                self.count -= self.step
                return await self.render()
            
            @action("reset")
            async def reset_count(self, request):
                self.count = 0
                return await self.render()
        
        # Test initialization
        comp = CounterComponent(count=5, step=2)
        assert comp.count == 5
        assert comp.step == 2
        
        # Test state persistence
        state = comp.get_state()
        assert state["count"] == 5
        assert state["step"] == 2
        
        # Test context data
        ctx = comp.get_context_data()
        assert ctx["count"] == 5
        assert ctx["step"] == 2
        assert callable(ctx["action_url"])
        
        # Test action URL generation
        assert comp.action_url("increment") == "/_eden/component/counter_test/increment"
        assert comp.action_url("reset") == "/_eden/component/counter_test/reset"
        
        # Test action marks
        assert CounterComponent.increment._is_eden_action is True
        assert CounterComponent.increment._action_slug == "increment"
        assert CounterComponent.reset_count._action_slug == "reset"

    def test_todo_list_component_structure(self):
        """Test a TodoList component with list state management."""
        from eden.components import Component, register, action
        
        @register("todos_test")
        class TodoListComponent(Component):
            template_name = "test.html"
            
            def __init__(self, items=None, next_id=1, **kwargs):
                self.items = items or []
                self.next_id = next_id
                super().__init__(**kwargs)
            
            def get_context_data(self, **kwargs):
                ctx = super().get_context_data(**kwargs)
                ctx["pending_count"] = sum(1 for i in self.items if not i.get("done"))
                ctx["done_count"] = sum(1 for i in self.items if i.get("done"))
                return ctx
            
            @action
            async def add_item(self, request, text: str):
                if text.strip():
                    self.items.append({"id": self.next_id, "text": text.strip(), "done": False})
                    self.next_id += 1
                return await self.render()
            
            @action
            async def toggle_item(self, request, item_id: int):
                for item in self.items:
                    if item.get("id") == item_id:
                        item["done"] = not item.get("done", False)
                return await self.render()
        
        # Test initialization
        todo_comp = TodoListComponent()
        assert todo_comp.items == []
        assert todo_comp.next_id == 1
        
        # Test with initial items
        items = [{"id": 1, "text": "Task 1", "done": False}]
        todo_comp2 = TodoListComponent(items=items, next_id=2)
        assert len(todo_comp2.items) == 1
        assert todo_comp2.next_id == 2
        
        # Test context data with computed fields
        ctx = todo_comp2.get_context_data()
        assert ctx["pending_count"] == 1
        assert ctx["done_count"] == 0
        
        # Test state persistence includes lists
        state = todo_comp2.get_state()
        assert state["items"] == items
        assert state["next_id"] == 2
