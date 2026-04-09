from __future__ import annotations
"""
Eden Authentication System — Complete Implementation (Legacy Wrapper)

This module is now a legacy wrapper that exports components from the unified
auth system. New code should import directly from eden.auth.

Unified locations:
- BaseUser -> eden.auth.base
- Password Hashing -> eden.auth.hashers
- RBAC -> eden.auth.access
- Actions -> eden.auth.actions
- Decorators -> eden.auth.decorators
"""


import logging
import warnings
from typing import Any, List, Optional

from eden.auth.base import BaseUser
from eden.auth.hashers import hash_password, check_password as verify_password
from eden.auth.actions import authenticate, login, logout, create_user
from eden.auth.access import (
    RoleHierarchy as RoleManager,
    check_permission,
    require_permission,
)
from eden.auth.decorators import (
    login_required,
    staff_required,
    require_permission as permission_required,
)
from eden.auth.oauth import OAuthProvider

logger = logging.getLogger(__name__)

# Emit deprecation warning on import
warnings.warn(
    "eden.auth.complete is deprecated. Import from eden.auth instead.",
    DeprecationWarning,
    stacklevel=2
)

# Legacy constants
DEFAULT_PASSWORD_HASHER = None # No longer explicitly used as a class in the new system

__all__ = [
    # Hashing
    "hash_password",
    "verify_password",
    "DEFAULT_PASSWORD_HASHER",
    # Models
    "BaseUser",
    # Auth
    "authenticate",
    "login",
    "logout",
    "create_user",
    # RBAC
    "RoleManager",
    "check_permission",
    "require_permission",
    # Decorators
    "login_required",
    "staff_required",
    "permission_required",
    # OAuth
    "OAuthProvider",
]
