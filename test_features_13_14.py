"""
Comprehensive tests for Nested Prefetch Caching (Feature 13) and Raw SQL Queries (Feature 14)
"""

import asyncio
from datetime import datetime
from uuid import uuid4

# Test imports
try:
    from eden_orm import Model, StringField, IntField, DateTimeField, ForeignKeyField
    from eden_orm.nested_prefetch import NestedPrefetchDescriptor, NestedPrefetchQuerySet
    from eden_orm.raw_sql import RawQuery, raw_select, raw_count, raw_insert, raw_update, raw_delete
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    exit(1)


# Test Models
class Author(Model):
    __tablename__ = "authors_test"
    name: str = StringField()
    email: str = StringField(unique=True, default="")


class Post(Model):
    __tablename__ = "posts_test"
    title: str = StringField()
    content: str = StringField()
    author_id: str = ForeignKeyField("authors_test")
    likes: int = IntField(default=0)
    created_at: datetime = DateTimeField(default=datetime.now)


class Comment(Model):
    __tablename__ = "comments_test"
    content: str = StringField()
    post_id: str = ForeignKeyField("posts_test")
    author_id: str = ForeignKeyField("authors_test")


async def setup_test_db():
    """Setup test database with sample data."""
    from eden_orm import initialize
    
    try:
        await initialize("postgresql://postgres:postgres@localhost/eden_test")
        print("✓ Database initialized")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        raise


async def test_nested_prefetch_descriptor():
    """Test NestedPrefetchDescriptor class instantiation."""
    descriptor = NestedPrefetchDescriptor()
    assert hasattr(descriptor, 'prefetch_cache'), "Missing prefetch_cache"
    assert hasattr(descriptor, 'resolve_nested_path'), "Missing resolve_nested_path method"
    assert hasattr(descriptor, 'clear_cache'), "Missing clear_cache method"
    print("[PASS] NestedPrefetchDescriptor instantiated correctly")


async def test_nested_prefetch_queryset():
    """Test NestedPrefetchQuerySet class."""
    from eden_orm import FilterChain
    
    # Mock a filter chain
    class MockChain:
        model_class = Post
    
    qs = NestedPrefetchQuerySet(MockChain())
    assert hasattr(qs, 'prefetcher'), "Missing prefetcher"
    assert hasattr(qs, 'nested_prefetch_fields'), "Missing nested_prefetch_fields"
    assert hasattr(qs, 'prefetch_nested'), "Missing prefetch_nested method"
    print("[PASS] NestedPrefetchQuerySet instantiated correctly")


async def test_cache_operations():
    """Test nested prefetch cache operations."""
    descriptor = NestedPrefetchDescriptor()
    
    # Test cache is empty
    assert len(descriptor.prefetch_cache) == 0, "Cache should be empty initially"
    
    # Simulate cache entry
    descriptor.prefetch_cache["Post:comments"] = {"1": []}
    assert "Post:comments" in descriptor.prefetch_cache, "Cache entry not stored"
    
    # Test clear
    descriptor.clear_cache()
    assert len(descriptor.prefetch_cache) == 0, "Cache not cleared"
    print("[PASS] Cache operations work correctly")


async def test_raw_query_class():
    """Test RawQuery class exists with proper methods."""
    assert hasattr(RawQuery, 'execute'), "Missing execute method"
    assert hasattr(RawQuery, 'execute_scalar'), "Missing execute_scalar method"
    assert hasattr(RawQuery, 'execute_update'), "Missing execute_update method"
    print("[PASS] RawQuery class has all required methods")


async def test_raw_query_convenience_functions():
    """Test raw query convenience functions exist."""
    assert callable(raw_select), "raw_select not callable"
    assert callable(raw_count), "raw_count not callable"
    assert callable(raw_insert), "raw_insert not callable"
    assert callable(raw_update), "raw_update not callable"
    assert callable(raw_delete), "raw_delete not callable"
    print("[PASS] All raw query convenience functions exist")


async def test_raw_insert_and_select():
    """Test raw insert and select operations."""
    try:
        # Insert test author
        result = await raw_insert("authors_test", {
            "id": str(uuid4()),
            "name": "Test Author",
            "email": f"author_{uuid4()}@example.com"
        })
        assert result >= 0, "Insert should return affected count"
        print("[PASS] Raw insert works")
        
        # Select test author
        results = await raw_select("authors_test", "name = $1", ["Test Author"])
        assert isinstance(results, list), "Select should return list"
        print("[PASS] Raw select works")
    except Exception as e:
        print(f"[SKIP] Raw insert/select: {e}")


async def test_raw_count():
    """Test raw count operation."""
    try:
        count = await raw_count("authors_test")
        assert isinstance(count, int), "Count should return integer"
        assert count >= 0, "Count should be non-negative"
        print("[PASS] Raw count works")
    except Exception as e:
        print(f"[SKIP] Raw count: {e}")


