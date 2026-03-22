import pytest
from eden.db import Model, f, Reference, Relationship, Mapped
from typing import List

class AdvUser(Model):
    name: str = f(max_length=100)
    posts: Mapped[List["AdvPost"]] = Relationship("AdvPost", back_populates="author")

class AdvPost(Model):
    title: str = f(max_length=200)
    author: Mapped["AdvUser"] = Reference(back_populates="posts")

@pytest.fixture(autouse=True)
async def setup_db_tables(db):
    """Ensure tables are created and clean for these specific models."""
    async with db.engine.begin() as conn:
        await conn.run_sync(AdvPost.__table__.drop, checkfirst=True)
        await conn.run_sync(AdvUser.__table__.drop, checkfirst=True)
        await conn.run_sync(Model.metadata.create_all)
    yield

@pytest.mark.asyncio
async def test_orm_relationships_o2m(db, db_transaction):
    # 1. Create User and Posts
    user = await AdvUser.create(name="Author 1")
    await AdvPost.create(title="Post 1", author_id=user.id)
    await AdvPost.create(title="Post 2", author_id=user.id)
    
    # 2. Verify relationships
    fetched_user = await AdvUser.query().prefetch("posts").filter(name="Author 1").first()
    assert fetched_user is not None
    assert len(fetched_user.posts) == 2
    assert fetched_user.posts[0].title in ["Post 1", "Post 2"]
    assert fetched_user.posts[0].author_id == user.id

@pytest.mark.asyncio
async def test_orm_m2o_navigation(db, db_transaction):
    user = await AdvUser.create(name="Author 2")
    post = await AdvPost.create(title="Navigation Post", author_id=user.id)
    
    fetched_post = await AdvPost.query().prefetch("author").filter(id=post.id).first()
    assert fetched_post.author is not None
    assert fetched_post.author.name == "Author 2"

@pytest.mark.asyncio
async def test_orm_prefetch_syntax(db, db_transaction):
    # Test multiple prefetch formats
    await AdvUser.create(name="Prefetch User")
    
    # Prefetch as string
    qs = AdvUser.query().prefetch("posts")
    assert "posts" in qs._prefetch_paths
    
    # Execution
    user = await qs.filter(name="Prefetch User").first()
    assert user is not None
