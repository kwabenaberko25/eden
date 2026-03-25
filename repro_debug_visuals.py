
import os
import sys
from starlette.testclient import TestClient
from eden.app import Eden
from jinja2 import Environment, DictLoader

def test_debug_page_visuals():
    # Setup app in debug mode
    app = Eden(debug=True)
    
    # Create a template with a syntax error
    # We use a DictLoader for simplicity in the repro
    templates = {
        "syntax_error.html": "<h1>Hello</h1>\n{% broken %}\n<p>World</p>",
        "undefined_error.html": "<h1>{{ mandatory_check(user) }}</h1>"
    }
    
    # We need to inject our templates into the app
    # app.templates is usually an EdenTemplates instance
    from eden.templating import EdenTemplates
    # Create a dummy templates dir if needed, but we'll use DictLoader
    app._templates = EdenTemplates(directory=".") 
    app._templates.env.loader = DictLoader(templates)
    
    def mandatory_check(val):
        from jinja2 import UndefinedError
        if val is None:
            raise UndefinedError("User is required but was None")
        return val
        
    app._templates.env.globals["mandatory_check"] = mandatory_check

    @app.route("/syntax")
    async def syntax(request):
        return app.render("syntax_error.html")

    @app.route("/undefined")
    async def undefined(request):
        return app.render("undefined_error.html", {"user": None})

    @app.exception_handler(Exception)
    async def handle_error(request, exc):
        print(f"DEBUG: Exception type: {type(exc)}")
        print(f"DEBUG: lineno: {getattr(exc, 'lineno', 'N/A')}")
        print(f"DEBUG: column: {getattr(exc, 'column', 'N/A')}")
        print(f"DEBUG: message: {getattr(exc, 'message', 'N/A')}")
        # Call the actual handler
        from eden.error_middleware import ErrorHandlerMiddleware
        mw = ErrorHandlerMiddleware(app, app)
        return await mw._render_enhanced_template_error(request, exc)

    client = TestClient(app, raise_server_exceptions=False)
    
    print("\n--- Testing Syntax Error ---")
    response = client.get("/syntax")
    print(f"Status: {response.status_code}")
    # print(response.text[:500]) # Print first 500 chars
    with open("syntax_error_output.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    
    if "Syntax Error" in response.text and 'class="column-marker"' in response.text:
        print("✅ Syntax Error page contains the column marker div.")
    else:
        print("❌ Syntax Error page missing the render-time column marker.")
        if "column-marker" in response.text:
            print("   (Note: Found it in CSS, but not in the line content)")

    print("\n--- Testing Undefined Error ---")
    response = client.get("/undefined")
    print(f"Status: {response.status_code}")
    with open("undefined_error_output.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    
    if "Undefined Variable" in response.text:
        print("✅ Undefined Variable page rendered.")
    else:
        print("❌ Undefined Variable page missing title.")

if __name__ == "__main__":
    test_debug_page_visuals()
