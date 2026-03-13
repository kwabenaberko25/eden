#!/usr/bin/env python
"""
Standalone Test Suite for Eden ORM - No External Dependencies

Tests core logic without requiring asyncpg or databases.
"""

import asyncio
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)


def test_field_types():
    """Test field type definitions."""
    print("\n" + "="*70)
    print("TEST: FIELD TYPES & DEFINITIONS")
    print("="*70 + "\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Import field types directly without connection
    import sys
    from pathlib import Path
    
    # Test 1: StringField basic definition
    try:
        from eden_orm.fields import StringField
        field = StringField(max_length=100)
        assert field.max_length == 100
        print("[PASS] StringField definition")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] StringField failed: {e}")
        tests_failed += 1
    
    # Test 2: IntField
    try:
        from eden_orm.fields import IntField
        field = IntField()
        assert field is not None
        print("[PASS] IntField definition")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] IntField failed: {e}")
        tests_failed += 1
    
    # Test 3: UUIDField
    try:
        from eden_orm.fields import UUIDField
        field = UUIDField(primary_key=True)
        assert field.primary_key == True
        print("[PASS] UUIDField with primary_key")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] UUIDField failed: {e}")
        tests_failed += 1
    
    # Test 4: DateTimeField
    try:
        from eden_orm.fields import DateTimeField
        field = DateTimeField(auto_now_add=True)
        assert field.auto_now_add == True
        print("[PASS] DateTimeField with auto_now_add")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] DateTimeField failed: {e}")
        tests_failed += 1
    
    print(f"\nResult: {tests_passed} passed, {tests_failed} failed\n")
    return tests_failed == 0


def test_queries_and_filtering():
    """Test query and filtering logic."""
    print("\n" + "="*70)
    print("TEST: QUERY FILTERING & BUILDING")
    print("="*70 + "\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Query dataclass
    try:
        from eden_orm.query import Query
        query = Query(field="name", operator="exact", value="Alice")
        assert query.field == "name"
        assert query.operator == "exact"
        assert query.value == "Alice"
        print("[PASS] Query dataclass creation")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Query dataclass failed: {e}")
        tests_failed += 1
    
    # Test 2: FilterChain dataclass
    try:
        from eden_orm.query import FilterChain, Query
        
        # Create a mock model class
        class MockModel:
            __tablename__ = "users"
            __fields__ = {}
        
        chain = FilterChain(model_class=MockModel)
        assert chain.model_class == MockModel
        assert chain.conditions == []
        assert chain.select_related_fields == []
        assert chain.prefetch_related_fields == []
        print("[PASS] FilterChain dataclass initialization")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] FilterChain failed: {e}")
        tests_failed += 1
    
    # Test 3: Query building (_build_condition)
    try:
        from eden_orm.query import FilterChain, Query
        
        class MockModel:
            __tablename__ = "users"
            __fields__ = {}
        
        chain = FilterChain(model_class=MockModel)
        
        # Test different operators
        operators = {
            "exact": ("name = $1", [("Alice", )]),
            "icontains": ("name ILIKE $1", [("{text}",)]),
            "gte": ("age >= $1", [(18,)]),
        }
        
        for op, (expected_sql_part, _) in operators.items():
            query = Query(field="name", operator=op, value="test")
            sql, params = chain._build_condition(query, 1)
            assert "$1" in sql
        
        print("[PASS] Query condition building")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Query building failed: {e}")
        tests_failed += 1
    
    # Test 4: SQL generation (without JOINs)
    try:
        from eden_orm.query import FilterChain
        
        class MockModel:
            __tablename__ = "users"
            __fields__ = {}
        
        chain = FilterChain(model_class=MockModel)
        chain.conditions = []
        chain.order_fields = []
        chain.select_related_fields = []
        
        sql, params = chain._build_sql()
        assert "SELECT *" in sql
        assert "FROM users" in sql
        print("[PASS] Basic SQL generation")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] SQL generation failed: {e}")
        tests_failed += 1
    
    # Test 5: SQL generation with JOINs
    try:
        from eden_orm.query import FilterChain
        
        class MockAuthor:
            __tablename__ = "authors"
        
        class MockField:
            def __init__(self):
                self.to_model = MockAuthor
        
        class MockModel:
            __tablename__ = "posts"
            __fields__ = {"author_id": MockField()}
        
        chain = FilterChain(model_class=MockModel)
        chain.select_related_fields = ["author"]
        chain.conditions = []
        chain.order_fields = []
        
        sql, params = chain._build_sql()
        assert "LEFT JOIN" in sql
        assert "authors" in sql
        print("[PASS] SQL generation with JOINs")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] JOINs SQL generation failed: {e}")
        tests_failed += 1
    
    print(f"\nResult: {tests_passed} passed, {tests_failed} failed\n")
    return tests_failed == 0


