import pytest
import asyncio
from sqlalchemy import text
from eden.db import (
    Model, f, Relationship, Reference, 
    StringField, IntField, FloatField, UUIDField, ForeignKeyField
)
from eden.db.session import Database, get_session
from eden.tenancy.models import Tenant
from eden.db.aggregates import Sum, Avg, Count

# Postgres Test Configuration
POSTGRES_URL = "postgresql+asyncpg://postgres:0123456789@localhost:5432/eden_tests"

from sqlalchemy.orm import Mapped

# --- Test Models ---

class LiveAuthor(Model):
    __tablename__ = "live_authors"
    name: Mapped[str] = StringField(max_length=100)
    tenant_id: Mapped[str | None] = UUIDField(nullable=True) 
    books: Mapped[list["LiveBook"]] = Relationship(back_populates="author")

class LiveBook(Model):
    __tablename__ = "live_books"
    title: Mapped[str] = StringField(max_length=200)
    price: Mapped[float] = FloatField(default=0.0)
    author_id: Mapped[str] = ForeignKeyField("live_authors.id")
    
    author: Mapped["LiveAuthor"] = Reference(back_populates="books")
    reviews: Mapped[list["LiveReview"]] = Relationship(back_populates="book")

class LiveReview(Model):
    __tablename__ = "live_reviews"
    content: Mapped[str] = StringField(max_length=1000) # content is often text
    rating: Mapped[int] = IntField(default=0)
    book_id: Mapped[str] = ForeignKeyField("live_books.id")
    
    book: Mapped["LiveBook"] = Reference(back_populates="reviews")


@pytest.fixture(scope="module")
async def db_pg():
    """Fixture to manage a real Postgres connection lifecycle."""
    from sqlalchemy.pool import NullPool
    # Use NullPool to ensure search_path doesn't leak between pooled connections
    db = Database(url=POSTGRES_URL, poolclass=NullPool)
    await db.connect()
    
    # Create all tables in public schema for initial setup
    async with db.transaction() as session:
        def _create_all(sync_session):
            Model.metadata.create_all(bind=sync_session.connection())
        await session.run_sync(_create_all)
    
    yield db

    # Cleanup: Drop everything in public with CASCADE and disconnect
    async with db.transaction() as session:
        from sqlalchemy import text
        # On Postgres, we need CASCADE to handle dependencies cleanly
        await session.execute(text("DROP TABLE IF EXISTS live_reviews CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS live_books CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS live_authors CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS eden_tenants CASCADE"))
        
        # Also drop the test schemas
        await session.execute(text("DROP SCHEMA IF EXISTS tenant_alpha CASCADE"))
        await session.execute(text("DROP SCHEMA IF EXISTS tenant_beta CASCADE"))
        
    await db.disconnect()

@pytest.mark.asyncio
async def test_postgres_session_identity(db_pg):
    """
    1. DB connection and closure is working.
    Verifies that the entire framework uses a single session within a transaction.
    """
    async with db_pg.transaction() as session:
        # Check that get_session() returns the same object
        context_session = get_session()
        assert context_session is session
        assert id(context_session) == id(session)
        
        # Verify multiple queries use the same session identity
        q1 = LiveAuthor.query()
        async with q1._provide_session() as s1:
            assert s1 is session
        
        q2 = LiveBook.query()
        async with q2._provide_session() as s2:
            assert s2 is session
        
        # Ensure they all share an active transaction
        assert session.in_transaction()

@pytest.mark.asyncio
async def test_postgres_orm_complex_lookups(db_pg):
    """
    2. The ORM, models and queries, complex aggregation and lookups work.
    Verifies Layer 3 (Deep Path) and Layer 2 (Session) on Postgres.
    """
    async with db_pg.transaction() as session:
        # Setup data
        author = LiveAuthor(name="Postgres Pro")
        session.add(author)
        await session.flush()
        
        book = LiveBook(title="Eden for Postgres", price=45.0, author_id=author.id)
        session.add(book)
        await session.flush()
        
        review = LiveReview(content="Great!", rating=5, book_id=book.id)
        session.add(review)
        await session.flush()
        
        # Test 1: Deep Path Lookup (Auto-Join)
        # Find books by authors with certain name
        qs = LiveBook.filter(author__name="Postgres Pro")
        found_books = await qs.all()
        assert len(found_books) == 1
        assert found_books[0].title == "Eden for Postgres"
        
        # Test 2: Complex Aggregation
        # Count reviews for books by this author
        stats = await LiveBook.filter(author__name="Postgres Pro").annotate(
            review_count=Count("reviews"),
            avg_rating=Avg("reviews__rating")
        ).values("title", "review_count", "avg_rating")
        
        assert stats[0]["review_count"] == 1
        assert stats[0]["avg_rating"] == 5.0

