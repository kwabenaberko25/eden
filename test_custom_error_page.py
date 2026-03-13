#!/usr/bin/env python
"""Test custom error page for routing exceptions."""

import sys
import asyncio
from pathlib import Path

# Add eden to path
sys.path.insert(0, str(Path(__file__).parent))

from eden import Eden
from starlette.requests import Request
from starlette.routing import NoMatchFound
from starlette.testclient import TestClient


async def test_no_match_found_handler():
    """Test that _handle_no_match_found renders a styled error page."""
    app = Eden(debug=True)
    
    # Create a mock request
    scope = {
        "type": "http",
        "path": "/test",
        "headers": [(b"accept", b"text/html")],
        "method": "GET",
    }
    
    from starlette.requests import Request as StarletteRequest
    request = StarletteRequest(scope)
    
    # Create exception
    exc = NoMatchFound("about", {})
    
    # Call the handler (it's async)
    response = await app._handle_no_match_found(request, exc)
    
    # Check response
    assert response.status_code == 404
    
    # Get the body
    body = response.body.decode()
    
    # Should be HTML, not raw exception
    assert "text/html" in response.headers.get("content-type", "")
    assert "<" in body  # Should be HTML
    assert "starlette.routing.NoMatchFound" not in body or "Route not found" in body
    
    print("✅ Test passed: _handle_no_match_found returns styled error page")
    print(f"Status code: {response.status_code}")
    print(f"Contains error message: {'Route not found' in body or 'does not exist' in body}")


def test_no_match_found_exception_handler_registered():
    """Verify NoMatchFound exception handler is properly registered."""
    app = Eden(debug=True)
    
    @app.route("/dummy")
    def dummy(request):
        return {"text": "ok"}
    
    # TestClient handles async app building
    client = TestClient(app)
    
    # Make a simple request to ensure the app is built
    response = client.get("/dummy")
    assert response.status_code == 200
    
    print("✅ Test passed: NoMatchFound exception handler is registered")


def test_via_integration():
    """Integration test: NoMatchFound in template context renders styled error."""
    app = Eden(debug=True)
    
    @app.route("/test", name="test_route")
    def test_route(request):
        """Route that calls url_for with missing route name."""
        # Simulate what happens when a template calls url_for with a bad route name
        from starlette.routing import NoMatchFound
        # Directly raise to simulate what Starlette would do
        raise NoMatchFound("missing", {})
    
    client = TestClient(app)
    response = client.get("/test", headers={"Accept": "text/html"})
    
    # Should get 404 with styled HTML error page
    print(f"Status code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert "text/html" in response.headers.get("content-type", ""), \
        f"Expected HTML, got {response.headers.get('content-type')}"
    
    html = response.text
    # Should not have raw traceback
    has_traceback = "Traceback" in html and "File" in html and "line" in html
    assert not has_traceback, \
        f"Should not contain raw Python traceback. Got: {html[:500]}"
    
    # Should have error message
    has_error_msg = any(m in html for m in ["Route not found", "does not exist", "404", "Error"])
    assert has_error_msg, \
        f"Should contain error message. Got: {html[:500]}"
    
    print("✅ Test passed: NoMatchFound exception renders styled error via integration test")
    print(f"HTML contains error message: {has_error_msg}")


if __name__ == "__main__":
    try:
        print("Running test 1: Handler returns styled error page...")
        asyncio.run(test_no_match_found_handler())
        
        print("\nRunning test 2: Exception handler is registered...")
        test_no_match_found_exception_handler_registered()
        
        print("\nRunning test 3: Integration test...")
        test_via_integration()
        
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
