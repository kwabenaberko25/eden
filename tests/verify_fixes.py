import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch
from eden import Eden, Model, f, LocalStorageBackend, storage
from eden.auth.providers import JWTProvider
from eden.middleware import ratelimit
from eden.payments import StripeProvider
from sqlalchemy import Column, String

# Define a model for testing Search
class SearchPost(Model):
    __tablename__ = "search_posts"
    title: str = f(max_length=255)
    content: str = f()

@pytest.mark.asyncio
async def test_model_search_fix():
    """Verify that Model.search() builds the correct Q objects."""
    app = Eden()
    mock_session = AsyncMock()
    
    with patch.object(SearchPost, "filter") as mock_filter:
        mock_filter.return_value.all = AsyncMock(return_value=[SearchPost(title="Hello")])
        
        # Test search
        results = await SearchPost.search("hello", session=mock_session)
        
        assert len(results) == 1
        assert results[0].title == "Hello"
        mock_filter.assert_called_once()
        
        # Verify it passed a Q object
        args, kwargs = mock_filter.call_args
        from eden.db import Q
        assert isinstance(args[0], Q)

@pytest.mark.asyncio
async def test_ratelimit_decorator_fix():
    """Verify that @ratelimit returns a callable and doesn't crash."""
    
    @ratelimit(max_requests=5, window_seconds=60)
    async def my_view(request):
        return {"ok": True}
        
    # Check if it's the wrapper (functools.wraps preserves name)
    assert my_view.__name__ == "my_view"
    
    # Test execution (requires request)
    mock_request = AsyncMock()
    mock_request.app.cache = AsyncMock()
    mock_request.app.cache.get = AsyncMock(return_value=0)
    mock_request.client.host = "127.0.0.1"
    
    # We need to simulate the request context
    with patch("eden.context.get_request", return_value=mock_request):
        resp = await my_view(mock_request)
        assert resp == {"ok": True}

@pytest.mark.asyncio
async def test_jwt_provider_aliases():
    """Verify encode/decode aliases work."""
    provider = JWTProvider(secret="secret")
    payload = {"user_id": 1}
    
    token = provider.encode(payload)
    assert isinstance(token, str)
    
    decoded = provider.decode(token)
    assert decoded["user_id"] == 1

@pytest.mark.asyncio
async def test_billing_manager_integration():
    """Verify user.billing property and manager."""
    from eden.auth.models import User
    
    user = User(email="test@example.com")
    
    # Mock request context for BillingManager's _get_provider
    mock_request = AsyncMock()
    mock_request.app.payments = StripeProvider(api_key="sk_test")
    
    with patch("eden.context.request", mock_request):
        manager = user.billing
        assert manager.instance == user
        
        # Test checkout session creation (mock provider)
        with patch.object(mock_request.app.payments, "create_customer", AsyncMock(return_value="cus_123")):
            with patch.object(mock_request.app.payments, "create_checkout_session", AsyncMock(return_value="http://stripe.com/out")):
                with patch.object(user, "save", AsyncMock()):
                    url = await manager.create_checkout_session(plan_id="price_123")
                    assert url == "http://stripe.com/out"
                    assert user.stripe_customer_id == "cus_123"

def test_storage_backend_registration():
    """Verify SupabaseStorageBackend exists and can be imported."""
    from eden import SupabaseStorageBackend
    assert SupabaseStorageBackend is not None
    
    backend = SupabaseStorageBackend(url="http://site.com", key="key")
    assert backend.bucket == "uploads"
