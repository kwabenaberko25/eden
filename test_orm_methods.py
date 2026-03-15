"""
Tests for ORM methods: count(), get_or_404(), filter_one(), get_or_create(), bulk_create()
"""

import pytest
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from eden import Model, StringField, IntField, Database
from eden.exceptions import NotFound


# ──────────────────────────────────────────────────────────────────────────
# Test Models
# ──────────────────────────────────────────────────────────────────────────

class User(Model):
    """Test user model."""
    __tablename__ = "users"
    
    name: str = StringField(required=True)
    email: str = StringField(required=True, unique=True)
    age: int = IntField(required=False)


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
async def test_users(db_session):
    """Create test users."""
    user1 = User(name="Alice", email="alice@example.com", age=30)
    user2 = User(name="Bob", email="bob@example.com", age=25)
    user3 = User(name="Charlie", email="charlie@example.com", age=35)
    
    db_session.add(user1)
    db_session.add(user2)
    db_session.add(user3)
    await db_session.commit()
    
    # Refresh to get IDs
    await db_session.refresh(user1)
    await db_session.refresh(user2)
    await db_session.refresh(user3)
    
    return [user1, user2, user3]


# ──────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_queryset_count(db_session, test_users):
    """Test QuerySet.count() method."""
    count = await User.query(db_session).count()
    assert count == 3, f"Expected 3 users, got {count}"
    
    # Test count with filter
    count_alice = await User.query(db_session).filter(name="Alice").count()
    assert count_alice == 1, f"Expected 1 Alice, got {count_alice}"
    
    print("✅ count() works")


@pytest.mark.asyncio
async def test_model_count(db_session, test_users):
    """Test Model.count() class method."""
    count = await User.count(db_session)
    assert count == 3, f"Expected 3 users, got {count}"
    
    # Test count with filter
    count_young = await User.count(db_session, age__lt=30)
    assert count_young == 1, f"Expected 1 young user, got {count_young}"
    
    print("✅ Model.count() works")


@pytest.mark.asyncio
async def test_queryset_get_or_404(db_session, test_users):
    """Test QuerySet.get_or_404() method."""
    alice_id = test_users[0].id
    
    # Should find existing user
    user = await User.query(db_session).get_or_404(id=alice_id)
    assert user.name == "Alice", f"Expected Alice, got {user.name}"
    
    # Should raise NotFound when user doesn't exist
    with pytest.raises(NotFound):
        await User.query(db_session).get_or_404(id=uuid.uuid4())
    
    print("✅ QuerySet.get_or_404() works")


@pytest.mark.asyncio
async def test_model_get_or_404(db_session, test_users):
    """Test Model.get_or_404() class method."""
    alice_id = test_users[0].id
    
    # Should find existing user
    user = await User.get_or_404(db_session, alice_id)
    assert user.name == "Alice", f"Expected Alice, got {user.name}"
    
    # Should raise NotFound when user doesn't exist
    with pytest.raises(NotFound):
        await User.get_or_404(db_session, uuid.uuid4())
    
    print("✅ Model.get_or_404() works")


@pytest.mark.asyncio
async def test_queryset_filter_one(db_session, test_users):
    """Test QuerySet.filter_one() method."""
    # Should find user by email
    user = await User.query(db_session).filter_one(email="alice@example.com")
    assert user is not None, "Should find Alice"
    assert user.name == "Alice", f"Expected Alice, got {user.name}"
    
    # Should return None for non-existent user
    user_none = await User.query(db_session).filter_one(email="nonexistent@example.com")
    assert user_none is None, "Should return None for non-existent user"
    
    print("✅ QuerySet.filter_one() works")


@pytest.mark.asyncio
async def test_model_filter_one(db_session, test_users):
    """Test Model.filter_one() class method."""
    # Should find user by email
    user = await User.filter_one(db_session, email="bob@example.com")
    assert user is not None, "Should find Bob"
    assert user.name == "Bob", f"Expected Bob, got {user.name}"
    
    # Should return None for non-existent user
    user_none = await User.filter_one(db_session, email="fake@example.com")
    assert user_none is None, "Should return None"
    
    print("✅ Model.filter_one() works")


@pytest.mark.asyncio
async def test_queryset_get_or_create(db_session):
    """Test QuerySet.get_or_create() method."""
    # Create new user
    user, created = await User.query(db_session).get_or_create(
        email="diana@example.com",
        defaults={"name": "Diana", "age": 28}
    )
    assert created is True, "Should have created a new user"
    assert user.name == "Diana", f"Expected Diana, got {user.name}"
    
    # Get existing user
    user2, created = await User.query(db_session).get_or_create(
        email="diana@example.com",
        defaults={"name": "Different Name"}
    )
    assert created is False, "Should not have created a new user"
    assert user2.id == user.id, "Should be same user"
    assert user2.name == "Diana", "Should keep original name"
    
    print("✅ QuerySet.get_or_create() works")


@pytest.mark.asyncio
async def test_model_get_or_create(db_session):
    """Test Model.get_or_create() class method."""
    # Create new user
    user, created = await User.get_or_create(
        db_session,
        email="eve@example.com",
        defaults={"name": "Eve", "age": 32}
    )
    assert created is True, "Should have created a new user"
    assert user.name == "Eve", f"Expected Eve, got {user.name}"
    
    # Get existing user
    user2, created = await User.get_or_create(
        db_session,
        email="eve@example.com",
        defaults={"name": "Different"}
    )
    assert created is False, "Should not have created"
    assert user2.id == user.id, "Should be same user"
    
    print("✅ Model.get_or_create() works")


@pytest.mark.asyncio
async def test_queryset_bulk_create(db_session):
    """Test QuerySet.bulk_create() method."""
    users = [
        User(name="Frank", email="frank@example.com", age=40),
        User(name="Grace", email="grace@example.com", age=26),
        User(name="Henry", email="henry@example.com", age=45),
    ]
    
    count = await User.query(db_session).bulk_create(users)
    assert count == 3, f"Expected 3 created users, got {count}"
    
    # Verify all were created
    total = await User.count(db_session)
    assert total == 3, f"Expected 3 total users, got {total}"
    
    print("✅ QuerySet.bulk_create() works")


@pytest.mark.asyncio
async def test_model_bulk_create(db_session):
    """Test Model.bulk_create() class method."""
    users = [
        User(name="Iris", email="iris@example.com", age=29),
        User(name="Jack", email="jack@example.com", age=33),
    ]
    
    created_users = await User.bulk_create(users, db_session)
    assert len(created_users) == 2, f"Expected 2 created users"
    
    # Verify
    total = await User.count(db_session)
    assert total == 2, f"Expected 2 total users"
    
    print("✅ Model.bulk_create() works")


# ──────────────────────────────────────────────────────────────────────────
# Run tests
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
