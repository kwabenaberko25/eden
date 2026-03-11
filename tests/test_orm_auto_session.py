import pytest
from unittest.mock import MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from eden.orm import Model, Database
from eden.context import set_request
from eden.requests import Request

class MockModel(Model):
    __tablename__ = "mock_session_models"

@pytest.mark.asyncio
async def test_session_fallback_to_request_state():
    """Verify that Model._get_session prefers the session in request.state.db"""
    # 1. Setup bound DB (dummy URL)
    db = Database("sqlite+aiosqlite:///:memory:")
    Model._bind_db(db)
    
    # 2. Mock a session
    mock_session = MagicMock(spec=AsyncSession)
    
    # 3. Create a mock request with the session in state.db
    scope = {"type": "http", "method": "GET", "path": "/"}
    request = Request(scope)
    request.state.db = mock_session
    
    # 4. Use the request context
    token = set_request(request)
    try:
        # 5. Verify Model._get_session yields the mock_session
        async with MockModel._get_session() as session:
            assert session is mock_session
    finally:
        from eden.context import reset_request
        reset_request(token)

@pytest.mark.asyncio
async def test_session_fallback_to_request_state_alias():
    """Verify that Model._get_session also checks request.state.db_session"""
    db = Database("sqlite+aiosqlite:///:memory:")
    Model._bind_db(db)
    
    mock_session = MagicMock(spec=AsyncSession)
    request = Request({"type": "http", "method": "GET", "path": "/"})
    request.state.db_session = mock_session
    
    token = set_request(request)
    try:
        async with MockModel._get_session() as session:
            assert session is mock_session
    finally:
        from eden.context import reset_request
        reset_request(token)

@pytest.mark.asyncio
async def test_session_fallback_no_request():
    """Verify that Model._get_session falls back to bound DB if no request context"""
    db = Database("sqlite+aiosqlite:///:memory:")
    Model._bind_db(db)
    
    # Ensure tables exist for our dummy model
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)

    async with MockModel._get_session() as session:
        assert isinstance(session, AsyncSession)
        assert session.bind is db.engine
