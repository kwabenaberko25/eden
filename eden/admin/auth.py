"""
Authentication system for Eden Admin Dashboard.

Supports multiple strategies:
- JWT tokens
- Session-based authentication
- OAuth2-like integration hooks
- Role-based access control (RBAC)

Usage:
    from eden.admin.auth import AdminAuthManager
    
    auth = AdminAuthManager(
        secret_key="your-secret-key",
        users={"admin": "password_hash"}
    )
    
    # Use in FastAPI
    @app.post("/admin/login")
    async def login(username: str, password: str):
        token = auth.create_token(username, password)
        return {"access_token": token}
    
    @app.get("/admin", dependencies=[Depends(auth.verify)])
    async def dashboard():
        return AdminDashboardTemplate.render()
"""

import jwt
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from eden.requests import Request
from eden import HttpException as HTTPException, Depends


class AdminRole(str, Enum):
    """Admin dashboard roles."""
    ADMIN = "admin"           # Full access
    EDITOR = "editor"         # Can create/edit flags
    VIEWER = "viewer"         # Read-only access


@dataclass
class AdminUser:
    """Admin user with role and permissions."""
    username: str
    password_hash: str
    role: AdminRole = AdminRole.VIEWER
    created_at: datetime = None
    last_login: datetime = None
    is_active: bool = True
    password_changed_at: datetime = None
    password_history: List[str] = field(default_factory=list)  # Last 5 password hashes
    failed_login_attempts: int = 0
    locked_until: datetime = None
    totp_enabled: bool = False  # Whether 2FA is enabled
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.password_changed_at is None:
            self.password_changed_at = datetime.now(timezone.utc)


@dataclass
class AdminSession:
    """Admin session."""
    user: AdminUser
    token: str
    expires_at: datetime
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > self.expires_at


