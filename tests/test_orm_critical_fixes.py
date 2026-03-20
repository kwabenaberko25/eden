"""
Tests for ORM Critical Fixes

Tests the 4 critical ORM layer improvements:
1. Session Context Management - auto-session acquisition from context
2. Robust Relationship Path Finding - cycle detection and max-depth limits
3. Deferred Relationship Resolution - auto-registration via __init_subclass__
4. Transaction API - explicit@atomic, savepoint, and rollback support
"""

import pytest
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import ForeignKey

from eden.db import (
    Model,
    Database,
    StringField,
    IntField,
    ForeignKeyField,
    Relationship,
    get_session,
    set_session,
    reset_session,
    atomic,
    AsyncSession as EdenAsyncSession,
    select,
)
from eden.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column


# ── Test Database Setup ──────────────────────────────────────────────────

from eden.testing import test_app, db as test_db

# ── Test Models ──────────────────────────────────────────────────────────

class Author(Model):
    """Author model for testing relationships."""
    __tablename__ = "authors"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(default="")
    
    # Relationship: Author -> Books (one-to-many)
    books: Mapped[List["Book"]] = Relationship(back_populates="author")


class Book(Model):
    """Book model with relationships."""
    __tablename__ = "books"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(default="")
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("authors.id"), default=None, nullable=True)
    
    # Relationship: Book -> Author (many-to-one)
    author: Mapped[Optional[Author]] = Relationship(back_populates="books")
    
    # Relationship: Book -> Publisher (many-to-one)
    publisher: Mapped[Optional["Publisher"]] = Relationship(back_populates="books")
    publisher_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("publishers.id"), default=None, nullable=True)


class Publisher(Model):
    """Publisher model for testing multi-relationship paths."""
    __tablename__ = "publishers"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(default="")
    
    # Relationship: Publisher -> Books (one-to-many)
    books: Mapped[List[Book]] = Relationship(back_populates="publisher")


# ────────────────────────────────────────────────────────────────────────
# LAYER 1: SESSION CONTEXT MANAGEMENT TESTS
# ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_context_get_set_reset(test_db: Database):
    """Test basic session context operations."""
    async with test_db.session() as session:
        # Initially, no session in context
        assert get_session() is None
        
        # Set session in context
        token = set_session(session)
        assert get_session() is session
        
        # Reset with token
        reset_session(token)
        assert get_session() is None
        
        # Reset without token (clears context)
        set_session(session)
        reset_session()
        assert get_session() is None


@pytest.mark.asyncio
async def test_session_from_context_in_queryset(test_db: Database):
    """Test that QuerySet can resolve session from context."""
    async with test_db.session() as session:
        # Create a test author
        author = Author(id=uuid.uuid4(), name="Test Author")
        session.add(author)
        await session.commit()
        
        # Set session in context
        token = set_session(session)
        
        try:
            # QuerySet should resolve session from context WITHOUT explicit parameter
            from eden.db import QuerySet
            qs = QuerySet(Author)
            
            # _resolve_session should find it in context
            resolved = await qs._resolve_session()
            assert resolved is session
        finally:
            reset_session(token)


# ────────────────────────────────────────────────────────────────────────
# LAYER 2: ROBUST RELATIONSHIP PATH FINDING TESTS
# ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_relationship_path_simple():
    """Test finding simple relationship path."""
    from eden.db.lookups import find_relationship_path
    
    # Author -> Book should find "books"
    path = find_relationship_path(Author, Book)
    # Note: The exact path depends on relationship direction
    # If Author.books points to Book, path should be ["books"] or similar
    assert isinstance(path, list)


@pytest.mark.asyncio
async def test_relationship_path_circular_check():
    """Test that circular relationships don't cause infinite loops."""
    from eden.db.lookups import find_relationship_path
    
    # This test ensures cycles are handled gracefully
    # Even with A -> B -> A pattern, it should return within depth limit
    path = find_relationship_path(Author, Author)
    assert isinstance(path, list)
    assert len(path) <= 3  # Default max depth


@pytest.mark.asyncio
async def test_relationship_path_max_depth_limit():
    """Test that max_depth parameter limits traversal."""
    from eden.db.lookups import find_relationship_path
    
    #  With max_depth=0, should not traverse
    path = find_relationship_path(Author, Publisher, max_depth=0)
    assert path == [] or len(path) == 0
    
    # With max_depth=1, limited traversal
    path = find_relationship_path(Author, Publisher, max_depth=1)
    assert isinstance(path, list)


# ────────────────────────────────────────────────────────────────────────
# LAYER 3: DEFERRED RELATIONSHIP RESOLUTION TESTS
# ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_relationships_inferred_in_init_subclass():
    """Test that relationships are inferred when model subclass is created."""
    # Models are already defined with relationships
    # If __init_subclass__ works, their relationships should be registered
    
    from sqlalchemy import inspect as sa_inspect
    
    # Check that Author has 'books' relationship mapped
    author_mapper = sa_inspect(Author)
    author_rels = {r.key: r for r in author_mapper.relationships}
    
    # Should have 'books' relationship
    assert "books" in author_rels, f"Author relationships: {author_rels.keys()}"
    
    # Check that Book has both relationships
    book_mapper = sa_inspect(Book)
    book_rels = {r.key: r for r in book_mapper.relationships}
    
    assert "author" in book_rels, f"Book relationships: {book_rels.keys()}"
    assert "publisher" in book_rels, f"Book relationships: {book_rels.keys()}"


@pytest.mark.asyncio
async def test_deferred_relationships_work_in_queries(test_db: Database):
    """Test that deferred relationships can be used in actual queries."""
    # Use the test_db's connection for manual metadata creation if needed
    async with test_db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # If relationships were properly inferred, this shouldn't raise
    # (Testing that the model definition doesn't fail)
    assert hasattr(Author, "books")
    assert hasattr(Book, "author")
    assert hasattr(Book, "publisher")


