"""
Eden Auth System - Implementation Guide & Examples

This module demonstrates all 5 critical auth system components now properly
integrated and production-ready.

STATUS: ✅ ALL ISSUES FIXED
1. ✅ First-Class User Model - BaseUser properly defined and exported
2. ✅ Password Hashing - Argon2id configured with secure defaults
3. ✅ RBAC Declarative+Enforcement - Hierarchical roles with query filtering
4. ✅ OAuth Framework - Google & GitHub with token exchange
5. ✅ Permission Middleware - Automatic request user binding
"""

# ──────────────────────────────────────────────────────────────────────────
# LAYER 1: FIRST-CLASS USER MODEL
# ──────────────────────────────────────────────────────────────────────────

from eden.auth import User, BaseUser, SocialAccount, hash_password, check_password

# Example 1a: Using the framework User model
async def create_user_example():
    """Create a new user with encrypted password."""
    user = User(
        email="alice@example.com",
        full_name="Alice Smith",
    )
    user.set_password("SecurePassword123!")  # Uses Argon2id internally
    # Save to database
    return user

# Example 1b: Custom user with BaseUser mixin
from eden.db import Model
from sqlalchemy.orm import Mapped, mapped_column

class CustomUser(Model, BaseUser):
    """Custom user model for specific business needs."""
    __tablename__ = "custom_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(nullable=True)  # Extra field
    
# ──────────────────────────────────────────────────────────────────────────
# LAYER 2: PASSWORD HASHING INFRASTRUCTURE
# ──────────────────────────────────────────────────────────────────────────

async def password_hashing_example():
    """Secure password handling with Argon2id."""
    password = "MySecurePassword123!"
    
    # Hash for storage
    hashed = hash_password(password)
    
    # Verify during login
    is_correct = check_password(password, hashed)
    assert is_correct
    
    # Verify wrong password fails
    is_wrong = check_password("WrongPassword", hashed)
    assert not is_wrong

# ──────────────────────────────────────────────────────────────────────────
# LAYER 3: QUERY-LEVEL RBAC ENFORCEMENT
# ──────────────────────────────────────────────────────────────────────────

from eden.auth import default_rbac, apply_rbac_filter, user_has_permission

# Setup roles and permissions
def setup_rbac():
    """Configure hierarchical roles."""
    # Define permissions
    default_rbac.add_permission("editor", "view_posts")
    default_rbac.add_permission("editor", "create_posts")
    default_rbac.add_permission("editor", "edit_own_posts")
    
    default_rbac.add_permission("admin", "view_posts")
    default_rbac.add_permission("admin", "create_posts")
    default_rbac.add_permission("admin", "edit_all_posts")
    default_rbac.add_permission("admin", "delete_posts")
    
    # Define hierarchy: admin > editor
    default_rbac.add_role("admin", parents=["editor"])

# Example: Query-level filtering
async def get_user_posts_example(user, db):
    """Get posts user can view (query-level RBAC)."""
    from eden.db import Post  # Example model
    
    posts_query = Post.select()
    
    # Automatically filters: if not admin, only own posts
    posts_query = apply_rbac_filter(
        user, 
        posts_query, 
        "view_all_posts",
        field_name="author_id"
    )
    
    return await posts_query.all()

# Example: Permission checking
def check_delete_permission_example(user):
    """Check if user can delete posts."""
    if user_has_permission(user, "delete_posts"):
        return True  # User can delete
    return False

# ──────────────────────────────────────────────────────────────────────────
# LAYER 4: OAUTH PROVIDER FRAMEWORK
# ──────────────────────────────────────────────────────────────────────────

from eden.auth import OAuthManager

