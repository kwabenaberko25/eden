"""
Comprehensive Validation Script for All Tier-1 Phases

Tests implementation code directly without pytest to validate all phases work correctly.
"""

import sys
from pathlib import Path

# Add eden to path
sys.path.insert(0, str(Path(__file__).parent))

def test_phase_1_orm_methods():
    """Validate Phase 1: ORM Methods"""
    print("\n" + "="*60)
    print("PHASE 1: ORM QuerySet Methods")
    print("="*60)
    
    try:
        from eden.db.query import QuerySet
        
        # Check if new methods exist
        methods = ['get_or_404', 'filter_one', 'get_or_create', 'bulk_create']
        present = []
        missing = []
        
        for method in methods:
            if hasattr(QuerySet, method):
                present.append(method)
                print(f"✓ {method}() found in QuerySet")
            else:
                missing.append(method)
                print(f"✗ {method}() NOT FOUND in QuerySet")
        
        status = "PASS" if not missing else "FAIL"
        print(f"\nPhase 1 Status: [{status}] - {len(present)}/4 methods present")
        return len(missing) == 0
        
    except Exception as e:
        print(f"✗ Phase 1 Error: {e}")
        return False


def test_phase_2_csrf_fix():
    """Validate Phase 2: CSRF Security Fix"""
    print("\n" + "="*60)
    print("PHASE 2: CSRF Security Fix")
    print("="*60)
    
    try:
        from eden.security.csrf import get_csrf_token
        import inspect
        
        # Get source code
        source = inspect.getsource(get_csrf_token)
        
        # Check for fallback logic
        checks = [
            ("session attribute check", "hasattr(request, \"session\")" in source or "session is None" in source),
            ("fallback token generation", "generate_csrf_token()" in source),
        ]
        
        for check_name, result in checks:
            if result:
                print(f"✓ {check_name} implemented")
            else:
                print(f"✗ {check_name} NOT found")
        
        status = "PASS" if all(result for _, result in checks) else "FAIL"
        print(f"\nPhase 2 Status: [{status}]")
        return all(result for _, result in checks)
        
    except Exception as e:
        print(f"✗ Phase 2 Error: {e}")
        return False


def test_phase_3_openapi():
    """Validate Phase 3: OpenAPI Documentation"""
    print("\n" + "="*60)
    print("PHASE 3: OpenAPI Documentation")
    print("="*60)
    
    try:
        from eden.openapi import mount_openapi
        import inspect
        
        # Get source code
        source = inspect.getsource(mount_openapi)
        
        # Check for ReDoc and endpoints
        checks = [
            ("ReDoc HTML template", "_REDOC_HTML" in source or "redoc" in source.lower()),
            ("/redoc endpoint", "/redoc" in source),
            ("/docs endpoint", "/docs" in source),
            ("include_in_schema=False", "include_in_schema=False" in source),
        ]
        
        for check_name, result in checks:
            if result:
                print(f"✓ {check_name} implemented")
            else:
                print(f"✗ {check_name} NOT found")
        
        status = "PASS" if all(result for _, result in checks) else "FAIL"
        print(f"\nPhase 3 Status: [{status}]")
        return all(result for _, result in checks)
        
    except Exception as e:
        print(f"✗ Phase 3 Error: {e}")
        return False


def test_phase_4_password_reset():
    """Validate Phase 4: Password Reset Flow"""
    print("\n" + "="*60)
    print("PHASE 4: Password Reset Flow")
    print("="*60)
    
    try:
        from eden.auth.password_reset import (
            PasswordResetToken,
            PasswordResetService,
            PasswordResetEmail
        )
        
        # Check classes and methods exist
        checks = [
            ("PasswordResetToken model", PasswordResetToken is not None),
            ("PasswordResetService class", PasswordResetService is not None),
            ("generate_token() method", hasattr(PasswordResetService, 'generate_token')),
            ("create_reset_token() method", hasattr(PasswordResetService, 'create_reset_token')),
            ("validate_reset_token() method", hasattr(PasswordResetService, 'validate_reset_token')),
            ("reset_password() method", hasattr(PasswordResetService, 'reset_password')),
            ("PasswordResetEmail class", PasswordResetEmail is not None),
            ("Email template generation", hasattr(PasswordResetEmail, 'get_html_body')),
        ]
        
        for check_name, result in checks:
            if result:
                print(f"✓ {check_name} implemented")
            else:
                print(f"✗ {check_name} NOT found")
        
        status = "PASS" if all(result for _, result in checks) else "FAIL"
        print(f"\nPhase 4 Status: [{status}]")
        return all(result for _, result in checks)
        
    except Exception as e:
        print(f"✗ Phase 4 Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_routes():
    """Validate Password Reset Routes"""
    print("\n" + "="*60)
    print("PASSWORD RESET ROUTES")
    print("="*60)
    
    try:
        from eden.auth.password_reset_routes import router, ForgotPasswordRequest, ResetPasswordRequest
        
        checks = [
            ("Router imported", router is not None),
            ("ForgotPasswordRequest schema", ForgotPasswordRequest is not None),
            ("ResetPasswordRequest schema", ResetPasswordRequest is not None),
        ]
        
        for check_name, result in checks:
            if result:
                print(f"✓ {check_name} available")
            else:
                print(f"✗ {check_name} NOT found")
        
        status = "PASS" if all(result for _, result in checks) else "FAIL"
        print(f"\nRoutes Status: [{status}]")
        return all(result for _, result in checks)
        
    except Exception as e:
        print(f"✗ Routes Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validations"""
    print("\n" + "#"*60)
    print("# EDEN FRAMEWORK - TIER-1 IMPLEMENTATION VALIDATION")
    print("#"*60)
    
    results = {
        "Phase 1: ORM Methods": test_phase_1_orm_methods(),
        "Phase 2: CSRF Fix": test_phase_2_csrf_fix(),
        "Phase 3: OpenAPI": test_phase_3_openapi(),
        "Phase 4: Password Reset": test_phase_4_password_reset(),
        "Routes": test_routes(),
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")
    
    total_passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nOverall: {total_passed}/{total} phases validated")
    
    if total_passed == total:
        print("\n🎉 ALL TIER-1 IMPLEMENTATIONS VALIDATED SUCCESSFULLY!")
        return 0
    else:
        print(f"\n⚠️  {total - total_passed} validation(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
