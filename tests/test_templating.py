import pytest
from eden.templating import EdenTemplates, EdenDirectivesExtension
from jinja2 import Environment

def test_directives_preprocessing():
    ext = EdenDirectivesExtension(Environment())
    
    source = """
    @if (user.is_admin) {
        <h1>Admin</h1>
    } @else if (user.is_editor) {
        <h2>Editor</h2>
    } @else {
        <p>User</p>
    }
    
    @for (item in items) {
        <li>{{ item }}</li>
    }
    
    @auth("admin", "editor") {
        <button>Logout</button>
    }
    
    @guest {
        <button>Login</button>
    }
    
    @csrf
    @method("PUT")
    @old("email", "default@site.com")
    <input type="checkbox" @checked(active)>
    <option @selected(item.id == 1)>One</option>
    <input @disabled(true) @readonly(false)>
    
    @css("app.css")
    @js("app.js")
    @vite("main.ts")
    
    @json(my_dict)
    @dump(user)
    
    @let x = 10
    @fragment("inbox") {
        <ul id="inbox"></ul>
    }
    """
    
    processed = ext.preprocess(source, "test.html")
    
    # Assertions
    assert "{% if user.is_admin %}" in processed
    assert "{% elif user.is_editor %}" in processed
    assert "{% else %}" in processed
    assert "{% endif %}" in processed
    assert "{% for item in items %}" in processed
    assert "{% endfor %}" in processed
    
    # Premium Meta
    assert '<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">' in processed
    assert '<input type="hidden" name="_method" value="PUT">' in processed
    assert '{{ old("email", "default@site.com") }}' in processed
    
    # Premium Attributes
    assert "{% if active %}checked{% endif %}" in processed
    assert "{% if item.id == 1 %}selected{% endif %}" in processed
    assert "{% if true %}disabled{% endif %}" in processed
    assert "{% if false %}readonly{% endif %}" in processed
    
    # Premium Assets
    assert '<link rel="stylesheet" href="app.css">' in processed
    assert '<script src="app.js"></script>' in processed
    assert '{{ vite("main.ts") }}' in processed
    
    # Premium Data/Debug
    assert '{{ my_dict | json_encode }}' in processed
    assert '{{ eden_dump(user, "user") }}' in processed
    
    # Auth/Guest Check
    assert "request.user.role in ['admin', 'editor']" in processed
    assert "{% if not (request.user and request.user.is_authenticated) %}" in processed
    
    assert "{% set x = 10 %}" in processed
    assert "{% block fragment_inbox %}" in processed

def test_render_fragment(tmp_path):
    from eden.templating import EdenTemplates, render_fragment

    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    # Use multiline so the pre-processor sees the closing } on its own line
    (template_dir / "page.html").write_text(
        "<html><body>\n"
        "@fragment(\"inbox\") {\n"
        "  <ul id=\"inbox\">\n"
        "  {% for m in messages %}<li>{{ m }}</li>{% endfor %}\n"
        "  </ul>\n"
        "}\n"
        "<footer>Full page footer</footer>\n"
        "</body></html>\n"
    )

    templates = EdenTemplates(directory=str(template_dir))
    html = render_fragment(templates.env, "page.html", "inbox", {"messages": ["Hello", "World"]})

    assert "<li>Hello</li>" in html
    assert "<li>World</li>" in html
    # The footer is NOT in the fragment output
    assert "Full page footer" not in html


def test_custom_filters():
    from eden.templating import format_time_ago, format_money, class_names
    import datetime
    
    # Time Ago
    now = datetime.datetime.now()
    past = now - datetime.timedelta(minutes=5)
    assert format_time_ago(past) == "5 minutes ago"
    
    # Money
    assert format_money(1234.56) == "$1,234.56"
    assert format_money(100, currency="€") == "€100.00"
    
    # Class Names
    assert class_names("btn", {"active": True, "disabled": False}) == "btn active"

def test_widget_tweaks_filters(tmp_path):
    from eden.templating import EdenTemplates
    from eden.forms import FormField
    from markupsafe import escape
    
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    
    # We will test chained filters
    (template_dir / "form.html").write_text(
        "{{ field | add_class('new-class') | attr('placeholder', 'test') | append_attr('data-x', '1') | add_error_class('has-error') }}"
    )
    
    templates = EdenTemplates(directory=str(template_dir))
    
    # Render with no error
    field_no_error = FormField("username", "admin")
    rendered_no_error = templates.get_template("form.html").render(field=field_no_error)
    assert 'class="' in rendered_no_error
    assert 'new-class' in rendered_no_error
    assert 'has-error' not in rendered_no_error
    assert 'placeholder="test"' in rendered_no_error
    assert 'data-x="1"' in rendered_no_error

    # Render with error
    field_error = FormField("username", "admin", error="Taken")
    rendered_error = templates.get_template("form.html").render(field=field_error)
    assert 'new-class' in rendered_error
    assert 'has-error' in rendered_error

def test_ui_components(tmp_path):
    from eden.templating import EdenTemplates
    from eden.components import Component, register
    
    # 1. Register a dummy component (unique name to avoid collisions with builtins)
    @register("test_custom_alert")
    class TestAlertComponent(Component):
        template_name = "alert_component.html"
        
        def get_context_data(self, variant="info", **kwargs):
            return {
                "variant": variant,
                "icon": "i-" + variant
            }
            
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    
    # 2. Write the component's internal template
    (template_dir / "alert_component.html").write_text(
        '<div class="alert alert-{{ variant }}">'
        '<span class="icon">{{ icon }}</span>'
        '<div class="body">{{ slots.default }}</div>'
        '<div class="actions">{{ slots.actions }}</div>'
        '</div>'
    )
    
    # 3. Write a page template that uses the component
    (template_dir / "page.html").write_text(
        '@component("test_custom_alert", variant="danger") {\n'
        '  This is a dangerous action!\n'
        '  @slot("actions") {\n'
        '    <button>Confirm</button>\n'
        '  }\n'
        '}\n'
    )
    
    templates = EdenTemplates(directory=str(template_dir))
    
    rendered = templates.get_template("page.html").render()
    
    assert '<div class="alert alert-danger">' in rendered
    assert '<span class="icon">i-danger</span>' in rendered
    assert 'This is a dangerous action!' in rendered
    assert '<div class="actions">    <button>Confirm</button>\n</div>' in rendered or '<button>Confirm</button>' in rendered

@pytest.mark.asyncio
async def test_template_response(tmp_path):
    # Setup a temporary templates directory
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "index.html").write_text("@if (name) { Hello, {{ name }}! }")
    
    templates = EdenTemplates(directory=str(template_dir))
    
    # Mock request
    from unittest.mock import MagicMock
    request = MagicMock()
    request.scope = {"type": "http", "session": {}}
    
    response = templates.template_response("index.html", {"request": request, "name": "Eden"})
    
    # We can't easily check the body without running the full ASGI cycle or mocking more
    # but we can verify the template was loaded and processed
    template = templates.get_template("index.html")
    rendered = template.render(name="Eden")
    assert "Hello, Eden!" in rendered
