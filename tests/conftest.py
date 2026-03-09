"""
Eden — Test configuration and shared fixtures.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from eden import Eden, Depends, Router, Request, Database


@pytest.fixture
def app() -> Eden:
    """Create a fresh Eden app for testing."""
    return Eden(title="Test App", debug=True)


@pytest.fixture
async def client(app: Eden) -> AsyncClient:
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.connect(create_tables=True)
    yield database
    await database.disconnect()
