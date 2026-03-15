#!/usr/bin/env python
"""Test with actual template file."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eden import Eden
from starlette.testclient import TestClient


def test_real_template_error():
    """Test with a real template file that has an error."""
    app = Eden(debug=True)
    
    # Create a test template with an error
    template_dir = Path("templates")
    template_dir.mkdir(exist_ok=True)
    
    # Create a template with invalid Jinja2 syntax
    error_template = template_dir / "syntax_error_test.html"
    error_template.write_text("""
<h1>Test Page</h1>
<p>This will cause a syntax error: {% if user %} hello {% %}</p>
""")
    
    @app.route("/test_template")
    def test_route(request):
        from eden.templating import EdenTemplates
        templates = EdenTemplates(directory="templates")
        return templates.TemplateResponse(
            "syntax_error_test.html",
            {"request": request}
        )
    
    client = TestClient(app, headers={"Accept": "text/html"})
    response = client.get("/test_template")
    
    print(f"Status: {response.status_code}")
    html = response.text
    
    if "expected" in html.lower() or "syntax" in html.lower() or "error" in html.lower():
        print("✅ Found error message about syntax issue")
    else:
        print("⚠️  Could not find error message about the undefined variable")
    
    # Check if the full error message is there
    if response.status_code == 500:
        print("✅ Got 500 status code as expected")
        
        # Save for inspection
        with open("c:\\ideas\\eden\\real_error_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("✅ Saved real error page to real_error_page.html")
        
        # Look for the banner
        if 'bg-red-500/10' in html:
            print("✅ Error banner styling found")
        else:
            print("❌ Error banner styling NOT found")
    
    # Clean up
    error_template.unlink()


if __name__ == "__main__":
    test_real_template_error()
