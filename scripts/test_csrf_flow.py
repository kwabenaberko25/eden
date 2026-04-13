import asyncio
import httpx
import secrets
import re
from eden.app import Eden
from eden.responses import HtmlResponse
from eden.middleware import get_csrf_token

async def test_csrf_flow():
    # Initialize app with session and CSRF enabled
    app = Eden(debug=True, secret_key="test-secret-key-123")
    
    @app.route("/form", methods=["GET", "POST"])
    async def sample_form(request):
        if request.method == "POST":
            # CSRF Middleware should have validated the token before getting here
            return HtmlResponse("<h1>POST SUCCESS</h1>")
        
        # GET: Render form with CSRF token
        token = get_csrf_token(request)
        return HtmlResponse(f"""
            <form method="POST" action="/form">
                <input type="hidden" name="csrf_token" value="{token}">
                <button type="submit">Submit</button>
            </form>
        """)

    app.setup_defaults()
    
    # Use ASGITransport for in-process testing
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\n[INFO] Starting CSRF Flow Test...")
        
        # 1. GET request to fetch form and initiate session
        print("[STEP 1] GET /form")
        res_get = await client.get("/form")
        assert res_get.status_code == 200
        assert "eden_session" in client.cookies
        print(f"[OK] Session cookie set: {client.cookies['eden_session'][:20]}...")
        
        # Extract CSRF token from HTML
        match = re.search(r'name="csrf_token" value="(.*?)"', res_get.text)
        assert match, "CSRF token not found in HTML"
        token = match.group(1)
        print(f"[OK] Found CSRF token: {token[:10]}...")
        
        # 2. POST request WITH valid token
        print("[STEP 2] POST /form (Valid Token)")
        res_post_valid = await client.post("/form", data={"csrf_token": token})
        if res_post_valid.status_code == 200 and "POST SUCCESS" in res_post_valid.text:
            print("[OK] Valid token POST correctly accepted")
        else:
            print(f"[FAIL] Valid token POST rejected: {res_post_valid.status_code}")
            print(res_post_valid.text)
            raise AssertionError("Valid CSRF token was rejected")
            
        # 3. POST request WITH INVALID token
        print("[STEP 3] POST /form (Invalid Token)")
        res_post_invalid = await client.post("/form", data={"csrf_token": "wrong-token"})
        if res_post_invalid.status_code == 403:
            print("[OK] Invalid token POST correctly rejected with 403")
        else:
            print(f"[FAIL] Invalid token POST accepted: {res_post_invalid.status_code}")
            raise AssertionError("Invalid CSRF token was NOT rejected")

        # 4. POST request WITHOUT token
        print("[STEP 4] POST /form (Missing Token)")
        res_post_missing = await client.post("/form", data={})
        if res_post_missing.status_code == 403:
            print("[OK] Missing token POST correctly rejected with 403")
        else:
            print(f"[FAIL] Missing token POST accepted: {res_post_missing.status_code}")
            raise AssertionError("Missing CSRF token was NOT rejected")

    print("\n[SUCCESS] All CSRF flow tests passed!")

if __name__ == "__main__":
    try:
        asyncio.run(test_csrf_flow())
    except Exception as e:
        print(f"\n[CRITICAL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