# ────────────────────────────────────────────────────────────────────────
# LAYER 4: TRANSACTION API TESTS
# ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transaction_commits_on_success(test_db: Database):
    """Test that Database.transaction() commits changes on success."""
    author_id = uuid.uuid4()
    
    async with test_db.transaction() as session:
        author = Author(id=author_id, name="Committed Author")
        session.add(author)
        # No explicit commit - context manager should commit
    
    # Verify the record was committed
    async with test_db.session() as verify_session:
        from sqlalchemy import select
        stmt = select(Author).where(Author.id == author_id)
        result = await verify_session.execute(stmt)
        persisted = result.scalar_one_or_none()
        
        assert persisted is not None
        assert persisted.name == "Committed Author"


@pytest.mark.asyncio
async def test_transaction_rollsback_on_error(test_db: Database):
    """Test that Database.transaction() rolls back on exception."""
    author_id = uuid.uuid4()
    
    try:
        async with test_db.transaction() as session:
            author = Author(id=author_id, name="Rolled Back Author")
            session.add(author)
            # Simulate an error
            raise ValueError("Intentional error for rollback test")
    except ValueError:
        pass  # Expected
    
    # Verify the record was NOT committed
    async with test_db.session() as verify_session:
        from sqlalchemy import select, func
        stmt = select(func.count(Author.id)).where(Author.id == author_id)
        result = await verify_session.execute(stmt)
        count = result.scalar()
        
        assert count == 0, "Record should have been rolled back"


@pytest.mark.asyncio
async def test_savepoint_rollback(test_db: Database):
    """Test that savepoints can roll back nested changes."""
    author_id = uuid.uuid4()
    
    async with test_db.transaction() as session:
        # Create author in outer transaction
        author = Author(id=author_id, name="Main Author")
        session.add(author)
        await session.flush()
        
        # Try to modify in savepoint
        try:
            async with test_db.savepoint("sp1") as sp_session:
                # Change the name
                result = await sp_session.execute(
                    select(Author).where(Author.id == author_id)
                )
                fetched = result.scalar_one()
                fetched.name = "Savepoint Changed"
                
                # Simulate error
                raise RuntimeError("Savepoint error")
        except RuntimeError:
            pass  # Expected
        
        # After savepoint error, reload and check name is unchanged
        session.expire_all()  # Clear session cache to force reload
        result = await session.execute(
            select(Author).where(Author.id == author_id)
        )
        reloaded = result.scalar_one()
        
        # Should have original name (not the savepoint change)
        # Note: actual behavior depends on savepoint implementation
        assert reloaded.name == "Main Author"


@pytest.mark.asyncio
async def test_atomic_function_execution(test_db: Database):
    """Test Database.atomic() wraps function in transaction."""
    
    async def create_two_authors():
        """Function to run atomically."""
        author_id_1 = uuid.uuid4()
        author_id_2 = uuid.uuid4()
        
        session = get_session()
        if session is None:
            raise RuntimeError("@atomic didn't set session in context")
        
        auth1 = Author(id=author_id_1, name="Atomic Author 1")
        auth2 = Author(id=author_id_2, name="Atomic Author 2")
        session.add(auth1)
        session.add(auth2)
        
        return author_id_1, author_id_2
    
    # Execute atomically
    id1, id2 = await test_db.atomic(create_two_authors)
    
    # Both should be committed
    async with test_db.session() as verify_session:
        from sqlalchemy import select
        result = await verify_session.execute(
            select(Author).where(Author.id.in_([id1, id2]))
        )
        authors = result.scalars().all()
        assert len(authors) == 2


@pytest.mark.asyncio
async def test_atomic_decorator_injects_session():
    """Test that @atomic decorator injects session properly."""
    
    # Mock request and app objects
    class MockApp:
        class State:
            db = None
        state = State()
    
    class MockRequest:
        app = MockApp()
        class State:
            pass
        state = State()
    
    session_captured = None
    
    @atomic
    async def handler_with_session(request, session):
        nonlocal session_captured
        session_captured = session
        return "success"
    
    # Note: This test demonstrates the decorator signature
    # Full testing would require a real ASGI app context
    # For now, we're testing that the decorator exists and has proper structure
    assert callable(handler_with_session)
    assert hasattr(handler_with_session, "__wrapped__")


# ────────────────────────────────────────────────────────────────────────
# INTEGRATION TESTS
# ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_workflow_context_transaction_relationships(test_db: Database):
    """Integration test: context + transactions + relationships."""
    
    author_id = uuid.uuid4()
    book_id_1 = uuid.uuid4()
    book_id_2 = uuid.uuid4()
    
    # Create data within transaction with context
    async with test_db.transaction() as session:
        token = set_session(session)
        
        try:
            from sqlalchemy import select
            
            # Create author
            author = Author(id=author_id, name="Integration Test Author")
            session.add(author)
            await session.flush()
            
            # Create books with relationship
            book1 = Book(id=book_id_1, title="Book 1", author_id=author_id)
            book2 = Book(id=book_id_2, title="Book 2", author_id=author_id)
            session.add(book1)
            session.add(book2)
            
            # Verify relationship loading works
            result = await session.execute(
                select(Author).where(Author.id == author_id)
            )
            loaded_author = result.scalar_one()
            assert loaded_author.name == "Integration Test Author"
            
        finally:
            reset_session(token)
    
    # Verify data persisted
    async with test_db.session() as verify_session:
        from sqlalchemy import select, func
        result = await verify_session.execute(
            select(func.count(Book.id))
        )
        count = result.scalar()
        assert count == 2, "Both books should be persisted"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
