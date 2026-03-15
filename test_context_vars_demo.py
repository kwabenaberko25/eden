#!/usr/bin/env python
"""
Demo script showing the enhanced template error page with context variables.
"""
import tempfile
from pathlib import Path
from starlette.testclient import TestClient
from eden.app import Eden

def test_context_variables_display():
    """Demonstrate that context variables are now displayed in error page."""
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        template_dir = Path(tmp_dir) / "templates"
        template_dir.mkdir()
        
        # Create a template with an INTENTIONAL SYNTAX ERROR
        template_content = "<h1>Test</h1>\n<p>Line 2</p>\n{% broken_tag %}"
        (template_dir / "error.html").write_text(template_content)
        
        # Create an Eden app
        app = Eden(debug=True)
        app.template_dir = str(template_dir)
        
        # Route that passes context variables
        @app.route("/test")
        async def test_route(request):
            return app.render("error.html", {
                "user": {"name": "Alice", "email": "alice@example.com"},
                "items": ["item1", "item2", "item3"],
                "count": 42,
                "active": True,
                "data": None,
                "tags": ["python", "eden", "framework"],
                "config": {"debug": True, "timeout": 30}
            })
        
        # Test the error page
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code != 500:
            print(f"ERROR: Expected status 500, got {response.status_code}")
            return False
        
        html = response.text
        
        # Check for the new "Template Variables" section heading
        has_vars_section = "Template Variables" in html
        print(f"{'✅' if has_vars_section else '❌'} Template Variables section: {has_vars_section}")
        
        # Check for individual variables being displayed  
        variables_to_check = ["user", "items", "count", "active", "tags", "config"]
        all_found = True
        for var in variables_to_check:
            found = var in html
            print(f"{'✅' if found else '❌'} Variable '{var}': {found}")
            all_found = all_found and found
        
        # Check for key sections
        has_error = "Template Error" in html or "Syntax Error" in html
        has_code = "Code Explorer" in html
        has_env = "Environment Snapshot" in html
        
        print(f"{'✅' if has_error else '❌'} Error section: {has_error}")
        print(f"{'✅' if has_code else '❌'} Code Explorer: {has_code}")
        print(f"{'✅' if has_env else '❌'} Environment Snapshot: {has_env}")
        
        success = has_vars_section and all_found and has_error and has_code and has_env
        
        if success:
            print(f"\n✅ All checks passed! Context variables are properly displayed.")
            var_count = html.count("<tr>")
            print(f"   Found {var_count} table rows for variables")
        
        return success

if __name__ == "__main__":
    success = test_context_variables_display()
    exit(0 if success else 1)