def setup_oauth(app):
    """Configure OAuth providers (Google, GitHub)."""
    oauth = OAuthManager()
    
    # Setup Google OAuth
    oauth.register_google(
        client_id="YOUR_GOOGLE_CLIENT_ID",
        client_secret="YOUR_GOOGLE_CLIENT_SECRET",
        scopes=["openid", "email", "profile"],
    )
    
    # Setup GitHub OAuth
    oauth.register_github(
        client_id="YOUR_GITHUB_CLIENT_ID",
        client_secret="YOUR_GITHUB_CLIENT_SECRET",
        scopes=["read:user", "user:email"],
    )
    
    # Mount routes: /auth/oauth/{provider}/login and /callback
    oauth.mount(app, prefix="/auth/oauth")
    
    return oauth

# OAuth login flow (automatic via mounted routes):
# 1. GET /auth/oauth/google/login → Redirect to Google
# 2. User authorizes
# 3. GET /auth/oauth/google/callback → Exchange code for token
# 4. User linked/created, redirect to dashboard

# ──────────────────────────────────────────────────────────────────────────
# LAYER 5: PERMISSION MIDDLEWARE & AUTO-BINDING
# ──────────────────────────────────────────────────────────────────────────

from eden.auth import (
    AuthenticationMiddleware,
    AuthBackend,
    require_permission,
    require_role,
)

# Example: Setting up middleware
def setup_middleware(app):
    """Configure authentication middleware."""
    # Define auth backends (database, session, token, etc.)
    backends = [
        # SessionBackend(),    # Check session cookies
        # BearerTokenBackend(),  # Check JWT Bearer tokens
    ]
    
    app.add_middleware(AuthenticationMiddleware, backends=backends)

# Example: Route handlers with permission checks
async def admin_dashboard_example(request):
    """Admin dashboard - requires permission."""
    # request.user is automatically set by middleware
    if not request.user:
        return {"error": "Not authenticated"}
    
    if "admin" not in request.user.roles:
        return {"error": "Admin access required"}
    
    return {"message": f"Welcome {request.user.email}"}

# Example: Using decorators for cleaner permission checks
@require_permission("delete_users")
async def delete_user_example(request):
    """Delete a user - requires delete_users permission."""
    # Middleware automatically checked permission via decorator
    return {"deleted": True}

@require_role("admin")
async def admin_settings_example(request):
    """Admin settings - requires admin role."""
    return {"settings": {...}}

# ──────────────────────────────────────────────────────────────────────────
# COMPLETE SETUP EXAMPLE
# ──────────────────────────────────────────────────────────────────────────

async def setup_complete_auth_system(app):
    """Full auth system setup."""
    
    # 1. Configure RBAC
    setup_rbac()
    
    # 2. Configure middleware for auto user-binding
    setup_middleware(app)
    
    # 3. Configure OAuth
    oauth = setup_oauth(app)
    
    return {
        "user_model": User,
        "rbac": default_rbac,
        "oauth": oauth,
        "password_hashing": "Argon2id",
    }

# ──────────────────────────────────────────────────────────────────────────
# ALL EXPORT & USAGE SUMMARY
# ──────────────────────────────────────────────────────────────────────────

"""
LAYER 1 - User Model:
    from eden.auth import User, BaseUser, SocialAccount
    
LAYER 2 - Password Hashing:
    from eden.auth import hash_password, check_password
    
LAYER 3 - Query-Level RBAC:
    from eden.auth import (
        default_rbac,
        apply_rbac_filter,
        user_has_permission,
        user_has_role,
    )
    
LAYER 4 - OAuth:
    from eden.auth import OAuthManager
    oauth = OAuthManager()
    oauth.register_google(...)
    oauth.mount(app)
    
LAYER 5 - Middleware & Decorators:
    from eden.auth import (
        AuthenticationMiddleware,
        require_permission,
        require_role,
    )
    app.add_middleware(AuthenticationMiddleware, backends=[...])

ALL ISSUES FIXED:
✅ User Model - Properly defined and exported (can subclass/import)
✅ Password Hashing - Argon2id with default hasher configured
✅ RBAC - Declarative roles with query-level enforcement (apply_rbac_filter)
✅ OAuth - Google/GitHub providers with automatic token handling
✅ Middleware - Automatic user binding to requests (request.user)
"""
