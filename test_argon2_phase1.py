#!/usr/bin/env python
"""Test Phase 1 Argon2 implementation."""
import sys
sys.path.insert(0, 'C:\\PROJECTS\\eden-framework')

from eden.admin.auth import AdminAuthManager, AdminRole

def test_argon2_hashing():
    """Test Argon2 password hashing."""
    auth = AdminAuthManager(secret_key="test-secret")
    
    # Test 1: Register user with valid password
    print("✓ Test 1: Register user with valid password")
    user = auth.register_user("admin", "ValidPassword123!", AdminRole.ADMIN)
    assert user.username == "admin"
    assert user.role == AdminRole.ADMIN
    assert len(user.password_history) == 1
    print(f"  User registered: {user.username} (role: {user.role.value})")
    print(f"  Password hash starts with: {user.password_hash[:20]}...")
    
    # Test 2: Verify password
    print("\n✓ Test 2: Verify password with Argon2")
    is_valid = auth.verify_password("ValidPassword123!", user.password_hash)
    assert is_valid, "Password verification failed"
    print(f"  Password verification: {is_valid}")
    
    # Test 3: Reject weak passwords
    print("\n✓ Test 3: Reject weak passwords")
    weak_passwords = [
        ("short", "too short"),
        ("noupppercase1!", "no uppercase"),
        ("NOLOWERCASE1!", "no lowercase"),
        ("NoNumbers!", "no digits"),
        ("NoSpecial123", "no special chars"),
    ]
    for pwd, reason in weak_passwords:
        errors = auth.validate_password_strength(pwd)
        assert len(errors) > 0, f"Should reject '{pwd}' ({reason})"
        print(f"  ✗ '{pwd}' rejected: {errors[0]}")
    
    # Test 4: Password history
    print("\n✓ Test 4: Password history and reuse prevention")
    auth.change_password("admin", "ValidPassword123!", "NewPassword456!")
    assert len(user.password_history) == 2
    print(f"  Password changed, history size: {len(user.password_history)}")
    
    # Try to reuse old password
    try:
        auth.change_password("admin", "NewPassword456!", "ValidPassword123!")
        assert False, "Should reject reused password"
    except ValueError as e:
        print(f"  ✓ Reuse prevented: {e}")
    
    # Test 5: Login with lockout
    print("\n✓ Test 5: Login attempt tracking")
    auth2 = AdminAuthManager(
        secret_key="test-secret",
        max_login_attempts=3,
        lockout_minutes=1
    )
    auth2.register_user("user1", "ValidPassword123!", AdminRole.VIEWER)
    
    # Try wrong password 3 times
    for i in range(3):
        try:
            auth2.login("user1", "WrongPassword!")
        except:
            pass
    
    user1 = auth2.get_user("user1")
    assert user1.failed_login_attempts == 3
    assert user1.locked_until is not None
    print(f"  Failed attempts: {user1.failed_login_attempts}")
    print(f"  Account locked until: {user1.locked_until}")
    
    # Test 6: Successful login
    print("\n✓ Test 6: Successful login clears attempts")
    token = auth2.login("user1", "ValidPassword123!")
    assert token is not None
    user1 = auth2.get_user("user1")
    assert user1.failed_login_attempts == 0
    assert user1.locked_until is None
    print(f"  Login successful, token: {token[:30]}...")
    print(f"  Failed attempts reset: {user1.failed_login_attempts}")
    
    print("\n" + "="*60)
    print("✓ All Phase 1 tests passed!")
    print("="*60)

if __name__ == "__main__":
    try:
        test_argon2_hashing()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
