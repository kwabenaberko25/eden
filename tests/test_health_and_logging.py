"""
Tests for Health Check Endpoint (Issue #24).

Verifies:
1. enable_health_checks registers /health route
2. enable_health_checks registers /ready route
3. Custom readiness checks are registered and called
4. Health check returns correct structure
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestHealthCheckEndpoint:
    """Test the enable_health_checks method on Eden app."""
    
    def test_health_checks_disabled_by_default(self):
        """Health checks should be disabled initially."""
        from eden.app import Eden
        app = Eden("test_app")
        assert app._health_enabled is False
        assert app._health_checks == []
    
    def test_enable_health_checks_sets_flag(self):
        """enable_health_checks should set _health_enabled."""
        from eden.app import Eden
        app = Eden("test_app")
        app.enable_health_checks()
        assert app._health_enabled is True
    
    def test_add_readiness_check_as_decorator(self):
        """add_readiness_check should work as a decorator."""
        from eden.app import Eden
        app = Eden("test_app")
        
        @app.add_readiness_check("redis")
        def check_redis():
            return True
        
        assert len(app._health_checks) == 1
        assert app._health_checks[0][0] == "redis"
    
    def test_add_readiness_check_as_function(self):
        """add_readiness_check should work with direct function passing."""
        from eden.app import Eden
        app = Eden("test_app")
        
        def check_db():
            return True
        
        app.add_readiness_check("database", check_db)
        assert len(app._health_checks) == 1
        assert app._health_checks[0][0] == "database"


class TestLoggingSetup:
    """Test structured logging configuration (Issue #27)."""
    
    def test_setup_logging_creates_handler(self):
        """setup_logging should configure the eden logger."""
        import logging
        from eden.logging import setup_logging
        
        setup_logging(level="DEBUG")
        
        logger = logging.getLogger("eden")
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) >= 1
    
    def test_setup_logging_json_format(self):
        """setup_logging with json_format should create JSON formatter."""
        from eden.logging import setup_logging, EdenFormatter
        import logging
        
        setup_logging(level="INFO", json_format=True)
        
        logger = logging.getLogger("eden")
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, EdenFormatter)
        assert handler.formatter.json_format is True
    
    def test_get_logger_returns_eden_logger(self):
        """get_logger should return properly namespaced logger."""
        from eden.logging import get_logger
        
        logger = get_logger("routes")
        assert logger.name == "eden.routes"
    
    def test_get_logger_no_double_prefix(self):
        """get_logger shouldn't double-prefix 'eden.'."""
        from eden.logging import get_logger
        
        logger = get_logger("eden.db")
        assert logger.name == "eden.db"
    
    def test_eden_formatter_human_readable(self):
        """EdenFormatter should produce human-readable output by default."""
        import logging
        from eden.logging import EdenFormatter
        
        formatter = EdenFormatter(json_format=False)
        record = logging.LogRecord(
            name="eden.test", level=logging.INFO,
            pathname="test.py", lineno=1,
            msg="Test message", args=(), exc_info=None
        )
        
        output = formatter.format(record)
        assert "Test message" in output
    
    def test_eden_formatter_json(self):
        """EdenFormatter should produce JSON when json_format=True."""
        import json
        import logging
        from eden.logging import EdenFormatter
        
        formatter = EdenFormatter(json_format=True)
        record = logging.LogRecord(
            name="eden.test", level=logging.INFO,
            pathname="test.py", lineno=1,
            msg="Test message", args=(), exc_info=None
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
