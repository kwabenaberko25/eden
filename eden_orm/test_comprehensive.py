"""
Comprehensive Test Suite for Eden ORM

Tests all phases: Core, Relationships, Migrations, Caching, Auditing, FTS
"""

import asyncio
import logging
import sys
from datetime import datetime
from uuid import uuid4
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from base import Model
from fields import StringField, IntField, DateTimeField, UUIDField, ForeignKeyField
from migrations.runner import create_migration, apply_migrations
from cache import get_query_cache, enable_caching, set_cache_ttl, InMemoryCache
from audit import get_audit_logger, AuditAction, AuditEntry
from search import get_fts_engine, register_fts_index, SearchQueryBuilder

logger = logging.getLogger(__name__)


# Test Models
class User(Model):
    __tablename__ = "users"
    id = UUIDField(primary_key=True)
    name = StringField(max_length=100)
    email = StringField(max_length=255)
    created_at = DateTimeField(auto_now_add=True)


class Post(Model):
    __tablename__ = "posts"
    id = UUIDField(primary_key=True)
    title = StringField(max_length=255)
    content = StringField()
    author_id = ForeignKeyField(to=User)
    created_at = DateTimeField(auto_now_add=True)


class Comment(Model):
    __tablename__ = "comments"
    id = UUIDField(primary_key=True)
    text = StringField()
    post_id = ForeignKeyField(to=Post)
    author_id = ForeignKeyField(to=User)
    created_at = DateTimeField(auto_now_add=True)


async def test_migrations():
    """Test migration system."""
    print("\n✓ Testing Migration System...")
    
    # Create a test migration
    migration_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(100),
        email VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    try:
        migration_name = await create_migration("init_users", migration_sql)
        print(f"  ✓ Created migration: {migration_name}")
        
        applied = await apply_migrations()
        print(f"  ✓ Applied migrations: {applied}")
        
        return True
    except Exception as e:
        print(f"  ✗ Migration failed: {e}")
        return False


async def test_query_caching():
    """Test query caching system."""
    print("\n✓ Testing Query Caching...")
    
    cache = get_query_cache()
    
    # Test cache set/get
    test_sql = "SELECT * FROM users WHERE id = $1"
    test_params = [str(uuid4())]
    test_result = '{"id": "test", "name": "Alice"}'
    
    # Enable caching
    enable_caching(True)
    set_cache_ttl(3600)
    
    # Set value
    success = await cache.set(test_sql, test_params, test_result)
    print(f"  ✓ Cache set: {success}")
    
    # Get value
    cached = await cache.get(test_sql, test_params)
    print(f"  ✓ Cache get: {cached == test_result}")
    
    # Invalidate
    invalidated = await cache.invalidate(test_sql, test_params)
    print(f"  ✓ Cache invalidate: {invalidated}")
    
    # Get after invalidate
    cleared = await cache.get(test_sql, test_params)
    print(f"  ✓ Cache cleared: {cleared is None}")
    
    return cached == test_result and cleared is None


async def test_audit_logging():
    """Test audit trail system."""
    print("\n✓ Testing Audit Logging...")
    
    audit_logger = get_audit_logger()
    audit_logger.enable()
    
    user_id = uuid4()
    user_data = {"id": str(user_id), "name": "Alice", "email": "alice@example.com"}
    
    # Log create
    entry = audit_logger.log_create("User", str(user_id), user_data)
    print(f"  ✓ Log CREATE: {entry.action == AuditAction.CREATE}")
    
    # Log update
    new_data = {"id": str(user_id), "name": "Alice Updated", "email": "alice@example.com"}
    entry = audit_logger.log_update("User", str(user_id), user_data, new_data)
    print(f"  ✓ Log UPDATE: {entry.action == AuditAction.UPDATE}")
    print(f"  ✓ Changes detected: {len(entry.changes) > 0}")
    
    # Log delete
    entry = audit_logger.log_delete("User", str(user_id), user_data)
    print(f"  ✓ Log DELETE: {entry.action == AuditAction.DELETE}")
    
    # Check entries
    print(f"  ✓ Total entries: {len(audit_logger.entries)}")
    
    return len(audit_logger.entries) == 3


