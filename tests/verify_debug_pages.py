
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from eden.exceptions.debug import render_premium_debug_page, render_error_response
from eden.admin_error_handler import AdminErrorHandler
from starlette.requests import Request
from starlette.datastructures import Headers

def verify_debug_page():
    print("--- Verifying Premium Debug Page ---")
    try:
        # Mocking enough of a request and frame info
        # In a real scenario, this would be more complex, but we just want to see if it renders
        html_res = render_premium_debug_page(
            title="NameError",
            message="name 'undefined_var' is not defined",
            filename="app/routes.py",
            lineno=42,
            column=10,
            code_frame="<div class='code-line error-line'>undefined_var += 1</div>",
            context_vars={"user_id": 123, "session": {"token": "abc"}},
            metadata={"Request": {"method": "GET", "url": "/test"}},
            traceback_html="<div class='traceback'>Mock Traceback</div>",
            suggestions=["Check if 'undefined_var' is defined in the current scope.", "Ensure the variable name is spelled correctly."],
            status_code=500
        )
        html = html_res.body.decode()
        
        # Check for external CDNs
        cdns = ["cdnjs.cloudflare.com", "fonts.googleapis.com", "unpkg.com", "cdn.tailwindcss.com"]
        for cdn in cdns:
            if cdn in html:
                print(f"[FAIL] Found external CDN link: {cdn}")
            else:
                print(f"[OK] No {cdn} found.")
        
        # Check for embedded CSS
        if "<style>" in html and ":root" in html:
            print("[OK] Found embedded CSS variables.")
        else:
            print("[FAIL] Embedded CSS not found.")
            
        # Write to file for manual inspection
        with open("artifacts/debug_page_preview.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Preview saved to artifacts/debug_page_preview.html")
        
    except Exception as e:
        print(f"[CRITICAL] Failed to render debug page: {e}")

def verify_admin_fallback():
    print("\n--- Verifying Admin Luxury Fallback ---")
    try:
        handler = AdminErrorHandler()
        # Mock request
        scope = {
            "type": "http",
            "path": "/admin/users",
            "headers": [(b"accept", b"text/html")],
            "method": "GET"
        }
        request = Request(scope=scope)
        
        # Manually trigger the luxury fallback by passing details
        details = {
            "title": "Forbidden",
            "message": "You do not have permission to delete this user.",
            "error_id": "ERR-999"
        }
        html_res = handler._render_luxury_error_page(details, 403)
        html = html_res.body.decode()
        
        # Check for premium elements
        if "ERROR_ID" in html and "ERR-999" in html:
            print("[OK] Found Error ID in fallback.")
        if "Back to Dashboard" in html:
            print("[OK] Found 'Back to Dashboard' button.")
            
        # Write to file for manual inspection
        with open("artifacts/admin_error_preview.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Preview saved to artifacts/admin_error_preview.html")
            
    except Exception as e:
        print(f"[CRITICAL] Failed to render admin fallback: {e}")

if __name__ == "__main__":
    # Ensure artifacts directory exists in workspace for script access (not just the tool's artifacts dir)
    os.makedirs("artifacts", exist_ok=True)
    verify_debug_page()
    verify_admin_fallback()
