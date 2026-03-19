"""
Password Reset System for Eden Framework

Provides secure token-based password reset functionality with email notifications.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from eden import Model, StringField, UUIDField, DateTimeField
from eden.exceptions import BadRequest, NotFound


UTC = timezone.utc


class PasswordResetToken(Model):
    """
    Stores password reset tokens for users.
    
    Fields:
        user_id: UUID of the user requesting password reset
        token: Secure token sent via email (one-time use)
        expires_at: When the token expires (default: 24 hours)
        used_at: When the token was used (None if unused)
    """
    __tablename__ = "password_reset_tokens"
    
    user_id: UUID = UUIDField(required=True, foreign_key="eden_users.id")
    token: str = StringField(required=True, unique=True, index=True)
    expires_at: datetime = DateTimeField(required=True)
    used_at: Optional[datetime] = DateTimeField(required=False, default=None)


class PasswordResetService:
    """Service for managing password reset tokens and operations."""
    
    # Token expiration (24 hours by default)
    TOKEN_EXPIRATION_HOURS = 24
    
    # Token length (32 bytes = 256 bits of security)
    TOKEN_LENGTH = 32
    
    @staticmethod
    def generate_token() -> str:
        """
        Generate a secure, cryptographically random token.
        
        Returns:
            A secure random token suitable for password reset links.
        """
        return secrets.token_urlsafe(PasswordResetService.TOKEN_LENGTH)
    
    @staticmethod
    async def create_reset_token(session, user_id: UUID) -> str:
        """
        Create a password reset token for a user.
        
        Args:
            session: SQLAlchemy async session
            user_id: UUID of the user
            
        Returns:
            The generated token string (send this via email)
            
        Raises:
            BadRequest: If user not found or token creation fails
        """
        from eden import User  # Import here to avoid circular imports
        
        # Verify user exists
        user = await User.get_or_404(session, user_id)
        
        # Generate new token
        token = PasswordResetService.generate_token()
        expires_at = datetime.now(UTC) + timedelta(hours=PasswordResetService.TOKEN_EXPIRATION_HOURS)
        
        db = PasswordResetToken._get_db()
        async with db.transaction(session=session) as tx_session:
            # Invalidate any existing tokens for this user
            existing_tokens = await PasswordResetToken.query(tx_session).filter(
                user_id=user_id,
                used_at=None
            ).all()
            
            for t in existing_tokens:
                t.used_at = datetime.now(UTC)
            await tx_session.flush()

            reset_token = PasswordResetToken(
                user_id=user_id,
                token=token,
                expires_at=expires_at
            )
            tx_session.add(reset_token)
            await tx_session.flush()
        
        return token
    
    @staticmethod
    async def validate_reset_token(session, token: str) -> UUID:
        """
        Validate a password reset token and return the user ID.
        
        Args:
            session: SQLAlchemy async session
            token: The reset token to validate
            
        Returns:
            The user_id associated with the token
            
        Raises:
            NotFound: If token doesn't exist, is expired, or already used
        """
        reset_token = await PasswordResetToken.filter_one(
            session,
            token=token
        )
        
        if not reset_token:
            raise NotFound(detail="Invalid password reset token")
        
        if reset_token.used_at:
            raise BadRequest(detail="Password reset token has already been used")
        
        if datetime.now(UTC) > reset_token.expires_at:
            raise BadRequest(detail="Password reset token has expired")
        
        return reset_token.user_id
    
    @staticmethod
    async def reset_password(session, token: str, new_password: str) -> None:
        """
        Reset a user's password using a valid reset token.
        
        Args:
            session: SQLAlchemy async session
            token: The reset token
            new_password: The new password to set
            
        Raises:
            BadRequest: If password is invalid or token invalid/expired
            NotFound: If token not found
        """
        from eden import User
        from eden.auth.hashers import hash_password
        
        if not new_password or len(new_password) < 8:
            raise BadRequest(detail="Password must be at least 8 characters")
        
        db = PasswordResetToken._get_db()
        async with db.transaction(session=session) as tx_session:
            # Validate token
            user_id = await PasswordResetService.validate_reset_token(tx_session, token)
            
            # Get user
            user = await User.get_or_404(tx_session, user_id)
            
            # Update password
            user.password = hash_password(new_password)
            
            # Mark token as used
            reset_token = await PasswordResetToken.filter_one(tx_session, token=token)
            if reset_token:
                reset_token.used_at = datetime.now(UTC)
            
            await tx_session.flush()


class PasswordResetEmail:
    """Template and helpers for password reset emails."""
    
    @staticmethod
    def get_reset_link(token: str, app_url: str = "http://localhost:8000") -> str:
        """
        Generate the password reset link to send to user.
        
        Args:
            token: The reset token
            app_url: Your application URL (customize per environment)
            
        Returns:
            Full reset link URL
        """
        return f"{app_url}/auth/reset-password?token={token}"
    
    @staticmethod
    def get_html_body(user_name: str, reset_link: str, app_name: str = "Eden App") -> str:
        """
        Generate HTML email body for password reset.
        
        Args:
            user_name: User's name for personalization
            reset_link: Full reset link URL
            app_name: Your app name
            
        Returns:
            HTML email body
        """
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; }}
        .container {{ max-width: 500px; margin: 0 auto; }}
        .header {{ background: #0F172A; color: #fff; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .button {{ background: #3B82F6; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 20px 0; }}
        .footer {{ padding: 10px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{app_name}</h1>
        </div>
        <div class="content">
            <h2>Reset Your Password</h2>
            <p>Hi {user_name},</p>
            <p>We received a request to reset the password for your account. Click the button below to reset it:</p>
            <p>
                <a href="{reset_link}" class="button">Reset Password</a>
            </p>
            <p>Or copy this link: <code>{reset_link}</code></p>
            <p><strong>This link expires in 24 hours.</strong></p>
            <p>If you didn't request a password reset, you can safely ignore this email.</p>
            <p>Thanks,<br>{app_name} Team</p>
        </div>
        <div class="footer">
            <p>© 2026 {app_name}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>"""
    
    @staticmethod
    def get_text_body(user_name: str, reset_link: str, app_name: str = "Eden App") -> str:
        """
        Generate plain text email body for password reset.
        
        Args:
            user_name: User's name for personalization
            reset_link: Full reset link URL
            app_name: Your app name
            
        Returns:
            Plain text email body
        """
        return f"""Reset Your Password

Hi {user_name},

We received a request to reset the password for your account. Click the link below to reset it:

{reset_link}

This link expires in 24 hours.

If you didn't request a password reset, you can safely ignore this email.

Thanks,
{app_name} Team"""