@pytest.mark.asyncio
async def test_postgres_multi_tenancy_schemas(db_pg, monkeypatch):
    """
    3. Multi tenancy works with the postgres schema setup.
    Verifies isolation using PG search_path and Tenant.provision_schema.
    """
    # Mock MigrationManager.stamp to avoid failure if migrations folder doesn't exist
    from eden.db.migrations import MigrationManager
    # Mock MigrationManager.stamp to avoid failure if migrations folder doesn't exist
    from eden.db.migrations import MigrationManager
    # 1. Clean state
    async with db_pg.transaction() as session:
        await session.execute(text("DROP SCHEMA IF EXISTS tenant_alpha CASCADE"))
        await session.execute(text("DROP SCHEMA IF EXISTS tenant_beta CASCADE"))
        await session.execute(text("DELETE FROM live_authors"))
        await session.execute(text("DELETE FROM eden_tenants"))

    # 2. Create tenants
    async with db_pg.transaction() as session:
        t1 = Tenant(name="Tenant Alpha", slug="alpha", schema_name="tenant_alpha")
        t2 = Tenant(name="Tenant Beta", slug="beta", schema_name="tenant_beta")
        session.add_all([t1, t2])
        await session.flush()
        
        # Provision t1
        await t1.provision_schema(session)
        # Check if table exists in alpha
        res = await session.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'tenant_alpha' AND table_name = 'live_authors'"))
        assert res.scalar() == 1, "Table live_authors not found in tenant_alpha"

        # Provision t2
        await t2.provision_schema(session)
        # Check if table exists in beta
        res = await session.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'tenant_beta' AND table_name = 'live_authors'"))
        assert res.scalar() == 1, "Table live_authors not found in tenant_beta"

    # 3. Insert Alpha data
    async with db_pg.transaction() as session:
        await db_pg.set_schema(session, "tenant_alpha")
        session.add(LiveAuthor(name="Alpha Author"))
        await session.flush()
    
    # 4. Insert Beta data
    async with db_pg.transaction() as session:
        await db_pg.set_schema(session, "tenant_beta")
        session.add(LiveAuthor(name="Beta Author"))
        await session.flush()

    # 5. Verify Isolation
    async with db_pg.transaction() as session:
        # Verify Alpha only has Alpha
        await db_pg.set_schema(session, "tenant_alpha")
        authors = await LiveAuthor.query().all()
        names = [a.name for a in authors]
        assert len(authors) == 1, f"Alpha expected 1, got {names}"
        assert names[0] == "Alpha Author"

        # Verify Beta only has Beta
        await db_pg.set_schema(session, "tenant_beta")
        authors_b = await LiveAuthor.query().all()
        names_b = [a.name for a in authors_b]
        assert len(authors_b) == 1, f"Beta expected 1, got {names_b}"
        assert names_b[0] == "Beta Author"
        
    # Check Beta: Should ONLY see Beta Author
    async with db_pg.transaction() as session:
        session.expire_all()
        await session.execute(text("SET search_path TO tenant_beta, public"))
        authors_in_beta = await LiveAuthor.query().all()
        assert len(authors_in_beta) == 1
        assert authors_in_beta[0].name == "Beta Author"
        
    # 6. Cleanup dynamic schemas
    async with db_pg.transaction() as session:
        await session.execute(text("DROP SCHEMA IF EXISTS tenant_alpha CASCADE"))
        await session.execute(text("DROP SCHEMA IF EXISTS tenant_beta CASCADE"))
