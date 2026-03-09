import pytest
from uuid import uuid4
from datetime import datetime
from eden.db import Model, f, QuerySet, Sum, Avg, Max, Q
from sqlalchemy import func

class EnhancedUser(Model):
    name: str = f(max_length=50)
    data: dict = f(json=True, default={})
    score: int = f(default=0)
    tags: list = f(json=True, default=[])

@pytest.fixture(autouse=True)
async def setup_db(db):
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
    yield
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)

@pytest.mark.asyncio
async def test_orm_json_field():
    user = await EnhancedUser.create(
        name="Alice", 
        data={"skills": ["python", "sql"], "pref": "dark"},
        tags=["dev", "admin"]
    )
    
    fetched = await EnhancedUser.get(user.id)
    assert fetched.data["skills"] == ["python", "sql"]
    assert fetched.data["pref"] == "dark"
    assert fetched.tags == ["dev", "admin"]
    
    # Update JSON field
    fetched.data["pref"] = "light"
    await fetched.save()
    
    refreshed = await EnhancedUser.get(user.id)
    assert refreshed.data["pref"] == "light"

@pytest.mark.asyncio
async def test_queryset_aggregate_django_style():
    await EnhancedUser.create(name="A", score=10)
    await EnhancedUser.create(name="B", score=20)
    await EnhancedUser.create(name="C", score=30)
    
    # Test Django-style aggregate objects
    stats = await EnhancedUser.query().aggregate(
        total=Sum("score"),
        average=Avg("score"),
        maximum=Max("score")
    )
    
    assert int(stats["total"]) == 60
    assert int(stats["average"]) == 20
    assert int(stats["maximum"]) == 30

@pytest.mark.asyncio
async def test_queryset_annotate_complex():
    await EnhancedUser.create(name="Alice", score=100)
    await EnhancedUser.create(name="Bob", score=40)
    
    # Annotate with a boolean condition
    qs = EnhancedUser.query().annotate(is_high_score=EnhancedUser.score > 50)
    results = await qs.order_by("name").values("name", "is_high_score")
    
    assert results[0]["name"] == "Alice"
    assert results[0]["is_high_score"] is True
    assert results[1]["name"] == "Bob"
    assert results[1]["is_high_score"] is False

@pytest.mark.asyncio
async def test_orm_complex_lookups():
    await EnhancedUser.create(name="Alice", score=10, data={"dept": "IT"})
    await EnhancedUser.create(name="Bob", score=20, data={"dept": "HR"})
    await EnhancedUser.create(name="Charlie", score=30, data={"dept": "IT"})
    
    # Complex AND/OR with Q objects
    q = (Q(name="Alice") | Q(name="Bob")) & Q(score__lt=25)
    users = await EnhancedUser.filter(q)
    
    assert len(users) == 2
    names = {u.name for u in users}
    assert names == {"Alice", "Bob"}

@pytest.mark.asyncio
async def test_queryset_update_returning():
    await EnhancedUser.create(name="Ghost", score=0)
    
    # Bulk update
    count = await EnhancedUser.filter(name="Ghost").update(score=99)
    assert count == 1
    
    user = await EnhancedUser.filter_one(name="Ghost")
    assert user.score == 99

@pytest.mark.asyncio
async def test_queryset_delete():
    await EnhancedUser.create(name="To Delete", score=0)
    assert await EnhancedUser.count() == 1
    
    await EnhancedUser.filter(name="To Delete").delete()
    assert await EnhancedUser.count() == 0
