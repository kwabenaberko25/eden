#!/usr/bin/env python
"""Test that template error messages are properly displayed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eden import Eden
from starlette.testclient import TestClient
from jinja2.exceptions import UndefinedError, TemplateSyntaxError


def test_template_error_message_displayed():
    """Test that error messages are properly shown, not truncated."""
    app = Eden(debug=True)
    
    @app.route("/test_undefined")
    def test_undefined(request):
        """Route that triggers an UndefinedError."""
        from eden.templating import EdenTemplates
        templates = EdenTemplates(directory="templates")
        # This will raise UndefinedError for missing 'missing_var'
        return templates.TemplateResponse(
            "test_template.html",
            {"request": request, "missing_var": None},
            status_code=200,
        )
    
    app.route("/test_syntax_error")(lambda request: None)
    
    client = TestClient(app)
    
    # Manually raise an error to test the handler
    async def test_handler():
        from starlette.requests import Request as StarletteRequest
        from eden.requests import Request
        
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"accept", b"text/html")],
            "method": "GET",
        }
        
        starlette_req = StarletteRequest(scope)
        eden_req = Request(starlette_req.scope, starlette_req.receive, starlette_req._send)
        
        # Create a template error with a meaningful message
        try:
            raise TemplateSyntaxError("unexpected '}'", lineno=5, name="test.html")
        except TemplateSyntaxError as e:
            response = app._render_enhanced_template_error(eden_req, e)
            html = response.body.decode()
            
            # Check that the message is present and not empty
            assert "unexpected '\\}'" in html or "unexpected" in html, \
                f"Error message should be displayed. Got: {html[500:1500]}"
            
            print("✅ Test passed: Error message is properly displayed")
            print(f"Message found in response: {'unexpected' in html}")
            return True
    
    import asyncio
    result = asyncio.run(test_handler())
    assert result


def test_undefined_variable_error():
    """Test that UndefinedError messages are shown."""
    import asyncio
    
    async def test():
        from starlette.requests import Request as StarletteRequest
        from eden.requests import Request
        from jinja2.exceptions import UndefinedError
        
        app = Eden(debug=True)
        
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"accept", b"text/html")],
            "method": "GET",
        }
        
        starlette_req = StarletteRequest(scope)
        eden_req = Request(starlette_req.scope, starlette_req.receive, starlette_req._send)
        
        try:
            # UndefinedError just takes the message
            raise UndefinedError("'user_name' is undefined")
        except UndefinedError as e:
            response = app._render_enhanced_template_error(eden_req, e)
            html = response.body.decode()
            
            # Check for the error message
            assert "user_name" in html or "undefined" in html.lower(), \
                f"Undefined variable message should be shown. Got: {html[500:1500]}"
            
            print("✅ Test passed: UndefinedError message is properly displayed")
            print(f"Contains 'undefined': {'undefined' in html.lower()}")
            return True
    
    result = asyncio.run(test())
    assert result


if __name__ == "__main__":
    try:
        print("Test 1: Template error message display...")
        test_template_error_message_displayed()
        
        print("\nTest 2: Undefined variable error message...")
        test_undefined_variable_error()
        
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
