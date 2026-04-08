"""
Pytest Configuration and Shared Fixtures

This file enables the Eden testing infrastructure for the entire test suite.
"""

import os
import pytest

# Ensure all tests run in test mode so the security guard in Eden.__init__
# allows construction without a secret_key.
os.environ["EDEN_ENV"] = "test"
from eden.testing import (
    EdenTestClient as TestClient,
    test_app,
    db,
    db_transaction,
    client,
    test_user,
    admin_user,
    user_factory,
    tenant_factory,
    mock_stripe,
    mock_email,
    mock_s3,
    UserFactory,
    TenantFactory
)

# Export fixtures to be discovered by pytest
__all__ = [
    "TestClient",
    "test_app",
    "db",
    "db_transaction",
    "client",
    "test_user",
    "admin_user",
    "user_factory",
    "tenant_factory",
    "mock_stripe",
    "mock_email",
    "mock_s3",
    "UserFactory",
    "TenantFactory"
]
