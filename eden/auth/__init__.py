"""
Eden Authentication Module

Provides authentication, authorization, user management, password hashing, OAuth, and RBAC.

Core Components:
- User Model: BaseUser and User classes with first-class framework integration
- Password Hashing: Argon2id-based secure password hashing (hash_password, check_password)
- OAuth: Google and GitHub OAuth provider framework with token exchange
- RBAC: Role-Based Access Control with hierarchical roles and permissions
- Middleware: AuthenticationMiddleware for request-scoped user binding
- Decorators: Permission/role checking for route handlers

Quick Start:
    from eden.auth import User, hash_password, check_password, BaseUser
    from eden.auth import OAuthManager, AuthenticationMiddleware
    from eden.auth import require_permission, require_role, default_rbac

Example - Creating a user:
    user = User(email="alice@example.com")
    user.set_password("secure_password_123")
    
Example - OAuth setup:
    oauth = OAuthManager()
    oauth.register_google(client_id="...", client_secret="...")
    oauth.mount(app)
    
Example - Permission checks:
    @app.get("/admin")
    @require_permission("view_admin_panel")
    async def admin(request):
        return {"message": "Admin area"}
"""

# ── User Models ──────────────────────────────────────────────────────────

from eden.auth.models import User, BaseUser, SocialAccount
from eden.auth.utils import get_user_model, set_user_model

# ── Password Hashing ─────────────────────────────────────────────────────

from eden.auth.hashers import (
    hash_password,
    check_password,
    check_password as verify_password,
    needs_rehash,
    hasher,
    Argon2Hasher,
    BcryptHasher,
    HasherRegistry,
    registry as hasher_registry,
)

# ── Password Reset ───────────────────────────────────────────────────────

from eden.auth.password_reset import (
    PasswordResetToken,
    PasswordResetService,
    PasswordResetEmail,
)
from eden.auth.password_reset_routes import router as password_reset_router

# ── Built-in Auth Routes ─────────────────────────────────────────────────

from eden.auth.routes import auth_router

# ── Session Tracking ─────────────────────────────────────────────────────

from eden.auth.session_tracker import SessionTracker, InMemorySessionTrackerStore

# ── OAuth ────────────────────────────────────────────────────────────────

from eden.auth.oauth import OAuthManager, OAuthProvider, GoogleProvider, GitHubProvider

# ── RBAC & Authorization ────────────────────────────────────────────────

from eden.auth.rbac import (
    PermissionRegistry,
    default_registry,
    PermissionPolicy,
)
from eden.auth.access import (
    default_rbac, 
    RoleHierarchy, 
    RoleHierarchy as EdenRBAC,  # Legacy alias
    check_permission, 
    require_permission as access_require_permission,
    RoleManager,
)

from eden.auth.base import get_current_user
from eden.auth.decorators import (
    login_required,
    roles_required,
    permissions_required,
    require_permission,
    can_read,
    can_write,
    is_authorized,
    bind_user_principal,
    require_role,
    require_any_permission,
    require_any_role,
    staff_required,
    require_permission as permission_required, # Alias
    require_role as role_required, # Alias
    view_decorator,
)

# ── Middleware ───────────────────────────────────────────────────────────

from eden.auth.middleware import AuthenticationMiddleware, AuthorizationMiddleware

# ── Backend Interface ────────────────────────────────────────────────────

from eden.auth.base import AuthBackend, get_current_user, current_user

# ── Authentication Backends ──────────────────────────────────────────────

from eden.auth.backends.jwt import JWTBackend
from eden.auth.backends.session import SessionBackend
from eden.auth.backends.api_key import APIKeyBackend

# ── API Key Model ────────────────────────────────────────────────────────

from eden.auth.api_key_model import APIKey

# ── Providers (Convenience Aliases) ──────────────────────────────────────

from eden.auth.providers import JWTProvider

# ── Query-Level RBAC ─────────────────────────────────────────────────────

from eden.auth.query_filtering import (
    apply_rbac_filter,
    user_has_permission,
    user_has_role,
    user_has_any_permission,
    user_has_any_role,
)
# ── Unified Auth System Functions ────────────────────────────────────────
# These provide high-level auth convenience functions migrated from complete.py

from eden.auth.actions import (
    authenticate,
    login,
    logout,
    logout_all,
    create_user,
)

from eden.auth.audit import auth_audit

from eden.auth.access import (
    RoleManager,
)

async def require_auth(request):
    from eden.exceptions import Unauthorized
    user = await get_current_user(request)
    if user is None:
        raise Unauthorized(detail="Authentication required.")
    return user

__all__ = [
    # Models & Utils
    "User",
    "BaseUser",
    "SocialAccount",
    "APIKey",
    "get_user_model",
    "set_user_model",
    
    # Password hashing
    "hash_password",
    "check_password",
    "verify_password",
    "needs_rehash",
    "hasher",
    "hasher_registry",
    "Argon2Hasher",
    "BcryptHasher",
    "HasherRegistry",
    
    # Password reset
    "PasswordResetToken",
    "PasswordResetService",
    "PasswordResetEmail",
    "password_reset_router",
    
    # Built-in Auth Routes
    "auth_router",
    
    # Session Tracking
    "SessionTracker",
    "InMemorySessionTrackerStore",
    
    # OAuth
    "OAuthManager",
    "OAuthProvider",
    "GoogleProvider",
    "GitHubProvider",
    
    # RBAC & Authorization
    "default_rbac",
    "RoleHierarchy",
    "EdenRBAC",
    "PermissionRegistry",
    "default_registry",
    "PermissionPolicy",
    "login_required",
    "roles_required",
    "permissions_required",
    "require_permission",
    "require_role",
    "can_read",
    "can_write",
    "require_any_permission",
    "require_any_role",
    "is_authorized",
    "bind_user_principal",
    "staff_required",
    "permission_required",
    "role_required",
    "view_decorator",
    
    # Query-Level RBAC
    "apply_rbac_filter",
    "user_has_permission",
    "user_has_role",
    "user_has_any_permission",
    "user_has_any_role",
    
    # High-level convenience functions
    "authenticate",
    "login",
    "logout",
    "logout_all",
    "create_user",
    
    # Audit logging
    "auth_audit",
    
    "check_permission",
    "RoleManager",
    "require_auth",
    
    # Middleware
    "AuthenticationMiddleware",
    "AuthorizationMiddleware",
    
    # Backends
    "AuthBackend",
    "get_current_user",
    "current_user",
    "JWTBackend",
    "SessionBackend",
    "APIKeyBackend",
    
    # Providers
    "JWTProvider",
]
