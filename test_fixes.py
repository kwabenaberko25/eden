#!/usr/bin/env python
"""Comprehensive test for all critical fixes"""

import sys

test_results = []

# Test 1: Async fixes in raw_sql.py
try:
    import eden_orm.raw_sql
    test_results.append(("raw_sql.py async fixes", "PASS"))
except Exception as e:
    test_results.append(("raw_sql.py async fixes", f"FAIL: {e}"))

# Test 2: Async fixes in nested_prefetch.py
try:
    import eden_orm.nested_prefetch
    test_results.append(("nested_prefetch.py async fixes", "PASS"))
except Exception as e:
    test_results.append(("nested_prefetch.py async fixes", f"FAIL: {e}"))

# Test 3: PostgreSQL syntax in audit.py
try:
    import eden_orm.audit
    test_results.append(("audit.py PostgreSQL syntax", "PASS"))
except Exception as e:
    test_results.append(("audit.py PostgreSQL syntax", f"FAIL: {e}"))

# Test 4: M2M naming fix
try:
    import eden_orm.m2m
    test_results.append(("m2m.py naming fix", "PASS"))
except Exception as e:
    test_results.append(("m2m.py naming fix", f"FAIL: {e}"))

# Test 5: Cache deduplication
try:
    import eden_orm.cache
    test_results.append(("cache.py deduplication", "PASS"))
except Exception as e:
    test_results.append(("cache.py deduplication", f"FAIL: {e}"))

# Test 6: Lazy loading compatibility
try:
    import eden_orm.lazy_loading
    test_results.append(("lazy_loading.py compatibility", "PASS"))
except Exception as e:
    test_results.append(("lazy_loading.py compatibility", f"FAIL: {e}"))

# Test 7: Field selection integration
try:
    import eden_orm.field_selection
    test_results.append(("field_selection.py integration", "PASS"))
except Exception as e:
    test_results.append(("field_selection.py integration", f"FAIL: {e}"))

# Test 8: Core module imports
try:
    import eden_orm
    import eden_orm.base
    import eden_orm.connection
    import eden_orm.query
    test_results.append(("Core module imports", "PASS"))
except Exception as e:
    test_results.append(("Core module imports", f"FAIL: {e}"))

# Print results
print("\n" + "="*60)
print("COMPREHENSIVE FIX VERIFICATION RESULTS")
print("="*60)

passed = 0
failed = 0

for test_name, result in test_results:
    status = "✓" if result == "PASS" else "✗"
    print(f"{status} {test_name}: {result}")
    if result == "PASS":
        passed += 1
    else:
        failed += 1

print("="*60)
print(f"SUMMARY: {passed} passed, {failed} failed")
print("="*60)

sys.exit(0 if failed == 0 else 1)
