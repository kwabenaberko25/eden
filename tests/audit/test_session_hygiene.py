import pytest
from eden.app import Eden
from starlette.middleware import Middleware

@pytest.mark.asyncio
async def test_session_middleware_not_present_without_secret():
    """Verify that sessions/csrf are NOT added if secret_key is missing."""
    class MockConfig:
        secret_key = None
        title = "Eden"
        version = "0.1.0"
        debug = False

    app = Eden(secret_key=None, config=MockConfig())
    
    # Check default middleware
    middleware_types = [m[0].__name__ for m in app._middleware_stack]
    
    assert "SecurityHeadersMiddleware" in middleware_types
    assert "SessionMiddleware" not in middleware_types
    assert "CSRFMiddleware" not in middleware_types
    assert "CORSMiddleware" in middleware_types

@pytest.mark.asyncio
async def test_session_middleware_present_with_secret():
    """Verify that sessions/csrf ARE added if secret_key is present."""
    app = Eden(secret_key="some-secret")
    
    middleware_types = [m[0].__name__ for m in app._middleware_stack]
    
    assert "SessionMiddleware" in middleware_types
    assert "CSRFMiddleware" in middleware_types

@pytest.mark.asyncio
async def test_cors_default_allow_none():
    """Verify that CORS defaults to restricted mode (allow_origins=None)."""
    app = Eden()
    
    cors_mw_tuple = next(m for m in app._middleware_stack if m[0].__name__ == "CORSMiddleware")
    # CORSMiddleware in our stack is (cls, kwargs, priority)
    assert cors_mw_tuple[1]["allow_origins"] is None
