"""
Tests for Eden Model Schemas.
"""

import pytest
from unittest.mock import AsyncMock
from pydantic import ValidationError
import uuid

from eden.schemas import ModelSchema, SchemaConfig, ValidationException
from eden.db import Model, mapped_column, String
from datetime import datetime


class TestUser(Model):
    """Test user model."""
    name: str = mapped_column(String(100))
    email: str = mapped_column(String(255))
    age: int = mapped_column(String(3))  # Note: using String for simplicity


class TestUserSchema(ModelSchema):
    """Test schema for users."""

    class Meta:
        model = TestUser
        exclude_fields = []
        read_only_fields = ["id"]
        required_fields = ["name", "email"]


@pytest.mark.asyncio
async def test_schema_creation():
    """Test schema creation and field detection."""
    schema = TestUserSchema(name="John Doe", email="john@example.com", age=30)

    assert schema.name == "John Doe"
    assert schema.email == "john@example.com"
    assert schema.age == 30


@pytest.mark.asyncio
async def test_schema_validation():
    """Test schema validation."""
    # Valid data
    schema = TestUserSchema(name="John Doe", email="john@example.com", age=30)
    is_valid, errors = await TestUserSchema.is_valid({"name": "John Doe", "email": "john@example.com", "age": 30})
    assert is_valid is True

    # Invalid data - missing required field
    is_valid, errors = await TestUserSchema.is_valid({"name": "John Doe"})  # Missing email
    assert is_valid is False
    assert "email" in errors


@pytest.mark.asyncio
async def test_schema_save():
    """Test schema save functionality."""
    schema = TestUserSchema(name="Jane Doe", email="jane@example.com", age=25)

    # Mock the create method
    original_create = TestUser.create
    TestUser.create = AsyncMock(return_value=TestUser(
        id=uuid.uuid4(),
        name="Jane Doe",
        email="jane@example.com",
        age=25
    ))

    try:
        saved_instance = await schema.save()

        assert saved_instance.name == "Jane Doe"
        assert saved_instance.email == "jane@example.com"
        TestUser.create.assert_called_once()

    finally:
        TestUser.create = original_create


@pytest.mark.asyncio
async def test_schema_from_model():
    """Test creating schema from model instance."""
    user = TestUser(
        id=uuid.uuid4(),
        name="Bob Smith",
        email="bob@example.com",
        age=40
    )

    schema = TestUserSchema.from_model(user)

    assert schema.name == "Bob Smith"
    assert schema.email == "bob@example.com"
    assert schema.age == 40


def test_schema_to_dict():
    """Test schema serialization."""
    schema = TestUserSchema(name="Alice", email="alice@example.com", age=35)

    data = schema.to_dict()

    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    assert data["age"] == 35


@pytest.mark.asyncio
async def test_schema_config():
    """Test schema configuration."""
    config = SchemaConfig(
        model=TestUser,
        exclude_fields=["age"],
        read_only_fields=["id", "created_at"],
        required_fields=["name", "email"]
    )

    assert config.model == TestUser
    assert "age" in config.exclude_fields
    assert "id" in config.read_only_fields
    assert "name" in config.required_fields


def test_schema_validation_error():
    """Test validation error handling."""
    # This would normally be tested with invalid data
    # For now, just test the error class exists
    try:
        raise ValidationException({"field": ["error message"]})
    except ValidationException as e:
        assert "field" in e.errors
        assert e.errors["field"] == ["error message"]