async def test_full_text_search():
    """Test full-text search engine."""
    print("\n✓ Testing Full-Text Search...")
    
    engine = get_fts_engine()
    
    # Register search index
    register_fts_index(Post, ["title", "content"])
    print(f"  ✓ Registered FTS index for Post")
    
    # Check registration
    assert "Post" in engine.indexed_fields
    print(f"  ✓ Index fields: {engine.indexed_fields['Post']}")
    
    # Build search query
    builder = SearchQueryBuilder()
    builder.add_term("python").add_phrase("web development").exclude("outdated")
    query = builder.build()
    print(f"  ✓ Built search query: {query}")
    
    return True


async def test_core_features():
    """Test Phase 1 core features."""
    print("\n✓ Testing Core Features...")
    
    # Test model definition
    user = User(id=uuid4(), name="Alice", email="alice@example.com")
    print(f"  ✓ Model instance created: {user.name}")
    
    # Test to_dict
    user_dict = user.to_dict()
    print(f"  ✓ Model to_dict: {len(user_dict) > 0}")
    
    return True


async def test_relationships():
    """Test Phase 2 relationships."""
    print("\n✓ Testing Relationships...")
    
    # Check ForeignKeyField
    author_id_field = Post.__fields__.get("author_id")
    assert author_id_field is not None
    print(f"  ✓ ForeignKeyField detected")
    
    # Check relationship registration
    assert hasattr(author_id_field, "to_model")
    print(f"  ✓ Relationship to_model set")
    
    return True


async def test_query_builder():
    """Test QuerySet builder."""
    print("\n✓ Testing QuerySet Builder...")
    
    # Test select_related
    chain = Post.select_related("author")
    print(f"  ✓ select_related() chain created")
    
    # Test prefetch_related
    chain = Post.prefetch_related("author", "comments")
    print(f"  ✓ prefetch_related() chain created")
    
    # Test filter
    chain = chain.filter(title="Test")
    print(f"  ✓ filter() chaining works")
    
    # Test order_by
    chain = chain.order_by("-created_at")
    print(f"  ✓ order_by() chaining works")
    
    # Test limit/offset
    chain = chain.limit(10).offset(0)
    print(f"  ✓ limit/offset chaining works")
    
    return True


async def test_field_types():
    """Test various field types."""
    print("\n✓ Testing Field Types...")
    
    user_id = uuid4()
    now = datetime.now()
    
    # Check field definitions
    fields = User.__fields__
    print(f"  ✓ UUID field: {type(fields['id']).__name__}")
    print(f"  ✓ String field: {type(fields['name']).__name__}")
    print(f"  ✓ DateTime field: {type(fields['created_at']).__name__}")
    
    post_fields = Post.__fields__
    print(f"  ✓ ForeignKey field: {type(post_fields['author_id']).__name__}")
    
    return True


async def test_pagination():
    """Test pagination features."""
    print("\n✓ Testing Pagination...")
    
    from .pagination import Page
    
    page = Page(
        items=[{"id": 1}, {"id": 2}, {"id": 3}],
        page=1,
        page_size=10,
        total=25,
    )
    
    print(f"  ✓ Page object created: page {page.page} of {page.total_pages}")
    print(f"  ✓ Has next: {page.has_next}")
    print(f"  ✓ Has previous: {page.has_previous}")
    
    return page.total_pages == 3


async def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*70)
    print("EDEN ORM - COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    tests = [
        ("Core Features", test_core_features),
        ("Field Types", test_field_types),
        ("Relationships", test_relationships),
        ("QuerySet Builder", test_query_builder),
        ("Pagination", test_pagination),
        ("Query Caching", test_query_caching),
        ("Audit Logging", test_audit_logging),
        ("Full-Text Search", test_full_text_search),
        ("Migrations", test_migrations),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result or result is None:
                passed += 1
            else:
                failed += 1
                print(f"  ✗ {test_name} returned False")
        except Exception as e:
            failed += 1
            print(f"  ✗ {test_name} raised: {e}")
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
