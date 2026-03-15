import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.testclient import TestClient
from starlette.applications import Starlette
from sqlalchemy import select
from eden.auth.oauth import OAuthManager
from eden.auth.models import SocialAccount
from eden.db import Database
from eden.requests import Request
from eden.app import Eden

@pytest.mark.asyncio
async def test_oauth_unlink_security_guard():
    """
    Verify that a user cannot unlink their last remaining login method.
    """
    app = Eden(secret_key="test-secret")
    # Mock Database
    mock_db = MagicMock(spec=Database)
    mock_db.execute = AsyncMock()
    # In Eden, db is in app.state._state (it's a starlette State) or just app._app.state
    # But for mounting, we just need the app to have .get/.post
    app.state.db = mock_db
    
    manager = OAuthManager()
    manager.mount(app, prefix="/auth/oauth")
    
    # Mock request with authenticated user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.is_authenticated = True
    mock_user.password_hash = None
    
    # 1. Test case: User has only ONE social account. Unlinking should fail.
    mock_sa = MagicMock(spec=SocialAccount)
    mock_sa.provider = "google"
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_sa]
    mock_db.execute.return_value = mock_result
    
    # Use TestClient for the mounted app
    client = TestClient(app)
    
    # Let's find the route handler
    unlink_handler = None
    for route in app._router.routes:
        if route.name == "oauth_unlink":
            unlink_handler = route.endpoint
            break
            
    assert unlink_handler is not None
    
    # Create a mock request
    request = MagicMock(spec=Request)
    request.user = mock_user
    request.state.db = AsyncMock() # The session (AsyncSession)
    request.state.db.execute.return_value = mock_result
    request.query_params = {}
    
    from urllib.parse import unquote
    # Call handler with only one account
    response = await unlink_handler(request, provider="google")
    assert response.status_code == 307
    location = unquote(str(response.headers.get("location")))
    assert "error=" in location
    assert "last remaining login method" in location

    # 2. Test case: User has TWO social accounts. Unlinking ONE should succeed.
    mock_sa2 = MagicMock(spec=SocialAccount)
    mock_sa2.provider = "github"
    mock_result.scalars.return_value.all.return_value = [mock_sa, mock_sa2]
    
    request.state.db.delete = AsyncMock()
    request.state.db.commit = AsyncMock()
    
    response = await unlink_handler(request, provider="google")
    assert response.status_code == 307
    assert "message=" in unquote(str(response.headers.get("location")))
    # We use await db.execute(delete_stmt) now
    assert request.state.db.execute.call_count >= 2 # Once for select, once for delete
    request.state.db.commit.assert_called_once()
