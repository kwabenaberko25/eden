#!/usr/bin/env python
"""
Minimal test to reproduce the login redirect issue.
"""
import sys
import asyncio
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_login_redirect():
    """Test the complete login flow."""
    from eden.app import Eden
    from eden.db import init_db
    from eden.auth.models import User
    from eden.admin import PremiumAdmin
    import httpx
    
    print("=== Testing Admin Login Flow ===\n")
    
    # Initialize app
    app = Eden(debug=True, secret_key="test-secret-12345")
    db = init_db("sqlite+aiosqlite:///:memory:", app=app)
    app.state.db = db
    
    # Setup database
    await db.connect(create_tables=True)
    
    # Create demo user
    async with db.session() as session:
        user = User(
            username="demo",
            email="demo@test.com",
            is_staff=True,
            is_superuser=True,
        )
        user.set_password("demo_password")
        session.add(user)
        await session.commit()
        print(f"✓ Created user: demo@test.com")
        print(f"  is_staff: True")
        print(f"  is_superuser: True\n")
    
    # Setup admin site
    admin = PremiumAdmin(app=app, prefix="/admin")
    app.setup_defaults()
    
    # Use test client
    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        # Step 1: GET login page
        print("Step 1: GET /admin/login")
        resp = await client.get("/admin/login")
        print(f"  Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"  ❌ Expected 200, got {resp.status_code}\n")
            return False
        
        # Extract CSRF token
        import re
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
        if not match:
            print("  ❌ CSRF token not found\n")
            return False
        
        csrf_token = match.group(1)
        print(f"  ✓ CSRF token: {csrf_token[:20]}...\n")
        
        # Step 2: POST login
        print("Step 2: POST /admin/login with correct credentials")
        resp = await client.post(
            "/admin/login",
            data={
                "email": "demo@test.com",
                "password": "demo_password",
                "csrf_token": csrf_token,
            }
        )
        print(f"  Status: {resp.status_code}")
        print(f"  Redirect: {resp.headers.get('location', 'N/A')}")
        
        # Check the response
        if resp.status_code == 303:
            location = resp.headers.get('location')
            if location == '/admin/':
                print(f"  ✓ Redirected to /admin/\n")
                return True
            else:
                print(f"  ❌ Redirected to {location} instead of /admin/\n")
                return False
        else:
            print(f"  ❌ Expected 303, got {resp.status_code}")
            print(f"  Response: {resp.text[:200]}\n")
            return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_login_redirect())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
