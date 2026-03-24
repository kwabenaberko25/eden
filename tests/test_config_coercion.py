import pytest
import os
from eden.config import Config, ConfigManager

def test_config_debug_coercion():
    """
    Verifies that 'debug' is correctly coerced to bool from various env strings.
    """
    os.environ["EDEN_DEBUG"] = "true"
    config = Config(debug=os.environ["EDEN_DEBUG"])
    assert config.debug is True
    
    os.environ["EDEN_DEBUG"] = "false"
    config = Config(debug=os.environ["EDEN_DEBUG"])
    assert config.debug is False
    
    os.environ["EDEN_DEBUG"] = "1"
    config = Config(debug=os.environ["EDEN_DEBUG"])
    assert config.debug is True

def test_config_manager_load_coercion():
    """
    Verifies ConfigManager.load() handles EDEN_DEBUG correctly.
    """
    manager = ConfigManager()
    
    os.environ["EDEN_DEBUG"] = "true"
    config = manager.load()
    assert config.debug is True
    
    os.environ["EDEN_DEBUG"] = "false"
    config = manager.load()
    assert config.debug is False
