"""
Model Validation Hooks - Validate data before save/delete

Allows defining validation logic with hooks:
- clean() - Override to add custom validation
- validate_<field>() - Field-specific validators
- pre_save/post_save hooks
- pre_delete/post_delete hooks

Usage:
    class User(Model):
        email: str = StringField()
        age: int = IntField()
        
        def clean(self):
            \"\"\"Custom validation.\"\"\"
            if self.age < 0:
                raise ValidationError('Age cannot be negative')
        
        def validate_email(self):
            \"\"\"Validate email field.\"\"\"
            if '@' not in self.email:
                raise ValidationError('Invalid email format')
    
    # Hooks
    async def before_save(instance):
        print(f"About to save {instance}")
    
    User.pre_save(before_save)
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field as dc_field
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


@dataclass
class ValidationRule:
    """A single validation rule."""
    
    field_name: str
    rule_type: str  # 'required', 'email', 'min_length', 'max_length', 'pattern', 'custom'
    rule_value: Any = None
    message: Optional[str] = None
    validator_func: Optional[Callable] = None


class ValidatorMixin:
    """Mixin to add validation hooks to models."""
    
    # Class-level defaults (will be overridden per subclass via __init_subclass__)
    _validation_rules: Dict[str, List[ValidationRule]] = {}
    _pre_save_hooks: List[Callable] = []
    _post_save_hooks: List[Callable] = []
    _pre_delete_hooks: List[Callable] = []
    _post_delete_hooks: List[Callable] = []
    
    def __init_subclass__(cls, **kwargs):
        """Called when a subclass is created. Isolate validation state per model."""
        super().__init_subclass__(**kwargs)
        
        # Create per-model validation state (don't share with parent)
        cls._validation_rules = {}
        cls._pre_save_hooks = []
        cls._post_save_hooks = []
        cls._pre_delete_hooks = []
        cls._post_delete_hooks = []
        
        logger.debug(f"Initialized validation state for {cls.__name__}")
    
    @classmethod
    def add_validation_rule(
        cls,
        field_name: str,
        rule: ValidationRule
    ) -> None:
        """Add a validation rule to a field."""
        if field_name not in cls._validation_rules:
            cls._validation_rules[field_name] = []
        
        cls._validation_rules[field_name].append(rule)
        logger.debug(f"Added validation rule for {cls.__name__}.{field_name}")
    
    @classmethod
    def required(cls, field_name: str, message: Optional[str] = None) -> None:
        """Mark field as required."""
        msg = message or f"{field_name} is required"
        rule = ValidationRule(
            field_name=field_name,
            rule_type='required',
            message=msg
        )
        cls.add_validation_rule(field_name, rule)
    
    @classmethod
    def email(cls, field_name: str) -> None:
        """Validate field as email."""
        rule = ValidationRule(
            field_name=field_name,
            rule_type='email',
            message=f"{field_name} must be a valid email"
        )
        cls.add_validation_rule(field_name, rule)
    
    @classmethod
    def min_length(cls, field_name: str, length: int) -> None:
        """Validate minimum length."""
        rule = ValidationRule(
            field_name=field_name,
            rule_type='min_length',
            rule_value=length,
            message=f"{field_name} must be at least {length} characters"
        )
        cls.add_validation_rule(field_name, rule)
    
    @classmethod
    def max_length(cls, field_name: str, length: int) -> None:
        """Validate maximum length."""
        rule = ValidationRule(
            field_name=field_name,
            rule_type='max_length',
            rule_value=length,
            message=f"{field_name} must not exceed {length} characters"
        )
        cls.add_validation_rule(field_name, rule)
    
    @classmethod
    def pattern(cls, field_name: str, regex: str, message: Optional[str] = None) -> None:
        """Validate field matches regex pattern."""
        msg = message or f"{field_name} format is invalid"
        rule = ValidationRule(
            field_name=field_name,
            rule_type='pattern',
            rule_value=regex,
            message=msg
        )
        cls.add_validation_rule(field_name, rule)
    
    @classmethod
    def custom(cls, field_name: str, validator: Callable, message: str) -> None:
        """Add custom validation function."""
        rule = ValidationRule(
            field_name=field_name,
            rule_type='custom',
            message=message,
            validator_func=validator
        )
        cls.add_validation_rule(field_name, rule)
    
    async def validate(self) -> List[ValidationError]:
        """
        Run all validation rules and return errors.
        
        Returns:
            List of ValidationError objects
        """
        errors: List[ValidationError] = []
        
        # Run field-specific validators
        for field_name, rules in self._validation_rules.items():
            field_value = getattr(self, field_name, None)
            
            for rule in rules:
                try:
                    self._validate_rule(field_name, field_value, rule)
                except ValidationError as e:
                    errors.append(e)
        
        # Run clean() method if defined
        if hasattr(self, 'clean'):
            try:
                await self.clean() if hasattr(self.clean, '__await__') else self.clean()
            except ValidationError as e:
                errors.append(e)
        
        return errors
    
    def _validate_rule(self, field_name: str, value: Any, rule: ValidationRule) -> None:
        """Validate a single rule."""
        if rule.rule_type == 'required':
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValidationError(rule.message or f"{field_name} is required", field_name)
        
        elif rule.rule_type == 'email':
            if value and not self._is_valid_email(value):
                raise ValidationError(rule.message or f"Invalid email format", field_name)
        
        elif rule.rule_type == 'min_length':
            if value and len(str(value)) < rule.rule_value:
                raise ValidationError(rule.message, field_name)
        
        elif rule.rule_type == 'max_length':
            if value and len(str(value)) > rule.rule_value:
                raise ValidationError(rule.message, field_name)
        
        elif rule.rule_type == 'pattern':
            if value and not re.match(rule.rule_value, str(value)):
                raise ValidationError(rule.message, field_name)
        
        elif rule.rule_type == 'custom':
            if rule.validator_func:
                if not rule.validator_func(value):
                    raise ValidationError(rule.message, field_name)
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Simple email validation."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @classmethod
    def pre_save(cls, hook: Callable) -> None:
        """Register a pre-save hook."""
        cls._pre_save_hooks.append(hook)
        logger.debug(f"Registered pre_save hook on {cls.__name__}")
    
    @classmethod
    def post_save(cls, hook: Callable) -> None:
        """Register a post-save hook."""
        cls._post_save_hooks.append(hook)
        logger.debug(f"Registered post_save hook on {cls.__name__}")
    
    @classmethod
    def pre_delete(cls, hook: Callable) -> None:
        """Register a pre-delete hook."""
        cls._pre_delete_hooks.append(hook)
        logger.debug(f"Registered pre_delete hook on {cls.__name__}")
    
    @classmethod
    def post_delete(cls, hook: Callable) -> None:
        """Register a post-delete hook."""
        cls._post_delete_hooks.append(hook)
        logger.debug(f"Registered post_delete hook on {cls.__name__}")
    
    async def _run_pre_save_hooks(self) -> None:
        """Run all pre-save hooks."""
        for hook in self._pre_save_hooks:
            try:
                if hasattr(hook, '__await__'):
                    await hook(self)
                else:
                    hook(self)
            except Exception as e:
                logger.error(f"Error in pre_save hook: {e}")
                raise
    
    async def _run_post_save_hooks(self) -> None:
        """Run all post-save hooks."""
        for hook in self._post_save_hooks:
            try:
                if hasattr(hook, '__await__'):
                    await hook(self)
                else:
                    hook(self)
            except Exception as e:
                logger.error(f"Error in post_save hook: {e}")
    
    async def _run_pre_delete_hooks(self) -> None:
        """Run all pre-delete hooks."""
        for hook in self._pre_delete_hooks:
            try:
                if hasattr(hook, '__await__'):
                    await hook(self)
                else:
                    hook(self)
            except Exception as e:
                logger.error(f"Error in pre_delete hook: {e}")
                raise
    
    async def _run_post_delete_hooks(self) -> None:
        """Run all post-delete hooks."""
        for hook in self._post_delete_hooks:
            try:
                if hasattr(hook, '__await__'):
                    await hook(self)
                else:
                    hook(self)
            except Exception as e:
                logger.error(f"Error in post_delete hook: {e}")


@dataclass
class ValidationResult:
    """Result of model validation."""
    
    is_valid: bool
    errors: List[ValidationError] = dc_field(default_factory=list)
    
    def add_error(self, error: ValidationError) -> None:
        """Add an error."""
        self.errors.append(error)
        self.is_valid = False
    
    def get_errors_by_field(self) -> Dict[str, List[str]]:
        """Group errors by field."""
        errors_by_field = {}
        for error in self.errors:
            field = error.field or '__all__'
            if field not in errors_by_field:
                errors_by_field[field] = []
            errors_by_field[field].append(error.message)
        return errors_by_field


# Helper function to validate before save
async def validate_on_save(instance: Any) -> ValidationResult:
    """
    Validate instance before saving.
    
    Usage:
        result = await validate_on_save(user)
        if not result.is_valid:
            for error in result.errors:
                print(f"{error.field}: {error.message}")
    """
    if hasattr(instance, 'validate'):
        errors = await instance.validate()
        result = ValidationResult(is_valid=len(errors) == 0, errors=errors)
        return result
    
    return ValidationResult(is_valid=True)
