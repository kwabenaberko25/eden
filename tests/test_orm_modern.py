import pytest
import uuid
from typing import Annotated, Optional, List
from eden.db import (
    Model, 
    MaxLength, 
    Required, 
    Indexed, 
    Database, 
    relationship, 
    Mapped,
    ForeignKey
)

# Define models using the new Annotated pattern
class ModernUser(Model):
    __tablename__ = "modern_users"
    
    name: Annotated[str, MaxLength(100), Indexed()]
    email: Annotated[str, Required(), Indexed()]
    bio: Annotated[Optional[str], MaxLength(500)] = ""
    
    # Relationship using Mapped
    posts: Mapped[List["ModernPost"]] = relationship(back_populates="author")

class ModernPost(Model):
    __tablename__ = "modern_posts"
    
    title: Annotated[str, MaxLength(200)]
    content: str = ""
    author_id: Annotated[uuid.UUID, ForeignKey("modern_users.id")]
    
    author: Mapped[ModernUser] = relationship(back_populates="posts")

@pytest.fixture(autouse=True)
async def setup_db_tables(db):
    """Ensure tables are created for these specific models."""
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
    yield

@pytest.mark.asyncio
async def test_annotated_schema_inference(db):
    """Test that schema is correctly inferred from Annotated types."""
    from sqlalchemy import inspect
    
    def get_columns(conn):
        inspector = inspect(conn)
        return {c["name"]: [c, inspector] for c in inspector.get_columns(ModernUser.__tablename__)}
    
    async with db.engine.connect() as conn:
        columns_data = await conn.run_sync(get_columns)
    
    # Check name column
    assert "name" in columns_data
    col = columns_data["name"][0]
    assert col["type"].length == 100
    
    # Check email column
    assert "email" in columns_data
    assert columns_data["email"][0]["nullable"] is False
    
    # Check bio column
    assert "bio" in columns_data
    assert columns_data["bio"][0]["type"].length == 500
    assert columns_data["bio"][0]["nullable"] is True

@pytest.mark.asyncio
async def test_modern_crud_operations(db):
    """Test CRUD operations with modern models."""
    # Create
    user = await ModernUser.create(
        name="Modern User",
        email="modern@example.com",
        bio="I am a modern user."
    )
    assert user.id is not None
    assert user.name == "Modern User"
    
    # Create related
    post = await ModernPost.create(
        title="Modern Post",
        author_id=user.id
    )
    assert post.author_id == user.id
    
    # Fetch with relationship
    fetched_user = await ModernUser.query().prefetch("posts").filter(id=user.id).first()
    assert len(fetched_user.posts) == 1
    assert fetched_user.posts[0].title == "Modern Post"

@pytest.mark.asyncio
async def test_validation_rules_from_annotated(db):
    """Test that validation rules are correctly extracted from Annotated."""
    # bio has MaxLength(500)
    long_bio = "a" * 501
    
    # The validation happens in .clean() or during .create() if it calls clean
    # Model.create usually does validation
    from eden.exceptions import ValidationError
    
    with pytest.raises(ValidationError) as excinfo:
        await ModernUser.create(
            name="Test",
            email="test@example.com",
            bio=long_bio
        )
    
    # Check that it's a validation error for 'bio'
    error_dict = excinfo.value.to_dict()
    errors = error_dict["extra"]["errors"]
    assert any(e["loc"] == ("bio",) or e["loc"] == ["bio"] for e in errors)
    assert any("500" in e["msg"] for e in errors)
