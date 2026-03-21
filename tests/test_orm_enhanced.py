from __future__ import annotations

from typing import List, Optional
from uuid import UUID
import pytest
from sqlalchemy.orm import Mapped
from eden.db import Model, f, Relationship, Reference, Database, QuerySet, Sum, Avg, Max, Q
from sqlalchemy import func

print("DEBUG: test_orm_enhanced.py IMPORTED")

# Premium bidirectional relationship definitions
class EnhancedUser(Model):
    name: str = f(max_length=50)
    data: dict = f(json=True, default={})
    score: int = f(default=0)
    tags: list = f(json=True, default=[])

class EnhancedParent(Model):
    name: str = f()
    children: Mapped[List["EnhancedChild"]] = Relationship(back_populates="parent")

class EnhancedChild(Model):
    name: str = f()
    parent: Mapped["EnhancedParent"] = Reference(back_populates="children")

@pytest.fixture(autouse=True)
async def setup_db(db, db_transaction):
    print("DEBUG: setup_db called")
    print(f"DEBUG: Tables in metadata: {list(Model.metadata.tables.keys())}")
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
    yield
    print("DEBUG: setup_db yielded")

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

@pytest.mark.asyncio
async def test_orm_f_relationship_oneliner():
    # Test that EnhancedChild model has parent_id automatically created
    parent = await EnhancedParent.create(name="EnhancedParent 1")
    child = await EnhancedChild.create(name="EnhancedChild 1", parent_id=parent.id)
    
    # Verify data exists
    count = await EnhancedChild.query().filter(parent_id=parent.id).count()
    print(f"DEBUG: EnhancedChild count for parent {parent.id}: {count}")
    
    # Check parent's children
    fetched_parents = await EnhancedParent.query().prefetch("children").filter(id=parent.id).all()
    fetched_parent = fetched_parents[0]
    print(f"DEBUG: fetched_parent.children type: {type(fetched_parent.children)}")
    print(f"DEBUG: fetched_parent.children items: {len(fetched_parent.children)}")
    if len(fetched_parent.children) > 0:
        print(f"DEBUG: Example child: {fetched_parent.children[0].name}")
    
    assert len(fetched_parent.children) == 1
    assert fetched_parent.children[0].name == "EnhancedChild 1"
