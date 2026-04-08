"""
Tests for Eden QuerySets.
"""

import pytest
from unittest.mock import AsyncMock
import uuid

from eden.querysets import QuerySet, Manager
from eden.db import Model, mapped_column, String


class TestUser(Model):
    """Test user model."""
    name: str = mapped_column(String(100))
    email: str = mapped_column(String(255))
    active: bool = mapped_column(String(5))  # Simplified for testing


@pytest.mark.asyncio
async def test_queryset_creation():
    """Test QuerySet creation."""
    qs = QuerySet(TestUser)

    assert qs._model_cls == TestUser
    assert qs._annotations == {}


@pytest.mark.asyncio
async def test_queryset_filter():
    """Test QuerySet filtering."""
    qs = QuerySet(TestUser)

    # Apply filter
    filtered = qs.filter(active=True)

    assert filtered is not qs  # Should return new instance
    assert filtered._model_cls == TestUser


@pytest.mark.asyncio
async def test_queryset_exists():
    """Test QuerySet exists method."""
    qs = QuerySet(TestUser)

    # Mock the execute_scalar method
    qs._execute_scalar = AsyncMock(return_value=1)

    result = await qs.exists()
    assert result is True

    qs._execute_scalar.assert_called_once()


@pytest.mark.asyncio
async def test_queryset_count():
    """Test QuerySet count method."""
    qs = QuerySet(TestUser)

    # Mock the execute_scalar method
    qs._execute_scalar = AsyncMock(return_value=42)

    result = await qs.count()
    assert result == 42

    qs._execute_scalar.assert_called_once()


@pytest.mark.asyncio
async def test_queryset_aggregate():
    """Test QuerySet aggregate method."""
    qs = QuerySet(TestUser)

    # Mock the execute_first method
    mock_result = (25, 100)
    qs._execute_first = AsyncMock(return_value=mock_result)

    # Use actual SQLAlchemy expressions for aggregation
    from sqlalchemy import func
    expr1 = func.count(TestUser.id).label("avg_age")
    expr2 = func.count(TestUser.id).label("total_count")

    result = await qs.aggregate(expr1, expr2)

    expected = {"avg_age": 25, "total_count": 100}
    assert result == expected


@pytest.mark.asyncio
async def test_queryset_bulk_create():
    """Test QuerySet bulk_create method."""
    qs = QuerySet(TestUser)

    # Mock instances
    instances = [
        TestUser(name="User 1", email="user1@example.com", active=True),
        TestUser(name="User 2", email="user2@example.com", active=True),
    ]

    # Mock session and bulk operations
    mock_session = AsyncMock()
    qs._resolve_session = AsyncMock(return_value=mock_session)

    result = await qs.bulk_create(instances)

    assert result == instances
    mock_session.add_all.assert_called_once_with(instances)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_queryset_bulk_update():
    """Test QuerySet bulk_update method."""
    qs = QuerySet(TestUser)

    # Mock instances
    instances = [
        TestUser(id=uuid.uuid4(), name="User 1", email="user1@example.com", active=True),
        TestUser(id=uuid.uuid4(), name="User 2", email="user2@example.com", active=True),
    ]

    # Mock the save method on instances
    for instance in instances:
        instance.save = AsyncMock()

    result = await qs.bulk_update(instances, ["name"])

    assert result == 2
    for instance in instances:
        instance.save.assert_called_once()


@pytest.mark.asyncio
async def test_queryset_annotate():
    """Test QuerySet annotate method."""
    qs = QuerySet(TestUser)

    annotated = qs.annotate(post_count=5)

    assert annotated._annotations == {"post_count": 5}
    assert annotated is not qs  # Should be new instance


@pytest.mark.asyncio
async def test_queryset_values():
    """Test QuerySet values method."""
    qs = QuerySet(TestUser)

    values_qs = qs.values("name", "email")

    assert values_qs._return_dicts is True
    assert values_qs is not qs


@pytest.mark.asyncio
async def test_queryset_distinct():
    """Test QuerySet distinct method."""
    qs = QuerySet(TestUser)

    distinct_qs = qs.distinct("email")

    assert distinct_qs is not qs
    # In a real implementation, this would modify the SQL


@pytest.mark.asyncio
async def test_manager_creation():
    """Test Manager creation."""
    manager = Manager(TestUser)

    assert manager.model_cls == TestUser


@pytest.mark.asyncio
async def test_manager_get_queryset():
    """Test Manager get_queryset method."""
    manager = Manager(TestUser)

    qs = manager.get_queryset()

    assert isinstance(qs, QuerySet)
    assert qs._model_cls == TestUser


@pytest.mark.asyncio
async def test_manager_delegation():
    """Test Manager method delegation to QuerySet."""
    manager = Manager(TestUser)

    # Mock the queryset methods
    mock_qs = AsyncMock()
    manager.get_queryset = AsyncMock(return_value=mock_qs)

    # Test delegation
    await manager.all()
    mock_qs.all.assert_called_once()

    await manager.count()
    mock_qs.count.assert_called_once()


@pytest.mark.asyncio
async def test_manager_create():
    """Test Manager create method."""
    manager = Manager(TestUser)

    # Mock the model's create method
    TestUser.create = AsyncMock(return_value=TestUser(
        id=uuid.uuid4(),
        name="Test User",
        email="test@example.com",
        active=True
    ))

    try:
        result = await manager.create(name="Test User", email="test@example.com", active=True)

        assert result.name == "Test User"
        assert result.email == "test@example.com"
        TestUser.create.assert_called_once_with(name="Test User", email="test@example.com", active=True)

    finally:
        # Restore original method
        delattr(TestUser, 'create')