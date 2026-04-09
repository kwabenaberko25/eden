#!/usr/bin/env python
"""
Comprehensive test suite for Eden Admin Authentication Enhancement.

Tests all three phases:
- Phase 1: Argon2 password hashing
- Phase 2: Email functionality & password reset
- Phase 3: TOTP 2FA

Run with: python test_admin_complete.py
"""

import sys
import asyncio
sys.path.insert(0, 'C:\\PROJECTS\\eden-framework')

from datetime import datetime, timedelta
from eden.admin.auth import AdminAuthManager, AdminRole
from eden.admin.email import EmailService, EmailConfig, PasswordResetTokenManager
from eden.admin.totp import TOTPManager, TOTPSecretManager


class TestSuite:
    """Complete test suite."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def assert_true(self, condition, message):
        if condition:
            self.passed += 1
            print(f"  ✓ {message}")
        else:
            self.failed += 1
            print(f"  ✗ {message}")
            raise AssertionError(message)
    
    def assert_equal(self, actual, expected, message):
        if actual == expected:
            self.passed += 1
            print(f"  ✓ {message}")
        else:
            self.failed += 1
            print(f"  ✗ {message}: expected {expected}, got {actual}")
            raise AssertionError(f"{message}: expected {expected}, got {actual}")
    
    def assert_in(self, item, container, message):
        if item in container:
            self.passed += 1
            print(f"  ✓ {message}")
        else:
            self.failed += 1
            print(f"  ✗ {message}")
            raise AssertionError(message)
    
    def test(self, name):
        """Decorator for test methods."""
        def decorator(func):
            self.tests.append((name, func))
            return func
        return decorator
    
    async def run_all(self):
        """Run all tests."""
        print("=" * 70)
        print("Eden Admin Authentication Enhancement - Comprehensive Test Suite")
        print("=" * 70)
        
        for test_name, test_func in self.tests:
            print(f"\n{test_name}")
            print("-" * 70)
            try:
                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
            except Exception as e:
                self.failed += 1
                print(f"  ✗ Test failed with exception: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 70)
        print(f"Results: {self.passed} passed, {self.failed} failed")
        print("=" * 70)
        
        return self.failed == 0


suite = TestSuite()


# =====================================================================
# Phase 1: Argon2 Password Hashing Tests
# =====================================================================

@suite.test("Phase 1.1: Argon2 Password Hashing & Complexity")
def test_argon2_hashing():
    auth = AdminAuthManager(secret_key="test-secret")
    
    # Test valid password registration
    user = auth.register_user("admin", "ValidPassword123!", AdminRole.ADMIN)
    suite.assert_equal(user.username, "admin", "User registered with correct username")
    suite.assert_true(len(user.password_hash) > 20, "Password hash generated (Argon2)")
    suite.assert_true(user.password_hash.startswith("$argon2"), "Hash is Argon2 format")
    suite.assert_equal(len(user.password_history), 1, "Password history initialized")
    
    # Test password verification
    verified = auth.verify_password("ValidPassword123!", user.password_hash)
    suite.assert_true(verified, "Password verification successful")
    
    # Test invalid password
    not_verified = auth.verify_password("WrongPassword!", user.password_hash)
    suite.assert_true(not not_verified, "Invalid password rejected")


@suite.test("Phase 1.2: Password Complexity Requirements")
def test_password_complexity():
    auth = AdminAuthManager(secret_key="test-secret")
    
    # Test too short
    errors = auth.validate_password_strength("Short1!")
    suite.assert_true(len(errors) > 0, "Too short password rejected")
    suite.assert_in("12 characters", errors[0], "Error message mentions minimum length")
    
    # Test no uppercase
    errors = auth.validate_password_strength("nouppercase123!")
    suite.assert_true(len(errors) > 0, "No uppercase rejected")
    
    # Test no lowercase
    errors = auth.validate_password_strength("NOLOWERCASE123!")
    suite.assert_true(len(errors) > 0, "No lowercase rejected")
    
    # Test no digits
    errors = auth.validate_password_strength("NoDigits!@#")
    suite.assert_true(len(errors) > 0, "No digits rejected")
    
    # Test no special characters
    errors = auth.validate_password_strength("NoSpecial123")
    suite.assert_true(len(errors) > 0, "No special chars rejected")
    
    # Test valid password
    errors = auth.validate_password_strength("ValidPassword123!")
    suite.assert_equal(len(errors), 0, "Valid password accepted")


@suite.test("Phase 1.3: Password History & Reuse Prevention")
def test_password_history():
    auth = AdminAuthManager(secret_key="test-secret")
    auth.register_user("user1", "Password123!", AdminRole.VIEWER)
    
    # Change password
    success = auth.change_password("user1", "Password123!", "NewPassword456!")
    suite.assert_true(success, "Password changed successfully")
    
    user = auth.get_user("user1")
    suite.assert_equal(len(user.password_history), 2, "Password history has 2 entries")
    
    # Try to reuse old password
    try:
        auth.change_password("user1", "NewPassword456!", "Password123!")
        suite.assert_true(False, "Should reject reused password")
    except ValueError as e:
        suite.assert_true("reuse" in str(e).lower(), "Reuse prevention message shown")


@suite.test("Phase 1.4: Login Attempt Tracking & Lockout")
def test_login_lockout():
    auth = AdminAuthManager(
        secret_key="test-secret",
        max_login_attempts=3,
        lockout_minutes=1
    )
    auth.register_user("locked_user", "Password123!", AdminRole.VIEWER)
    
    # Try failed logins
    for i in range(3):
        try:
            auth.login("locked_user", "WrongPassword!")
        except:
            pass
    
    user = auth.get_user("locked_user")
    suite.assert_equal(user.failed_login_attempts, 3, "Failed attempts counted")
    suite.assert_true(user.locked_until is not None, "Account locked")
    
    # Try to login while locked
    try:
        auth.login("locked_user", "Password123!")
        suite.assert_true(False, "Should reject login while locked")
    except:
        pass
    
    # Successfully login resets attempts
    user.locked_until = datetime.utcnow() - timedelta(minutes=2)  # Simulate unlock
    token = auth.login("locked_user", "Password123!")
    suite.assert_true(token is not None, "Login successful after unlock")
    
    user = auth.get_user("locked_user")
    suite.assert_equal(user.failed_login_attempts, 0, "Failed attempts reset")


# =====================================================================
# Phase 2: Email & Password Reset Tests
# =====================================================================

@suite.test("Phase 2.1: Password Reset Token Management")
def test_password_reset_tokens():
    manager = PasswordResetTokenManager(expiry_hours=24)
    
    # Create token
    token_obj = manager.create_token("testuser")
    suite.assert_true(len(token_obj.token) > 20, "Token generated")
    suite.assert_true(not token_obj.is_expired(), "Token not expired")
    
    # Verify token
    verified_token = manager.verify_token(token_obj.token)
    suite.assert_true(verified_token is not None, "Token verified")
    suite.assert_equal(verified_token.username, "testuser", "Correct username in token")
    
    # Consume token
    username = manager.consume_token(token_obj.token)
    suite.assert_equal(username, "testuser", "Token consumed and username returned")
    
    # Verify token is gone
    verified_again = manager.verify_token(token_obj.token)
    suite.assert_true(verified_again is None, "Token cannot be reused")


@suite.test("Phase 2.2: Expired Token Cleanup")
def test_token_expiry():
    manager = PasswordResetTokenManager(expiry_hours=0)  # Immediately expired
    
    token_obj = manager.create_token("testuser")
    suite.assert_true(token_obj.is_expired(), "Token is expired")
    
    # Try to verify expired token
    verified = manager.verify_token(token_obj.token)
    suite.assert_true(verified is None, "Expired token rejected")
    suite.assert_true(token_obj.token not in manager.tokens, "Expired token cleaned up")


@suite.test("Phase 2.3: Password Reset with Validation")
def test_password_reset_flow():
    auth = AdminAuthManager(secret_key="test-secret")
    auth.register_user("resetuser", "OldPassword123!", AdminRole.VIEWER)
    
    # Initiate reset
    token = auth.initiate_password_reset("resetuser")
    suite.assert_true(len(token) > 20, "Reset token generated")
    
    # Verify token
    username = auth.verify_reset_token(token)
    suite.assert_equal(username, "resetuser", "Token verified")
    
    # Reset password with invalid token
    try:
        auth.reset_password_with_token("invalid-token", "NewPassword456!")
        suite.assert_true(False, "Should reject invalid token")
    except ValueError:
        pass
    
    # Reset password with valid token
    success = auth.reset_password_with_token(token, "NewPassword456!")
    suite.assert_true(success, "Password reset successful")
    
    # Verify new password works
    token = auth.login("resetuser", "NewPassword456!")
    suite.assert_true(token is not None, "Login with new password successful")


@suite.test("Phase 2.4: Email Service Configuration")
async def test_email_service():
    config = EmailConfig(
        smtp_host="smtp.example.com",
        smtp_port=587,
        sender_email="admin@example.com",
        sender_name="Eden Admin"
    )
    
    service = EmailService(config)
    suite.assert_equal(service.config.smtp_host, "smtp.example.com", "Email config set")
    
    # Test email sending (logging mode)
    success = await service.send_email(
        "user@example.com",
        "Test Email",
        "<p>Test body</p>"
    )
    suite.assert_true(success, "Email sent (logged)")


# =====================================================================
# Phase 3: TOTP 2FA Tests
# =====================================================================

@suite.test("Phase 3.1: TOTP Secret Generation & QR Code")
def test_totp_generation():
    totp_mgr = TOTPManager(issuer="Eden Test")
    
    secret, uri = totp_mgr.generate_secret("testuser")
    suite.assert_true(len(secret) > 10, "Secret generated")
    suite.assert_true(secret.replace("=", "").isalnum(), "Secret is base32")
    suite.assert_true("otpauth://" in uri, "Provisioning URI contains otpauth")
    suite.assert_true("testuser" in uri, "URI contains username")
    suite.assert_true("issuer=" in uri, "URI contains issuer")


@suite.test("Phase 3.2: TOTP Code Verification")
def test_totp_verification():
    totp_mgr = TOTPManager(issuer="Eden Test")
    secret, _ = totp_mgr.generate_secret("testuser")
    
    # Get current code
    code, seconds_remaining = totp_mgr.get_current_code(secret)
    suite.assert_equal(len(code), 6, "Code is 6 digits")
    suite.assert_true(code.isdigit(), "Code contains only digits")
    suite.assert_true(0 < seconds_remaining <= 30, "Seconds remaining in valid range")
    
    # Verify same code
    verified = totp_mgr.verify(secret, code)
    suite.assert_true(verified, "Current code verified")
    
    # Reject wrong code
    wrong_verified = totp_mgr.verify(secret, "000000")
    suite.assert_true(not wrong_verified, "Wrong code rejected")


@suite.test("Phase 3.3: Backup Code Generation")
def test_backup_codes():
    codes = TOTPManager.generate_backup_codes(count=5, length=8)
    
    suite.assert_equal(len(codes), 5, "Correct number of codes generated")
    for code in codes:
        suite.assert_true("-" in code, f"Code formatted with dash: {code}")
        suite.assert_true(len(code) == 9, "Code has correct length with dash")


@suite.test("Phase 3.4: TOTP Secret Manager")
def test_totp_manager():
    manager = TOTPSecretManager(issuer="Eden Test")
    
    # Setup 2FA
    uri, backup_codes = manager.setup_2fa("setupuser")
    suite.assert_true("otpauth://" in uri, "Provisioning URI generated")
    suite.assert_equal(len(backup_codes), 10, "10 backup codes generated")
    
    # Get TOTP secret
    secret = manager.get_totp_secret("setupuser")
    suite.assert_true(secret is not None, "Secret exists")
    suite.assert_true(not secret.verified, "Secret not yet verified")
    
    # Verify setup
    # Generate valid code
    totp_mgr = TOTPManager()
    current_code, _ = totp_mgr.get_current_code(secret.secret)
    
    verified = manager.verify_setup("setupuser", current_code)
    suite.assert_true(verified, "Setup verification successful")
    
    # Check secret now verified
    secret = manager.get_totp_secret("setupuser")
    suite.assert_true(secret.verified, "Secret is verified")
    suite.assert_true(secret.enabled_at is not None, "Enabled timestamp set")


@suite.test("Phase 3.5: Backup Code Usage")
def test_backup_code_usage():
    manager = TOTPSecretManager()
    
    uri, backup_codes = manager.setup_2fa("backupuser")
    
    # Verify setup with valid TOTP code
    totp_mgr = TOTPManager()
    current_code, _ = totp_mgr.get_current_code(manager.get_totp_secret("backupuser").secret)
    manager.verify_setup("backupuser", current_code)
    
    # Use backup code
    test_code = backup_codes[0].replace("-", "")
    used = manager.use_backup_code("backupuser", test_code)
    suite.assert_true(used, "Backup code accepted")
    
    # Try to reuse same code
    reused = manager.use_backup_code("backupuser", test_code)
    suite.assert_true(not reused, "Backup code cannot be reused")
    
    # Use another code
    test_code2 = backup_codes[1].replace("-", "")
    used2 = manager.use_backup_code("backupuser", test_code2)
    suite.assert_true(used2, "Second backup code accepted")


@suite.test("Phase 3.6: 2FA in Admin Auth Manager")
def test_auth_manager_2fa():
    auth = AdminAuthManager(secret_key="test-secret")
    auth.register_user("twofa_user", "Password123!", AdminRole.VIEWER)
    
    # Setup 2FA
    uri, backup_codes = auth.setup_2fa("twofa_user")
    suite.assert_true("otpauth://" in uri, "Provisioning URI generated")
    
    user = auth.get_user("twofa_user")
    suite.assert_true(not user.totp_enabled, "2FA not yet enabled")
    
    # Verify setup
    totp_secret_mgr = auth._get_totp_manager()
    totp_mgr = TOTPManager()
    secret_obj = totp_secret_mgr.get_totp_secret("twofa_user")
    current_code, _ = totp_mgr.get_current_code(secret_obj.secret)
    
    verified = auth.verify_2fa_setup("twofa_user", current_code)
    suite.assert_true(verified, "2FA setup verified")
    
    user = auth.get_user("twofa_user")
    suite.assert_true(user.totp_enabled, "2FA is enabled")
    
    # Verify TOTP code for login
    current_code, _ = totp_mgr.get_current_code(secret_obj.secret)
    verified = auth.verify_2fa_code("twofa_user", current_code)
    suite.assert_true(verified, "TOTP code verified for login")
    
    # Disable 2FA
    disabled = auth.disable_2fa("twofa_user")
    suite.assert_true(disabled, "2FA disabled")
    
    user = auth.get_user("twofa_user")
    suite.assert_true(not user.totp_enabled, "2FA is now disabled")


async def main():
    """Run all tests."""
    success = await suite.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
