import pytest
import os
from eden.app import Eden, AppStatus
from eden.config import create_config

def test_app_fails_without_secret_key_in_dev():
    """Verify that Eden() raises RuntimeError if secret_key is missing in dev."""
    from eden.config import ConfigManager
    # Reset singleton to ensure it re-reads environment
    ConfigManager.instance().reset()
    os.environ["EDEN_ENV"] = "dev"
    
    with pytest.raises(RuntimeError) as excinfo:
        Eden(secret_key=None)
    
    assert "SECRET_KEY environment variable" in str(excinfo.value)

def test_app_status_lifecycle():
    """Verify AppStatus transitions."""
    app = Eden(secret_key="test-secret")
    assert app.status == AppStatus.STARTING
    
    # Simulate lifespan to test transitions
    # Note: Using mock or manual trigger since full ASGI lifespan needs a runner
    pass

@pytest.mark.asyncio
async def test_app_status_running():
    """Verify status is RUNNING after startup."""
    app = Eden(secret_key="test-secret")
    
    # Trigger lifespan startup manually or via TestClient
    from starlette.testclient import TestClient
    with TestClient(app):
        assert app.status == AppStatus.RUNNING
    
    assert app.status == AppStatus.STOPPED
