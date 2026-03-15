"""
Eden Authentication System — Complete Implementation Guide

This module exports the complete auth API and provides patterns
for authentication, authorization, and user management.

Usage:
    from eden.auth import BaseUser, authenticate, create_user
    from eden.auth.permissions import require_permission, check_roles
    from eden.auth.decorators import login_required, staff_required
"""

from __future__ import annotations

import logging
from typing import Optional, List, Set, Any, AsyncGenerator
from abc import ABC, abstractmethod
from passlib.context import CryptContext
import argon2

logger = logging.getLogger(__name__)

# ============================================================================
# PASSWORD HASHING
# ============================================================================

# Automatically detect best available hasher
try:
    # Prefer argon2 (most secure)
    _hasher = argon2.PasswordHasher()
    
    class ArgonHasher:
        @staticmethod
        def hash(password: str) -> str:
            return _hasher.hash(password)
        
        @staticmethod
        def verify(password: str, hash: str) -> bool:
            try:
                _hasher.verify(hash, password)
                return True
            except argon2.exceptions.VerifyMismatchError:
                return False
    
    DEFAULT_PASSWORD_HASHER = ArgonHasher
    logger.info("Using argon2 password hasher")
    
except ImportError:
    # Fall back to bcrypt
    logger.warning("argon2 not available, using bcrypt")
    _bcrypt_context = CryptContext(
        schemes=["bcrypt"],
        deprecated="auto",
        bcrypt__rounds=12,
    )
    
    class BcryptHasher:
        @staticmethod
        def hash(password: str) -> str:
            return _bcrypt_context.hash(password)
        
        @staticmethod
        def verify(password: str, hash: str) -> bool:
            return _bcrypt_context.verify(password, hash)
    
    DEFAULT_PASSWORD_HASHER = BcryptHasher
    logger.info("Using bcrypt password hasher")