def test_caching_system():
    """Test caching system logic."""
    print("\n" + "="*70)
    print("TEST: CACHING & QUERY CACHE")
    print("="*70 + "\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Cache key generation
    try:
        from eden_orm.cache import QueryCache, InMemoryCache
        
        cache = QueryCache(backend=InMemoryCache())
        key1 = cache.generate_key("SELECT * FROM users", ["123"])
        key2 = cache.generate_key("SELECT * FROM users", ["456"])
        
        assert key1.startswith("query:")
        assert key1 != key2
        print("[PASS] Cache key generation")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Cache key generation failed: {e}")
        tests_failed += 1
    
    # Test 2: QueryCache initialization
    try:
        from eden_orm.cache import QueryCache, InMemoryCache
        
        cache = QueryCache(backend=InMemoryCache())
        assert cache.enabled == True
        assert cache.ttl == 3600
        print("[PASS] QueryCache initialization")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] QueryCache init failed: {e}")
        tests_failed += 1
    
    # Test 3: Cache enable/disable
    try:
        from eden_orm.cache import enable_caching, set_cache_ttl, get_query_cache
        
        enable_caching(True)
        cache = get_query_cache()
        assert cache.enabled == True
        
        enable_caching(False)
        cache = get_query_cache()
        assert cache.enabled == False
        
        print("[PASS] Cache enable/disable")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Cache enable/disable failed: {e}")
        tests_failed += 1
    
    print(f"\nResult: {tests_passed} passed, {tests_failed} failed\n")
    return tests_failed == 0


def test_audit_system():
    """Test audit trail system."""
    print("\n" + "="*70)
    print("TEST: AUDIT TRAIL SYSTEM")
    print("="*70 + "\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: AuditAction enum
    try:
        from eden_orm.audit import AuditAction
        
        assert AuditAction.CREATE.value == "CREATE"
        assert AuditAction.UPDATE.value == "UPDATE"
        assert AuditAction.DELETE.value == "DELETE"
        print("[PASS] AuditAction enum")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] AuditAction enum failed: {e}")
        tests_failed += 1
    
    # Test 2: AuditEntry creation
    try:
        from eden_orm.audit import AuditEntry, AuditAction
        
        entry = AuditEntry(
            model_name="User",
            record_id="123",
            action=AuditAction.CREATE,
            new_data={"name": "Alice"},
        )
        
        assert entry.model_name == "User"
        assert entry.action == AuditAction.CREATE
        assert entry.new_data["name"] == "Alice"
        print("[PASS] AuditEntry creation")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] AuditEntry failed: {e}")
        tests_failed += 1
    
    # Test 3: AuditEntry to_dict
    try:
        from eden_orm.audit import AuditEntry, AuditAction
        
        entry = AuditEntry(
            model_name="User",
            record_id="123",
            action=AuditAction.UPDATE,
            old_data={"name": "Alice"},
            new_data={"name": "Bob"},
        )
        
        entry_dict = entry.to_dict()
        assert entry_dict["model_name"] == "User"
        assert entry_dict["action"] == "UPDATE"
        print("[PASS] AuditEntry serialization")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] AuditEntry serialization failed: {e}")
        tests_failed += 1
    
    # Test 4: AuditLogger
    try:
        from eden_orm.audit import AuditLogger, AuditAction
        
        logger = AuditLogger(enabled=True)
        logger.enable()
        assert logger.enabled == True
        
        entry = logger.log_create("User", "123", {"name": "Alice"})
        assert len(logger.entries) == 1
        assert logger.entries[0].action == AuditAction.CREATE
        
        logger.disable()
        assert logger.enabled == False
        
        print("[PASS] AuditLogger operations")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] AuditLogger failed: {e}")
        tests_failed += 1
    
    # Test 5: Audit change detection
    try:
        from eden_orm.audit import AuditLogger
        
        logger = AuditLogger(enabled=True)
        old_data = {"name": "Alice", "age": 30}
        new_data = {"name": "Bob", "age": 30}
        
        entry = logger.log_update("User", "123", old_data, new_data)
        assert "name" in entry.changes
        assert "age" not in entry.changes
        print("[PASS] Change detection")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Change detection failed: {e}")
        tests_failed += 1
    
    print(f"\nResult: {tests_passed} passed, {tests_failed} failed\n")
    return tests_failed == 0


