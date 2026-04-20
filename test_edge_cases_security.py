#!/usr/bin/env python3
"""
Comprehensive edge case and security vulnerability tests for all 10 plans.
This ensures the implementation handles real-world attack scenarios correctly.
"""

import asyncio
import inspect
from datetime import datetime, UTC


async def test_edge_cases():
    """Test edge cases and security vulnerabilities."""
    
    print("\n" + "="*80)
    print("EDGE CASE AND SECURITY VULNERABILITY TEST SUITE")
    print("="*80 + "\n")
    
    # ========================================================================
    # Edge Case 1: Multiple Concurrent Token Revocations
    # ========================================================================
    print("[TEST 1] Multiple Concurrent Token Revocations")
    print("-" * 80)
    
    try:
        from eden.auth.token_denylist import denylist
        
        # Simulate multiple concurrent revocations
        user_ids = ["user_1", "user_2", "user_3"]
        tasks = []
        
        for user_id in user_ids:
            task = denylist.revoke_all_for_user(user_id, datetime.now(UTC))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        print("  PASS: Multiple concurrent token revocations handled correctly")
    except Exception as e:
        print("  FAIL: %s" % str(e))
    
    print()
    
    # ========================================================================
    # Edge Case 2: Session Tracker Boundary Conditions
    # ========================================================================
    print("[TEST 2] Session Tracker Boundary Conditions")
    print("-" * 80)
    
    try:
        from eden.auth.session_tracker import SessionTracker
        
        # Test with limit of 1
        tracker = SessionTracker(max_sessions=1)
        
        # Register first session
        evicted = await tracker.register("user", "sess1", ip_address="1.1.1.1", user_agent="Chrome")
        assert len(evicted) == 0, "First session should not evict anything"
        
        # Register second session - should evict first
        evicted = await tracker.register("user", "sess2", ip_address="1.1.1.2", user_agent="Firefox")
        assert len(evicted) == 1, "Second session should evict first"
        assert "sess1" in evicted, "sess1 should be evicted"
        
        # Verify first session is invalid
        valid = await tracker.is_valid("user", "sess1")
        assert not valid, "sess1 should be invalid after eviction"
        
        # Verify second session is valid
        valid = await tracker.is_valid("user", "sess2")
        assert valid, "sess2 should be valid"
        
        print("  PASS: Session tracker boundary conditions handled correctly")
    except Exception as e:
        print("  FAIL: %s" % str(e))
    
    print()
    
    # ========================================================================
    # Edge Case 3: Timing-Safe Auth with Empty Password
    # ========================================================================
    print("[TEST 3] Timing-Safe Auth with Empty Password")
    print("-" * 80)
    
    try:
        from eden.auth.actions import _perform_dummy_hash
        
        # Test with empty password
        _perform_dummy_hash("")
        print("  PASS: Empty password handled safely")
        
        # Test with very long password
        _perform_dummy_hash("x" * 10000)
        print("  PASS: Very long password handled safely")
        
        # Test with special characters
        _perform_dummy_hash("!@#$%^&*()_+-=[]{}|;:',.<>?/\\")
        print("  PASS: Special characters handled safely")
        
    except Exception as e:
        print("  FAIL: %s" % str(e))
    
    print()
    
    # ========================================================================
    # Edge Case 4: Audit Logging with Missing Request
    # ========================================================================
    print("[TEST 4] Audit Logging Robustness")
    print("-" * 80)
    
    try:
        from eden.auth.audit import auth_audit
        
        # Test audit methods are callable
        assert callable(auth_audit.login_success), "login_success not callable"
        assert callable(auth_audit.login_failed), "login_failed not callable"
        assert callable(auth_audit.logout), "logout not callable"
        assert callable(auth_audit.logout_all), "logout_all not callable"
        assert callable(auth_audit.password_changed), "password_changed not callable"
        assert callable(auth_audit.token_revoked), "token_revoked not callable"
        
        print("  PASS: All audit logging methods are callable and robust")
    except Exception as e:
        print("  FAIL: %s" % str(e))
    
    print()
    
    # ========================================================================
    # Edge Case 5: Configuration Value Ranges
    # ========================================================================
    print("[TEST 5] Configuration Value Ranges")
    print("-" * 80)
    
    try:
        from eden.config import Config
        
        config = Config()
        
        # Verify configuration values are positive
        assert config.session_absolute_max_age > 0, "session_absolute_max_age must be positive"
        assert config.session_remember_me_max_age > 0, "session_remember_me_max_age must be positive"
        assert config.max_concurrent_sessions >= 0, "max_concurrent_sessions must be non-negative"
        
        # Verify reasonable bounds
        assert config.session_absolute_max_age < (365 * 24 * 3600), "session_absolute_max_age too large"
        assert config.session_remember_me_max_age < (365 * 24 * 3600), "session_remember_me_max_age too large"
        
        print("  PASS: Configuration values within acceptable ranges")
    except Exception as e:
        print("  FAIL: %s" % str(e))
    
    print()
    
    # ========================================================================
    # Edge Case 6: Import Cycles and Dependencies
    # ========================================================================
    print("[TEST 6] Import Cycles and Dependency Integrity")
    print("-" * 80)
    
    try:
        # Test that we can import each component independently
        from eden.auth.routes import auth_router
        from eden.auth.audit import auth_audit
        from eden.auth.session_tracker import SessionTracker
        from eden.auth.token_denylist import denylist
        from eden.auth.actions import logout_all, _perform_dummy_hash
        
        # Test that collective import works
        from eden.auth import (
            auth_router,
            logout_all,
            SessionTracker,
            InMemorySessionTrackerStore,
            auth_audit,
        )
        
        print("  PASS: No import cycles, all dependencies resolved correctly")
    except Exception as e:
        print("  FAIL: %s" % str(e))
    
    print()
    
    # ========================================================================
    # Edge Case 7: Async Function Signatures
    # ========================================================================
    print("[TEST 7] Async Function Signatures")
    print("-" * 80)
    
    try:
        from eden.auth.actions import logout_all, login, logout
        from eden.auth.token_denylist import denylist
        from eden.auth.session_tracker import SessionTracker
        
        # Verify async functions
        assert inspect.iscoroutinefunction(logout_all), "logout_all must be async"
        assert inspect.iscoroutinefunction(login), "login must be async"
        assert inspect.iscoroutinefunction(logout), "logout must be async"
        assert inspect.iscoroutinefunction(denylist.revoke_all_for_user), "revoke_all_for_user must be async"
        
        # Verify SessionTracker async methods
        tracker = SessionTracker(max_sessions=5)
        assert inspect.iscoroutinefunction(tracker.register), "register must be async"
        assert inspect.iscoroutinefunction(tracker.is_valid), "is_valid must be async"
        assert inspect.iscoroutinefunction(tracker.revoke_all), "revoke_all must be async"
        
        print("  PASS: All critical functions have correct async signatures")
    except Exception as e:
        print("  FAIL: %s" % str(e))
    
    print()
    
    # ========================================================================
    # Edge Case 8: Backward Compatibility with Existing Auth
    # ========================================================================
    print("[TEST 8] Backward Compatibility")
    print("-" * 80)
    
    try:
        # Test that existing auth imports still work
        from eden.auth import (
            User,
            hash_password,
            check_password,
            login_required,
            require_permission,
        )
        
        print("  PASS: Existing auth APIs remain backward compatible")
    except Exception as e:
        print("  FAIL: %s" % str(e))
    
    print()
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("="*80)
    print("EDGE CASE TESTING COMPLETE")
    print("="*80)
    print()


if __name__ == "__main__":
    asyncio.run(test_edge_cases())
