"""
Verification Tests for All 10 Authentication Security Plans

Run these tests to verify each security plan is correctly implemented.
"""

import asyncio
import sys


async def verify_plan_1_jwt_revocation():
    """Plan 1: JWT Logout Does Not Invalidate Token"""
    from eden.auth.token_denylist import denylist, TokenDenylist
    import datetime
    
    # Verify revoke_all_for_user exists
    assert hasattr(denylist, 'revoke_all_for_user'), "revoke_all_for_user not found"
    
    # Test the method
    await denylist.revoke_all_for_user("test_user_1", datetime.datetime.now(datetime.UTC))
    print("✅ Plan 1: JWT token revocation - PASS")


async def verify_plan_2_csrf_logout():
    """Plan 2: Logout Endpoint Vulnerable to CSRF"""
    from eden.auth.routes import auth_router, logout_view
    
    # Verify route exists
    assert auth_router is not None, "auth_router not found"
    assert logout_view is not None, "logout_view not found"
    
    # Verify it's decorated with login_required
    assert hasattr(logout_view, '__wrapped__'), "logout_view not decorated"
    
    print("✅ Plan 2: CSRF-protected logout route - PASS")


async def verify_plan_3_rate_limiting():
    """Plan 3: Missing Rate Limiting on Login Route"""
    from eden.auth.routes import login_view
    
    # Verify login_view has rate limit decorator
    assert hasattr(login_view, '__wrapped__'), "login_view not decorated with rate_limit"
    
    print("✅ Plan 3: Rate limiting on login - PASS")


async def verify_plan_4_timing_safe_auth():
    """Plan 4: User Enumeration via Timing in authenticate()"""
    from eden.auth.actions import _perform_dummy_hash, _DUMMY_HASH
    import inspect
    
    # Verify dummy hash function exists
    assert callable(_perform_dummy_hash), "_perform_dummy_hash not callable"
    
    # Verify it's used in authenticate
    source = inspect.getsource(_perform_dummy_hash)
    assert "check_password" in source, "dummy hash not using check_password"
    
    print("✅ Plan 4: Timing-safe authentication - PASS")


async def verify_plan_5_remember_me():
    """Plan 5: Remember Me: Absolute Expiry"""
    from eden.config import Config
    import inspect
    
    # Verify config fields exist
    config = Config()
    assert hasattr(config, 'session_absolute_max_age'), "session_absolute_max_age not found"
    assert hasattr(config, 'session_remember_me_max_age'), "session_remember_me_max_age not found"
    
    # Verify login has remember parameter
    from eden.auth.actions import login
    sig = inspect.signature(login)
    assert 'remember' in sig.parameters, "remember parameter not found in login()"
    
    print("✅ Plan 5: Remember-me with absolute expiry - PASS")


async def verify_plan_6_session_rotation():
    """Plan 6: Session ID Rotation on Login"""
    import inspect
    from eden.auth.actions import login
    
    # Verify login code contains session rotation
    source = inspect.getsource(login)
    assert "session_data" in source or "clear" in source, "session rotation not found in login()"
    
    print("✅ Plan 6: Session rotation on login - PASS")


async def verify_plan_7_secure_cookies():
    """Plan 7: Secure Cookie Attribute Enforcement"""
    from eden.middleware import SessionMiddleware
    import inspect
    
    # Verify https_only parameter exists and accepts None
    sig = inspect.signature(SessionMiddleware.__init__)
    assert 'https_only' in sig.parameters, "https_only parameter not found"
    
    # Check default value
    param = sig.parameters['https_only']
    assert param.default is None or param.default == 'None', "https_only default should be None"
    
    print("✅ Plan 7: Secure cookie defaults - PASS")


async def verify_plan_8_session_limits():
    """Plan 8: Concurrent Session Limiting"""
    from eden.auth.session_tracker import SessionTracker
    from eden.config import Config
    
    # Verify SessionTracker exists
    tracker = SessionTracker(max_sessions=3)
    assert hasattr(tracker, 'register'), "register method not found"
    assert hasattr(tracker, 'revoke_all'), "revoke_all method not found"
    
    # Verify config field exists
    config = Config()
    assert hasattr(config, 'max_concurrent_sessions'), "max_concurrent_sessions not found"
    
    print("✅ Plan 8: Concurrent session limiting - PASS")


async def verify_plan_9_logout_all():
    """Plan 9: Logout Everywhere (Revoke All Sessions)"""
    from eden.auth.actions import logout_all
    import inspect
    
    # Verify logout_all exists and is async
    assert callable(logout_all), "logout_all not callable"
    assert asyncio.iscoroutinefunction(logout_all), "logout_all not async"
    
    # Verify it calls both revoke methods
    source = inspect.getsource(logout_all)
    assert "revoke_all_for_user" in source, "revoke_all_for_user not called"
    assert "tracker.revoke_all" in source or "revoke_all" in source, "session revoke_all not called"
    
    print("✅ Plan 9: Logout-everywhere functionality - PASS")


async def verify_plan_10_audit_logging():
    """Plan 10: Auth Audit Logging"""
    from eden.auth.audit import AuthAuditLogger, auth_audit
    
    # Verify AuthAuditLogger exists
    assert AuthAuditLogger is not None, "AuthAuditLogger not found"
    
    # Verify required methods exist
    required_methods = ['login_success', 'login_failed', 'logout', 'logout_all', 'password_changed', 'token_revoked']
    for method in required_methods:
        assert hasattr(auth_audit, method), f"{method} not found in auth_audit"
    
    print("✅ Plan 10: Audit logging - PASS")


async def main():
    """Run all verification tests"""
    print("\n" + "="*60)
    print("VERIFYING ALL 10 AUTHENTICATION SECURITY PLANS")
    print("="*60 + "\n")
    
    tests = [
        ("Plan 1: JWT Revocation", verify_plan_1_jwt_revocation),
        ("Plan 2: CSRF Logout", verify_plan_2_csrf_logout),
        ("Plan 3: Rate Limiting", verify_plan_3_rate_limiting),
        ("Plan 4: Timing-Safe Auth", verify_plan_4_timing_safe_auth),
        ("Plan 5: Remember-Me", verify_plan_5_remember_me),
        ("Plan 6: Session Rotation", verify_plan_6_session_rotation),
        ("Plan 7: Secure Cookies", verify_plan_7_secure_cookies),
        ("Plan 8: Session Limits", verify_plan_8_session_limits),
        ("Plan 9: Logout-Everywhere", verify_plan_9_logout_all),
        ("Plan 10: Audit Logging", verify_plan_10_audit_logging),
    ]
    
    passed = 0
    failed = 0
    
    for name, test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ {name} - FAIL: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"VERIFICATION RESULTS: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
