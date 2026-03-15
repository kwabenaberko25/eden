"""
Manual verification: Create a simple route with template syntax error
and verify the premium error page displays correctly.
"""
import tempfile
import os
from pathlib import Path
from starlette.testclient import TestClient
from eden.app import Eden

# Create a temporary directory for templates
with tempfile.TemporaryDirectory() as tmpdir:
    template_dir = Path(tmpdir) / "templates"
    template_dir.mkdir()
    
    # Create a template with a syntax error (invalid Jinja2 syntax)
    # This uses an invalid {% %} tag that will be caught by Jinja2 parser
    template_file = template_dir / "broken.html"
    template_file.write_text("""
    <html>
    <head><title>Test</title></head>
    <body>
        <h1>Test Page</h1>
        {% if %}
            <p>Incomplete condition</p>
        {% endif %}
    </body>
    </html>
    """)
    
    # Create app and register route
    app = Eden(debug=True)
    app.template_dir = str(template_dir)
    
    @app.get("/error-test")
    async def error_route(request):
        """This route will trigger a template error."""
        return app.render("broken.html")
    
    # Test the route with client that doesn't raise exceptions
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/error-test")
    
    print(f"Status Code: {response.status_code}")
    print(f"Has 'Template Error' badge: {'Template Error' in response.text}")
    print(f"Has 'Syntax Error' badge: {'Syntax Error' in response.text}")
    print(f"Has line numbers: {'<li>' in response.text or 'line' in response.text.lower()}")
    print(f"Has error message: {'Expected an expression' in response.text or 'unexpected' in response.text.lower()}")
    
    # Check for premium error page elements
    has_premium_elements = all([
        'Template Error' in response.text,
        'Syntax Error' in response.text,
        response.status_code == 500
    ])
    
    if has_premium_elements:
        print("\n✓ Premium error page is rendering correctly!")
    else:
        print("\n✗ Premium error page may not be rendering correctly")
        print(f"\nResponse preview:\n{response.text[:500]}")