class AdminAuthManager:
    """Manages admin authentication and authorization."""
    
    # Password complexity requirements
    MIN_PASSWORD_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    PASSWORD_HISTORY_SIZE = 5
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        token_expiry_hours: int = 24,
        max_login_attempts: int = 5,
        lockout_minutes: int = 15,
    ):
        """
        Initialize auth manager.
        
        Args:
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm (default: HS256)
            token_expiry_hours: Token expiration time in hours
            max_login_attempts: Max failed login attempts before lockout
            lockout_minutes: Lockout duration in minutes
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiry_hours = token_expiry_hours
        self.max_login_attempts = max_login_attempts
        self.lockout_minutes = lockout_minutes
        self.password_hasher = PasswordHasher()
        
        # In-memory storage (replace with database for production)
        self.users: Dict[str, AdminUser] = {}
        self.sessions: Dict[str, AdminSession] = {}
        
        # Lazy-load 2FA manager
        self._totp_manager = None
    
    # =====================================================================
    # User Management
    # =====================================================================
    
    def register_user(
        self,
        username: str,
        password: str,
        role: AdminRole = AdminRole.VIEWER,
    ) -> AdminUser:
        """
        Register a new admin user.
        
        Args:
            username: Username (unique)
            password: Plain password (will be hashed)
            role: User role
            
        Returns:
            Created AdminUser
            
        Raises:
            ValueError: If username already exists or password invalid
        """
        if username in self.users:
            raise ValueError(f"User '{username}' already exists")
        
        # Validate password strength
        validation_errors = self.validate_password_strength(password)
        if validation_errors:
            raise ValueError(f"Password does not meet requirements: {', '.join(validation_errors)}")
        
        password_hash = self._hash_password(password)
        user = AdminUser(
            username=username,
            password_hash=password_hash,
            role=role,
            password_history=[password_hash],
        )
        self.users[username] = user
        return user
    
    def update_user_role(self, username: str, role: AdminRole) -> AdminUser:
        """Update user's role."""
        if username not in self.users:
            raise ValueError(f"User '{username}' not found")
        
        self.users[username].role = role
        return self.users[username]
    
    def delete_user(self, username: str) -> None:
        """Delete a user."""
        if username in self.users:
            del self.users[username]
            # Also invalidate any active sessions
            self.sessions = {
                k: v for k, v in self.sessions.items()
                if v.user.username != username
            }
    
    def list_users(self) -> List[AdminUser]:
        """Get all users."""
        return list(self.users.values())
    
    def get_user(self, username: str) -> Optional[AdminUser]:
        """Get user by username."""
        return self.users.get(username)
    
    # =====================================================================
    # Password Management
    # =====================================================================
    
    @staticmethod
    def validate_password_strength(password: str) -> List[str]:
        """
        Validate password meets complexity requirements.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if len(password) < AdminAuthManager.MIN_PASSWORD_LENGTH:
            errors.append(f"At least {AdminAuthManager.MIN_PASSWORD_LENGTH} characters required")
        
        if AdminAuthManager.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("At least one uppercase letter required")
        
        if AdminAuthManager.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("At least one lowercase letter required")
        
        if AdminAuthManager.REQUIRE_DIGIT and not re.search(r'\d', password):
            errors.append("At least one digit required")
        
        if AdminAuthManager.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("At least one special character required (!@#$%^&*(),.?\":{}|<>)")
        
        return errors
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using Argon2."""
        return self.password_hasher.hash(password)
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash using Argon2."""
        try:
            self.password_hasher.verify(password_hash, password)
            return True
        except (VerifyMismatchError, VerificationError):
            return False
    
    def _add_to_password_history(self, user: AdminUser, new_hash: str) -> None:
        """Add password hash to history, keeping only last 5."""
        user.password_history.insert(0, new_hash)
        if len(user.password_history) > self.PASSWORD_HISTORY_SIZE:
            user.password_history.pop()
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """
        Change user password.
        
        Args:
            username: Username
            old_password: Current password
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If user not found, password incorrect, or new password invalid
        """
        user = self.get_user(username)
        if not user:
            raise ValueError(f"User '{username}' not found")
        
        if not self.verify_password(old_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        
        # Validate new password strength
        validation_errors = self.validate_password_strength(new_password)
        if validation_errors:
            raise ValueError(f"New password does not meet requirements: {', '.join(validation_errors)}")
        
        # Check if new password matches any in history
        new_hash = self._hash_password(new_password)
        for historical_hash in user.password_history:
            if self.verify_password(new_password, historical_hash):
                raise ValueError("Cannot reuse a previous password")
        
        # Update password
        user.password_hash = new_hash
        user.password_changed_at = datetime.now(timezone.utc)
        self._add_to_password_history(user, new_hash)
        return True
    
    # =====================================================================
    # Login & Session Management
    # =====================================================================
    
    def login(self, username: str, password: str) -> str:
        """
        Login user and create session.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            JWT token
            
        Raises:
            HTTPException: If login fails
        """
        # Find user first
        user = self.get_user(username)
        
        # Check lockout
        if user and user.locked_until and datetime.now(timezone.utc) < user.locked_until:
            raise HTTPException(
                status_code=429,
                detail="Too many failed login attempts. Try again later."
            )
        elif user and user.locked_until and datetime.now(timezone.utc) >= user.locked_until:
            # Lockout expired, reset
            user.locked_until = None
            user.failed_login_attempts = 0
        
        # Verify user exists
        if not user:
            self._record_failed_attempt(None)
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # Verify password
        if not self.verify_password(password, user.password_hash):
            self._record_failed_attempt(user)
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # Check if active
        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="User account is inactive"
            )
        
        # Clear failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        
        # Create token and session
        token = self._create_jwt_token(user)
        user.last_login = datetime.now(timezone.utc)
        
        # Store session
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.token_expiry_hours)
        session = AdminSession(
            user=user,
            token=token,
            expires_at=expires_at,
        )
        self.sessions[token] = session
        
        return token
    
    def logout(self, token: str) -> bool:
        """Logout user and invalidate session."""
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False
    
    def logout_all(self, username: str) -> int:
        """Logout user from all sessions."""
        count = 0
        tokens_to_remove = [
            token for token, session in self.sessions.items()
            if session.user.username == username
        ]
        for token in tokens_to_remove:
            del self.sessions[token]
            count += 1
        return count
    
    # =====================================================================
    # Token Management
    # =====================================================================
    
    def _create_jwt_token(self, user: AdminUser) -> str:
        """Create JWT token for user."""
        payload = {
            "username": user.username,
            "role": user.role.value,
            "jti": str(uuid.uuid4()),  # Unique token ID
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=self.token_expiry_hours),
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Token payload
            
        Raises:
            HTTPException: If token invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
    
    def get_current_user(self, token: str) -> AdminUser:
        """
        Get current user from token.
        
        Args:
            token: JWT token
            
        Returns:
            AdminUser
            
        Raises:
            HTTPException: If token invalid or user not found
        """
        payload = self.verify_token(token)
        username = payload.get("username")
        
        user = self.get_user(username)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=401,
                detail="User not found or inactive"
            )
        
        return user
    
    # =====================================================================
    # FastAPI Dependencies
    # =====================================================================
    
    def verify(self, request: Request) -> AdminUser:
        """
        FastAPI dependency to verify authentication.
        
        Usage:
            @app.get("/admin", dependencies=[Depends(auth.verify)])
            async def dashboard():
                return ...
        """
        authorization = request.headers.get("authorization")
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Missing authorization header"
            )
        
        # Extract token from "Bearer <token>"
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise ValueError()
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format"
            )
        
        return self.get_current_user(token)
    
    def require_role(self, *required_roles: AdminRole):
        """
        FastAPI dependency to verify role.
        
        Usage:
            @app.delete("/admin/users/{id}",
                       dependencies=[Depends(auth.require_role(AdminRole.ADMIN))])
            async def delete_user(id: str):
                return ...
        """
        async def check_role(user: AdminUser = Depends(self.verify)) -> AdminUser:
            if user.role not in required_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions. Required roles: {', '.join([r.value for r in required_roles])}"
                )
            return user
        
        return check_role
    
    # =====================================================================
    # Two-Factor Authentication (2FA) with TOTP
    # =====================================================================
    
    def _get_totp_manager(self):
        """Get or initialize TOTP manager (lazy load)."""
        if self._totp_manager is None:
            from eden.admin.totp import TOTPSecretManager
            self._totp_manager = TOTPSecretManager(issuer="Eden Admin")
        return self._totp_manager
    
    def setup_2fa(self, username: str) -> tuple[str, List[str]]:
        """
        Setup 2FA for a user.
        
        Returns provisioning URI (for QR code) and backup codes.
        
        Args:
            username: Username
            
        Returns:
            (provisioning_uri, backup_codes)
            
        Raises:
            ValueError: If user not found
        """
        user = self.get_user(username)
        if not user:
            raise ValueError(f"User '{username}' not found")
        
        if user.totp_enabled:
            raise ValueError(f"2FA is already enabled for user '{username}'")
        
        totp_manager = self._get_totp_manager()
        uri, backup_codes = totp_manager.setup_2fa(username)
        
        return uri, backup_codes
    
    def verify_2fa_setup(self, username: str, code: str) -> bool:
        """
        Verify 2FA setup by checking a TOTP code.
        
        Args:
            username: Username
            code: 6-digit TOTP code
            
        Returns:
            True if code is valid
        """
        user = self.get_user(username)
        if not user:
            raise ValueError(f"User '{username}' not found")
        
        totp_manager = self._get_totp_manager()
        if totp_manager.verify_setup(username, code):
            user.totp_enabled = True
            return True
        
        return False
    
    def verify_2fa_code(self, username: str, code: str) -> bool:
        """
        Verify a TOTP code for login.
        
        Args:
            username: Username
            code: 6-digit TOTP code
            
        Returns:
            True if code is valid
        """
        user = self.get_user(username)
        if not user or not user.totp_enabled:
            return False
        
        totp_manager = self._get_totp_manager()
        return totp_manager.verify_code(username, code)
    
    def verify_backup_code(self, username: str, code: str) -> bool:
        """
        Verify a backup code for login (when TOTP device unavailable).
        
        Args:
            username: Username
            code: Backup code
            
        Returns:
            True if backup code is valid and unused
        """
        user = self.get_user(username)
        if not user or not user.totp_enabled:
            return False
        
        totp_manager = self._get_totp_manager()
        return totp_manager.use_backup_code(username, code)
    
    def disable_2fa(self, username: str) -> bool:
        """
        Disable 2FA for a user.
        
        Args:
            username: Username
            
        Returns:
            True if disabled
        """
        user = self.get_user(username)
        if not user:
            raise ValueError(f"User '{username}' not found")
        
        totp_manager = self._get_totp_manager()
        if totp_manager.disable_2fa(username):
            user.totp_enabled = False
            return True
        
        return False
    
    # =====================================================================
    # Password Reset & Email
    # =====================================================================
    
    def initiate_password_reset(self, username: str) -> str:
        """
        Initiate password reset for a user.
        
        Args:
            username: Username
            
        Returns:
            Reset token (URL-safe string)
            
        Raises:
            ValueError: If user not found
        """
        user = self.get_user(username)
        if not user:
            raise ValueError(f"User '{username}' not found")
        
        # Import here to avoid circular imports
        from eden.admin.email import PasswordResetTokenManager
        
        if not hasattr(self, '_reset_token_manager'):
            self._reset_token_manager = PasswordResetTokenManager(expiry_hours=24)
        
        token_obj = self._reset_token_manager.create_token(username)
        return token_obj.token
    
    def verify_reset_token(self, token: str) -> Optional[str]:
        """
        Verify a password reset token.
        
        Args:
            token: Reset token
            
        Returns:
            Username if valid, None otherwise
        """
        from eden.admin.email import PasswordResetTokenManager
        
        if not hasattr(self, '_reset_token_manager'):
            return None
        
        reset_token = self._reset_token_manager.verify_token(token)
        return reset_token.username if reset_token else None
    
    def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """
        Reset password using a reset token.
        
        Args:
            token: Reset token
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If token invalid or password invalid
        """
        from eden.admin.email import PasswordResetTokenManager
        
        if not hasattr(self, '_reset_token_manager'):
            raise ValueError("No password reset manager initialized")
        
        username = self._reset_token_manager.consume_token(token)
        if not username:
            raise ValueError("Invalid or expired reset token")
        
        user = self.get_user(username)
        if not user:
            raise ValueError(f"User '{username}' not found")
        
        # Validate new password strength
        validation_errors = self.validate_password_strength(new_password)
        if validation_errors:
            raise ValueError(f"Password does not meet requirements: {', '.join(validation_errors)}")
        
        # Check if new password matches any in history
        new_hash = self._hash_password(new_password)
        for historical_hash in user.password_history:
            if self.verify_password(new_password, historical_hash):
                raise ValueError("Cannot reuse a previous password")
        
        # Update password
        user.password_hash = new_hash
        user.password_changed_at = datetime.now(timezone.utc)
        self._add_to_password_history(user, new_hash)
        return True
    
    # =====================================================================
    # Helper Methods
    # =====================================================================
    
    def _record_failed_attempt(self, user: Optional[AdminUser]) -> None:
        """Record failed login attempt and apply lockout if needed."""
        if not user:
            return
        
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= self.max_login_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=self.lockout_minutes)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        active_sessions = [s for s in self.sessions.values() if not s.is_expired()]
        
        return {
            "total_users": len(self.users),
            "active_sessions": len(active_sessions),
            "total_sessions": len(self.sessions),
            "users_by_role": {
                role.value: sum(1 for u in self.users.values() if u.role == role)
                for role in AdminRole
            },
        }


# =====================================================================
# Decorators
# =====================================================================

def require_auth(auth: AdminAuthManager, *required_roles: AdminRole):
    """
    Decorator to require authentication on a function.
    
    Usage:
        auth = AdminAuthManager(secret_key="...")
        
        @require_auth(auth, AdminRole.ADMIN)
        def delete_flag(flag_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Token should be in kwargs or args
            token = kwargs.get("token") or (args[0] if args else None)
            
            if not token:
                raise HTTPException(
                    status_code=401,
                    detail="Missing token"
                )
            
            user = auth.get_current_user(token)
            
            if required_roles and user.role not in required_roles:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
            
            kwargs["current_user"] = user
            return await func(*args, **kwargs) if hasattr(func, '__await__') else func(*args, **kwargs)
        
        return wrapper
    return decorator
