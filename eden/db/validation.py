"""
Eden DB - Validation System

Provides declarative validation rules and lifecycle hooks for models.
"""

from typing import Any, Dict, List, Optional, Callable, Union, ClassVar
from dataclasses import dataclass, field as dc_field
import re
import logging
import asyncio

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
    
    # Class-level state per model (isolated in __init_subclass__)
    _validation_rules: ClassVar[Dict[str, List[ValidationRule]]] = {}
    _pre_save_hooks: ClassVar[List[Callable]] = []
    _post_save_hooks: ClassVar[List[Callable]] = []
    _pre_delete_hooks: ClassVar[List[Callable]] = []
    _post_delete_hooks: ClassVar[List[Callable]] = []
    
    def __init_subclass__(cls, **kwargs):
        """Isolate validation state per model to prevent rule leakage."""
        super().__init_subclass__(**kwargs)
        
        # Initialize isolated lists for the subclass
        cls._validation_rules = {}
        cls._pre_save_hooks = []
        cls._post_save_hooks = []
        cls._pre_delete_hooks = []
        cls._post_delete_hooks = []
    
    @classmethod
    def add_validation_rule(cls, field_name: str, rule: ValidationRule) -> None:
        """Add a validation rule to a field."""
        if field_name not in cls._validation_rules:
            cls._validation_rules[field_name] = []
        cls._validation_rules[field_name].append(rule)
    
    @classmethod
    def rule_required(cls, field_name: str, message: Optional[str] = None) -> None:
        """Mark field as required."""
        cls.add_validation_rule(field_name, ValidationRule(
            field_name=field_name,
            rule_type='required',
            message=message or f"{field_name} is required"
        ))
    
    @classmethod
    def rule_email(cls, field_name: str, message: Optional[str] = None) -> None:
        """Validate field as email."""
        cls.add_validation_rule(field_name, ValidationRule(
            field_name=field_name,
            rule_type='email',
            message=message or f"{field_name} must be a valid email"
        ))
    
    @classmethod
    def rule_min_length(cls, field_name: str, length: int, message: Optional[str] = None) -> None:
        """Validate minimum length."""
        cls.add_validation_rule(field_name, ValidationRule(
            field_name=field_name,
            rule_type='min_length',
            rule_value=length,
            message=message or f"{field_name} must be at least {length} characters"
        ))
    
    @classmethod
    def rule_max_length(cls, field_name: str, length: int, message: Optional[str] = None) -> None:
        """Validate maximum length."""
        cls.add_validation_rule(field_name, ValidationRule(
            field_name=field_name,
            rule_type='max_length',
            rule_value=length,
            message=message or f"{field_name} must be at most {length} characters"
        ))

    @classmethod
    def rule_choices(cls, field_name: str, options: list, message: Optional[str] = None) -> None:
        """Validate field value is one of the choices."""
        cls.add_validation_rule(field_name, ValidationRule(
            field_name=field_name,
            rule_type='choices',
            rule_value=options,
            message=message or f"{field_name} must be one of {options}"
        ))

    @classmethod
    def rule_pattern(cls, field_name: str, regex: str, message: Optional[str] = None) -> None:
        """Validate field value against a regex pattern."""
        cls.add_validation_rule(field_name, ValidationRule(
            field_name=field_name,
            rule_type='pattern',
            rule_value=regex,
            message=message or f"{field_name} has invalid format"
        ))
    
    @classmethod
    def rule_custom(cls, field_name: str, validator: Callable, message: str) -> None:
        """Add custom validation function."""
        cls.add_validation_rule(field_name, ValidationRule(
            field_name=field_name,
            rule_type='custom',
            message=message,
            validator_func=validator
        ))
    
    async def validate(self) -> List[ValidationError]:
        """Run all validation rules and return errors."""
        errors: List[ValidationError] = []
        
        # Run declarative rules
        for field_name, rules in self._validation_rules.items():
            field_value = getattr(self, field_name, None)
            for rule in rules:
                try:
                    self._validate_rule(field_name, field_value, rule)
                except ValidationError as e:
                    errors.append(e)
        
        # Run clean() method if defined
        if hasattr(self, 'clean'):
            if asyncio.iscoroutinefunction(self.clean):
                try:
                    await self.clean()
                except ValidationError as e:
                    errors.append(e)
            else:
                try:
                    self.clean()
                except ValidationError as e:
                    errors.append(e)
        
        # Run field-specific clean_<field>() methods
        for field_name in self.__fields__.keys() if hasattr(self, '__fields__') else []:
            clean_method = f"clean_{field_name}"
            if hasattr(self, clean_method):
                method = getattr(self, clean_method)
                try:
                    if asyncio.iscoroutinefunction(method):
                        await method()
                    else:
                        method()
                except ValidationError as e:
                    errors.append(e)
                    
        return errors
    
    def _validate_rule(self, field_name: str, value: Any, rule: ValidationRule) -> None:
        """Internal rule validator."""
        if rule.rule_type == 'required':
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValidationError(rule.message, field_name)
        
        elif rule.rule_type == 'email':
            if value and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(value)):
                raise ValidationError(rule.message, field_name)
        
        elif rule.rule_type == 'min_length':
            if value and len(str(value)) < rule.rule_value:
                raise ValidationError(rule.message, field_name)
        
        elif rule.rule_type == 'max_length':
            if value and len(str(value)) > rule.rule_value:
                raise ValidationError(rule.message, field_name)

        elif rule.rule_type == 'choices':
            if value is not None and value not in rule.rule_value:
                raise ValidationError(rule.message, field_name)

        elif rule.rule_type == 'pattern':
            if value and not re.match(rule.rule_value, str(value)):
                raise ValidationError(rule.message, field_name)
        
        elif rule.rule_type == 'custom' and rule.validator_func:
            if not rule.validator_func(value):
                raise ValidationError(rule.message, field_name)

    @classmethod
    def pre_save(cls, hook: Callable) -> None: cls._pre_save_hooks.append(hook)
    
    @classmethod
    def post_save(cls, hook: Callable) -> None: cls._post_save_hooks.append(hook)

    async def _trigger_hooks(self, hook_list: List[Callable]) -> None:
        """Execute a list of hooks."""
        for hook in hook_list:
            if asyncio.iscoroutinefunction(hook):
                await hook(self)
            else:
                hook(self)


@dataclass
class ValidationResult:
    """Result of model validation."""
    is_valid: bool
    errors: List[ValidationError] = dc_field(default_factory=list)
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Group errors by field."""
        result = {}
        for err in self.errors:
            field = err.field or '__all__'
            if field not in result:
                result[field] = []
            result[field].append(err.message)
        return result
