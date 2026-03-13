#!/usr/bin/env python
"""
Example: Testing the Eden ORM

This file demonstrates how to test the Eden ORM with practical examples.
Run with: python example_orm_test.py
"""

import asyncio
from datetime import datetime
from eden_orm import (
    Model,
    StringField,
    IntField,
    TextField,
    DateTimeField,
    UUIDField,
    BooleanField,
    ForeignKeyField,
)

# ============================================================================
# STEP 1: Define Your Models
# ============================================================================

class User(Model):
    """User model with various field types."""
    
    __tablename__ = "users"
    
    id: str = UUIDField(primary_key=True)
    email: str = StringField(unique=True, nullable=False)
    username: str = StringField(max_length=50)
    bio: str = TextField(nullable=True)
    age: int = IntField(nullable=True)
    is_active: bool = BooleanField(default=True)
    created_at: datetime = DateTimeField(auto_now_add=True)
    updated_at: datetime = DateTimeField(auto_now=True)


class Post(Model):
    """Blog post model with foreign key to User."""
    
    __tablename__ = "posts"
    
    id: str = UUIDField(primary_key=True)
    title: str = StringField(max_length=200)
    content: str = TextField()
    author_id: str = ForeignKeyField("users")
    is_published: bool = BooleanField(default=False)
    created_at: datetime = DateTimeField(auto_now_add=True)


class Comment(Model):
    """Comment model with relationships."""
    
    __tablename__ = "comments"
    
    id: str = UUIDField(primary_key=True)
    content: str = TextField()
    author_id: str = ForeignKeyField("users")
    post_id: str = ForeignKeyField("posts")
    created_at: datetime = DateTimeField(auto_now_add=True)


# ============================================================================
# STEP 2: Test Field Definitions
# ============================================================================

def test_field_definitions():
    """Test that field types are properly defined."""
    print("\n" + "="*70)
    print("TEST 1: Field Definitions")
    print("="*70)
    
    # Test StringField
    email_field = StringField(unique=True, max_length=255)
    assert email_field.unique == True
    assert email_field.max_length == 255
    print("✓ StringField attributes stored correctly")
    
    # Test IntField
    age_field = IntField(nullable=True)
    assert age_field.nullable == True
    print("✓ IntField attributes stored correctly")
    
    # Test BooleanField
    active_field = BooleanField(default=True)
    assert active_field.default == True
    print("✓ BooleanField with default value")
    
    # Test DateTimeField
    created_field = DateTimeField(auto_now_add=True)
    assert created_field.auto_now_add == True
    print("✓ DateTimeField with auto_now_add")
    
    # Test ForeignKeyField
    author_field = ForeignKeyField("users")
    assert author_field is not None
    print("✓ ForeignKeyField created")
    
    print("\n✓ All field definitions passed!\n")


# ============================================================================
# STEP 3: Test Model Definition & Instantiation
# ============================================================================

def test_model_instantiation():
    """Test that models can be instantiated with field values."""
    print("="*70)
    print("TEST 2: Model Instantiation")
    print("="*70)
    
    # Create a user instance (in-memory, no database)
    user = User(
        id="user-123",
        email="john@example.com",
        username="johndoe",
        age=30,
    )
    
    assert user.email == "john@example.com"
    assert user.username == "johndoe"
    assert user.age == 30
    print("✓ User model instantiated with correct attributes")
    
    # Create a post instance
    post = Post(
        id="post-456",
        title="Introduction to Eden ORM",
        content="Eden ORM is a powerful async ORM...",
        author_id="user-123",
    )
    
    assert post.title == "Introduction to Eden ORM"
    assert post.author_id == "user-123"
    print("✓ Post model instantiated with correct attributes")
    
    # Create a comment
    comment = Comment(
        id="comment-789",
        content="Great post!",
        author_id="user-123",
        post_id="post-456",
    )
    
    assert comment.content == "Great post!"
    assert comment.post_id == "post-456"
    print("✓ Comment model instantiated with correct attributes")
    
    print("\n✓ All model instantiation tests passed!\n")


# ============================================================================
# STEP 4: Test Query Builder
# ============================================================================

def test_query_builder():
    """Test that query objects can be built correctly."""
    print("="*70)
    print("TEST 3: Query Builder")
    print("="*70)
    
    from eden_orm.query import FilterChain
    
    # Create a filter chain
    filter_chain = FilterChain(model_class=User)
    assert filter_chain.model_class == User
    print("✓ FilterChain created for User model")
    
    # Test chaining
    filter_chain = filter_chain.filter(is_active=True)
    assert filter_chain.conditions is not None
    print("✓ Filter conditions applied to query")
    
    # Test ordering
    filter_chain = filter_chain.order_by("-created_at")
    assert filter_chain.order_fields is not None
    print("✓ Ordering applied to query")
    
    # Test pagination
    filter_chain = filter_chain.limit(10).offset(0)
    assert filter_chain.limit_value == 10
    assert filter_chain.offset_value == 0
    print("✓ Limit and offset applied to query")
    
    print("\n✓ All query builder tests passed!\n")


# ============================================================================
# STEP 5: Test Pagination
# ============================================================================

