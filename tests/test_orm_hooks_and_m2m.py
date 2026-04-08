import pytest
from eden.db import Model, f, ManyToManyField, Mapped
from typing import List

class LifecycleModel(Model):
    name: str = f(max_length=100)
    hook_triggered: bool = f(default=False)
    
    async def before_save(self, session):
        self.hook_triggered = True

class M2MTag(Model):
    name: str = f(max_length=50)
    articles: Mapped[List["M2MArticle"]] = ManyToManyField("M2MArticle", back_populates="tags")

class M2MArticle(Model):
    title: str = f(max_length=100)
    tags: Mapped[List["M2MTag"]] = ManyToManyField("M2MTag", back_populates="articles")

@pytest.fixture(scope="function", autouse=True)
async def setup_orm_tables(db):
    """Ensure tables are created for models in this file."""
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
    yield

@pytest.mark.asyncio
async def test_orm_hooks(db, db_transaction):
    obj = await LifecycleModel.create(name="Test Hooks")
    assert obj.hook_triggered is True
    
    # Reload and check
    fetched = await LifecycleModel.get(obj.id)
    assert fetched.hook_triggered is True

@pytest.mark.asyncio
async def test_orm_m2m(db, db_transaction):
    # 1. Create entities
    tag1 = await M2MTag.create(name="Python")
    tag2 = await M2MTag.create(name="Eden")
    
    article = await M2MArticle.create(title="M2M Article")
    
    # 2. Add to collection
    article.tags.append(tag1)
    article.tags.append(tag2)
    await article.save()
    
    # 3. Verify
    fetched = await M2MArticle.query().prefetch("tags").filter(id=article.id).first()
    assert len(fetched.tags) == 2
    assert tag1.name in [t.name for t in fetched.tags]
    assert tag2.name in [t.name for t in fetched.tags]
    
    # Check reverse
    fetched_tag = await M2MTag.query().prefetch("articles").filter(id=tag1.id).first()
    assert len(fetched_tag.articles) == 1
    assert fetched_tag.articles[0].title == "M2M Article"
