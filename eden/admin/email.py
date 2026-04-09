"""
Email service for Eden Admin Dashboard.

Handles sending emails for password resets, verification, 2FA codes, etc.
Supports SMTP configuration with templates.

Usage:
    from eden.admin.email import EmailService, EmailConfig
    
    config = EmailConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        sender_email="noreply@example.com",
        sender_name="Eden Admin"
    )
    
    email_service = EmailService(config)
    
    await email_service.send_password_reset(
        to_email="user@example.com",
        username="admin",
        reset_token="abc123",
        reset_url="https://admin.example.com/reset?token=abc123"
    )
"""

import os
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta
import secrets
from abc import ABC, abstractmethod


@dataclass
class EmailConfig:
    """Email service configuration."""
    smtp_host: str
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    sender_email: str = "noreply@example.com"
    sender_name: str = "Eden Admin"
    use_tls: bool = True
    use_ssl: bool = False


class EmailTemplate(ABC):
    """Base class for email templates."""
    
    @abstractmethod
    async def render(self, **kwargs) -> tuple[str, str]:
        """
        Render email template.
        
        Returns:
            (subject, html_body)
        """
        pass


class PasswordResetEmailTemplate(EmailTemplate):
    """Email template for password reset."""
    
    async def render(self, username: str, reset_url: str, expiry_hours: int = 24) -> tuple[str, str]:
        """Render password reset email."""
        subject = "Reset your Eden Admin password"
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Password Reset Request</h2>
                    <p>Hi <strong>{username}</strong>,</p>
                    <p>We received a request to reset your Eden Admin password. 
                    Click the link below to reset it:</p>
                    
                    <div style="margin: 30px 0;">
                        <a href="{reset_url}" 
                           style="background-color: #6366f1; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        This link will expire in {expiry_hours} hours. If you didn't request this, 
                        please ignore this email.
                    </p>
                    
                    <p style="color: #666; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
                        If the link doesn't work, copy and paste this URL in your browser:<br>
                        <code>{reset_url}</code>
                    </p>
                </div>
            </body>
        </html>
        """
        return subject, html_body


class VerificationEmailTemplate(EmailTemplate):
    """Email template for account verification."""
    
    async def render(self, username: str, verification_url: str) -> tuple[str, str]:
        """Render verification email."""
        subject = "Verify your Eden Admin account"
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Verify Your Account</h2>
                    <p>Hi <strong>{username}</strong>,</p>
                    <p>Welcome to Eden Admin! Please verify your email address by clicking the link below:</p>
                    
                    <div style="margin: 30px 0;">
                        <a href="{verification_url}" 
                           style="background-color: #10b981; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Verify Email
                        </a>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        This link will expire in 24 hours.
                    </p>
                </div>
            </body>
        </html>
        """
        return subject, html_body


class TwoFAEmailTemplate(EmailTemplate):
    """Email template for 2FA code."""
    
    async def render(self, username: str, code: str, expiry_minutes: int = 10) -> tuple[str, str]:
        """Render 2FA email."""
        subject = "Your Eden Admin verification code"
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Your Verification Code</h2>
                    <p>Hi <strong>{username}</strong>,</p>
                    <p>Your verification code is:</p>
                    
                    <div style="margin: 30px 0; text-align: center;">
                        <div style="font-size: 48px; font-weight: bold; letter-spacing: 8px; 
                                  background-color: #f3f4f6; padding: 20px; border-radius: 5px;">
                            {code}
                        </div>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        This code will expire in {expiry_minutes} minutes. If you didn't request this code,
                        please ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """
        return subject, html_body


class EmailService:
    """Service for sending emails."""
    
    def __init__(self, config: EmailConfig):
        """Initialize email service."""
        self.config = config
        self._aiosmtplib = None
    
    async def _get_smtp_client(self):
        """Get SMTP client (lazy load aiosmtplib)."""
        if self._aiosmtplib is None:
            try:
                import aiosmtplib
                self._aiosmtplib = aiosmtplib
            except ImportError:
                raise ImportError(
                    "aiosmtplib is required for email functionality. "
                    "Install with: pip install aiosmtplib"
                )
        return self._aiosmtplib
    
    async def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """
        Send email.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_body: HTML email body
            
        Returns:
            True if sent successfully
        """
        try:
            aiosmtplib = await self._get_smtp_client()
            
            # For testing/demo, just log it
            import logging
            logger = logging.getLogger("eden.admin.email")
            logger.info(f"Email would be sent to {to_email}: {subject}")
            
            # In production, uncomment below and remove the logger above
            # async with aiosmtplib.SMTP(hostname=self.config.smtp_host, port=self.config.smtp_port) as smtp:
            #     if self.config.use_tls:
            #         await smtp.starttls()
            #     if self.config.smtp_username and self.config.smtp_password:
            #         await smtp.login(self.config.smtp_username, self.config.smtp_password)
            #     
            #     message = f"""From: {self.config.sender_name} <{self.config.sender_email}>
            # To: {to_email}
            # Subject: {subject}
            # MIME-Version: 1.0
            # Content-Type: text/html; charset="UTF-8"
            # 
            # {html_body}
            # """
            #     await smtp.send_message(message)
            
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger("eden.admin.email")
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_password_reset(
        self,
        to_email: str,
        username: str,
        reset_token: str,
        reset_url: str,
        expiry_hours: int = 24
    ) -> bool:
        """Send password reset email."""
        template = PasswordResetEmailTemplate()
        subject, html_body = await template.render(
            username=username,
            reset_url=reset_url,
            expiry_hours=expiry_hours
        )
        return await self.send_email(to_email, subject, html_body)
    
    async def send_verification(
        self,
        to_email: str,
        username: str,
        verification_url: str
    ) -> bool:
        """Send account verification email."""
        template = VerificationEmailTemplate()
        subject, html_body = await template.render(
            username=username,
            verification_url=verification_url
        )
        return await self.send_email(to_email, subject, html_body)
    
    async def send_2fa_code(
        self,
        to_email: str,
        username: str,
        code: str,
        expiry_minutes: int = 10
    ) -> bool:
        """Send 2FA code email."""
        template = TwoFAEmailTemplate()
        subject, html_body = await template.render(
            username=username,
            code=code,
            expiry_minutes=expiry_minutes
        )
        return await self.send_email(to_email, subject, html_body)


