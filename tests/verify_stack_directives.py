import sys
import os
from pathlib import Path

# Ensure eden is in path
sys.path.insert(0, os.getcwd())

from starlette.requests import Request
from eden.templating import EdenTemplates
from unittest.mock import MagicMock

def test_stack_ordering(tmp_path):
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    
    # 1. Create base.html with a stack in head
    (template_dir / "base.html").write_text("""
<html>
<head>
    @stack('styles')
</head>
<body>
    @yield('content')
</body>
</html>
""", encoding="utf-8")
    
    # 2. Create dashboard.html with both prepend and push
    (template_dir / "dashboard.html").write_text("""
@extends("base.html")
@prepend("styles") {
    <style>.prepend { color: red; }</style>
}
@push("styles") {
    <style>.push { color: blue; }</style>
}
@section("content") {
    <h1>Main Content</h1>
}
""", encoding="utf-8")
    
    templates = EdenTemplates(directory=str(template_dir))
    
    # Mock request with state and session initialized
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "state": {},
        "session": {}
    }
    request = Request(scope)
    
    from eden.context import set_request
    set_request(request)
    
    # Render Dashboard
    response = templates.TemplateResponse(request, "dashboard.html", {})
    
    # DEBUG: Show compiled template to verify lifting
    print("\n--- COMPILED JINJA2 (PRE-PROCESSED) ---")
    source, filename, _ = templates.env.loader.get_source(templates.env, "dashboard.html")
    # Get the extension instance to call preprocess
    ext = [e for e in templates.env.extensions.values() if e.__class__.__name__ == 'EdenDirectivesExtension'][0]
    print(ext.preprocess(source, "dashboard.html", filename))
    print("---------------------------------------\n")

    content = response.body.decode()
    
    print("\n--- FINAL RENDERED OUTPUT ---")
    print(content)
    print("-----------------------------\n")
    
    # Assertions
    assert ".prepend { color: red; }" in content, "Prepended content missing"
    assert ".push { color: blue; }" in content, "Pushed content missing"
    assert "[[EDEN_STACK" not in content, "Stack placeholder not replaced"
    
    # Verify Order: prepend should be before push
    prepend_pos = content.find(".prepend")
    push_pos = content.find(".push")
    assert prepend_pos != -1 and push_pos != -1
    assert prepend_pos < push_pos, "@prepend should appear before @push in the final rendered stack"
    
    # Verify positions relative to head
    head_pos = content.find("<html>")
    assert prepend_pos > head_pos, "Styles should be rendered after <html>"
    
    print("[SUCCESS] @stack, @push, and @prepend are working and ordered correctly!")

if __name__ == "__main__":
    import tempfile
    import shutil
    tmpdir = Path(tempfile.mkdtemp())
    try:
        test_stack_ordering(tmpdir)
    finally:
        shutil.rmtree(tmpdir)
