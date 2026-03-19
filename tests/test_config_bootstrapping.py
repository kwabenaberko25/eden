import os
import pytest
from eden.app import Eden
from eden.config import ConfigManager, get_config
from eden.db import Model

def test_config_population_into_state(monkeypatch):
    """Verify that environment variables are correctly populated into Eden.state."""
    # Set mock environment variables
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///test_auto.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:9999")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-123")
    monkeypatch.setenv("EDEN_ENV", "dev")
    
    # Reset config manager to force reload
    ConfigManager.instance().reset()
    
    # Initialize app without explicit config
    app = Eden()
    
    # Check if app.config has the values
    assert app.config.database_url == "sqlite+aiosqlite:///test_auto.db"
    assert app.config.redis_url == "redis://localhost:9999"
    assert app.config.secret_key == "test-secret-key-123"
    
    # Check if app attributes are synced
    assert app.secret_key == "test-secret-key-123"
    
    # Check if app.state has the values (This is what bootstrappers use)
    assert app.state.database_url == "sqlite+aiosqlite:///test_auto.db"
    assert app.state.redis_url == "redis://localhost:9999"
    assert app.state.env == "dev"

@pytest.mark.asyncio
async def test_bootstrapper_automatic_execution(monkeypatch):
    """Verify that bootstrappers automatically use config values."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///test_boot.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:9999")
    
    ConfigManager.instance().reset()
    
    # Reset Model._db to ensure fresh bootstrapping
    if hasattr(Model, "_db"):
        Model._db = None
    
    app = Eden()
    await app.build()
    
    # Check if database was bootstrapped
    assert hasattr(Model, "_db")
    assert Model._db is not None
    
    # Check if cache was bootstrapped
    assert app.cache is not None
    assert app.cache.url == "redis://localhost:9999"
