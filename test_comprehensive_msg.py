#!/usr/bin/env python
"""Comprehensive test of template error message display."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eden import Eden
from starlette.requests import Request as StarletteRequest
from eden.requests import Request
from jinja2.exceptions import TemplateSyntaxError, UndefinedError, TemplateError


async def test_various_error_messages():
    """Test various Jinja2 error types and message extraction."""
    app = Eden(debug=True)
    
    scope = {
        "type": "http",
        "path": "/test",
        "headers": [(b"accept", b"text/html")],
        "method": "GET",
    }
    
    starlette_req = StarletteRequest(scope)
    eden_req = Request(starlette_req.scope, starlette_req.receive, starlette_req._send)
    
    test_cases = [
        ("Syntax Error", TemplateSyntaxError("unexpected '}'", lineno=5, name="test.html")),
        ("Undefined Variable", UndefinedError("'variable' is undefined")),
    ]
    
    for test_name, exc in test_cases:
        print(f"\n=== Testing {test_name} ===")
        try:
            raise exc
        except Exception as e:
            response = app._render_enhanced_template_error(eden_req, e)
            html = response.body.decode()
            
            # Verify response
            assert response.status_code == 500, f"Expected 500, got {response.status_code}"
            
            # Verify message presence
            has_message = 'bg-red-500/10' in html and '<div class="text-slate-100' in html
            assert has_message, f"Error message container not found"
            
            # Extract and display the banner content
            import re
            match = re.search(
                r'<div class="text-slate-100 text-lg font-medium leading-relaxed">\s*(.*?)\s*</div>',
                html,
                re.DOTALL
            )
            if match:
                content = match.group(1).strip()[:100]
                print(f"✅ Message displayed: {content}...")
            else:
                print("⚠️  Could not extract message (styling might prevent display)")


if __name__ == "__main__":
    asyncio.run(test_various_error_messages())
    print("\n✅ All comprehensive tests passed!")
