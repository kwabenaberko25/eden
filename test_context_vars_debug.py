#!/usr/bin/env python
"""
Demo script showing the enhanced template error page with context variables.
Saves the HTML output for inspection.
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
        
        # Save HTML to file for inspection (with UTF-8 encoding)
        output_file = Path("error_page_output.html")
        output_file.write_text(html, encoding='utf-8')
        print(f"\n✅ Error page HTML saved to: {output_file}")
        
        # Check for key sections
        has_template_vars_section = "Template Variables" in html
        has_error = "Template Error" in html or "Syntax Error" in html
        has_code = "Code Explorer" in html
        has_env = "Environment Snapshot" in html
        has_table = "<table" in html
        
        print(f"\n{'✅' if has_error else '❌'} Error badge section")
        print(f"{'✅' if has_code else '❌'} Code Explorer section")
        print(f"{'✅' if has_template_vars_section else '❌'} Template Variables section (NEW)")
        print(f"{'✅' if has_table else '❌'} Variables table HTML")
        print(f"{'✅' if has_env else '❌'} Environment Snapshot section")
        
        # Count elements
        tr_count = html.count("<tr>")
        print(f"\nHTML contains {tr_count} table rows")
        
        if tr_count > 0:
            print("✅ Variables are being displayed in table format!")
            return True
        else:
            print("❌ No variables table found")
            return False

if __name__ == "__main__":
    success = test_context_variables_display()
    exit(0 if success else 1)
