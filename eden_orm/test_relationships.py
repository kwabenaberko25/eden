"""
Phase 2 Tests: Relationships & Eager Loading

Tests for select_related() JOIN-based eager loading and prefetch_related().
"""

import asyncio
from datetime import datetime
from uuid import uuid4

from .base import Model
from .fields import StringField, IntField, DateTimeField, UUIDField, ForeignKeyField


class Author(Model):
    """Test model: Author"""
    __tablename__ = "authors"
    
    id = UUIDField(primary_key=True)
    name = StringField(max_length=100)
    email = StringField(max_length=255)
    created_at = DateTimeField(auto_now_add=True)


class Post(Model):
    """Test model: Post with FK to Author"""
    __tablename__ = "posts"
    
    id = UUIDField(primary_key=True)
    title = StringField(max_length=255)
    content = StringField()
    author_id = ForeignKeyField(to=Author)
    created_at = DateTimeField(auto_now_add=True)


class Comment(Model):
    """Test model: Comment with FK to Post"""
    __tablename__ = "comments"
    
    id = UUIDField(primary_key=True)
    text = StringField()
    post_id = ForeignKeyField(to=Post)
    author_id = ForeignKeyField(to=Author)
    created_at = DateTimeField(auto_now_add=True)


async def test_select_related_generates_join():
    """Test that select_related() adds JOIN to SQL"""
    query_chain = Post.select_related("author")
    sql, params = query_chain._build_sql()
    
    # Should contain LEFT JOIN
    assert "LEFT JOIN" in sql, f"SQL missing JOIN: {sql}"
    assert "authors" in sql, f"SQL missing authors table: {sql}"
    assert "author_id" in sql, f"SQL missing FK reference: {sql}"
    
    print("✓ select_related() generates JOIN SQL")


async def test_select_related_with_filter():
    """Test select_related() combined with filter()"""
    query_chain = Post.select_related("author").filter(title="Test Post")
    sql, params = query_chain._build_sql()
    
    assert "LEFT JOIN" in sql, "Missing JOIN"
    assert "WHERE" in sql, "Missing WHERE clause"
    assert "title" in sql, "Missing title filter"
    
    print("✓ select_related() works with filters")


async def test_select_related_multiple():
    """Test multiple select_related() calls"""
    query_chain = Comment.select_related("post", "author")
    sql, params = query_chain._build_sql()
    
    assert sql.count("LEFT JOIN") >= 2, "Should have at least 2 JOINs"
    
    print("✓ Multiple select_related() calls work")


async def test_prefetch_related_fields():
    """Test that prefetch_related() populates field list"""
    query_chain = Post.prefetch_related("author", "comments")
    
    assert hasattr(query_chain, 'prefetch_related_fields'), "Missing prefetch_related_fields"
    assert "author" in query_chain.prefetch_related_fields, "author not in prefetch"
    assert "comments" in query_chain.prefetch_related_fields, "comments not in prefetch"
    
    print("✓ prefetch_related() populates field list")


async def test_select_related_chaining():
    """Test that select_related() returns self for chaining"""
    chain1 = Post.select_related("author")
    chain2 = chain1.filter(title="Test")
    
    assert isinstance(chain2, type(chain1)), "select_related() should return FilterChain"
    
    print("✓ select_related() supports method chaining")


async def test_relationship_field_detection():
    """Test that ForeignKeyField is properly detected"""
    author_id_field = Post.__fields__.get("author_id")
    
    assert author_id_field is not None, "author_id field not found"
    assert hasattr(author_id_field, "to_model"), "ForeignKeyField missing to_model"
    
    print("✓ ForeignKeyField properly configured")


async def test_query_chain_initialization():
    """Test that FilterChain initializes all fields"""
    chain = Post.all()
    
    assert hasattr(chain, 'select_related_fields'), "Missing select_related_fields"
    assert hasattr(chain, 'prefetch_related_fields'), "Missing prefetch_related_fields"
    assert isinstance(chain.select_related_fields, list), "select_related_fields should be list"
    assert isinstance(chain.prefetch_related_fields, list), "prefetch_related_fields should be list"
    
    print("✓ FilterChain initializes all fields")


async def run_tests():
    """Run all Phase 2 tests"""
    print("\n" + "="*60)
    print("PHASE 2: RELATIONSHIPS & EAGER LOADING TESTS")
    print("="*60 + "\n")
    
    tests = [
        test_select_related_generates_join,
        test_select_related_with_filter,
        test_select_related_multiple,
        test_prefetch_related_fields,
        test_select_related_chaining,
        test_relationship_field_detection,
        test_query_chain_initialization,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {str(e)}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    exit(0 if success else 1)
