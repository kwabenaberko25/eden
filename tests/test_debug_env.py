
import os
import pytest
from pathlib import Path
from eden.config import get_config, ConfigManager

@pytest.mark.asyncio
async def test_print_db_url(test_app, monkeypatch):
    print(f"\nDEBUG: CWD={Path.cwd()}")
    print(f"DEBUG: .env.test exists={Path('.env.test').exists()}")
    print(f"DEBUG: OS DATABASE_URL={os.getenv('DATABASE_URL')}")
    
    # Reload manually to see if it makes a difference inside the test
    monkeypatch.setenv("EDEN_ENV", "test")
    ConfigManager.instance().reset()
    config = ConfigManager.instance().load()
    
    print(f"DEBUG: Reloaded Config env={config.env}")
    print(f"DEBUG: Reloaded Config database_url={config.database_url}")
    print(f"DEBUG: Reloaded Config get_database_url()={config.get_database_url()}")
