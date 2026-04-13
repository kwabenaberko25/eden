#!/usr/bin/env python
"""
Debug script to test password hashing and authentication flow.
"""
import sys
import asyncio
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_hashing():
    """Test password hashing."""
    from eden.auth.hashers import hash_password, check_password
    
    print("=== Testing Password Hashing ===\n")
    
    # Test 1: Hash and verify
    password = "demo_password"
    hashed = hash_password(password)
    print(f"Original: {password}")
    print(f"Hashed: {hashed[:50]}...\n")
    
    # Test 2: Check password
    is_valid = check_password(password, hashed)
    print(f"check_password('{password}', hash) = {is_valid}")
    
    is_invalid = check_password("wrong_password", hashed)
    print(f"check_password('wrong_password', hash) = {is_invalid}\n")
    
    if not is_valid:
        print("❌ PASSWORD HASHING BROKEN!")
        return False
    return True

async def test_user_creation():
    """Test user creation and password verification."""
    from pathlib import Path
    import os
    
    print("=== Testing User Creation ===\n")
    
    # Initialize database
    from eden.db import init_db
    from eden.auth.models import User
    from eden.app import Eden
    
    # Create in-memory database
    app = Eden(debug=True, secret_key="test")
    db = init_db("sqlite+aiosqlite:///:memory:", app=app)
    await db.connect(create_tables=True)
    
    # Create a test user
    async with db.session() as session:
        user = User(
            username="testuser",
            email="test@example.com",
            is_staff=True,
            is_superuser=True,
        )
        user.set_password("test_password_123")
        print(f"Created user: {user.email}")
        print(f"Password hash: {user.password_hash[:50]}...\n")
        
        session.add(user)
        await session.commit()
        
        # Reload to verify
        retrieved_user = await User.filter(email__iexact="test@example.com").first()
        print(f"Retrieved user: {retrieved_user.email}")
        print(f"is_staff: {retrieved_user.is_staff}")
        print(f"is_superuser: {retrieved_user.is_superuser}\n")
        
        # Test password verification
        from eden.auth.hashers import check_password
        is_valid = check_password("test_password_123", retrieved_user.password_hash)
        print(f"check_password('test_password_123', hash) = {is_valid}\n")
        
        if not is_valid:
            print("❌ PASSWORD VERIFICATION FAILED!")
            return False
        
        return True

async def test_authenticate():
    """Test the authenticate function."""
    print("=== Testing Authenticate Function ===\n")
    
    from eden.db import init_db
    from eden.auth.models import User
    from eden.auth.actions import authenticate
    from eden.app import Eden
    
    # Create in-memory database
    app = Eden(debug=True, secret_key="test")
    db = init_db("sqlite+aiosqlite:///:memory:", app=app)
    await db.connect(create_tables=True)
    
    # Create a test user
    async with db.session() as session:
        user = User(
            username="authtest",
            email="auth@test.com",
            is_staff=True,
            is_superuser=True,
        )
        user.set_password("auth_password_456")
        session.add(user)
        await session.commit()
    
    # Test authentication
    authenticated_user = await authenticate(email="auth@test.com", password="auth_password_456")
    
    if authenticated_user:
        print(f"✅ Authenticated user: {authenticated_user.email}")
        print(f"   is_staff: {authenticated_user.is_staff}")
        print(f"   is_superuser: {authenticated_user.is_superuser}\n")
        return True
    else:
        print("❌ Authentication failed!\n")
        return False

async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("AUTH SYSTEM DEBUG TEST")
    print("="*60 + "\n")
    
    results = []
    results.append(("Password Hashing", await test_hashing()))
    results.append(("User Creation", await test_user_creation()))
    results.append(("Authenticate", await test_authenticate()))
    
    print("="*60)
    print("RESULTS:")
    print("="*60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("✅ All tests passed!" if all_passed else "❌ Some tests failed!"))
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
