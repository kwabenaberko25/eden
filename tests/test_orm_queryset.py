import pytest
from uuid import uuid4
from eden.db import Model, f

class QSUser(Model):
    name: str = f(max_length=50)
    age: int = f()
    is_active: bool = f(default=True)

@pytest.fixture(autouse=True)
async def setup_db(db):
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
    yield
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)

@pytest.fixture
async def sample_users():
    u1 = await QSUser.create(name="Alice", age=30, is_active=True)
    u2 = await QSUser.create(name="Bob", age=25, is_active=False)
    u3 = await QSUser.create(name="Charlie", age=35, is_active=True)
    u4 = await QSUser.create(name="David", age=30, is_active=True)
    return [u1, u2, u3, u4]

@pytest.mark.asyncio
async def test_queryset_filter_chaining(sample_users):
    qs = QSUser.filter(is_active=True).filter(age__gte=30)
    users = await qs
    assert len(users) == 3
    names = {u.name for u in users}
    assert names == {"Alice", "Charlie", "David"}

@pytest.mark.asyncio
async def test_queryset_exclude(sample_users):
    qs = QSUser.exclude(age__gte=30)
    users = await qs
    assert len(users) == 1
    assert users[0].name == "Bob"

@pytest.mark.asyncio
async def test_queryset_order_by(sample_users):
    # Ascending
    qs_asc = QSUser.order_by("age", "name")
    users = await qs_asc
    assert [u.name for u in users] == ["Bob", "Alice", "David", "Charlie"]

    # Descending
    qs_desc = QSUser.order_by("-age")
    users = await qs_desc
    assert users[0].name == "Charlie"
    assert users[-1].name == "Bob"

@pytest.mark.asyncio
async def test_queryset_limit_offset(sample_users):
    qs = QSUser.order_by("name").limit(2).offset(1)
    users = await qs
    assert len(users) == 2
    assert users[0].name == "Bob"
    assert users[1].name == "Charlie"

@pytest.mark.asyncio
async def test_queryset_values_multiple(sample_users):
    # Test multiple fields
    results = await QSUser.order_by("name").values("name", "is_active")
    assert len(results) == 4
    assert results[0] == {"name": "Alice", "is_active": True}
    assert results[1] == {"name": "Bob", "is_active": False}
    
    # Test single field
    names = await QSUser.order_by("name").values("name")
    assert names[0] == {"name": "Alice"}

@pytest.mark.asyncio
async def test_queryset_values_with_filter(sample_users):
    results = await QSUser.filter(age__lt=30).values("name")
    assert len(results) == 1
    assert results[0] == {"name": "Bob"}

@pytest.mark.asyncio
async def test_queryset_first_last(sample_users):
    # Ordered by name: Alice, Bob, Charlie, David
    first_user = await QSUser.order_by("name").first()
    assert first_user.name == "Alice"

    last_user = await QSUser.order_by("name").last()
    assert last_user.name == "David"
    
    # Ordered by age: Bob(25), Alice(30), David(30), Charlie(35)
    last_by_age = await QSUser.order_by("age", "name").last()
    assert last_by_age.name == "Charlie"

@pytest.mark.asyncio
async def test_queryset_exists(sample_users):
    exists = await QSUser.filter(name="Alice").exists()
    assert exists is True

    not_exists = await QSUser.filter(name="Zack").exists()
    assert not_exists is False

@pytest.mark.asyncio
async def test_queryset_all_as_dict(sample_users):
    # Manually setting _return_dicts for test
    qs = QSUser.order_by("name")
    qs._return_dicts = True
    results = await qs.all()
    assert len(results) == 4
    assert isinstance(results[0], dict)
    assert results[0]["name"] == "Alice"
    assert "id" in results[0]
    assert isinstance(results[0]["id"], str)

@pytest.mark.asyncio
async def test_queryset_first_as_dict(sample_users):
    qs = QSUser.order_by("name")
    qs._return_dicts = True
    result = await qs.first()
    assert isinstance(result, dict)
    assert result["name"] == "Alice"
    assert isinstance(result["id"], str)
