#!/usr/bin/env python
"""
Test Runner for Eden ORM

Runs all test suites and reports results.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)


async def test_core_features():
    """Test Phase 1-2 core features."""
    print("\n" + "="*70)
    print("PHASE 1-2: CORE FEATURES & RELATIONSHIPS")
    print("="*70 + "\n")
    
    from eden_orm.base import Model
    from eden_orm.fields import StringField, UUIDField, ForeignKeyField, DateTimeField
    from eden_orm.pagination import Page
    from uuid import uuid4
    from datetime import datetime
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Model definition
    try:
        class User(Model):
            __tablename__ = "users"
            id = UUIDField(primary_key=True)
            name = StringField(max_length=100)
        
        user = User(id=uuid4(), name="Alice")
        assert user.name == "Alice"
        print("✓ Test 1: Model definition and instantiation")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 1 failed: {e}")
        tests_failed += 1
    
    # Test 2: Fields registration
    try:
        assert "id" in User.__fields__
        assert "name" in User.__fields__
        print("✓ Test 2: Field registration")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 2 failed: {e}")
        tests_failed += 1
    
    # Test 3: Model to_dict
    try:
        user_dict = user.to_dict()
        assert "id" in user_dict
        assert user_dict["name"] == "Alice"
        print("✓ Test 3: Model to_dict conversion")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 3 failed: {e}")
        tests_failed += 1
    
    # Test 4: Relationships (ForeignKeyField)
    try:
        class Post(Model):
            __tablename__ = "posts"
            id = UUIDField(primary_key=True)
            title = StringField(max_length=255)
            author_id = ForeignKeyField(to=User)
        
        assert "author_id" in Post.__fields__
        assert hasattr(Post.__fields__["author_id"], "to_model")
        print("✓ Test 4: ForeignKeyField definition")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 4 failed: {e}")
        tests_failed += 1
    
    # Test 5: QuerySet filtering
    try:
        query_chain = Post.filter(title="Test")
        assert query_chain is not None
        assert len(query_chain.conditions) > 0
        print("✓ Test 5: QuerySet filtering")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 5 failed: {e}")
        tests_failed += 1
    
    # Test 6: QuerySet select_related
    try:
        query_chain = Post.select_related("author")
        assert "author" in query_chain.select_related_fields
        print("✓ Test 6: select_related() eager loading")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 6 failed: {e}")
        tests_failed += 1
    
    # Test 7: QuerySet prefetch_related
    try:
        query_chain = Post.prefetch_related("author")
        assert "author" in query_chain.prefetch_related_fields
        print("✓ Test 7: prefetch_related() framework")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 7 failed: {e}")
        tests_failed += 1
    
    # Test 8: QuerySet chaining
    try:
        query_chain = (
            Post.select_related("author")
            .filter(title="Test")
            .order_by("-created_at")
            .limit(10)
            .offset(0)
        )
        assert query_chain.limit_value == 10
        assert query_chain.offset_value == 0
        print("✓ Test 8: QuerySet method chaining")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 8 failed: {e}")
        tests_failed += 1
    
    # Test 9: Pagination
    try:
        page = Page(
            items=[{"id": i} for i in range(10)],
            page=1,
            page_size=10,
            total=25,
        )
        assert page.total_pages == 3
        assert page.has_next
        assert not page.has_previous
        print("✓ Test 9: Pagination logic")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 9 failed: {e}")
        tests_failed += 1
    
    # Test 10: SQL generation
    try:
        query_chain = Post.select_related("author").filter(title="Test")
        sql, params = query_chain._build_sql()
        assert "SELECT" in sql
        assert "LEFT JOIN" in sql
        assert "WHERE" in sql
        print("✓ Test 10: SQL generation with JOINs")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 10 failed: {e}")
        tests_failed += 1
    
    print(f"\n{tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


async def test_phase3_features():
    """Test Phase 3 (Caching)."""
    print("\n" + "="*70)
    print("PHASE 3: CACHING & OPTIMIZATION")
    print("="*70 + "\n")
    
    from eden_orm.cache import get_query_cache, enable_caching, InMemoryCache
    from uuid import uuid4
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: InMemoryCache
    try:
        cache = InMemoryCache(max_size=100)
        assert asyncio.iscoroutinefunction(cache.get)
        print("✓ Test 1: InMemoryCache initialization")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 1 failed: {e}")
        tests_failed += 1
    
    # Test 2: Cache set/get
    try:
        cache = InMemoryCache()
        await cache.set("test_key", "test_value", ttl=3600)
        value = await cache.get("test_key")
        assert value == "test_value"
        print("✓ Test 2: Cache set/get")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 2 failed: {e}")
        tests_failed += 1
    
    # Test 3: Cache invalidation
    try:
        cache = InMemoryCache()
        await cache.set("test_key", "value")
        await cache.delete("test_key")
        value = await cache.get("test_key")
        assert value is None
        print("✓ Test 3: Cache invalidation")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 3 failed: {e}")
        tests_failed += 1
    
    # Test 4: Cache clear
    try:
        cache = InMemoryCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        value1 = await cache.get("key1")
        value2 = await cache.get("key2")
        assert value1 is None and value2 is None
        print("✓ Test 4: Cache clear all")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 4 failed: {e}")
        tests_failed += 1
    
    # Test 5: Global query cache
    try:
        cache = get_query_cache()
        assert cache is not None
        print("✓ Test 5: Global query cache instance")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 5 failed: {e}")
        tests_failed += 1
    
    print(f"\n{tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


async def test_phase4_features():
    """Test Phase 4 (Audit Trails)."""
    print("\n" + "="*70)
    print("PHASE 4: AUDIT TRAILS")
    print("="*70 + "\n")
    
    from eden_orm.audit import get_audit_logger, AuditAction, AuditEntry
    from uuid import uuid4
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Audit logger
    try:
        logger = get_audit_logger()
        assert logger is not None
        print("✓ Test 1: Audit logger instance")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 1 failed: {e}")
        tests_failed += 1
    
    # Test 2: Log CREATE
    try:
        logger = get_audit_logger()
        logger.entries.clear()
        logger.enable()
        
        entry = logger.log_create("User", str(uuid4()), {"name": "Alice"})
        assert entry.action == AuditAction.CREATE
        assert len(logger.entries) == 1
        print("✓ Test 2: Log CREATE action")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 2 failed: {e}")
        tests_failed += 1
    
    # Test 3: Log UPDATE
    try:
        logger = get_audit_logger()
        logger.entries.clear()
        
        old_data = {"id": "123", "name": "Alice"}
        new_data = {"id": "123", "name": "Bob"}
        entry = logger.log_update("User", "123", old_data, new_data)
        
        assert entry.action == AuditAction.UPDATE
        assert len(entry.changes) > 0
        assert "name" in entry.changes
        print("✓ Test 3: Log UPDATE action with changes")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 3 failed: {e}")
        tests_failed += 1
    
    # Test 4: Log DELETE
    try:
        logger = get_audit_logger()
        logger.entries.clear()
        
        entry = logger.log_delete("User", "123", {"name": "Alice"})
        assert entry.action == AuditAction.DELETE
        assert entry.old_data == {"name": "Alice"}
        print("✓ Test 4: Log DELETE action")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 4 failed: {e}")
        tests_failed += 1
    
    # Test 5: Audit entry to_dict
    try:
        entry = AuditEntry(
            model_name="User",
            record_id="123",
            action=AuditAction.CREATE,
            new_data={"name": "Alice"},
        )
        entry_dict = entry.to_dict()
        assert entry_dict["model_name"] == "User"
        assert entry_dict["action"] == "CREATE"
        print("✓ Test 5: Audit entry serialization")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 5 failed: {e}")
        tests_failed += 1
    
    print(f"\n{tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


async def test_phase5_features():
    """Test Phase 5 (Full-Text Search)."""
    print("\n" + "="*70)
    print("PHASE 5: FULL-TEXT SEARCH")
    print("="*70 + "\n")
    
    from eden_orm.search import get_fts_engine, SearchQueryBuilder, register_fts_index
    from eden_orm.base import Model
    from eden_orm.fields import StringField, UUIDField
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: FTS engine
    try:
        engine = get_fts_engine()
        assert engine is not None
        print("✓ Test 1: FTS engine instance")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 1 failed: {e}")
        tests_failed += 1
    
    # Test 2: Register FTS index
    try:
        class Article(Model):
            __tablename__ = "articles"
            id = UUIDField(primary_key=True)
            title = StringField(max_length=255)
            content = StringField()
        
        register_fts_index(Article, ["title", "content"])
        engine = get_fts_engine()
        assert "Article" in engine.indexed_fields
        print("✓ Test 2: Register FTS index")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 2 failed: {e}")
        tests_failed += 1
    
    # Test 3: Search query builder
    try:
        builder = SearchQueryBuilder()
        builder.add_term("python")
        builder.add_phrase("web development")
        builder.exclude("outdated")
        
        query = builder.build()
        assert "python" in query
        assert '"web development"' in query
        assert "-outdated" in query
        print("✓ Test 3: Search query builder")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 3 failed: {e}")
        tests_failed += 1
    
    # Test 4: SearchQueryBuilder chaining
    try:
        builder = (
            SearchQueryBuilder()
            .add_term("typescript")
            .add_phrase("async/await")
            .exclude("legacy")
        )
        query = builder.build()
        assert "typescript" in query
        print("✓ Test 4: Search builder method chaining")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 4 failed: {e}")
        tests_failed += 1
    
    print(f"\n{tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


async def main():
    """Run all test suites."""
    logger.info("Starting Eden ORM comprehensive test suite")
    
    results = []
    
    # Run each phase
    try:
        results.append(("Phases 1-2: Core & Relationships", await test_core_features()))
    except Exception as e:
        logger.error(f"Phase 1-2 tests failed: {e}")
        results.append(("Phases 1-2: Core & Relationships", False))
    
    try:
        results.append(("Phase 3: Caching & Optimization", await test_phase3_features()))
    except Exception as e:
        logger.error(f"Phase 3 tests failed: {e}")
        results.append(("Phase 3: Caching & Optimization", False))
    
    try:
        results.append(("Phase 4: Audit Trails", await test_phase4_features()))
    except Exception as e:
        logger.error(f"Phase 4 tests failed: {e}")
        results.append(("Phase 4: Audit Trails", False))
    
    try:
        results.append(("Phase 5: Full-Text Search", await test_phase5_features()))
    except Exception as e:
        logger.error(f"Phase 5 tests failed: {e}")
        results.append(("Phase 5: Full-Text Search", False))
    
    # Summary
    print("\n" + "="*70)
    print("FINAL TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:.<50} {status}")
    
    print("="*70 + "\n")
    
    all_passed = all(passed for _, passed in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
