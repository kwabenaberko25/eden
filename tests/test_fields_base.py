"""
Tests for Field Base Infrastructure

Testing:
- FieldMetadata dataclass
- ValidationResult dataclass
- ValidationContext
- Validator ABC and protocol
- Field base class
- Composability with | operator
"""

import pytest
from typing import Any

from eden.fields import Field, FieldMetadata, FieldRegistry, ValidationContext, ValidationResult, Validator
from eden.fields.validator import CompositeValidator


# ─────────────────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────────────────


class TestValidationResult:
    """Test ValidationResult dataclass"""
    
    def test_validation_result_ok(self):
        """Test successful validation result"""
        result = ValidationResult(ok=True, value="test@example.com")
        assert result.ok is True
        assert result.value == "test@example.com"
        assert result.error is None
        assert bool(result) is True
    
    def test_validation_result_error(self):
        """Test failed validation result"""
        result = ValidationResult(ok=False, error="Invalid email format")
        assert result.ok is False
        assert result.error == "Invalid email format"
        assert result.value is None
        assert bool(result) is False
    
    def test_validation_result_truthiness(self):
        """Test truthiness checks"""
        ok_result = ValidationResult(ok=True)
        fail_result = ValidationResult(ok=False)
        
        if ok_result:
            pass  # Should enter
        else:
            pytest.fail("ok_result should be truthy")
        
        if fail_result:
            pytest.fail("fail_result should be falsy")


class TestValidationContext:
    """Test ValidationContext"""
    
    def test_validation_context_creation(self):
        """Test creating validation context"""
        context = ValidationContext(
            field_name="email",
            value="test@example.com",
            form_data={"email": "test@example.com", "password": "secret"}
        )
        assert context.field_name == "email"
        assert context.value == "test@example.com"
        assert context.form_data["password"] == "secret"
    
    def test_validation_context_with_instance(self):
        """Test context with model instance"""
        class MockUser:
            email = "existing@example.com"
        
        user = MockUser()
        context = ValidationContext(field_name="email", value="new@example.com", instance=user)
        assert context.instance.email == "existing@example.com"


class TestFieldMetadata:
    """Test FieldMetadata dataclass"""
    
    def test_field_metadata_defaults(self):
        """Test field metadata with defaults"""
        meta = FieldMetadata()
        assert meta.db_type == str
        assert meta.unique is False
        assert meta.index is False
        assert meta.nullable is False
        assert meta.default is None
        assert meta.widget == "input"
        assert meta.css_classes == []
        assert meta.validators == []
        assert meta.error_messages == {}
    
    def test_field_metadata_custom_values(self):
        """Test field metadata with custom values"""
        meta = FieldMetadata(
            name="email",
            db_type=str,
            unique=True,
            index=True,
            widget="email",
            label="Email Address",
            max_length=254,
            nullable=False
        )
        assert meta.name == "email"
        assert meta.unique is True
        assert meta.index is True
        assert meta.widget == "email"
        assert meta.label == "Email Address"
        assert meta.max_length == 254
        assert meta.nullable is False
    
    def test_field_metadata_constraints(self):
        """Test field metadata with constraints"""
        meta = FieldMetadata(
            db_type=str,
            max_length=100,
            min_length=5,
            pattern=r"^[a-z]+$"
        )
        assert meta.max_length == 100
        assert meta.min_length == 5
        assert meta.pattern == r"^[a-z]+$"
    
    def test_field_metadata_choices(self):
        """Test field metadata with choices"""
        choices = [("admin", "Administrator"), ("user", "Regular User")]
        meta = FieldMetadata(choices=choices)
        assert meta.choices == choices


