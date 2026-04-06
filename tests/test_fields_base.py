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
from typing import Any, Optional
from dataclasses import dataclass
from uuid import UUID

# Import from eden.fields once we implement it
# from eden.fields import (
#     FieldMetadata, ValidationResult, ValidationContext,
#     Validator, Field, FieldRegistry
# )


# These will be moved to eden/fields/base.py after implementation
@dataclass
class ValidationResult:
    """Result of a validation operation"""
    ok: bool
    value: Any = None
    error: str | None = None
    
    def __bool__(self):
        """Allow truthiness check: if result:"""
        return self.ok


@dataclass
class ValidationContext:
    """Context passed to validators during validation"""
    field_name: str
    value: Any
    instance: Any = None  # The model instance being validated
    form_data: dict | None = None  # All form data for cross-field validation
    request: Any = None  # Optional request object for context


@dataclass
class FieldMetadata:
    """Complete field metadata for ORM, form, and validation"""
    # Field identity
    name: str | None = None
    db_type: type = str
    
    # ORM Layer
    unique: bool = False
    index: bool = False
    nullable: bool = False
    default: Any = None
    primary_key: bool = False
    
    # Form Layer
    widget: str = "input"  # input, textarea, email, password, checkbox, etc.
    label: str | None = None
    placeholder: str | None = None
    help_text: str | None = None
    css_classes: list[str] = None
    
    # Validation Layer
    validators: list['Validator'] = None
    error_messages: dict[str, str] = None
    
    # Type-Specific Constraints
    max_length: int | None = None
    min_length: int | None = None
    pattern: str | None = None
    min_value: Any = None
    max_value: Any = None
    choices: list[tuple] | None = None
    
    def __post_init__(self):
        if self.css_classes is None:
            self.css_classes = []
        if self.validators is None:
            self.validators = []
        if self.error_messages is None:
            self.error_messages = {}


class Validator:
    """Base validator interface"""
    
    def __init__(self, name: str, async_mode: bool = False):
        self.name = name
        self.async_mode = async_mode
        self.error_message: str | None = None
    
    async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """
        Validate a value. Override in subclasses.
        
        Args:
            value: The value to validate
            context: ValidationContext with field name, instance, form data, etc.
        
        Returns:
            ValidationResult with ok bool and optional error message
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement validate()")
    
    def with_message(self, message: str) -> 'Validator':
        """Override error message"""
        self.error_message = message
        return self
    
    def __or__(self, other: 'Validator') -> 'CompositeValidator':
        """Support validator chaining with | operator"""
        if isinstance(self, CompositeValidator):
            return CompositeValidator(self.validators + [other])
        elif isinstance(other, CompositeValidator):
            return CompositeValidator([self] + other.validators)
        else:
            return CompositeValidator([self, other])


class CompositeValidator(Validator):
    """Chains multiple validators with AND logic"""
    
    def __init__(self, validators: list[Validator]):
        super().__init__("composite", async_mode=True)
        self.validators = validators
    
    async def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Run all validators in sequence"""
        for validator in self.validators:
            result = await validator.validate(value, context)
            if not result.ok:
                # Use custom message if set, otherwise use validator's error
                error_msg = self.error_message or result.error or f"Validation failed: {validator.name}"
                return ValidationResult(ok=False, error=error_msg)
        
        return ValidationResult(ok=True, value=value)


class FieldRegistry:
    """Registry for field types"""
    
    _registry: dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, field_class: type):
        """Register a field type"""
        cls._registry[name] = field_class
    
    @classmethod
    def get(cls, name: str) -> type | None:
        """Get a field type by name"""
        return cls._registry.get(name)
    
    @classmethod
    def all(cls) -> dict[str, type]:
        """Get all registered field types"""
        return cls._registry.copy()


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
        class StringField:
            pass
        
        FieldRegistry.register("string", StringField)
        assert FieldRegistry.get("string") == StringField
    
    def test_field_registry_all(self):
        """Test getting all registered fields"""
        class StringField:
            pass
        
        class IntField:
            pass
        
        FieldRegistry._registry = {}  # Clear for test
        FieldRegistry.register("string", StringField)
        FieldRegistry.register("int", IntField)
        
        all_fields = FieldRegistry.all()
        assert all_fields["string"] == StringField
        assert all_fields["int"] == IntField
        assert len(all_fields) == 2
    
    def test_field_registry_get_nonexistent(self):
        """Test getting nonexistent field type"""
        result = FieldRegistry.get("nonexistent")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
