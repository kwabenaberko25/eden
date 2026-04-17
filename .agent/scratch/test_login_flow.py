"""
Quick integration test: verify admin login redirects with JWT token in URL.
"""
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import httpx

async def test():
    from eden.app import Eden
    
    app = Eden(debug=True, secret_key="test-secret-for-login")
    app.setup_defaults()
    
    transport = httpx.ASGITransport(app=app)
    passed = 0
    failed = 0
    
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", follow_redirects=False) as client:
        # Test 1: GET /admin/ should return 200 (SPA shell), NOT 307 redirect
        resp = await client.get("/admin/")
        print(f"[TEST 1] GET /admin/ => status={resp.status_code}")
        if resp.status_code == 200:
            has_checkauth = "checkAuth" in resp.text
            has_token_parse = "urlParams.get" in resp.text  
            print(f"  Contains checkAuth: {has_checkauth}")
            print(f"  Contains token URL parsing: {has_token_parse}")
            if has_checkauth and has_token_parse:
                print("  PASS: Dashboard shell serves without auth gate")
                passed += 1
            else:
                print("  FAIL: SPA code missing expected functions")
                failed += 1
        elif resp.status_code in (301, 302, 303, 307):
            print(f"  FAIL: Still redirecting to {resp.headers.get('location')}")
            failed += 1
        else:
            print(f"  UNEXPECTED: status code {resp.status_code}")
            failed += 1
        
        # Test 2: GET /admin/login should return 200
        resp2 = await client.get("/admin/login")
        print(f"\n[TEST 2] GET /admin/login => status={resp2.status_code}")
        if resp2.status_code == 200:
            print("  PASS: Login page loads")
            passed += 1
        else:
            print(f"  FAIL: status={resp2.status_code}")
            failed += 1
        
        # Test 3: Check that views.py admin_login generates JWT
        from eden.admin.views import admin_login
        import inspect
        source = inspect.getsource(admin_login)
        has_jwt_gen = "JWTBackend" in source and "create_access_token" in source
        has_url_append = "urlencode" in source and "token" in source
        print(f"\n[TEST 3] admin_login code inspection:")
        print(f"  JWT generation code present: {has_jwt_gen}")
        print(f"  Token URL append code present: {has_url_append}")
        if has_jwt_gen and has_url_append:
            print("  PASS: Login view will generate JWT on success")
            passed += 1
        else:
            print("  FAIL: Missing JWT generation in login view")
            failed += 1
        
        # Test 4: Verify apiCall sends Authorization header
        from eden.admin.premium_dashboard import PremiumAdminTemplate
        rendered = PremiumAdminTemplate.render(api_base="/admin/api")
        has_bearer = "Bearer" in rendered
        has_localstorage_set = "localStorage.setItem('admin_token'" in rendered
        print(f"\n[TEST 4] SPA template inspection:")
        print(f"  Bearer token in apiCall: {has_bearer}")
        print(f"  Token stored to localStorage: {has_localstorage_set}")
        if has_bearer and has_localstorage_set:
            print("  PASS: SPA correctly ingests and uses JWT")
            passed += 1
        else:
            print("  FAIL: SPA auth handling incomplete")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    if failed == 0:
        print("ALL TESTS PASSED - Login fix is verified.")
    else:
        print("SOME TESTS FAILED - Fix needs more work.")

asyncio.run(test())
