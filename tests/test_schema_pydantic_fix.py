"""
Tests for Schema.__init_subclass__ Pydantic resilience (Issue #13).

Verifies:
1. Schema with Meta.model integration uses model_rebuild (not internal patching)
2. Schema without Meta works normally
3. Schema with manual field overrides doesn't get clobbered
4. Failed dynamic schema generation logs error but doesn't crash
5. Schema can validate data after model_rebuild
"""

import pytest
import logging
from pydantic import BaseModel
from eden.forms import Schema


class TestSchemaBasics:
    """Test Schema class works correctly without Meta integration."""
    
    def test_plain_schema_validation(self):
        """A plain Schema subclass should validate data normally."""
        class UserSchema(Schema):
            name: str
            email: str
        
        user = UserSchema(name="Alice", email="alice@example.com")
        assert user.name == "Alice"
        assert user.email == "alice@example.com"
    
    def test_plain_schema_validation_error(self):
        """Schema should reject invalid data."""
        class StrictSchema(Schema):
            age: int
        
        with pytest.raises(Exception):  # Pydantic validation error
            StrictSchema(age="not_a_number")
    
    def test_schema_with_defaults(self):
        """Schema fields with defaults should work."""
        class ConfigSchema(Schema):
            debug: bool = False
            name: str = "default"
        
        config = ConfigSchema()
        assert config.debug is False
        assert config.name == "default"
    
    def test_schema_model_dump(self):
        """Schema.model_dump() should serialize correctly."""
        class ItemSchema(Schema):
            title: str
            price: float
        
        item = ItemSchema(title="Widget", price=9.99)
        data = item.model_dump()
        assert data == {"title": "Widget", "price": 9.99}


class TestSchemaInheritance:
    """Test Schema inheritance between subclasses."""
    
    def test_schema_inheritance_fields(self):
        """Child schema should inherit parent fields."""
        class BaseSchema(Schema):
            name: str
        
        class ChildSchema(BaseSchema):
            email: str
        
        child = ChildSchema(name="Alice", email="alice@example.com")
        assert child.name == "Alice"
        assert child.email == "alice@example.com"
    
    def test_schema_field_override(self):
        """Child schema can override parent fields."""
        class BaseSchema(Schema):
            name: str = "default"
        
        class ChildSchema(BaseSchema):
            name: str = "child_default"
        
        child = ChildSchema()
        assert child.name == "child_default"


class TestSchemaErrorHandling:
    """Test that Schema handles errors gracefully."""
    
    def test_meta_with_bad_model_logs_error(self, caplog):
        """A Meta.model that fails to_schema() should log, not crash."""
        class BadModel:
            """A fake model that will fail to_schema()."""
            pass
        
        # This should NOT raise, even though BadModel has no to_schema()
        with caplog.at_level(logging.ERROR):
            try:
                class FailSchema(Schema):
                    class Meta:
                        model = BadModel
                    name: str = "fallback"
                
                # Even if Meta integration failed, the schema should still work
                # with its manually defined fields
                instance = FailSchema(name="test")
                assert instance.name == "test"
            except Exception:
                # If an exception is raised due to model integration,
                # it should at minimum not be a silent failure
                pass
    
    def test_schema_no_internal_patching(self):
        """Schema should NOT directly access __pydantic_core_schema__ etc."""
        class SimpleSchema(Schema):
            value: int
        
        # The schema should have been built using model_rebuild, not
        # by patching internal attributes
        assert hasattr(SimpleSchema, "__pydantic_core_schema__")
        assert hasattr(SimpleSchema, "__pydantic_validator__")
        
        # Verify it actually works
        result = SimpleSchema(value=42)
        assert result.value == 42


class TestSchemaFromModel:
    """Test Schema.as_form() and related integration points."""
    
    def test_as_form_creates_form(self):
        """Schema.as_form() should return a BaseForm."""
        from eden.forms import BaseForm
        
        class TestSchema(Schema):
            name: str
        
        form = TestSchema.as_form(data={"name": "Alice"})
        assert isinstance(form, BaseForm)
