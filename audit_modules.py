import asyncio
import time


async def run_audit():
    from eden.responses import JsonResponse, HtmlResponse, RedirectResponse
    from eden.cache import InMemoryCache
    from eden.tasks import EdenBroker
    from eden.storage import LocalStorageBackend
    from eden.validators import validate_email, validate_phone, validate_url
    from pydantic import BaseModel

    print("\n--- Starting Eden Core Modules Audit ---")

    # --- TEST 1: Responses & Serialization ---
    print("\n[Test 1] Responses & Serialization...")

    # Test JSON response with Pydantic model
    class User(BaseModel):
        name: str
        email: str

    user = User(name="John", email="john@example.com")
    resp = JsonResponse(user)
    content = resp.body
    if b"John" in content:
        print("[PASS] Pydantic model serialization works.")
    else:
        print("[FAIL] Pydantic model serialization failed.")

    # Test redirect
    redir = RedirectResponse(url="/login")
    if redir.status_code in (302, 307):
        print("[PASS] Redirect response works.")
    else:
        print(f"[FAIL] Redirect status: {redir.status_code}")

    # --- TEST 2: Cache ---
    print("\n[Test 2] Cache System...")

    cache = InMemoryCache()
    await cache.set("test_key", "test_value", ttl=10)
    val = await cache.get("test_key")
    if val == "test_value":
        print("[PASS] In-memory cache set/get works.")
    else:
        print(f"[FAIL] Cache returned: {val}")

    has_key = await cache.has("test_key")
    if has_key:
        print("[PASS] Cache has() works.")
    else:
        print("[FAIL] Cache has() failed.")

    # Test expiry
    await cache.set("expire_key", "value", ttl=1)
    await asyncio.sleep(1.1)
    exp_val = await cache.get("expire_key")
    if exp_val is None:
        print("[PASS] Cache expiry works.")
    else:
        print("[FAIL] Cache did not expire.")

    # --- TEST 3: Validators ---
    print("\n[Test 3] Validators...")

    # Email
    result = validate_email("test@example.com")
    if result.ok:
        print("[PASS] Email validation (valid).")
    else:
        print(f"[FAIL] Valid email rejected: {result.error}")

    result = validate_email("invalid-email")
    if not result.ok:
        print("[PASS] Email validation (invalid).")
    else:
        print("[FAIL] Invalid email accepted.")

    # Phone
    result = validate_phone("+1234567890")
    if result.ok:
        print("[PASS] Phone validation (valid).")
    else:
        print(f"[FAIL] Valid phone rejected: {result.error}")

    # URL
    result = validate_url("https://example.com")
    if result.ok:
        print("[PASS] URL validation (valid).")
    else:
        print(f"[FAIL] Valid URL rejected: {result.error}")

    # --- TEST 4: Storage ---
    print("\n[Test 4] Storage...")

    import os
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()
    storage = LocalStorageBackend(base_path=temp_dir)

    try:
        # Test saving bytes
        path = await storage.save(b"Hello World", name="test.txt")
        if os.path.exists(os.path.join(temp_dir, path)):
            print("[PASS] Local storage save works.")
        else:
            print("[FAIL] File not saved.")

        # Test URL generation
        url = storage.url("test.txt")
        if "/test.txt" in url:
            print("[PASS] Storage URL generation works.")
        else:
            print(f"[FAIL] Unexpected URL: {url}")

        # Test delete
        await storage.delete("test.txt")
        if not os.path.exists(os.path.join(temp_dir, "test.txt")):
            print("[PASS] Storage delete works.")
        else:
            print("[FAIL] File not deleted.")
    finally:
        shutil.rmtree(temp_dir)

    # --- TEST 5: Routing (Basic) ---
    print("\n[Test 5] Routing...")

    from eden.routing import Router, Route
    from eden.requests import Request

    router = Router()

    @router.get("/test")
    async def test_route(request):
        return {"status": "ok"}

    # Check route registration
    routes = router.routes
    if any(r.path == "/test" for r in routes):
        print("[PASS] Router registration works.")
    else:
        print("[FAIL] Router registration failed.")

    # --- TEST 6: Middleware Integration ---
    print("\n[Test 6] Middleware...")

    from eden.app import Eden
    from eden.middleware import CORSMiddleware, RateLimitMiddleware

    app = Eden(title="AuditApp")

    # Add CORS
    app.add_middleware("cors", allow_origins=["*"])

    # Just verify add_middleware doesn't raise
    try:
        app.add_middleware("ratelimit")
        print("[PASS] Middleware registration works.")
    except Exception as e:
        print(f"[FAIL] Middleware registration failed: {e}")

    # --- TEST 7: Telemetry (Basic) ---
    print("\n[Test 7] Telemetry...")

    from eden.telemetry import start_telemetry, get_telemetry

    token = start_telemetry()
    data = get_telemetry()

    if data:
        print("[PASS] Telemetry context works.")
    else:
        print("[FAIL] Telemetry context failed.")

    # --- TEST 8: Context ---
    print("\n[Test 8] Context Management...")

    from eden.context import set_user, get_user, set_request, reset_request

    # We can't easily test async context without a full app, but we can test the vars
    class MockUser:
        id = 1
        name = "Test"

    token = set_user(MockUser())
    user = get_user()
    if user and user.name == "Test":
        print("[PASS] Context user management works.")
    else:
        print("[FAIL] Context user management failed.")

    print("\n--- Audit Complete ---")


asyncio.run(run_audit())
