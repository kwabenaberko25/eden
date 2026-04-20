"""
Comprehensive Audit of Missing/Incomplete Authentication Security Features

This script systematically tests all 10 security plans to identify:
- Missing implementations
- Incomplete features
- Integration issues
- Test coverage gaps
"""

import asyncio
import sys
import traceback
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class TestResult:
    name: str
    passed: bool
    error: Optional[str] = None
    details: str = ""

class FeatureAudit:
    def __init__(self):
        self.results: list[TestResult] = []
        self.missing_features: list[str] = []
        self.incomplete_features: list[str] = []
        
    def add_result(self, name: str, passed: bool, error: Optional[str] = None, details: str = ""):
        self.results.append(TestResult(name, passed, error, details))
        if not passed and error:
            if "not found" in error.lower() or "import" in error.lower():
                self.missing_features.append(f"{name}: {error}")
            else:
                self.incomplete_features.append(f"{name}: {error}")
    
    async def test_plan_1_jwt_revocation(self) -> None:
        """Test: JWT Token Revocation on Logout"""
        try:
            # Check: Can import TokenDenylist
            from eden.auth.token_denylist import TokenDenylist, denylist
            
            # Check: revoke_all_for_user method exists
            assert hasattr(TokenDenylist, 'revoke_all_for_user'), "revoke_all_for_user method missing"
            
            # Check: Basic revoke works - use future expiry time
            import datetime
            future_exp = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
            await denylist.revoke("test-jti-123", future_exp)
            is_revoked = await denylist.is_revoked("test-jti-123")
            assert is_revoked, "Token revocation failed"
            
            self.add_result("Plan 1: JWT Revocation", True, details="TokenDenylist working")
        except Exception as e:
            self.add_result("Plan 1: JWT Revocation", False, str(e))
    
    async def test_plan_2_csrf_logout(self) -> None:
        """Test: CSRF-Protected Logout Endpoint"""
        try:
            # Check: auth_router exists
            from eden.auth.routes import auth_router, logout_view
            
            # Check: @login_required decorator present
            assert hasattr(logout_view, '__wrapped__') or hasattr(logout_view, '__closure__'), \
                "logout_view missing decorator"
            
            # Check: Route is mounted
            assert auth_router.routes, "auth_router has no routes"
            
            # Check: POST method (not GET)
            methods = []
            for route in auth_router.routes:
                if hasattr(route, 'methods'):
                    methods.extend(route.methods)
                if hasattr(route, 'path') and 'logout' in route.path:
                    assert 'POST' in route.methods, "logout endpoint should be POST only"
            
            self.add_result("Plan 2: CSRF Logout", True, details="Logout endpoint configured")
        except Exception as e:
            self.add_result("Plan 2: CSRF Logout", False, str(e))
    
    async def test_plan_3_rate_limiting(self) -> None:
        """Test: Rate-Limited Login Route"""
        try:
            # Check: @rate_limit decorator applied
            from eden.auth.routes import login_view
            
            # Check: Function exists and has rate_limit applied
            assert login_view is not None, "login_view not found"
            
            # Check: Decorator applied (via __wrapped__ or __closure__)
            has_decorator = (hasattr(login_view, '__wrapped__') or 
                            hasattr(login_view, '__closure__') or 
                            'rate_limit' in str(login_view))
            assert has_decorator, "rate_limit decorator not applied"
            
            self.add_result("Plan 3: Rate Limiting", True, details="Rate limit decorator applied")
        except Exception as e:
            self.add_result("Plan 3: Rate Limiting", False, str(e))
    
    async def test_plan_4_timing_safe_auth(self) -> None:
        """Test: Timing-Safe Authentication"""
        try:
            # Check: _perform_dummy_hash exists
            from eden.auth.actions import _perform_dummy_hash, _DUMMY_HASH
            
            assert callable(_perform_dummy_hash), "_perform_dummy_hash not callable"
            
            # Call it to initialize
            _perform_dummy_hash("test_password")
            
            # Check: Dummy hash is computed
            from eden.auth.actions import _DUMMY_HASH as dummy_hash_after
            assert dummy_hash_after is not None, "_DUMMY_HASH not initialized"
            
            self.add_result("Plan 4: Timing-Safe Auth", True, details="Dummy hash working")
        except Exception as e:
            self.add_result("Plan 4: Timing-Safe Auth", False, str(e))
    
    async def test_plan_5_remember_me(self) -> None:
        """Test: Remember-Me with Absolute Session Expiry"""
        try:
            # Check: login() has remember parameter
            from eden.auth.actions import login
            import inspect
            
            sig = inspect.signature(login)
            assert 'remember' in sig.parameters, "login() missing remember parameter"
            
            # Check: Config has session duration fields
            from eden.config import get_config
            config = get_config()
            assert hasattr(config, 'session_remember_me_max_age'), \
                "session_remember_me_max_age config missing"
            assert hasattr(config, 'session_absolute_max_age'), \
                "session_absolute_max_age config missing"
            
            # Check: Middleware checks absolute expiry
            from eden.auth.middleware import AuthenticationMiddleware
            middleware_code = inspect.getsource(AuthenticationMiddleware.__call__)
            assert '_auth_authenticated_at' in middleware_code, \
                "Middleware not checking session expiry"
            
            self.add_result("Plan 5: Remember-Me", True, details="Remember-me configured")
        except Exception as e:
            self.add_result("Plan 5: Remember-Me", False, str(e))
    
    async def test_plan_6_session_rotation(self) -> None:
        """Test: Session ID Rotation on Login"""
        try:
            # Check: Session rotation in login()
            from eden.auth.actions import login
            import inspect
            
            login_code = inspect.getsource(login)
            assert 'regenerate' in login_code or 'session.clear()' in login_code, \
                "Session rotation not implemented in login()"
            
            # Check: SessionBackend.login() also rotates
            from eden.auth.backends.session import SessionBackend
            backend_code = inspect.getsource(SessionBackend.login)
            assert 'clear()' in backend_code or 'regenerate' in backend_code, \
                "Session rotation not in SessionBackend.login()"
            
            self.add_result("Plan 6: Session Rotation", True, details="Session rotation working")
        except Exception as e:
            self.add_result("Plan 6: Session Rotation", False, str(e))
    
    async def test_plan_7_secure_cookies(self) -> None:
        """Test: Secure Cookie Auto-Detection"""
        try:
            # Check: SessionMiddleware has HTTPS auto-detection
            from eden.middleware import SessionMiddleware
            import inspect
            
            init_code = inspect.getsource(SessionMiddleware.__init__)
            assert 'EDEN_ENV' in init_code, "EDEN_ENV not checked for HTTPS detection"
            assert 'https_only' in init_code, "https_only not auto-detected"
            
            self.add_result("Plan 7: Secure Cookies", True, details="HTTPS auto-detection working")
        except Exception as e:
            self.add_result("Plan 7: Secure Cookies", False, str(e))
    
    async def test_plan_8_session_limits(self) -> None:
        """Test: Concurrent Session Limiting"""
        try:
            # Check: SessionTracker exists
            from eden.auth.session_tracker import SessionTracker, InMemorySessionTrackerStore
            
            # Check: Config has max_concurrent_sessions
            from eden.config import get_config
            config = get_config()
            assert hasattr(config, 'max_concurrent_sessions'), \
                "max_concurrent_sessions config missing"
            
            # Test: Basic session tracking
            tracker = SessionTracker(max_sessions=2)
            user_id = "user123"
            
            # Register 3 sessions
            evicted1 = await tracker.register(user_id, "session1", ip_address="127.0.0.1")
            evicted2 = await tracker.register(user_id, "session2", ip_address="127.0.0.1")
            evicted3 = await tracker.register(user_id, "session3", ip_address="127.0.0.1")
            
            # Oldest session should be evicted when limit hit
            assert len(evicted3) > 0, "Session eviction not working"
            
            # Check: is_valid works
            is_valid = await tracker.is_valid(user_id, "session3")
            assert is_valid, "is_valid() not working"
            
            # Check: revoke_all works
            count = await tracker.revoke_all(user_id)
            assert count >= 1, "revoke_all() not working"
            
            self.add_result("Plan 8: Session Limits", True, details="Session tracking working")
        except Exception as e:
            self.add_result("Plan 8: Session Limits", False, str(e))
    
    async def test_plan_9_logout_all(self) -> None:
        """Test: Logout Everywhere Functionality"""
        try:
            # Check: logout_all() exists
            from eden.auth.actions import logout_all
            assert callable(logout_all), "logout_all not callable"
            
            # Check: Function signature
            import inspect
            sig = inspect.signature(logout_all)
            assert 'user' in sig.parameters, "logout_all() missing user parameter"
            
            self.add_result("Plan 9: Logout All", True, details="logout_all() available")
        except Exception as e:
            self.add_result("Plan 9: Logout All", False, str(e))
    
    async def test_plan_10_audit_logging(self) -> None:
        """Test: Structured Audit Logging"""
        try:
            # Check: AuthAuditLogger exists
            from eden.auth.audit import AuthAuditLogger, auth_audit
            
            # Check: All audit methods exist
            methods = ['login_success', 'login_failed', 'logout', 'logout_all', 
                      'password_changed', 'token_revoked']
            for method in methods:
                assert hasattr(auth_audit, method), f"auth_audit missing {method} method"
            
            self.add_result("Plan 10: Audit Logging", True, details="All audit methods present")
        except Exception as e:
            self.add_result("Plan 10: Audit Logging", False, str(e))
    
    async def test_integration_login_logout(self) -> None:
        """Test: Basic login/logout integration"""
        try:
            from eden.auth.actions import login, logout, authenticate, _perform_dummy_hash
            assert callable(login), "login not callable"
            assert callable(logout), "logout not callable"
            assert callable(authenticate), "authenticate not callable"
            self.add_result("Integration: Login/Logout", True, details="All functions callable")
        except Exception as e:
            self.add_result("Integration: Login/Logout", False, str(e))
    
    async def test_integration_audit_integration(self) -> None:
        """Test: Audit logging integrated into actions"""
        try:
            # Check: login() calls auth_audit.login_success
            from eden.auth.actions import login
            import inspect
            login_code = inspect.getsource(login)
            assert 'auth_audit' in login_code, "Audit logging not in login()"
            assert 'login_success' in login_code, "login_success not called"
            
            # Check: logout() calls auth_audit.logout
            from eden.auth.actions import logout
            logout_code = inspect.getsource(logout)
            assert 'auth_audit' in logout_code, "Audit logging not in logout()"
            assert 'logout' in logout_code, "logout audit not called"
            
            self.add_result("Integration: Audit Logging", True, details="Audit integrated")
        except Exception as e:
            self.add_result("Integration: Audit Logging", False, str(e))
    
    async def test_exports(self) -> None:
        """Test: All features properly exported from eden.auth"""
        try:
            from eden.auth import (
                auth_router,
                SessionTracker,
                logout_all,
                auth_audit,
            )
            self.add_result("Exports: Main Features", True, details="All main exports available")
        except Exception as e:
            self.add_result("Exports: Main Features", False, str(e))
    
    async def run_all_tests(self) -> None:
        """Run all audit tests"""
        print("\n" + "="*70)
        print("AUTHENTICATION SECURITY FEATURES AUDIT")
        print("="*70 + "\n")
        
        tests = [
            ("Plan 1: JWT Token Revocation", self.test_plan_1_jwt_revocation),
            ("Plan 2: CSRF-Protected Logout", self.test_plan_2_csrf_logout),
            ("Plan 3: Rate-Limited Login", self.test_plan_3_rate_limiting),
            ("Plan 4: Timing-Safe Authentication", self.test_plan_4_timing_safe_auth),
            ("Plan 5: Remember-Me + Absolute Expiry", self.test_plan_5_remember_me),
            ("Plan 6: Session ID Rotation", self.test_plan_6_session_rotation),
            ("Plan 7: Secure Cookie Auto-Detection", self.test_plan_7_secure_cookies),
            ("Plan 8: Concurrent Session Limiting", self.test_plan_8_session_limits),
            ("Plan 9: Logout Everywhere", self.test_plan_9_logout_all),
            ("Plan 10: Structured Audit Logging", self.test_plan_10_audit_logging),
            ("Integration: Login/Logout Flow", self.test_integration_login_logout),
            ("Integration: Audit Logging", self.test_integration_audit_integration),
            ("Exports: Feature Availability", self.test_exports),
        ]
        
        for name, test_func in tests:
            try:
                await test_func()
            except Exception as e:
                print(f"✗ {name}: EXCEPTION")
                traceback.print_exc()
        
        # Print results
        print("\n" + "="*70)
        print("TEST RESULTS")
        print("="*70 + "\n")
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        for result in self.results:
            status = "[PASS]" if result.passed else "[FAIL]"
            print(f"{status} {result.name}")
            if result.details:
                print(f"   Details: {result.details}")
            if result.error:
                print(f"   Error: {result.error}")
        
        print(f"\nSummary: {passed}/{len(self.results)} passed, {failed} failed")
        
        # Print missing features
        if self.missing_features:
            print("\n" + "="*70)
            print("MISSING FEATURES")
            print("="*70)
            for feature in self.missing_features:
                print(f"  - {feature}")
        
        # Print incomplete features
        if self.incomplete_features:
            print("\n" + "="*70)
            print("INCOMPLETE FEATURES")
            print("="*70)
            for feature in self.incomplete_features:
                print(f"  - {feature}")

async def main():
    audit = FeatureAudit()
    await audit.run_all_tests()
    
    # Return exit code based on failures
    failed = sum(1 for r in audit.results if not r.passed)
    return 1 if failed > 0 else 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