def test_fts_system():
    """Test full-text search system."""
    print("\n" + "="*70)
    print("TEST: FULL-TEXT SEARCH SYSTEM")
    print("="*70 + "\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: SearchQueryBuilder
    try:
        from eden_orm.search import SearchQueryBuilder
        
        builder = SearchQueryBuilder()
        builder.add_term("python")
        builder.add_phrase("web development")
        builder.exclude("legacy")
        
        query = builder.build()
        assert "python" in query
        assert '"web development"' in query
        assert "-legacy" in query
        print("[PASS] SearchQueryBuilder")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] SearchQueryBuilder failed: {e}")
        tests_failed += 1
    
    # Test 2: SearchQueryBuilder chaining
    try:
        from eden_orm.search import SearchQueryBuilder
        
        query = (
            SearchQueryBuilder()
            .add_term("typescript")
            .add_phrase("type safety")
            .exclude("javascript")
            .build()
        )
        
        assert "typescript" in query
        assert '"type safety"' in query
        print("[PASS] SearchQueryBuilder chaining")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Chaining failed: {e}")
        tests_failed += 1
    
    # Test 3: SearchResult dataclass
    try:
        from eden_orm.search import SearchResult
        from uuid import uuid4
        
        result = SearchResult(id=uuid4(), relevance=0.95)
        assert result.relevance == 0.95
        assert result.model_instance is None
        print("[PASS] SearchResult dataclass")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] SearchResult failed: {e}")
        tests_failed += 1
    
    # Test 4: FTS engine registration
    try:
        from eden_orm.search import get_fts_engine, register_fts_index
        
        class MockModel:
            pass
        
        engine = get_fts_engine()
        register_fts_index(MockModel, ["title", "content"])
        
        assert "MockModel" in engine.indexed_fields
        assert engine.indexed_fields["MockModel"] == ["title", "content"]
        print("[PASS] FTS index registration")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] FTS registration failed: {e}")
        tests_failed += 1
    
    print(f"\nResult: {tests_passed} passed, {tests_failed} failed\n")
    return tests_failed == 0


def test_pagination():
    """Test pagination logic."""
    print("\n" + "="*70)
    print("TEST: PAGINATION SYSTEM")
    print("="*70 + "\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Page dataclass
    try:
        from eden_orm.pagination import Page
        
        page = Page(
            items=[1, 2, 3],
            page=1,
            per_page=10,
            total=25,
        )
        
        assert page.page == 1
        assert page.per_page == 10
        assert page.total == 25
        print("[PASS] Page dataclass")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Page creation failed: {e}")
        tests_failed += 1
    
    # Test 2: Page properties
    try:
        from eden_orm.pagination import Page
        
        page = Page(items=list(range(10)), page=1, per_page=10, total=25)
        
        assert page.total_pages == 3
        assert page.has_next == True
        assert page.has_previous == False
        assert page.start_index == 0
        assert page.end_index == 9
        print("[PASS] Page properties")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Page properties failed: {e}")
        tests_failed += 1
    
    # Test 3: Page navigation
    try:
        from eden_orm.pagination import Page
        
        page = Page(items=list(range(10)), page=2, per_page=10, total=35)
        
        assert page.previous_page == 1
        assert page.next_page == 3
        assert page.start_index == 10
        print("[PASS] Page navigation")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Page navigation failed: {e}")
        tests_failed += 1
    
    print(f"\nResult: {tests_passed} passed, {tests_failed} failed\n")
    return tests_failed == 0


def test_migrations():
    """Test migration system."""
    print("\n" + "="*70)
    print("TEST: MIGRATION SYSTEM")
    print("="*70 + "\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: MigrationRunner initialization
    try:
        from eden_orm.migrations.runner import MigrationRunner
        from pathlib import Path
        
        runner = MigrationRunner(migrations_dir="migrations")
        assert runner.migrations_dir is not None
        assert runner.migrations_dir.exists()
        print("[PASS] MigrationRunner initialization")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] MigrationRunner init failed: {e}")
        tests_failed += 1
    
    print(f"\nResult: {tests_passed} passed, {tests_failed} failed\n")
    return tests_failed == 0


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("EDEN ORM - COMPREHENSIVE STANDALONE TEST SUITE")
    print("="*70)
    print("Testing all phases without external dependencies\n")
    
    results = []
    
    # Run all test suites
    try:
        results.append(("Field Types", test_field_types()))
    except Exception as e:
        logger.error(f"Field types tests failed: {e}")
        results.append(("Field Types", False))
    
    try:
        results.append(("Query Filtering", test_queries_and_filtering()))
    except Exception as e:
        logger.error(f"Query tests failed: {e}")
        results.append(("Query Filtering", False))
    
    try:
        results.append(("Caching System", test_caching_system()))
    except Exception as e:
        logger.error(f"Caching tests failed: {e}")
        results.append(("Caching System", False))
    
    try:
        results.append(("Audit System", test_audit_system()))
    except Exception as e:
        logger.error(f"Audit tests failed: {e}")
        results.append(("Audit System", False))
    
    try:
        results.append(("FTS System", test_fts_system()))
    except Exception as e:
        logger.error(f"FTS tests failed: {e}")
        results.append(("FTS System", False))
    
    try:
        results.append(("Pagination", test_pagination()))
    except Exception as e:
        logger.error(f"Pagination tests failed: {e}")
        results.append(("Pagination", False))
    
    try:
        results.append(("Migrations", test_migrations()))
    except Exception as e:
        logger.error(f"Migration tests failed: {e}")
        results.append(("Migrations", False))
    
    # Final summary
    print("\n" + "="*70)
    print("FINAL TEST SUMMARY")
    print("="*70)
    
    passed_count = sum(1 for _, passed in results if passed)
    failed_count = len(results) - passed_count
    
    for test_name, passed in results:
        status = "[PASS] PASSED" if passed else "[FAIL] FAILED"
        print(f"{test_name:.<50} {status}")
    
    print("="*70)
    print(f"TOTAL: {passed_count} passed, {failed_count} failed")
    print("="*70 + "\n")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