class TestValidator:
    """Test Validator base class"""
    
    @pytest.mark.asyncio
    async def test_validator_with_message(self):
        """Test validator error message customization"""
        class TestValidator(Validator):
            async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
                return ValidationResult(ok=False, error="Original error")
        
        validator = TestValidator("test")
        validator_with_msg = validator.with_message("Custom error message")
        assert validator_with_msg.error_message == "Custom error message"
    
    @pytest.mark.asyncio
    async def test_validator_composition_or_operator(self):
        """Test composing validators with | operator"""
        class AlwaysValid(Validator):
            async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
                return ValidationResult(ok=True, value=value)
        
        class AlwaysInvalid(Validator):
            async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
                return ValidationResult(ok=False, error="Always invalid")
        
        v1 = AlwaysValid("v1")
        v2 = AlwaysInvalid("v2")
        
        composite = v1 | v2
        assert isinstance(composite, CompositeValidator)
        assert len(composite.validators) == 2
    
    @pytest.mark.asyncio
    async def test_validator_chaining_multiple(self):
        """Test chaining multiple validators"""
        class AlwaysValid(Validator):
            async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
                return ValidationResult(ok=True, value=value)
        
        v1 = AlwaysValid("v1")
        v2 = AlwaysValid("v2")
        v3 = AlwaysValid("v3")
        
        composite = v1 | v2 | v3
        assert isinstance(composite, CompositeValidator)
        assert len(composite.validators) == 3


class TestCompositeValidator:
    """Test CompositeValidator"""
    
    @pytest.mark.asyncio
    async def test_composite_all_pass(self):
        """Test composite validator when all validators pass"""
        class AlwaysValid(Validator):
            async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
                return ValidationResult(ok=True, value=value)
        
        validators = [AlwaysValid(f"v{i}") for i in range(3)]
        composite = CompositeValidator(validators)
        
        context = ValidationContext(field_name="test", value="test_value")
        result = await composite.validate("test_value", context)
        
        assert result.ok is True
        assert result.value == "test_value"
    
    @pytest.mark.asyncio
    async def test_composite_short_circuit_on_failure(self):
        """Test composite validator stops on first failure"""
        call_count = {"count": 0}
        
        class CountingValidator(Validator):
            def __init__(self, name: str, should_fail: bool = False):
                super().__init__(name)
                self.should_fail = should_fail
            
            async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
                call_count["count"] += 1
                if self.should_fail:
                    return ValidationResult(ok=False, error="Failed")
                return ValidationResult(ok=True, value=value)
        
        validators = [
            CountingValidator("v1"),
            CountingValidator("v2", should_fail=True),
            CountingValidator("v3"),  # Should not be called
        ]
        composite = CompositeValidator(validators)
        
        context = ValidationContext(field_name="test", value="test_value")
        result = await composite.validate("test_value", context)
        
        assert result.ok is False
        assert call_count["count"] == 2  # v1 and v2, not v3
    
    @pytest.mark.asyncio
    async def test_composite_custom_error_message(self):
        """Test composite validator with custom error message"""
        class AlwaysInvalid(Validator):
            async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
                return ValidationResult(ok=False, error="Validator error")
        
        validators = [AlwaysInvalid("v1")]
        composite = CompositeValidator(validators)
        composite.error_message = "Custom composite error"
        
        context = ValidationContext(field_name="test", value="test_value")
        result = await composite.validate("test_value", context)
        
        assert result.ok is False
        assert result.error == "Custom composite error"


class TestFieldRegistry:
    """Test FieldRegistry"""
    
    def test_field_registry_register_and_get(self):
        """Test registering and retrieving field types"""
        original_registry = FieldRegistry._registry.copy()
        class StringField:
            pass
        
        try:
            FieldRegistry.register("string", StringField)
            assert FieldRegistry.get("string") == StringField
        finally:
            FieldRegistry._registry = original_registry
    
    def test_field_registry_all(self):
        """Test getting all registered fields"""
        original_registry = FieldRegistry._registry.copy()
        class StringField:
            pass
        
        class IntField:
            pass
        
        try:
            FieldRegistry._registry = {}  # Clear for test
            FieldRegistry.register("string", StringField)
            FieldRegistry.register("int", IntField)
            
            all_fields = FieldRegistry.all()
            assert all_fields["string"] == StringField
            assert all_fields["int"] == IntField
            assert len(all_fields) == 2
        finally:
            FieldRegistry._registry = original_registry
    
    def test_field_registry_get_nonexistent(self):
        """Test getting nonexistent field type"""
        result = FieldRegistry.get("nonexistent")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
