import asyncio
import httpx
from eden.app import Eden
import re

async def test():
    app = Eden(debug=True, secret_key="test-secret")
    
    @app.route("/login", methods=["GET", "POST"])
    async def login(request):
        from starlette.responses import HTMLResponse
        if request.method == "POST":
            form = await request.form()
            return HTMLResponse(f"Success! token: {form.get('csrf_token')}")
        else:
            from eden.middleware import get_csrf_token
            token = get_csrf_token(request)
            return HTMLResponse(f'<form method="post"><input type="hidden" name="csrf_token" value="{token}"><input type="submit"></form>')
            
    app.setup_defaults()
    
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/admin/login")
        print(f"GET /admin/login cookies: {client.cookies}")
        csrf_token = None
        for k, v in client.cookies.items():
            if "eden_session" in k:
                try:
                    import base64, json
                    part = v.split(".")[0]
                    decoded = base64.b64decode(part + "=" * (-len(part) % 4)).decode()
                    sess_data = json.loads(decoded)
                except Exception:
                    pass
        
        # We need the CSRF token!
        import re
        match = re.search(r'name="csrf_token" value="(.*?)"', response.text)
        if match:
            csrf_token = match.group(1)
            print("Found CSRF token:", csrf_token)

            response2 = await client.post(
                "/admin/login", 
                data={"email": "test@example.com", "password": "password", "csrf_token": csrf_token or ""},
            )
            print("POST response status:", response2.status_code)
            print("POST response text:", response2.text)
        else:
            print("CSRF token not found in HTML")
            
asyncio.run(test())