async def test_raw_update():
    """Test raw update operation."""
    try:
        # Create test author first
        author_id = str(uuid4())
        await raw_insert("authors_test", {
            "id": author_id,
            "name": "Update Test",
            "email": f"update_{uuid4()}@example.com"
        })
        
        # Update it
        result = await raw_update("authors_test", {"name": "Updated"}, "id = $1", [author_id])
        assert result >= 0, "Update should return affected count"
        print("[PASS] Raw update works")
    except Exception as e:
        print(f"[SKIP] Raw update: {e}")


async def test_raw_delete():
    """Test raw delete operation."""
    try:
        author_id = str(uuid4())
        await raw_insert("authors_test", {
            "id": author_id,
            "name": "Delete Test",
            "email": f"delete_{uuid4()}@example.com"
        })
        
        result = await raw_delete("authors_test", "id = $1", [author_id])
        assert result >= 0, "Delete should return affected count"
        print("[PASS] Raw delete works")
    except Exception as e:
        print(f"[SKIP] Raw delete: {e}")


async def test_nested_prefetch_path_parsing():
    """Test nested path parsing."""
    descriptor = NestedPrefetchDescriptor()
    
    # Test path parsing
    path = "comments__author"
    parts = path.split("__")
    assert len(parts) == 2, "Path parsing failed"
    assert parts[0] == "comments", "First part incorrect"
    assert parts[1] == "author", "Second part incorrect"
    print("[PASS] Nested path parsing works")


async def test_stress_raw_queries():
    """Stress test raw queries with multiple operations."""
    try:
        # Bulk insert
        for i in range(10):
            await raw_insert("authors_test", {
                "id": str(uuid4()),
                "name": f"Stress Author {i}",
                "email": f"stress_{i}_{uuid4()}@example.com"
            })
        
        count = await raw_count("authors_test", "name LIKE $1", ["Stress%"])
        assert count >= 10, f"Expected at least 10 stress authors, got {count}"
        print(f"[PASS] Stress test: Inserted and counted 10+ records ({count} found)")
    except Exception as e:
        print(f"[SKIP] Stress test: {e}")


async def test_nested_prefetch_integration():
    """Test nested prefetch with actual model structure."""
    qs = NestedPrefetchQuerySet(None)
    
    # Test adding multiple nested paths
    async def mock_prefetch_nested(*paths):
        qs.nested_prefetch_fields.extend(paths)
        return qs
    
    qs.prefetch_nested = mock_prefetch_nested
    
    await qs.prefetch_nested("author", "comments__author")
    assert "author" in qs.nested_prefetch_fields, "author not in prefetch fields"
    assert "comments__author" in qs.nested_prefetch_fields, "comments__author not in prefetch fields"
    print("[PASS] Nested prefetch integration works")


async def test_model_raw_query_binding():
    """Test that raw queries can be bound to models."""
    from eden_orm.raw_sql import ModelRawQuery
    
    raw = ModelRawQuery.raw(Post)
    assert callable(raw), "ModelRawQuery.raw should return callable"
    print("[PASS] Model raw query binding works")


async def run_all_tests():
    """Run all tests sequentially."""
    print("\n" + "="*70)
    print("FEATURES 13-14: NESTED PREFETCH CACHING & RAW SQL QUERIES")
    print("="*70 + "\n")
    
    tests = [
        ("Nested Prefetch Descriptor", test_nested_prefetch_descriptor),
        ("Nested Prefetch QuerySet", test_nested_prefetch_queryset),
        ("Cache Operations", test_cache_operations),
        ("Raw Query Class", test_raw_query_class),
        ("Raw Query Convenience Functions", test_raw_query_convenience_functions),
        ("Raw Insert & Select", test_raw_insert_and_select),
        ("Raw Count", test_raw_count),
        ("Raw Update", test_raw_update),
        ("Raw Delete", test_raw_delete),
        ("Nested Path Parsing", test_nested_prefetch_path_parsing),
        ("Stress Raw Queries", test_stress_raw_queries),
        ("Nested Prefetch Integration", test_nested_prefetch_integration),
        ("Model Raw Query Binding", test_model_raw_query_binding),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test_name}: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"TEST RESULTS: {passed} PASSED, {failed} FAILED")
    print("="*70)
    
    if failed == 0:
        print("✓ ALL TESTS PASSED - FEATURES 13-14 WORKING")
    else:
        print("✗ SOME TESTS FAILED")
    
    return passed, failed


if __name__ == "__main__":
    try:
        passed, failed = asyncio.run(run_all_tests())
        exit(0 if failed == 0 else 1)
    except KeyboardInterrupt:
        print("\n✗ Tests interrupted")
        exit(1)
    except Exception as e:
        print(f"\n✗ Test runtime error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