def test_pagination():
    """Test the pagination system."""
    print("="*70)
    print("TEST 4: Pagination")
    print("="*70)
    
    from eden_orm.pagination import Page
    
    # Create a page object
    items = list(range(1, 11))  # Items 1-10
    page = Page(items=items, page=1, per_page=10, total=25)
    
    assert page.page == 1
    assert page.per_page == 10
    assert page.total == 25
    print("✓ Page object created with correct properties")
    
    # Test page calculations
    assert page.total_pages == 3
    assert page.has_next == True
    assert page.has_previous == False
    assert page.start_index == 0
    assert page.end_index == 9
    print("✓ Page calculations correct (0-based indices)")
    
    # Test page 2
    page2 = Page(items=list(range(11, 21)), page=2, per_page=10, total=25)
    assert page2.previous_page == 1
    assert page2.next_page == 3
    print("✓ Page navigation properties work correctly")
    
    print("\n✓ All pagination tests passed!\n")


# ============================================================================
# STEP 6: Test Caching System
# ============================================================================

def test_caching():
    """Test the query caching system."""
    print("="*70)
    print("TEST 5: Caching System")
    print("="*70)
    
    from eden_orm.cache import QueryCache
    
    # Test QueryCache
    query_cache = QueryCache()
    
    # Test key generation
    key = query_cache.generate_key("SELECT * FROM users WHERE id = ?", ["123"])
    assert key.startswith("query:")
    assert len(key) > 10
    print("✓ Cache key generated from SQL query")
    
    print("\n✓ All caching tests passed!\n")


# ============================================================================
# STEP 7: Test Audit System
# ============================================================================

def test_audit_system():
    """Test the audit trail system."""
    print("="*70)
    print("TEST 6: Audit Trail System")
    print("="*70)
    
    from eden_orm.audit import AuditLogger, AuditEntry, AuditAction
    
    # Test AuditAction enum
    assert AuditAction.CREATE == "CREATE"
    assert AuditAction.UPDATE == "UPDATE"
    assert AuditAction.DELETE == "DELETE"
    assert AuditAction.RESTORE == "RESTORE"
    print("✓ AuditAction enum has all required actions")
    
    # Test AuditEntry
    entry = AuditEntry(
        model_name="User",
        record_id="user-123",
        action=AuditAction.CREATE,
        user_id="admin",
        new_data={"email": "john@example.com", "username": "johndoe"},
    )
    
    assert entry.model_name == "User"
    assert entry.record_id == "user-123"
    assert entry.action == AuditAction.CREATE
    print("✓ AuditEntry created with correct attributes")
    
    # Test serialization
    entry_dict = entry.to_dict()
    assert entry_dict["model_name"] == "User"
    assert entry_dict["action"] == AuditAction.CREATE
    print("✓ AuditEntry serializes to dictionary")
    
    print("\n✓ All audit system tests passed!\n")


# ============================================================================
# STEP 8: Test Full-Text Search
# ============================================================================

def test_fts_system():
    """Test the full-text search system."""
    print("="*70)
    print("TEST 7: Full-Text Search System")
    print("="*70)
    
    from eden_orm.search import SearchQueryBuilder, SearchResult, FullTextSearchEngine
    
    # Test SearchQueryBuilder
    builder = SearchQueryBuilder("python")
    assert builder.base_query == "python"
    print("✓ SearchQueryBuilder created with base query")
    
    # Test chaining
    builder = builder.add_term("orm")
    builder = builder.add_phrase("full text search")
    builder = builder.exclude("deprecated")
    assert len(builder.terms) == 1
    assert len(builder.phrases) == 1
    assert len(builder.excluded) == 1
    print("✓ SearchQueryBuilder supports chaining")
    
    # Test query building
    final_query = builder.build()
    assert "orm" in final_query
    assert "deprecated" in final_query
    print("✓ SearchQueryBuilder builds complex queries")
    
    # Test SearchResult
    result = SearchResult(id="post-123", relevance=0.95)
    assert result.id == "post-123"
    assert result.relevance == 0.95
    print("✓ SearchResult dataclass works correctly")
    
    # Test FTS Engine
    engine = FullTextSearchEngine()
    engine.register_index(Post, ["title", "content"])
    assert "Post" in engine.indexed_fields
    print("✓ FullTextSearchEngine registers indices")
    
    print("\n✓ All FTS system tests passed!\n")


# ============================================================================
# STEP 9: Test Migrations
# ============================================================================

def test_migrations():
    """Test the migrations system."""
    print("="*70)
    print("TEST 8: Migrations System")
    print("="*70)
    
    from eden_orm.migrations.runner import MigrationRunner
    from pathlib import Path
    
    # Test MigrationRunner
    runner = MigrationRunner(migrations_dir="migrations")
    assert runner.migrations_dir == Path("migrations")
    print("✓ MigrationRunner initialized with dir")
    
    # Test that migrations directory is created
    assert runner.migrations_dir.exists()
    print("✓ Migrations directory created")
    
    print("\n✓ All migration tests passed!\n")


# ============================================================================
# MAIN: Run All Tests
# ============================================================================

def main():
    """Run all example tests."""
    print("\n" + "="*70)
    print("EDEN ORM - EXAMPLE TESTS")
    print("="*70)
    print("Demonstrating how to test the Eden ORM\n")
    
    try:
        test_field_definitions()
        test_model_instantiation()
        test_query_builder()
        test_pagination()
        test_caching()
        test_audit_system()
        test_fts_system()
        test_migrations()
        
        print("="*70)
        print("✓ ALL EXAMPLE TESTS PASSED")
        print("="*70)
        print("\nNow you can:")
        print("1. Modify these tests to cover your specific use cases")
        print("2. Define your own models based on the examples above")
        print("3. Test with real data using async/await")
        print("4. Integrate with your application\n")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