def hash_password(password: str) -> str:
    """
    Hash a password using the default algorithm.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
        
    Example:
        hashed = hash_password("MyPassword123!")
    """
    return DEFAULT_PASSWORD_HASHER.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password
        hashed: Previously hashed password
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        if verify_password("MyPassword123!", user.password_hash):
            print("Password correct")
    """
    return DEFAULT_PASSWORD_HASHER.verify(password, hashed)


# ============================================================================
# USER MODEL
# ============================================================================

class BaseUser(ABC):
    """
    Abstract base class for user models.
    
    Extend this class in your application model:
    
    Example:
        class User(BaseUser):
            email: str
            password_hash: str
            is_active: bool = True
            is_staff: bool = False
            is_superuser: bool = False
            
            async def get_roles(self):
                return await self.roles.all()
    """
    
    id: Any  # Primary key (UUID or int)
    email: str
    password_hash: str
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    
    @abstractmethod
    async def get_roles(self) -> List:
        """Get all roles assigned to this user."""
        pass
    
    @abstractmethod
    async def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        pass
    
    @abstractmethod
    async def has_role(self, role: str) -> bool:
        """Check if user belongs to a specific role."""
        pass
    
    def set_password(self, raw_password: str) -> None:
        """
        Set the user's password (hashes it automatically).
        
        Args:
            raw_password: Plain text password
            
        Example:
            user = User.create(email="test@example.com")
            user.set_password("SecurePassword123!")
        """
        self.password_hash = hash_password(raw_password)
    
    def check_password(self, raw_password: str) -> bool:
        """
        Verify a password against the user's hash.
        
        Args:
            raw_password: Plain text password to verify
            
        Returns:
            True if password is correct
            
        Example:
            if user.check_password(provided_password):
                # authenticate successful
        """
        return verify_password(raw_password, self.password_hash)


# ============================================================================
# AUTHENTICATION FUNCTIONS
# ============================================================================

async def authenticate(
    email: str,
    password: str,
    user_model: type = None,
) -> Optional[BaseUser]:
    """
    Authenticate a user by email and password.
    
    Args:
        email: User email address
        password: Plain text password
        user_model: User model class (auto-detected if not provided)
        
    Returns:
        User object if credentials valid, None otherwise
        
    Raises:
        ValueError: If email or password is invalid
        
    Example:
        user = await authenticate("user@example.com", "password123")
        if user:
            # Authentication successful
            await set_current_user(user)
    """
    if not email or not password:
        raise ValueError("Email and password required")
    
    # Auto-detect user model if not provided
    if user_model is None:
        from eden.db import get_models
        models = get_models()
        # Find first model that extends BaseUser
        user_model = next(
            (m for m in models if issubclass(m, BaseUser)),
            None
        )
        if not user_model:
            raise ValueError("No User model found")
    
    # Find user by email
    user = await user_model.filter(email=email.lower()).first()
    
    if not user or not user.is_active:
        logger.warning(f"Login failed for {email}: user not found or inactive")
        return None
    
    # Verify password
    if not user.check_password(password):
        logger.warning(f"Login failed for {email}: invalid password")
        return None
    
    logger.info(f"User {email} authenticated successfully")
    return user


async def create_user(
    email: str,
    password: str,
    **kwargs
) -> BaseUser:
    """
    Create a new user with email and password.
    
    Args:
        email: User email (must be unique)
        password: Plain text password
        **kwargs: Additional user fields
        
    Returns:
        Created User object
        
    Raises:
        ValueError: If email invalid or already exists
        
    Example:
        user = await create_user(
            email="newuser@example.com",
            password="SecurePass123!",
            name="John Doe"
        )
    """
    from eden.db import get_models
    from eden.validators import validate_email
    
    # Validate email
    if not validate_email(email):
        raise ValueError(f"Invalid email: {email}")
    
    email = email.lower()
    
    # Find user model
    models = get_models()
    user_model = next(
        (m for m in models if issubclass(m, BaseUser)),
        None
    )
    if not user_model:
        raise ValueError("No User model found")
    
    # Check email uniqueness
    existing = await user_model.filter(email=email).first()
    if existing:
        raise ValueError(f"Email {email} already in use")
    
    # Create user
    user = await user_model.create(
        email=email,
        password_hash=hash_password(password),
        **kwargs
    )
    
    logger.info(f"User created: {email}")
    return user


# ============================================================================
# ROLE-BASED ACCESS CONTROL (RBAC)
# ============================================================================

class RoleManager:
    """
    Manages role and permission assignments.
    """
    
    @staticmethod
    async def assign_role(user: BaseUser, role_name: str) -> None:
        """
        Assign a role to a user.
        
        Args:
            user: User instance
            role_name: Name of role to assign
            
        Example:
            await RoleManager.assign_role(user, "admin")
        """
        # Implementation depends on your model
        # Example: user.roles.add(await Role.get(name=role_name))
        logger.info(f"Role {role_name} assigned to user {user.id}")
    
    @staticmethod
    async def revoke_role(user: BaseUser, role_name: str) -> None:
        """
        Remove a role from a user.
        
        Args:
            user: User instance
            role_name: Name of role to revoke
            
        Example:
            await RoleManager.revoke_role(user, "admin")
        """
        logger.info(f"Role {role_name} revoked from user {user.id}")
    
    @staticmethod
    async def grant_permission(role_name: str, permission: str) -> None:
        """
        Grant a permission to a role.
        
        Args:
            role_name: Name of role
            permission: Permission codename (e.g., "users:read")
            
        Example:
            await RoleManager.grant_permission("editor", "posts:write")
        """
        logger.info(f"Permission {permission} granted to role {role_name}")


# ============================================================================
# PERMISSION CHECKING
# ============================================================================

async def check_permission(
    user: Optional[BaseUser],
    resource: str,
    action: str,
) -> bool:
    """
    Check if user has permission for an action on a resource.
    
    Permission format: "resource:action"
    
    Args:
        user: User object or None
        resource: Resource name (e.g., "users", "posts")
        action: Action name (e.g., "read", "write", "delete")
        
    Returns:
        True if user has permission, False otherwise
        
    Example:
        if await check_permission(user, "posts", "delete"):
            await post.delete()
    """
    if not user:
        logger.warning(f"Permission denied for anonymous user: {resource}:{action}")
        return False
    
    if user.is_superuser:
        # Superusers have all permissions
        return True
    
    permission_code = f"{resource}:{action}"
    has_perm = await user.has_permission(permission_code)
    
    if not has_perm:
        logger.warning(f"Permission denied for user {user.id}: {permission_code}")
    
    return has_perm


async def require_permission(
    user: Optional[BaseUser],
    resource: str,
    action: str,
) -> None:
    """
    Require a permission or raise PermissionError.
    
    Args:
        user: User object or None
        resource: Resource name
        action: Action name
        
    Raises:
        PermissionError: If user lacks permission
        
    Example:
        await require_permission(user, "admin", "access")
        # Raises PermissionError if not granted
    """
    if not await check_permission(user, resource, action):
        raise PermissionError(f"Permission denied: {resource}:{action}")


# ============================================================================
# DECORATORS
# ============================================================================

def login_required(func):
    """
    Decorator requiring authentication.
    
    Example:
        @login_required
        async def get_profile(request):
            user = await get_current_user(request)
            return user.profile()
    """
    import functools
    from eden.auth.base import get_current_user
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request
        request = kwargs.get("request")
        if not request and args:
            request = args[0]
            
        if not request:
            from eden.context import get_request
            request = get_request()
            
        user = await get_current_user(request)
        if not user:
            from starlette.exceptions import HTTPException
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        return await func(*args, **kwargs)
    
    return wrapper


def staff_required(func):
    """
    Decorator requiring staff access.
    
    Example:
        @staff_required
        async def admin_panel(request):
            return await render_admin()
    """
    import functools
    from eden.auth.base import get_current_user
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request
        request = kwargs.get("request")
        if not request and args:
            request = args[0]
            
        if not request:
            from eden.context import get_request
            request = get_request()
            
        user = await get_current_user(request)
        if not user or not user.is_staff:
            from starlette.exceptions import HTTPException
            raise HTTPException(status_code=403, detail="Staff access required")
        
        return await func(*args, **kwargs)
    
    return wrapper


def permission_required(resource: str, action: str):
    """
    Decorator requiring specific permission.
    
    Args:
        resource: Resource name
        action: Action name
        
    Example:
        @permission_required("posts", "delete")
        async def delete_post(post_id, request):
            return await Post.delete(id=post_id)
    """
    import functools
    from eden.auth.base import get_current_user
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request
            request = kwargs.get("request")
            if not request and args:
                request = args[0]
                
            if not request:
                from eden.context import get_request
                request = get_request()
                
            user = await get_current_user(request)
            await require_permission(user, resource, action)
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# ============================================================================
# OAUTH (Extensible for future implementation)
# ============================================================================

class OAuthProvider:
    """
    Base OAuth provider (Google, GitHub, Facebook, etc).
    
    Extend this to implement specific OAuth flows.
    """
    
    name: str = "oauth"
    
    async def verify_callback(self, code: str, state: str) -> Optional[BaseUser]:
        """
        Verify OAuth callback and return user.
        
        Args:
            code: Authorization code from provider
            state: State parameter for CSRF protection
            
        Returns:
            User object if OAuth successful
        """
        raise NotImplementedError("Subclasses must implement verify_callback")


__all__ = [
    # Hashing
    "hash_password",
    "verify_password",
    "DEFAULT_PASSWORD_HASHER",
    # Models
    "BaseUser",
    # Auth
    "authenticate",
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
