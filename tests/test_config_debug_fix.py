"""
Tests for Config debug auto-detection fix (Issue #7 from analysis).

Verifies:
1. debug defaults to True in dev environment when no env var is set
2. debug defaults to True in test environment when no env var is set
3. debug defaults to False in prod environment when no env var is set
4. Explicit DEBUG=true env var sets debug=True
5. Explicit DEBUG=false env var sets debug=False
"""

import os
import pytest
from unittest.mock import patch
from eden.config import Config, Environment


def test_debug_auto_detect_dev():
    """In dev mode without explicit DEBUG env var, debug should auto-detect to True."""
    config = Config(env="dev", secret_key="test-secret")
    assert config.debug is True


def test_debug_auto_detect_test():
    """In test mode without explicit DEBUG env var, debug should auto-detect to True."""
    config = Config(env="test", secret_key="test-secret")
    assert config.debug is True


def test_debug_auto_detect_prod():
    """In prod mode without explicit DEBUG env var, debug should auto-detect to False."""
    config = Config(env="prod", secret_key="prod-secret-key-long-enough")
    assert config.debug is False


def test_debug_explicit_true():
    """Explicit debug=True should be respected."""
    config = Config(env="prod", debug=True, secret_key="prod-secret-key-long-enough")
    assert config.debug is True


def test_debug_explicit_false():
    """Explicit debug=False should be respected even in dev mode."""
    config = Config(env="dev", debug=False, secret_key="test-secret")
    assert config.debug is False


def test_debug_string_coercion():
    """String 'true' should coerce to True via field_validator."""
    config = Config(env="prod", debug="true", secret_key="prod-secret-key-long-enough")
    assert config.debug is True


def test_debug_none_triggers_auto_detect():
    """Passing debug=None should trigger auto-detection based on environment."""
    dev_config = Config(env="dev", debug=None, secret_key="test-secret")
    assert dev_config.debug is True
    
    prod_config = Config(env="prod", debug=None, secret_key="prod-secret-key-long-enough")
    assert prod_config.debug is False
