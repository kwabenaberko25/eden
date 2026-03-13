"""
Password Reset Routes for Eden Framework

HTTP endpoints for:
- Forgot password (request)
- Reset password (confirm with token)
"""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field
from starlette import status
from eden.routing import Router
from eden.requests import Request
from eden.exceptions import BadRequest, NotFound
from eden.db import AsyncSession
from eden.auth.password_reset import (
    PasswordResetService,
    PasswordResetEmail
)


# Pydantic schemas for validation
class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset."""
    email: EmailStr = Field(..., description="User's email address")


class ResetPasswordRequest(BaseModel):
    """Submit password reset with token."""
    token: str = Field(..., min_length=1, description="Reset token from email")
    new_password: str = Field(..., min_length=8, description="New password (8+ chars)")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")


class ForgotPasswordResponse(BaseModel):
    """Response after requesting password reset."""
    message: str
    email: str


class ResetPasswordResponse(BaseModel):
    """Response after successful password reset."""
    message: str


# Create router
router = Router(prefix="/auth")


@router.post(
    "/forgot-password",
    summary="Request Password Reset",
    tags=["Authentication"]
)
async def forgot_password(
    body: ForgotPasswordRequest,
    session: AsyncSession,
    request: Request
):
    """
    Request a password reset link.
    
    Returns 200 regardless of whether the email exists (security best practice).
    If user exists, sends reset email immediately.
    
    Args:
        body: Request with user's email
        session: Database session
        request: HTTP request (for app_url)
    """
    from eden import User
    from eden.mail import Mail
    
    email = body.email.lower().strip()
    
    # Try to find user (silently fail if not found for security)
    try:
        user = await User.filter_one(session, email=email)
        
        # Generate reset token
        token = await PasswordResetService.create_reset_token(session, user.id)
        
        # Build reset link
        app_url = request.base_url.rstrip("/")
        reset_link = PasswordResetEmail.get_reset_link(token, str(app_url))
        
        # Send email
        mail = Mail()
        await mail.send(
            to=user.email,
            subject="Password Reset Request",
            html=PasswordResetEmail.get_html_body(user.first_name or "Friend", reset_link),
            text=PasswordResetEmail.get_text_body(user.first_name or "Friend", reset_link),
        )
    except NotFound:
        # User not found - still return success (security best practice)
        pass
    
    return {
        "message": "If an account with that email exists, a password reset link has been sent.",
        "email": email
    }


@router.post(
    "/reset-password",
    summary="Reset Password",
    tags=["Authentication"]
)
async def reset_password(
    body: ResetPasswordRequest,
    session: AsyncSession
):
    """
    Complete the password reset process.
    
    Args:
        body: Reset request with token and new password
        session: Database session
        
    Raises:
        BadRequest: If passwords don't match or are too short
        NotFound: If token invalid/expired
    """
    # Validate passwords match
    if body.new_password != body.confirm_password:
        raise BadRequest(detail="Passwords do not match")
    
    # Reset password
    await PasswordResetService.reset_password(session, body.token, body.new_password)
    
    return {
        "message": "Your password has been successfully reset. You can now log in with your new password."
    }


@router.get(
    "/reset-password",
    summary="Get Reset Password Form",
    tags=["Authentication"]
)
async def get_reset_password_form(token: str):
    """
    Return HTML form for password reset.
    
    Args:
        token: Reset token from URL parameter
    """
    return {
        "token": token,
        "form_url": "/auth/reset-password",
        "method": "POST"
    }
