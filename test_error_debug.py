#!/usr/bin/env python
"""Debug test to see what's happening with error message rendering."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eden import Eden
from starlette.requests import Request as StarletteRequest
from eden.requests import Request
from jinja2.exceptions import TemplateSyntaxError


async def test():
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
        raise TemplateSyntaxError("This is a test error message that should display", lineno=5, name="test.html")
    except TemplateSyntaxError as e:
        print(f"Exception message: {str(e)}")
        response = app._render_enhanced_template_error(eden_req, e)
        html = response.body.decode()
        
        # Look for the error message
        print(f"\n=== Searching for error content ===")
        
        if "This is a test error message" in html:
            print("✅ FOUND: Full error message is present!")
        elif "test error message" in html:
            print("✅ FOUND: Partial error message is present!")
        else:
            print("❌ NOT FOUND: Error message is missing!")
        
        # Check for the banner section
        if 'bg-red-500/10' in html:
            print("✅ FOUND: Error banner section exists")
        else:
            print("❌ NOT FOUND: Error banner section")
        
        # Extract the banner content
        import re
        banner_match = re.search(r'<div class="text-slate-100 text-lg font-medium leading-relaxed">\s*(.*?)\s*</div>', html, re.DOTALL)
        if banner_match:
            banner_content = banner_match.group(1).strip()
            print(f"\nBanner content: '{banner_content}'")
            print(f"Banner content length: {len(banner_content)}")
        else:
            print("\n❌ Could not extract banner content with regex")
        
        # Save the HTML for manual inspection
        with open("c:\\ideas\\eden\\error_page_debug.html", "w") as f:
            f.write(html)
        print(f"\n✅ Saved full HTML to error_page_debug.html")
        
        # Print a snippet around the banner
        if 'bg-red-500/10' in html:
            idx = html.find('bg-red-500/10')
            snippet = html[max(0, idx-200):min(len(html), idx+500)]
            print(f"\n=== HTML snippet around error banner ===")
            print(snippet)


if __name__ == "__main__":
    asyncio.run(test())
