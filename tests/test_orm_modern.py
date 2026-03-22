from __future__ import annotations
from typing import List, Optional, Annotated
import uuid
import pytest
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy import inspect, ForeignKey
from eden.db import Model, mapped_column, Required, MaxLength, Indexed

# Define models using the new Annotated pattern
class ModernUser(Model):
    __tablename__ = "modern_users"
    
    name: Annotated[str, MaxLength(100), Indexed()]
    email: Annotated[str, Required(), Indexed()]
    bio: Annotated[Optional[str], MaxLength(500)] = ""
    
    posts: Mapped[List["ModernPost"]] = relationship(back_populates="author")

class ModernPost(Model):
    __tablename__ = "modern_posts"
    
    title: Annotated[str, MaxLength(200)]
    content: str = ""
    author_id: Annotated[uuid.UUID, ForeignKey("modern_users.id")]
    
    author: Mapped[ModernUser] = relationship(back_populates="posts")

@pytest.mark.asyncio
async def test_annotated_schema_inference(db, db_transaction):
    """Test that schema is correctly inferred from Annotated types."""
    print("\n--- RUNNING test_annotated_schema_inference ---")
    mapper = inspect(ModernUser)
    
    # Check columns
    assert "name" in mapper.columns
    assert mapper.columns["name"].type.length == 100
    assert mapper.columns["name"].index is True
    
    assert "email" in mapper.columns
    assert mapper.columns["email"].nullable is False
    assert mapper.columns["email"].index is True
    
    assert "bio" in mapper.columns
    assert mapper.columns["bio"].type.length == 500
    assert mapper.columns["bio"].nullable is True
    
    # Check relationship
    assert "posts" in mapper.relationships
    relationship = mapper.relationships["posts"]
    assert relationship.target.name == "modern_posts"
    assert relationship.back_populates == "author"

@pytest.mark.asyncio
async def test_modern_crud_operations(db, db_transaction):
    """Test CRUD operations with modern models."""
    print("\n--- RUNNING test_modern_crud_operations ---")
    # Create
    user = await ModernUser.create(
        name="Modern User",
        email="modern@example.com",
        bio="I am a modern user."
    )
    assert user.id is not None
    assert user.name == "Modern User"
    
    post = await ModernPost.create(
        title="Modern Post",
        content="This is a modern post.",
        author_id=user.id
    )
    assert post.author_id == user.id
    
    # Read with relationship
    fetched_user = await ModernUser.query().prefetch("posts").get(user.id)
    assert len(fetched_user.posts) == 1
    assert fetched_user.posts[0].title == "Modern Post"

@pytest.mark.asyncio
async def test_validation_rules_from_annotated(db, db_transaction):
    """Test that validation rules are correctly extracted from Annotated."""
    # bio has MaxLength(500)
    long_bio = "a" * 501
    
    import eden.db.validation
    from eden.db.validation import ValidationErrors
    
    with pytest.raises(ValidationErrors) as excinfo:
        await ModernUser.create(
            name="Test",
            email="test@example.com",
            bio=long_bio
        )
    
    errors = excinfo.value.errors
    # errors is Dict[str, List[str]]
    assert "bio" in errors
    assert any("500" in msg for msg in errors["bio"])
