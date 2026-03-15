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

# ── OAuth ────────────────────────────────────────────────────────────────

from eden.auth.oauth import OAuthManager, OAuthProvider, GoogleProvider, GitHubProvider

# ── RBAC & Authorization ────────────────────────────────────────────────

from eden.auth.rbac import default_rbac, EdenRBAC
from eden.auth.decorators import (
    login_required,
    roles_required,
    permissions_required,
    require_permission,
    is_authorized,
    bind_user_principal,
    require_role,
    require_any_permission,
    require_any_role,
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
# ── New Complete Auth System Functions ───────────────────────────────────
# These provide high-level auth convenience functions
# Note: authenticate, create_user, check_permission are unique to complete.py
# require_permission and login_required already imported from decorators above

from eden.auth.complete import (
    authenticate,
    create_user,
    check_permission,
    staff_required,
    permission_required as complete_permission_required,
    RoleManager,
)
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
    
    # OAuth
    "OAuthManager",
    "OAuthProvider",
    "GoogleProvider",
    "GitHubProvider",
    
    # RBAC & Authorization
    "default_rbac",
    "EdenRBAC",
    "login_required",
    "roles_required",
    "permissions_required",
    "require_permission",
    "require_role",
    "require_any_permission",
    "require_any_role",
    "is_authorized",
    "bind_user_principal",
    
    # Query-Level RBAC
    "apply_rbac_filter",
    "user_has_permission",
    "user_has_role",
    "user_has_any_permission",
    "user_has_any_role",
    
    # High-level convenience functions (from complete module)
    "authenticate",
    "create_user",
    "check_permission",
    "staff_required",
    "complete_permission_required",
    "RoleManager",
    
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
