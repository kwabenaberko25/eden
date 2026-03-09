
import os
import pytest
from starlette.testclient import TestClient
from eden.app import Eden
from eden.templating import EdenDirectivesExtension
from jinja2 import Environment

def test_line_preservation_unit():
    """Unit test for line count stability in preprocessor."""
    env = Environment()
    ext = EdenDirectivesExtension(env)
    
    # Template with multi-line @if
    template = "line 1\n@if (\n  cond\n) {\n  err\n}\nline 7"
    processed = ext.preprocess(template, "test.html")
    
    assert processed.count('\n') == template.count('\n')
    lines = processed.splitlines()
    assert "line 7" in lines[6]

def test_syntax_error_rendering(tmp_path):
    """Integration test for premium error page on SyntaxError."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    
    # Line 1: Ok
    # Line 2: Ok
    # Line 3: Broken
    template_content = "<h1>Line 1</h1>\n<p>Line 2</p>\n{% broken %}"
    (template_dir / "error.html").write_text(template_content)
    
    app = Eden(debug=True)
    app.template_dir = str(template_dir)
    
    @app.route("/")
    async def index(request):
        return app.render("error.html")
    
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/")
    
    assert response.status_code == 500
    assert "Template Error" in response.text
    assert "Syntax Error" in response.text
    assert "Line 3" in response.text
    assert "unknown tag" in response.text and "broken" in response.text

@pytest.mark.asyncio
async def test_undefined_error_rendering(tmp_path):
    """Integration test for premium error page on UndefinedError."""
    # Note: UndefinedError requires StrictUndefined or a filter fail
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    
    template_content = "<h1>{{ missing | mandatory }}</h1>"
    (template_dir / "undef.html").write_text(template_content)
    
    app = Eden(debug=True)
    app.template_dir = str(template_dir)
    
    # Register a filter that fails
    def mandatory(value):
        from jinja2 import UndefinedError
        if not value:
            raise UndefinedError("'missing' is mandatory")
        return value
    
    app.templates.env.filters["mandatory"] = mandatory

    @app.route("/")
    async def index(request):
        return app.render("undef.html", {"missing": None})
    
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/")
    
    assert response.status_code == 500
    assert "Undefined Variable" in response.text or "Template Error" in response.text
    assert "mandatory" in response.text
