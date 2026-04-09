"""
Authenticated admin routes with authentication and authorization.

Integrates AdminAuthManager with dashboard routes.

Usage:
    from eden.admin.auth_routes import get_protected_admin_routes
    
    auth = AdminAuthManager(secret_key="your-secret-key")
    # Register default users
    auth.register_user("admin", "password", AdminRole.ADMIN)
    
    app = FastAPI()
    app.include_router(get_protected_admin_routes(auth))
"""

from typing import Optional
from eden import Router as APIRouter, HttpException as HTTPException, Depends, App as FastAPI
from eden.requests import Request
from eden.responses import HtmlResponse as HTMLResponse
from pydantic import BaseModel

from .auth import AdminAuthManager, AdminRole, AdminUser
from .dashboard_template import AdminDashboardTemplate
from .login_template import LoginPageTemplate
from .flags_panel import FlagsAdminPanel
from eden.flags import get_flag_manager


# =====================================================================
# Request/Response Models
# =====================================================================

class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    token_type: str = "Bearer"
    user: dict


class UserResponse(BaseModel):
    """User info response."""
    username: str
    role: str
    created_at: str
    last_login: Optional[str] = None
    is_active: bool


class SessionStats(BaseModel):
    """Session statistics."""
    total_users: int
    active_sessions: int
    total_sessions: int
    users_by_role: dict


class PasswordStrengthRequest(BaseModel):
    """Request to check password strength."""
    password: str


class PasswordStrengthResponse(BaseModel):
    """Password strength validation response."""
    is_valid: bool
    errors: list = []
    strength_score: int  # 0-100


# =====================================================================
# Router Factory
# =====================================================================

