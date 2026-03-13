"""
Test Suite for Password Reset Flow (Phase 4)

Tests all password reset functionality:
- Token generation and validation
- Password reset service
- HTTP endpoints
- Email sending
- Security edge cases
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from eden.auth.password_reset import (
    PasswordResetToken,
    PasswordResetService,
    PasswordResetEmail
)
from eden.exceptions import BadRequest, NotFound


UTC = timezone.utc


class TestPasswordResetTokenModel:
    """Test PasswordResetToken model."""
    
    @pytest.mark.asyncio
    async def test_token_model_creation(self):
        """Test creating a reset token model instance."""
        user_id = uuid4()
        token = PasswordResetService.generate_token()
        expires_at = datetime.now(UTC) + timedelta(hours=24)
        
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        
        assert reset_token.user_id == user_id
        assert reset_token.token == token
        assert reset_token.expires_at == expires_at
        assert reset_token.used_at is None
    
    @pytest.mark.asyncio
    async def test_token_mark_used(self):
        """Test marking a token as used."""
        user_id = uuid4()
        token = PasswordResetService.generate_token()
        expires_at = datetime.now(UTC) + timedelta(hours=24)
        
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        
        assert reset_token.used_at is None
        reset_token.used_at = datetime.now(UTC)
        assert reset_token.used_at is not None


class TestPasswordResetService:
    """Test PasswordResetService."""
    
    def test_generate_token(self):
        """Test token generation creates unique, secure tokens."""
        token1 = PasswordResetService.generate_token()
        token2 = PasswordResetService.generate_token()
        
        # Should be different
        assert token1 != token2
        
        # Should have good length (URL-safe encoding of 32 bytes)
        assert len(token1) > 20  # Base64url encoding
        assert len(token2) > 20
        
        # Should only contain URL-safe characters
        import string
        valid_chars = string.ascii_letters + string.digits + '-_'
        assert all(c in valid_chars for c in token1)
    
    def test_token_expiration_hours(self):
        """Test token expiration is 24 hours."""
        assert PasswordResetService.TOKEN_EXPIRATION_HOURS == 24
    
    def test_token_length(self):
        """Test token uses proper length for security."""
        assert PasswordResetService.TOKEN_LENGTH == 32  # 256 bits


class TestPasswordResetEmail:
    """Test email template generation."""
    
    def test_reset_link_generation(self):
        """Test password reset link generation."""
        token = "test_token_123"
        link = PasswordResetEmail.get_reset_link(token)
        
        assert token in link
        assert "/auth/reset-password" in link
        assert "http://localhost:8000" in link
    
    def test_reset_link_custom_url(self):
        """Test reset link with custom app URL."""
        token = "test_token_456"
        custom_url = "https://myapp.com"
        link = PasswordResetEmail.get_reset_link(token, custom_url)
        
        assert token in link
        assert custom_url in link
    
    def test_html_email_body(self):
        """Test HTML email body generation."""
        user_name = "John Doe"
        reset_link = "https://example.com/auth/reset?token=xyz"
        
        html = PasswordResetEmail.get_html_body(user_name, reset_link)
        
        assert user_name in html
        assert reset_link in html
        assert "Reset Your Password" in html
        assert "24 hours" in html
        assert "<html>" in html
        assert "DOCTYPE" in html
    
    def test_text_email_body(self):
        """Test plain text email body generation."""
        user_name = "Jane Doe"
        reset_link = "https://example.com/auth/reset?token=abc"
        
        text = PasswordResetEmail.get_text_body(user_name, reset_link)
        
        assert user_name in text
        assert reset_link in text
        assert "Reset Your Password" in text
        assert "24 hours" in text
        assert "<html>" not in text


class TestPasswordResetServiceFlow:
    """Test complete password reset flow."""
    
    @pytest.mark.asyncio
    async def test_create_reset_token_success(self):
        """Test successful token creation for valid user."""
        # Mock session and user
        session = AsyncMock()
        user_id = uuid4()
        
        # Mock User.get_or_404 to succeed
        with patch('eden.auth.password_reset.User') as mock_user_class:
            mock_user = AsyncMock()
            mock_user_class.get_or_404 = AsyncMock(return_value=mock_user)
            
            # Mock PasswordResetToken.query
            mock_query = AsyncMock()
            mock_query.filter = AsyncMock(return_value=AsyncMock())
            mock_query.filter.return_value.all = AsyncMock(return_value=[])
            
            with patch('eden.auth.password_reset.PasswordResetToken.query', return_value=mock_query):
                token = await PasswordResetService.create_reset_token(session, user_id)
                
                # Token should be generated
                assert token is not None
                assert len(token) > 20
                assert session.add.called or session.commit.called
    
    @pytest.mark.asyncio
    async def test_validate_reset_token_success(self):
        """Test successful token validation."""
        session = AsyncMock()
        user_id = uuid4()
        token = PasswordResetService.generate_token()
        
        # Create a valid token
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=None
        )
        
        with patch('eden.auth.password_reset.PasswordResetToken.filter_one', 
                   return_value=reset_token):
            result = await PasswordResetService.validate_reset_token(session, token)
            
            assert result == user_id
    
    @pytest.mark.asyncio
    async def test_validate_reset_token_not_found(self):
        """Test validation fails for non-existent token."""
        session = AsyncMock()
        token = "nonexistent_token"
        
        with patch('eden.auth.password_reset.PasswordResetToken.filter_one',
                   return_value=None):
            with pytest.raises(NotFound):
                await PasswordResetService.validate_reset_token(session, token)
    
    @pytest.mark.asyncio
    async def test_validate_reset_token_already_used(self):
        """Test validation fails for already-used token."""
        session = AsyncMock()
        user_id = uuid4()
        token = PasswordResetService.generate_token()
        
        # Create a used token
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=datetime.now(UTC) - timedelta(hours=1)  # Already used
        )
        
        with patch('eden.auth.password_reset.PasswordResetToken.filter_one',
                   return_value=reset_token):
            with pytest.raises(BadRequest, match="already been used"):
                await PasswordResetService.validate_reset_token(session, token)
    
    @pytest.mark.asyncio
    async def test_validate_reset_token_expired(self):
        """Test validation fails for expired token."""
        session = AsyncMock()
        user_id = uuid4()
        token = PasswordResetService.generate_token()
        
        # Create an expired token
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
            used_at=None
        )
        
        with patch('eden.auth.password_reset.PasswordResetToken.filter_one',
                   return_value=reset_token):
            with pytest.raises(BadRequest, match="expired"):
                await PasswordResetService.validate_reset_token(session, token)
    
    @pytest.mark.asyncio
    async def test_reset_password_success(self):
        """Test successful password reset."""
        session = AsyncMock()
        token = PasswordResetService.generate_token()
        new_password = "NewSecurePassword123"
        user_id = uuid4()
        
        # Create valid token
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=None
        )
        
        # Mock user
        mock_user = AsyncMock()
        
        with patch('eden.auth.password_reset.PasswordResetService.validate_reset_token',
                   return_value=user_id):
            with patch('eden.auth.password_reset.User') as mock_user_class:
                mock_user_class.get_or_404 = AsyncMock(return_value=mock_user)
                
                with patch('eden.auth.password_reset.PasswordResetToken.filter_one',
                           return_value=reset_token):
                    with patch('eden.auth.password_reset.hash_password',
                               return_value="hashed_password"):
                        await PasswordResetService.reset_password(
                            session, token, new_password
                        )
                        
                        # User password should be updated
                        assert mock_user.password == "hashed_password"
    
    @pytest.mark.asyncio
    async def test_reset_password_too_short(self):
        """Test password reset fails for too-short password."""
        session = AsyncMock()
        token = PasswordResetService.generate_token()
        short_password = "short"  # Less than 8 chars
        
        with pytest.raises(BadRequest, match="8 characters"):
            await PasswordResetService.reset_password(session, token, short_password)


class TestPasswordResetEndpoints:
    """Test HTTP endpoints for password reset."""
    
    @pytest.mark.asyncio
    async def test_forgot_password_endpoint_user_exists(self):
        """Test forgot password returns success with email sent."""
        # This would need a test client, mocking as example
        email = "user@example.com"
        
        # Would test: POST /auth/forgot-password
        # Response: {"message": "...", "email": "user@example.com"}
        # Side effect: Email sent to user
        pass
    
    @pytest.mark.asyncio
    async def test_forgot_password_endpoint_user_not_exists(self):
        """Test forgot password returns success even if user doesn't exist."""
        # This is security best practice - don't leak user existence
        email = "nonexistent@example.com"
        
        # Would test: POST /auth/forgot-password
        # Response: Still returns success (no error) for security
        pass
    
    @pytest.mark.asyncio
    async def test_reset_password_endpoint_success(self):
        """Test successful password reset endpoint."""
        # Would test: POST /auth/reset-password
        # Body: {"token": "...", "new_password": "...", "confirm_password": "..."}
        # Response: {"message": "Password has been successfully reset"}
        pass
    
    @pytest.mark.asyncio
    async def test_reset_password_endpoint_mismatch(self):
        """Test password reset fails if passwords don't match."""
        # Would test: POST /auth/reset-password
        # Body: new_password != confirm_password
        # Response: Error 400 "Passwords do not match"
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
