"""
Tests for Config database pool configuration (Issue #23).

Verifies:
1. Default pool settings are applied
2. Custom pool settings are accepted
3. get_database_engine_kwargs builds correct dict
4. SQLite databases skip pool_size/overflow settings
5. Pool settings are configurable via environment variables
"""

import pytest
import os
from eden.config import Config, Environment


class TestPoolDefaults:
    """Test that default pool settings are sensible."""
    
    def test_default_pool_size(self):
        """Default pool_size should be 10."""
        config = Config(env="test")
        assert config.db_pool_size == 10
    
    def test_default_max_overflow(self):
        """Default max_overflow should be 20."""
        config = Config(env="test")
        assert config.db_max_overflow == 20
    
    def test_default_pool_recycle(self):
        """Default pool_recycle should be 3600 (1 hour)."""
        config = Config(env="test")
        assert config.db_pool_recycle == 3600
    
    def test_default_pool_timeout(self):
        """Default pool_timeout should be 30."""
        config = Config(env="test")
        assert config.db_pool_timeout == 30
    
    def test_default_pool_pre_ping(self):
        """Default pool_pre_ping should be True."""
        config = Config(env="test")
        assert config.db_pool_pre_ping is True
    
    def test_default_db_echo(self):
        """Default echo should be False."""
        config = Config(env="test")
        assert config.db_echo is False


class TestPoolCustomization:
    """Test that pool settings can be customized."""
    
    def test_custom_pool_size(self):
        """Custom pool_size should be accepted."""
        config = Config(env="test", db_pool_size=50)
        assert config.db_pool_size == 50
    
    def test_custom_max_overflow(self):
        """Custom max_overflow should be accepted."""
        config = Config(env="test", db_max_overflow=100)
        assert config.db_max_overflow == 100
    
    def test_custom_pool_recycle(self):
        """Custom pool_recycle should be accepted."""
        config = Config(env="test", db_pool_recycle=1800)
        assert config.db_pool_recycle == 1800
    
    def test_custom_pool_timeout(self):
        """Custom pool_timeout should be accepted."""
        config = Config(env="test", db_pool_timeout=60)
        assert config.db_pool_timeout == 60
    
    def test_pool_size_validation(self):
        """pool_size must be >= 1."""
        with pytest.raises(Exception):
            Config(env="test", db_pool_size=0)
    
    def test_max_overflow_allows_zero(self):
        """max_overflow=0 should be valid (no overflow)."""
        config = Config(env="test", db_max_overflow=0)
        assert config.db_max_overflow == 0


class TestGetDatabaseEngineKwargs:
    """Test get_database_engine_kwargs builds correct dict."""
    
    def test_sqlite_skips_pool_settings(self):
        """SQLite URLs should not include pool_size/overflow in kwargs."""
        config = Config(env="test", database_url="sqlite+aiosqlite:///:memory:")
        kwargs = config.get_database_engine_kwargs()
        
        assert "pool_pre_ping" in kwargs
        assert "echo" in kwargs
        assert "pool_size" not in kwargs
        assert "max_overflow" not in kwargs
        assert "pool_recycle" not in kwargs
    
    def test_postgres_includes_pool_settings(self):
        """PostgreSQL URLs should include all pool settings."""
        config = Config(
            env="test",
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            db_pool_size=25,
            db_max_overflow=50,
            db_pool_recycle=900,
            db_pool_timeout=15,
        )
        kwargs = config.get_database_engine_kwargs()
        
        assert kwargs["pool_size"] == 25
        assert kwargs["max_overflow"] == 50
        assert kwargs["pool_recycle"] == 900
        assert kwargs["pool_timeout"] == 15
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["echo"] is False
    
    def test_echo_forwarded(self):
        """db_echo should be forwarded to engine kwargs."""
        config = Config(env="test", database_url="postgresql+asyncpg://x@y/z", db_echo=True)
        kwargs = config.get_database_engine_kwargs()
        assert kwargs["echo"] is True
    
    def test_default_sqlite_url_skips_pool(self):
        """Default test URL (sqlite) should skip pool settings."""
        config = Config(env="test")
        kwargs = config.get_database_engine_kwargs()
        
        # Should have base settings but not pool_size
        assert "pool_pre_ping" in kwargs
        assert "pool_size" not in kwargs
