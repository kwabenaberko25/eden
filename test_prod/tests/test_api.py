"""
API tests.
"""

import pytest

@pytest.mark.asyncio
async def test_index(client):
    """Test index endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_health(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