def get_protected_admin_routes(
    auth: AdminAuthManager,
    prefix: str = "/admin",
    flags_panel: Optional[FlagsAdminPanel] = None,
) -> APIRouter:
    """
    Create router with authenticated admin dashboard routes.
    
    Args:
        auth: AdminAuthManager instance
        prefix: URL prefix for admin routes
        flags_panel: Optional FlagsAdminPanel instance
        
    Returns:
        FastAPI Router with all protected endpoints
    """
    router = APIRouter(prefix=prefix, tags=["admin"])
    panel = flags_panel or FlagsAdminPanel(manager=get_flag_manager())
    
    # =====================================================================
    # Authentication Routes
    # =====================================================================
    
    @router.get("/login")
    async def login_page(request: Request):
        """Serve login page."""
        return LoginPageTemplate.render(login_url=f"{prefix}/api/login")
    
    @router.post("/api/login")
    async def login(request: Request):
        """
        Login endpoint.
        
        Returns JWT token in response.
        Client should store in localStorage and send as:
        Authorization: Bearer <token>
        """
        try:
            data = await request.json()
            req = LoginRequest(**data)
            token = auth.login(req.username, req.password)
            user = auth.get_user(req.username)
            
            return LoginResponse(
                access_token=token,
                user={
                    "username": user.username,
                    "role": user.role.value,
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/api/logout")
    async def logout(request: Request):
        """
        Logout endpoint.
        
        Invalidates the token.
        """
        authorization = request.headers.get("authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise ValueError()
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        auth.logout(token)
        return {"status": "logged_out"}
    
    # =====================================================================
    # Dashboard Routes
    # =====================================================================
    
    @router.get("/")
    async def dashboard(current_user: AdminUser = Depends(auth.verify)):
        """Serve authenticated dashboard."""
        return AdminDashboardTemplate.render(
            api_base=f"{prefix}/api/flags",
            app_name="Eden Framework"
        )
    
    @router.get("/dashboard")
    async def dashboard_explicit(current_user: AdminUser = Depends(auth.verify)):
        """Alias for dashboard route."""
        return AdminDashboardTemplate.render(
            api_base=f"{prefix}/api/flags",
            app_name="Eden Framework"
        )
    
    # =====================================================================
    # Flag Management Routes (Protected)
    # =====================================================================
    
    @router.get("/api/flags/")
    async def get_flags_stats(current_user: AdminUser = Depends(auth.verify)):
        """Get flag statistics (requires authentication)."""
        return await panel.get_stats()
    
    @router.get("/api/flags/flags")
    async def list_flags(current_user: AdminUser = Depends(auth.verify)):
        """List all flags (read-only role allowed)."""
        return await panel.list_flags()
    
    @router.post("/api/flags/flags")
    async def create_flag(
        request: Request,
        current_user: AdminUser = Depends(auth.require_role(AdminRole.ADMIN, AdminRole.EDITOR))
    ):
        """Create new flag (requires ADMIN or EDITOR role)."""
        data = await request.json()
        return await panel.create_flag(data)
    
    @router.get("/api/flags/flags/{flag_id}")
    async def get_flag(flag_id: str, current_user: AdminUser = Depends(auth.verify)):
        """Get flag details (read-only role allowed)."""
        return await panel.get_flag(flag_id)
    
    @router.patch("/api/flags/flags/{flag_id}")
    async def update_flag(
        flag_id: str,
        request: Request,
        current_user: AdminUser = Depends(auth.require_role(AdminRole.ADMIN, AdminRole.EDITOR))
    ):
        """Update flag (requires ADMIN or EDITOR role)."""
        data = await request.json()
        return await panel.update_flag(flag_id, data)
    
    @router.delete("/api/flags/flags/{flag_id}")
    async def delete_flag(
        flag_id: str,
        current_user: AdminUser = Depends(auth.require_role(AdminRole.ADMIN))
    ):
        """Delete flag (requires ADMIN role only)."""
        return await panel.delete_flag(flag_id)
    
    @router.get("/api/flags/flags/{flag_id}/metrics")
    async def get_flag_metrics(flag_id: str, current_user: AdminUser = Depends(auth.verify)):
        """Get flag metrics (read-only role allowed)."""
        return await panel.get_metrics(flag_id)
    
    @router.post("/api/flags/flags/{flag_id}/enable")
    async def enable_flag(
        flag_id: str,
        current_user: AdminUser = Depends(auth.require_role(AdminRole.ADMIN, AdminRole.EDITOR))
    ):
        """Enable flag (requires ADMIN or EDITOR role)."""
        return await panel.enable_flag(flag_id)
    
    @router.post("/api/flags/flags/{flag_id}/disable")
    async def disable_flag(
        flag_id: str,
        current_user: AdminUser = Depends(auth.require_role(AdminRole.ADMIN, AdminRole.EDITOR))
    ):
        """Disable flag (requires ADMIN or EDITOR role)."""
        return await panel.disable_flag(flag_id)
    
    # =====================================================================
    # User Management Routes (Admin Only)
    # =====================================================================
    
    @router.get("/api/users")
    async def list_users(
        current_user: AdminUser = Depends(auth.require_role(AdminRole.ADMIN))
    ):
        """List all users (ADMIN only)."""
        users = auth.list_users()
        return [
            {
                "username": u.username,
                "role": u.role.value,
                "created_at": u.created_at.isoformat(),
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "is_active": u.is_active,
            }
            for u in users
        ]
    
    @router.get("/api/users/{username}")
    async def get_user(
        username: str,
        current_user: AdminUser = Depends(auth.verify)
    ):
        """Get user info (self or ADMIN)."""
        # Users can only view their own info, or ADMIN can view anyone
        if current_user.username != username and current_user.role != AdminRole.ADMIN:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        user = auth.get_user(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            username=user.username,
            role=user.role.value,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
            is_active=user.is_active,
        )
    
    @router.post("/api/users")
    async def create_user(
        request: Request,
        current_user: AdminUser = Depends(auth.require_role(AdminRole.ADMIN))
    ):
        """Create new user (ADMIN only)."""
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        role = data.get("role", "viewer")
        
        try:
            admin_role = AdminRole[role.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {', '.join([r.value for r in AdminRole])}"
            )
        
        try:
            user = auth.register_user(username, password, admin_role)
            return {
                "username": user.username,
                "role": user.role.value,
                "created_at": user.created_at.isoformat(),
            }
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
    
    @router.patch("/api/users/{username}/role")
    async def update_user_role(
        username: str,
        request: Request,
        current_user: AdminUser = Depends(auth.require_role(AdminRole.ADMIN))
    ):
        """Update user role (ADMIN only)."""
        data = await request.json()
        role = data.get("role")
        
        try:
            admin_role = AdminRole[role.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {', '.join([r.value for r in AdminRole])}"
            )
        
        try:
            user = auth.update_user_role(username, admin_role)
            return {
                "username": user.username,
                "role": user.role.value,
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    @router.delete("/api/users/{username}")
    async def delete_user(
        username: str,
        current_user: AdminUser = Depends(auth.require_role(AdminRole.ADMIN))
    ):
        """Delete user (ADMIN only)."""
        if username == current_user.username:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
        auth.delete_user(username)
        return {"status": "deleted", "username": username}
    
    @router.post("/api/users/{username}/password")
    async def change_password(
        username: str,
        request: Request,
        current_user: AdminUser = Depends(auth.verify)
    ):
        """Change password (self only)."""
        if current_user.username != username:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        data = await request.json()
        old_password = data.get("old_password")
        new_password = data.get("new_password")
        
        try:
            auth.change_password(username, old_password, new_password)
            return {"status": "updated"}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/api/validate-password")
    async def validate_password(request: Request):
        """Validate password strength (public endpoint)."""
        data = await request.json()
        password = data.get("password", "")
        
        errors = auth.validate_password_strength(password)
        
        # Calculate strength score (0-100)
        score = 100
        score -= len(errors) * 20  # Each error reduces score by 20
        score = max(0, min(100, score))
        
        return PasswordStrengthResponse(
            is_valid=len(errors) == 0,
            errors=errors,
            strength_score=score
        )
    
    # =====================================================================
    # Password Reset Routes (Public)
    # =====================================================================
    
    @router.post("/api/forgot-password")
    async def forgot_password(request: Request):
        """
        Request password reset.
        
        In production, this should send an email with reset link.
        For now, it returns the token (you'd normally send via email).
        """
        data = await request.json()
        username = data.get("username")
        
        if not username:
            raise HTTPException(status_code=400, detail="Username required")
        
        try:
            token = auth.initiate_password_reset(username)
            
            # In production: await email_service.send_password_reset(...)
            # For now, return token for testing
            return {
                "status": "reset_requested",
                "message": "If an account exists, a reset link will be sent to the registered email",
                "token": token  # Remove in production
            }
        except ValueError:
            # Don't reveal if user exists
            return {
                "status": "reset_requested",
                "message": "If an account exists, a reset link will be sent to the registered email"
            }
    
    @router.post("/api/reset-password")
    async def reset_password(request: Request):
        """
        Reset password using reset token.
        
        Requires token and new password.
        """
        data = await request.json()
        token = data.get("token")
        new_password = data.get("new_password")
        
        if not token or not new_password:
            raise HTTPException(status_code=400, detail="Token and new password required")
        
        try:
            auth.reset_password_with_token(token, new_password)
            return {"status": "password_reset", "message": "Password reset successful"}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.get("/api/reset-password/verify/{token}")
    async def verify_reset_token(token: str):
        """
        Verify if a reset token is valid.
        
        Returns username if valid.
        """
        username = auth.verify_reset_token(token)
        if not username:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
        return {"valid": True, "username": username}
    
    # =====================================================================
    # Two-Factor Authentication (2FA) Routes
    # =====================================================================
    
    @router.post("/api/2fa/setup")
    async def setup_2fa(
        current_user: AdminUser = Depends(auth.verify)
    ):
        """
        Start 2FA setup for current user.
        
        Returns provisioning URI and backup codes.
        """
        try:
            uri, backup_codes = auth.setup_2fa(current_user.username)
            return {
                "provisioning_uri": uri,
                "backup_codes": backup_codes,
                "message": "Scan the QR code in your authenticator app, then verify the code."
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/api/2fa/verify-setup")
    async def verify_2fa_setup(
        request: Request,
        current_user: AdminUser = Depends(auth.verify)
    ):
        """
        Verify 2FA setup by providing a TOTP code.
        """
        data = await request.json()
        code = data.get("code", "").replace(" ", "").replace("-", "")
        
        if not code or len(code) != 6:
            raise HTTPException(status_code=400, detail="Code must be 6 digits")
        
        if not code.isdigit():
            raise HTTPException(status_code=400, detail="Code must contain only digits")
        
        if auth.verify_2fa_setup(current_user.username, code):
            return {"status": "2fa_enabled", "message": "2FA has been successfully enabled"}
        else:
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    @router.post("/api/2fa/verify-code")
    async def verify_2fa_code(
        request: Request,
        current_user: AdminUser = Depends(auth.verify)
    ):
        """
        Verify a TOTP code for login.
        
        Used in second factor of authentication.
        """
        data = await request.json()
        code = data.get("code", "").replace(" ", "").replace("-", "")
        
        if not code or len(code) != 6:
            raise HTTPException(status_code=400, detail="Code must be 6 digits")
        
        if not code.isdigit():
            raise HTTPException(status_code=400, detail="Code must contain only digits")
        
        if auth.verify_2fa_code(current_user.username, code):
            return {"valid": True}
        else:
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    @router.post("/api/2fa/verify-backup")
    async def verify_backup_code(
        request: Request,
        current_user: AdminUser = Depends(auth.verify)
    ):
        """
        Verify a backup code for login (when TOTP device unavailable).
        """
        data = await request.json()
        code = data.get("code", "").upper().replace(" ", "").replace("-", "")
        
        if not code:
            raise HTTPException(status_code=400, detail="Backup code required")
        
        if auth.verify_backup_code(current_user.username, code):
            return {"valid": True, "message": "Backup code accepted"}
        else:
            raise HTTPException(status_code=400, detail="Invalid or already-used backup code")
    
    @router.post("/api/2fa/disable")
    async def disable_2fa(
        request: Request,
        current_user: AdminUser = Depends(auth.require_role(AdminRole.ADMIN))
    ):
        """
        Disable 2FA for current user (ADMIN only).
        """
        data = await request.json()
        username = data.get("username", current_user.username)
        
        # Only allow users to disable their own 2FA, or admins can disable anyone
        if username != current_user.username and current_user.role != AdminRole.ADMIN:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        try:
            if auth.disable_2fa(username):
                return {"status": "2fa_disabled", "message": "2FA has been disabled"}
            else:
                raise HTTPException(status_code=400, detail="2FA not enabled for this user")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    @router.get("/api/2fa/status")
    async def get_2fa_status(
        current_user: AdminUser = Depends(auth.verify)
    ):
        """Get 2FA status for current user."""
        return {
            "username": current_user.username,
            "totp_enabled": current_user.totp_enabled,
            "role": current_user.role.value
        }
    
    # =====================================================================
    # Session & Stats Routes
    # =====================================================================
    
    @router.get("/api/me")
    async def get_current_user(current_user: AdminUser = Depends(auth.verify)):
        """Get current user info."""
        return UserResponse(
            username=current_user.username,
            role=current_user.role.value,
            created_at=current_user.created_at.isoformat(),
            last_login=current_user.last_login.isoformat() if current_user.last_login else None,
            is_active=current_user.is_active,
        )
    
    @router.get("/api/stats")
    async def get_stats(
        current_user: AdminUser = Depends(auth.require_role(AdminRole.ADMIN))
    ):
        """Get session statistics (ADMIN only)."""
        stats = auth.get_session_stats()
        return SessionStats(**stats)
    
    @router.post("/api/logout-all")
    async def logout_all_sessions(current_user: AdminUser = Depends(auth.verify)):
        """Logout from all sessions."""
        count = auth.logout_all(current_user.username)
        return {"status": "logged_out", "sessions_closed": count}
    
    return router


# =====================================================================
# Example Setup Function
# =====================================================================

def setup_auth(app, secret_key: str = "your-secret-key-here"):
    """
    Quick setup function to add authentication to FastAPI app.
    
    Usage:
        from eden import App as FastAPI
        from eden.admin.auth_routes import setup_auth
        
        app = FastAPI()
        setup_auth(app, secret_key="super-secret")
        
        # Default users created:
        # admin:password (ADMIN role)
        # editor:password (EDITOR role)
        # viewer:password (VIEWER role)
    """
    # Create auth manager
    auth = AdminAuthManager(secret_key=secret_key)
    
    # Create default users
    auth.register_user("admin", "admin", AdminRole.ADMIN)
    auth.register_user("editor", "editor", AdminRole.EDITOR)
    auth.register_user("viewer", "viewer", AdminRole.VIEWER)
    
    # Add routes
    app.include_router(get_protected_admin_routes(auth))
    
    return auth
