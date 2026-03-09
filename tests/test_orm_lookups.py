import pytest
from typing import Any, List, Optional
from sqlalchemy.orm import Mapped, Relationship
from eden.db import Model, f, Database, Reference, Q

# Models for testing multi-level joins
class Author(Model):
    __tablename__ = "authors"
    name: Mapped[str] = f()
    profile: Mapped["Profile"] = Relationship("Profile", back_populates="author", uselist=False)
    posts: Mapped[List["Post"]] = Relationship("Post", back_populates="author")

class Profile(Model):
    __tablename__ = "profiles"
    city: Mapped[str] = f()
    author_id: Mapped[int] = f(foreign_key="authors.id")
    author: Mapped["Author"] = Relationship("Author", back_populates="profile")

class Post(Model):
    __tablename__ = "posts"
    title: Mapped[str] = f()
    views: Mapped[int] = f(default=0)
    author_id: Mapped[int] = f(foreign_key="authors.id")
    author: Mapped["Author"] = Relationship("Author", back_populates="posts")

@pytest.fixture
async def db_with_data():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    
    # Create tables
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
        
    async with db.session() as session:
        a1 = Author(name="Alice")
        p1 = Profile(city="NY", author=a1)
        post1 = Post(title="Eden Guide", views=100, author=a1)
        
        a2 = Author(name="Bob")
        p2 = Profile(city="London", author=a2)
        post2 = Post(title="SQLAlchemy vs Django", views=50, author=a2)
        
        session.add_all([a1, p1, post1, a2, p2, post2])
        await session.commit()
        
    yield db
    await db.disconnect()

@pytest.mark.asyncio
async def test_expression_first_auto_join(db_with_data):
    """Verify that Post.filter(Author.name == 'Alice') auto-joins Author."""
    async with db_with_data.session() as session:
        # 1. Simple cross-model expression
        posts = await Post.query(session).filter(Author.name == "Alice").all()
        assert len(posts) == 1
        assert posts[0].title == "Eden Guide"

@pytest.mark.asyncio
async def test_deep_expression_auto_join(db_with_data):
    """Verify multi-level auto-joins: Post -> Author -> Profile."""
    async with db_with_data.session() as session:
        # 2. Deep path: Post.filter(Profile.city == "London")
        posts = await Post.query(session).filter(Profile.city == "London").all()
        assert len(posts) == 1
        assert posts[0].title == "SQLAlchemy vs Django"

@pytest.mark.asyncio
async def test_bitwise_q_with_expressions(db_with_data):
    """Verify bitwise logic on expressions via Q objects or direct expressions."""
    async with db_with_data.session() as session:
        # 3. Complex logic: (Title contains 'Eden') OR (City is 'London')
        # We want to support: Post.filter((Post.title.contains("Eden")) | (Profile.city == "London"))
        query = Post.query(session).filter(
            (Post.title.contains("Eden")) | (Profile.city == "London")
        )
        results = await query.all()
        assert len(results) == 2 # "Eden Guide" (via title) and "SQLAlchemy vs Django" (via city)

@pytest.mark.asyncio
async def test_f_expression_alternative(db_with_data):
    """Verify that pure SQLAlchemy expressions work as F-expressions."""
    async with db_with_data.session() as session:
        # Update likes/views based on another column (min_views concept)
        # Using filter(Post.views > some_value) is standard, but comparing columns:
        a1_posts = await Post.query(session).filter(Post.views >= 100).all()
        assert len(a1_posts) == 1
        
        # We can also do: views = views + 1 (Update test)
        await Post.query(session).filter(title="Eden Guide").update(views=Post.views + 1)
        
        updated = await Post.query(session).get(a1_posts[0].id)
        assert updated.views == 101

@pytest.mark.asyncio
async def test_hybrid_lookups(db_with_data):
    """Verify strings and expressions can be mixed."""
    async with db_with_data.session() as session:
        results = await Post.query(session).filter(
            Author.name == "Alice",
            title__icontains="Eden"
        ).all()
        assert len(results) == 1
        assert results[0].title == "Eden Guide"
