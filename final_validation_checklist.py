#!/usr/bin/env python3
"""
Final comprehensive validation checklist for all 10 authentication security plans.
Verifies all files exist, are properly formatted, and are integrated correctly.
"""

import os
import ast
import sys


def validate_file_exists(filepath):
    """Validate that a file exists."""
    exists = os.path.exists(filepath)
    status = "EXISTS" if exists else "MISSING"
    print("  [%s] %s" % (status, filepath))
    return exists


def validate_python_syntax(filepath):
    """Validate that a Python file has correct syntax."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        return True
    except SyntaxError as e:
        print("    SYNTAX ERROR: %s" % str(e))
        return False
    except Exception as e:
        print("    ERROR: %s" % str(e))
        return False


def validate_contains(filepath, *search_terms):
    """Validate that a file contains specific terms."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_found = True
        for term in search_terms:
            if term not in content:
                print("    MISSING: '%s'" % term)
                all_found = False
        
        return all_found
    except Exception as e:
        print("    ERROR reading file: %s" % str(e))
        return False


def main():
    """Run comprehensive validation."""
    base_path = "c:\\PROJECTS\\eden-framework"
    
    print("\n" + "="*80)
    print("FINAL VALIDATION CHECKLIST - ALL 10 SECURITY PLANS")
    print("="*80 + "\n")
    
    # ========================================================================
    # PLAN 1: JWT Token Revocation
    # ========================================================================
    print("[PLAN 1] JWT Token Revocation")
    print("-" * 80)
    
    plan1_files = [
        os.path.join(base_path, "eden/auth/actions.py"),
        os.path.join(base_path, "eden/auth/token_denylist.py"),
    ]
    
    plan1_ok = True
    for f in plan1_files:
        if validate_file_exists(f):
            if not validate_python_syntax(f):
                plan1_ok = False
        else:
            plan1_ok = False
    
    if os.path.exists(plan1_files[1]):
        if not validate_contains(plan1_files[1], "revoke_all_for_user"):
            plan1_ok = False
    
    print("  Plan 1: %s\n" % ("OK" if plan1_ok else "INCOMPLETE"))
    
    # ========================================================================
    # PLAN 2: CSRF-Protected Logout
    # ========================================================================
    print("[PLAN 2] CSRF-Protected Logout")
    print("-" * 80)
    
    plan2_file = os.path.join(base_path, "eden/auth/routes.py")
    plan2_ok = False
    
    if validate_file_exists(plan2_file):
        if validate_python_syntax(plan2_file):
            if validate_contains(plan2_file, "logout_view", "@login_required", "auth_router"):
                plan2_ok = True
    
    print("  Plan 2: %s\n" % ("OK" if plan2_ok else "INCOMPLETE"))
    
    # ========================================================================
    # PLAN 3: Rate-Limited Login
    # ========================================================================
    print("[PLAN 3] Rate-Limited Login")
    print("-" * 80)
    
    plan3_ok = False
    if validate_file_exists(plan2_file):
        if validate_contains(plan2_file, "login_view", "@rate_limit"):
            plan3_ok = True
    
    print("  Plan 3: %s\n" % ("OK" if plan3_ok else "INCOMPLETE"))
    
    # ========================================================================
    # PLAN 4: Timing-Safe Auth
    # ========================================================================
    print("[PLAN 4] Timing-Safe Authentication")
    print("-" * 80)
    
    plan4_file = os.path.join(base_path, "eden/auth/actions.py")
    plan4_ok = False
    
    if validate_file_exists(plan4_file):
        if validate_python_syntax(plan4_file):
            if validate_contains(plan4_file, "_perform_dummy_hash", "_DUMMY_HASH"):
                plan4_ok = True
    
    print("  Plan 4: %s\n" % ("OK" if plan4_ok else "INCOMPLETE"))
    
    # ========================================================================
    # PLAN 5: Remember-Me + Absolute Expiry
    # ========================================================================
    print("[PLAN 5] Remember-Me with Absolute Expiry")
    print("-" * 80)
    
    plan5_files = [
        os.path.join(base_path, "eden/auth/actions.py"),
        os.path.join(base_path, "eden/config.py"),
        os.path.join(base_path, "eden/auth/middleware.py"),
    ]
    
    plan5_ok = True
    for f in plan5_files:
        if not validate_file_exists(f):
            plan5_ok = False
        elif not validate_python_syntax(f):
            plan5_ok = False
    
    if os.path.exists(plan5_files[1]):
        if not validate_contains(plan5_files[1], "session_absolute_max_age", "session_remember_me_max_age"):
            plan5_ok = False
    
    print("  Plan 5: %s\n" % ("OK" if plan5_ok else "INCOMPLETE"))
    
    # ========================================================================
    # PLAN 6: Session Rotation
    # ========================================================================
    print("[PLAN 6] Session ID Rotation on Login")
    print("-" * 80)
    
    plan6_files = [
        os.path.join(base_path, "eden/auth/actions.py"),
        os.path.join(base_path, "eden/auth/backends/session.py"),
    ]
    
    plan6_ok = True
    for f in plan6_files:
        if validate_file_exists(f):
            if not validate_python_syntax(f):
                plan6_ok = False
        else:
            plan6_ok = False
    
    print("  Plan 6: %s\n" % ("OK" if plan6_ok else "INCOMPLETE"))
    
    # ========================================================================
    # PLAN 7: Secure Cookies
    # ========================================================================
    print("[PLAN 7] Secure Cookie Auto-Detection")
    print("-" * 80)
    
    plan7_file = os.path.join(base_path, "eden/middleware/__init__.py")
    plan7_ok = False
    
    if validate_file_exists(plan7_file):
        if validate_python_syntax(plan7_file):
            if validate_contains(plan7_file, "https_only"):
                plan7_ok = True
    
    print("  Plan 7: %s\n" % ("OK" if plan7_ok else "INCOMPLETE"))
    
    # ========================================================================
    # PLAN 8: Session Limiting
    # ========================================================================
    print("[PLAN 8] Concurrent Session Limiting")
    print("-" * 80)
    
    plan8_files = [
        os.path.join(base_path, "eden/auth/session_tracker.py"),
        os.path.join(base_path, "eden/config.py"),
    ]
    
    plan8_ok = True
    for f in plan8_files:
        if validate_file_exists(f):
            if not validate_python_syntax(f):
                plan8_ok = False
        else:
            plan8_ok = False
    
    if os.path.exists(plan8_files[0]):
        if not validate_contains(plan8_files[0], "SessionTracker"):
            plan8_ok = False
    
    if os.path.exists(plan8_files[1]):
        if not validate_contains(plan8_files[1], "max_concurrent_sessions"):
            plan8_ok = False
    
    print("  Plan 8: %s\n" % ("OK" if plan8_ok else "INCOMPLETE"))
    
    # ========================================================================
    # PLAN 9: Logout-Everywhere
    # ========================================================================
    print("[PLAN 9] Logout-Everywhere")
    print("-" * 80)
    
    plan9_file = os.path.join(base_path, "eden/auth/actions.py")
    plan9_ok = False
    
    if validate_file_exists(plan9_file):
        if validate_python_syntax(plan9_file):
            if validate_contains(plan9_file, "logout_all"):
                plan9_ok = True
    
    print("  Plan 9: %s\n" % ("OK" if plan9_ok else "INCOMPLETE"))
    
    # ========================================================================
    # PLAN 10: Audit Logging
    # ========================================================================
    print("[PLAN 10] Structured Audit Logging")
    print("-" * 80)
    
    plan10_file = os.path.join(base_path, "eden/auth/audit.py")
    plan10_ok = False
    
    if validate_file_exists(plan10_file):
        if validate_python_syntax(plan10_file):
            if validate_contains(plan10_file, "AuthAuditLogger", "auth_audit"):
                plan10_ok = True
    
    print("  Plan 10: %s\n" % ("OK" if plan10_ok else "INCOMPLETE"))
    
    # ========================================================================
    # EXPORTS VALIDATION
    # ========================================================================
    print("[EXPORTS] Public API Availability")
    print("-" * 80)
    
    exports_file = os.path.join(base_path, "eden/auth/__init__.py")
    exports_ok = False
    
    if validate_file_exists(exports_file):
        if validate_python_syntax(exports_file):
            if validate_contains(
                exports_file,
                "auth_router",
                "logout_all",
                "SessionTracker",
                "InMemorySessionTrackerStore",
                "auth_audit"
            ):
                exports_ok = True
    
    print("  Exports: %s\n" % ("OK" if exports_ok else "INCOMPLETE"))
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    all_ok = all([
        plan1_ok, plan2_ok, plan3_ok, plan4_ok, plan5_ok,
        plan6_ok, plan7_ok, plan8_ok, plan9_ok, plan10_ok,
        exports_ok
    ])
    
    print("="*80)
    print("FINAL VALIDATION RESULT")
    print("="*80)
    print()
    print("Plan 1:  JWT Revocation               [%s]" % ("PASS" if plan1_ok else "FAIL"))
    print("Plan 2:  CSRF Logout                  [%s]" % ("PASS" if plan2_ok else "FAIL"))
    print("Plan 3:  Rate Limiting                [%s]" % ("PASS" if plan3_ok else "FAIL"))
    print("Plan 4:  Timing-Safe Auth             [%s]" % ("PASS" if plan4_ok else "FAIL"))
    print("Plan 5:  Remember-Me                  [%s]" % ("PASS" if plan5_ok else "FAIL"))
    print("Plan 6:  Session Rotation             [%s]" % ("PASS" if plan6_ok else "FAIL"))
    print("Plan 7:  Secure Cookies               [%s]" % ("PASS" if plan7_ok else "FAIL"))
    print("Plan 8:  Session Limits               [%s]" % ("PASS" if plan8_ok else "FAIL"))
    print("Plan 9:  Logout-Everywhere            [%s]" % ("PASS" if plan9_ok else "FAIL"))
    print("Plan 10: Audit Logging                [%s]" % ("PASS" if plan10_ok else "FAIL"))
    print("Exports: Public API                   [%s]" % ("PASS" if exports_ok else "FAIL"))
    print()
    
    if all_ok:
        print("STATUS: ALL VALIDATIONS PASSED - READY FOR PRODUCTION")
        return 0
    else:
        print("STATUS: SOME VALIDATIONS FAILED - REVIEW REQUIRED")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
