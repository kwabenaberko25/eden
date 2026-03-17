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
    """Raised when validation fails for a single field or a complex constraint."""
    
    def __init__(self, message: Union[str, List[str], Dict[str, List[str]]], field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(str(message))

class ValidationErrors(Exception):
    """Raised when multiple validations fail across a model."""
    
    def __init__(self, errors: Dict[str, List[str]]):
        self.errors = errors
        message = "; ".join([f"{k}: {', '.join(v)}" for k, v in errors.items()])
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
    """Mixin to add validation hooks and full lifecycle cleaning to models."""
    
    # Class-level state per model (isolated in __init_subclass__)
    _validation_rules: ClassVar[Dict[str, List[ValidationRule]]] = {}
    _pre_save_hooks: ClassVar[List[Callable]] = []
    _post_save_hooks: ClassVar[List[Callable]] = []
    _pre_delete_hooks: ClassVar[List[Callable]] = []
    _post_delete_hooks: ClassVar[List[Callable]] = []

    def __init_subclass__(cls, **kwargs):
        """Isolate validation state per model to prevent rule leakage."""
        super().__init_subclass__(**kwargs)
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
    
    async def full_clean(self, exclude: Optional[List[str]] = None) -> None:
        """
        Run the full validation lifecycle for the model.
        1. clean_fields() - Validates each field individually
        2. clean() - Performs cross-field validation
        3. validate() - Runs declarative validation rules
        
        Raises ValidationErrors if any validation fails.
        """
        errors: Dict[str, List[str]] = {}
        exclude = exclude or []

        # 1. Individual field validation (metadata-based)
        try:
            await self.clean_fields(exclude=exclude)
        except ValidationErrors as e:
            errors.update(e.errors)

        # 2. Cross-field validation (custom clean method)
        try:
            if hasattr(self, 'clean'):
                if asyncio.iscoroutinefunction(self.clean):
                    await self.clean()
                else:
                    self.clean()
        except ValidationError as e:
            field = e.field or '__all__'
            if field not in errors: errors[field] = []
            errors[field].append(str(e.message))
        except ValidationErrors as e:
            errors.update(e.errors)

        # 3. Declarative validation rules
        for field_name, rules in self._validation_rules.items():
            if field_name in exclude:
                continue
            field_value = getattr(self, field_name, None)
            for rule in rules:
                try:
                    self._validate_rule(field_name, field_value, rule)
                except ValidationError as e:
                    if field_name not in errors: errors[field_name] = []
                    errors[field_name].append(str(e.message))

        if errors:
            raise ValidationErrors(errors)

    async def clean_fields(self, exclude: Optional[List[str]] = None) -> None:
        """
        Clean and validate each model field individually.
        Checks for clean_<fieldname>() methods on the model.
        """
        errors: Dict[str, List[str]] = {}
        exclude = exclude or []

        # Get all fields from mapped columns
        from sqlalchemy import inspect
        try:
            mapper = inspect(self.__class__)
        except Exception:
            # Not a mapped class or not ready
            return
        
        for name, column in mapper.columns.items():
            if name in exclude:
                continue
            
            # Call custom clean_<field> method if it exists
            clean_method = f"clean_{name}"
            if hasattr(self, clean_method):
                method = getattr(self, clean_method)
                try:
                    if asyncio.iscoroutinefunction(method):
                        await method()
                    else:
                        method()
                except ValidationError as e:
                    if name not in errors: errors[name] = []
                    errors[name].append(str(e.message))

        if errors:
            raise ValidationErrors(errors)

    def _validate_rule(self, field_name: str, value: Any, rule: ValidationRule) -> None:
        """Internal rule validator."""
        if rule.rule_type == 'required':
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValidationError(rule.message or f"{field_name} is required", field_name)
        
        elif rule.rule_type == 'email':
            if value and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(value)):
                raise ValidationError(rule.message or f"{field_name} must be a valid email", field_name)
        
        elif rule.rule_type == 'min_length':
            if value and len(str(value)) < rule.rule_value:
                raise ValidationError(rule.message or f"{field_name} must be at least {rule.rule_value} characters", field_name)
        
        elif rule.rule_type == 'max_length':
            if value and len(str(value)) > rule.rule_value:
                raise ValidationError(rule.message or f"{field_name} must be at most {rule.rule_value} characters", field_name)

        elif rule.rule_type == 'choices':
            if value is not None:
                # Handle list of tuples [(val, label), ...]
                if isinstance(rule.rule_value, list) and rule.rule_value and isinstance(rule.rule_value[0], (list, tuple)):
                    valid_values = [item[0] for item in rule.rule_value]
                else:
                    valid_values = rule.rule_value
                    
                if value not in valid_values:
                    raise ValidationError(rule.message or f"{field_name} must be one of {valid_values}", field_name)

        elif rule.rule_type == 'pattern':
            if value and not re.match(rule.rule_value, str(value)):
                raise ValidationError(rule.message or f"{field_name} has invalid format", field_name)
        
        elif rule.rule_type == 'custom' and rule.validator_func:
            if not rule.validator_func(value):
                raise ValidationError(rule.message or f"{field_name} is invalid", field_name)

    async def validate(self) -> List[ValidationError]:
        """
        Legacy compatibility: Run full_clean and return a list of ValidationError objects.
        Better to use full_clean() directly and catch ValidationErrors.
        """
        try:
            await self.full_clean()
            return []
        except ValidationErrors as e:
            res = []
            for field, messages in e.errors.items():
                for msg in messages:
                    res.append(ValidationError(msg, field))
            return res

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
    errors: Dict[str, List[str]] = dc_field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Returns the errors dictionary."""
        return self.errors
