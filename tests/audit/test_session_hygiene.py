import pytest
from eden.app import Eden
from starlette.middleware import Middleware

@pytest.mark.asyncio
async def test_session_middleware_not_present_without_secret(monkeypatch):
    """Verify that sessions/csrf are NOT added if secret_key is missing."""
    # EDEN_ENV=test is required because the security guard raises RuntimeError
    # when no secret_key is configured outside of test mode.
    monkeypatch.setenv("EDEN_ENV", "test")

    class MockConfig:
        secret_key = None
        title = "Eden"
        version = "1.0.0"
        debug = False
        browser_reload = False

    app = Eden(secret_key=None, config=MockConfig())
    await app.build()
    
    # Check default middleware
    middleware_types = [cls.__name__ for cls, _, _ in app._middleware_stack]
    
    assert "SecurityHeadersMiddleware" in middleware_types
    assert "SessionMiddleware" not in middleware_types
    assert "CSRFMiddleware" not in middleware_types
    assert "CORSMiddleware" in middleware_types

@pytest.mark.asyncio
async def test_session_middleware_present_with_secret(monkeypatch):
    """Verify that sessions/csrf ARE added if secret_key is present."""
    monkeypatch.setenv("EDEN_ENV", "prod")
    monkeypatch.setenv("SECRET_KEY", "some-prod-secret")
    app = Eden(secret_key="some-secret")
    await app.build()
    
    middleware_types = [cls.__name__ for cls, _, _ in app._middleware_stack]
    
    assert "SessionMiddleware" in middleware_types
    assert "CSRFMiddleware" in middleware_types

@pytest.mark.asyncio
async def test_cors_default_allow_none():
    """Verify that CORS defaults to restricted mode (allow_origins=None)."""
    app = Eden()
    await app.build()
    
    cors_mw_tuple = next(m for m in app._middleware_stack if m[0].__name__ == "CORSMiddleware")
    # CORSMiddleware in our stack is (cls, kwargs, priority)
    assert cors_mw_tuple[1]["allow_origins"] == []