class PasswordResetToken:
    """Represents a password reset token."""
    
    def __init__(self, username: str, token: Optional[str] = None, expiry_hours: int = 24):
        """
        Initialize password reset token.
        
        Args:
            username: Username
            token: Token (generated if not provided)
            expiry_hours: Token expiry time in hours
        """
        self.username = username
        self.token = token or secrets.token_urlsafe(32)
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(hours=expiry_hours)
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self) -> str:
        return f"PasswordResetToken(username={self.username}, expires_at={self.expires_at})"


class PasswordResetTokenManager:
    """Manages password reset tokens."""
    
    def __init__(self, expiry_hours: int = 24):
        """Initialize token manager."""
        self.expiry_hours = expiry_hours
        self.tokens: Dict[str, PasswordResetToken] = {}  # token -> PasswordResetToken
        self.user_tokens: Dict[str, str] = {}  # username -> token
    
    def create_token(self, username: str) -> PasswordResetToken:
        """
        Create a new password reset token.
        
        Args:
            username: Username
            
        Returns:
            PasswordResetToken
        """
        # Revoke any existing token for this user
        if username in self.user_tokens:
            old_token = self.user_tokens[username]
            if old_token in self.tokens:
                del self.tokens[old_token]
        
        token = PasswordResetToken(username, expiry_hours=self.expiry_hours)
        self.tokens[token.token] = token
        self.user_tokens[username] = token.token
        return token
    
    def verify_token(self, token: str) -> Optional[PasswordResetToken]:
        """
        Verify a password reset token.
        
        Args:
            token: Token string
            
        Returns:
            PasswordResetToken if valid, None otherwise
        """
        if token not in self.tokens:
            return None
        
        reset_token = self.tokens[token]
        if reset_token.is_expired():
            # Clean up expired token
            del self.tokens[token]
            if reset_token.username in self.user_tokens:
                del self.user_tokens[reset_token.username]
            return None
        
        return reset_token
    
    def consume_token(self, token: str) -> Optional[str]:
        """
        Consume a token (validate and remove it).
        
        Args:
            token: Token string
            
        Returns:
            Username if valid, None otherwise
        """
        reset_token = self.verify_token(token)
        if not reset_token:
            return None
        
        username = reset_token.username
        del self.tokens[token]
        if username in self.user_tokens:
            del self.user_tokens[username]
        return username
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired tokens.
        
        Returns:
            Number of tokens removed
        """
        expired_tokens = [
            token for token, reset_token in self.tokens.items()
            if reset_token.is_expired()
        ]
        
        for token in expired_tokens:
            del self.tokens[token]
        
        # Also clean up user_tokens mapping
        for username, token in list(self.user_tokens.items()):
            if token not in self.tokens:
                del self.user_tokens[username]
        
        return len(expired_tokens)


# Type hint for imports
from typing import Dict
