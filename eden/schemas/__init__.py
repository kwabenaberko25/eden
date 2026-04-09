from __future__ import annotations
"""
Eden Schemas - Type-safe form schemas with async validation.

Provides Pydantic-based schemas that auto-generate from Eden models,
with async validation, nested relationships, and API documentation.
"""


import uuid
from datetime import datetime, date, time
from typing import (
    Any, Dict, List, Optional, Type, TypeVar, Union, get_type_hints,
    get_origin, get_args, Callable, ClassVar
)
from pydantic import (
    BaseModel, Field, ValidationError, field_validator,
    model_validator, ConfigDict
)
from pydantic_core import PydanticUndefined

from ..db import Model
from ..responses import JSONResponse

T = TypeVar('T', bound=Model)

class ValidationException(Exception):
    """Raised when schema validation fails."""

    def __init__(self, errors: Dict[str, List[str]]):
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")

class SchemaConfig:
    """Configuration for ModelSchema behavior."""

    model: Type[Model]
    exclude_fields: List[str] = []
    read_only_fields: List[str] = []
    required_fields: List[str] = []
    nested_fields: List[str] = []
    validation_level: str = "strict"  # "strict", "lax", "none"

    # API documentation
    json_schema_extra: Dict[str, Any] = {}
    examples: List[Dict[str, Any]] = []

    def __init__(
        self,
        model: Type[Model],
        exclude_fields: Optional[List[str]] = None,
        read_only_fields: Optional[List[str]] = None,
        required_fields: Optional[List[str]] = None,
        nested_fields: Optional[List[str]] = None,
        validation_level: str = "strict",
        json_schema_extra: Optional[Dict[str, Any]] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
    ):
        self.model = model
        self.exclude_fields = exclude_fields or []
        default_read_only = ['id', 'created_at', 'updated_at']
        provided_read_only = read_only_fields or []
        self.read_only_fields = [
            field for field in (default_read_only + provided_read_only)
            if field not in self.exclude_fields
        ]
        self.required_fields = required_fields or []
        self.nested_fields = nested_fields or []
        self.validation_level = validation_level
        self.json_schema_extra = json_schema_extra or {}
        self.examples = examples or []

class ModelSchema(BaseModel):
    """
    Base schema class for Eden models.

    Auto-generates Pydantic fields from model annotations with async validation,
    nested relationships, and API documentation.
    """

    # Instance attributes
    _model_cls: ClassVar[Type[Model]]
    _config: ClassVar[SchemaConfig]
    _errors: Dict[str, List[str]] = {}

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            uuid.UUID: str,
        }
    )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Extract model from class name or Meta
        if hasattr(cls, 'Meta'):
            meta = cls.Meta()
            model_cls = getattr(meta, 'model', None)
        else:
            # Try to infer from class name (e.g., UserSchema -> User)
            class_name = cls.__name__
            if class_name.endswith('Schema'):
                model_name = class_name[:-6]  # Remove 'Schema'
                # This would need to be resolved at runtime
                model_cls = None
            else:
                model_cls = None

        if model_cls:
            cls._model_cls = model_cls
            cls._config = SchemaConfig(model=model_cls)
            cls._auto_generate_fields()

    @classmethod
    def _auto_generate_fields(cls):
        """Auto-generate Pydantic fields from model annotations."""
        if not hasattr(cls, '_model_cls'):
            return

        model_cls = cls._model_cls
        type_hints = get_type_hints(model_cls)

        for field_name, type_hint in type_hints.items():
            if field_name.startswith('_'):
                continue
            if field_name in cls._config.exclude_fields:
                continue

            # Skip if field already defined
            if field_name in cls.model_fields:
                continue

            # Convert SQLAlchemy types to Pydantic
            pydantic_type = cls._convert_type(type_hint, field_name)

            # Determine if required; read-only fields are not required for input
            is_required = (
                field_name in cls._config.required_fields or
                (
                    not cls._is_optional_type(type_hint) and
                    field_name not in cls._config.read_only_fields
                )
            )

            # Create field
            default_value = ... if is_required else None
            field_info = Field(default=default_value, description=f"{field_name} field")

            # Add field to class annotations and attributes
            annotations = getattr(cls, "__annotations__", {})
            annotations[field_name] = pydantic_type
            cls.__annotations__ = annotations
            setattr(cls, field_name, field_info)

        # Rebuild Pydantic model fields after dynamic field injection
        if hasattr(cls, "model_rebuild"):
            cls.model_rebuild()

    @classmethod
    def _convert_type(cls, type_hint: Any, field_name: str) -> Any:
        """Convert SQLAlchemy/Pydantic types appropriately."""
        origin = get_origin(type_hint)
        args = get_args(type_hint)

        # Handle Optional types
        if origin is Union and len(args) == 2 and type(None) in args:
            inner_type = args[0] if args[1] is type(None) else args[1]
            return Optional[cls._convert_type(inner_type, field_name)]

        # Handle List types (relationships)
        if origin is list and args:
            inner_type = cls._convert_type(args[0], field_name)
            return List[inner_type]

        # Basic type conversions
        type_mapping = {
            str: str,
            int: int,
            float: float,
            bool: bool,
            datetime: datetime,
            date: date,
            uuid.UUID: str,  # Convert UUID to string for JSON
        }

        return type_mapping.get(type_hint, Any)

    @classmethod
    def _is_optional_type(cls, type_hint: Any) -> bool:
        """Check if a type is Optional."""
        origin = get_origin(type_hint)
        args = get_args(type_hint)
        return (
            origin is Union and
            len(args) == 2 and
            type(None) in args
        )

    @classmethod
    async def is_valid(cls, data: Dict[str, Any]) -> bool:
        """
        Async validation of input data.

        Returns True if valid, False otherwise.
        Errors are stored in cls._errors.
        """
        try:
            # Create instance to trigger validation
            instance = cls(**data)
            cls._errors = {}
            return True
        except ValidationError as e:
            cls._errors = {}
            for error in e.errors():
                field = error['loc'][0] if error['loc'] else 'non_field'
                message = error['msg']
                if field not in cls._errors:
                    cls._errors[field] = []
                cls._errors[field].append(message)
            return False

    @property
    def errors(self) -> Dict[str, List[str]]:
        """Get validation errors."""
        return getattr(self, '_errors', {})

    async def save(self) -> Model:
        """
        Save the schema data to the database.

        Creates or updates the model instance.
        """
        if not hasattr(self, '_model_cls'):
            raise ValueError("No model class associated with schema")

        model_cls = self._model_cls
        data = self.model_dump(exclude_unset=True)

        # Handle nested relationships
        nested_data = {}
        for field_name in self._config.nested_fields:
            if field_name in data and isinstance(data[field_name], dict):
                nested_data[field_name] = data.pop(field_name)

        # Check if this is an update (has ID) or create
        instance_id = data.get('id')
        if instance_id:
            # Update existing
            instance = await model_cls.query().filter(id=instance_id).first()
            if not instance:
                raise ValueError(f"Instance with id {instance_id} not found")

            # Update fields
            for key, value in data.items():
                if key not in self._config.read_only_fields:
                    setattr(instance, key, value)

            await instance.save()
        else:
            # Create new
            instance = await model_cls.create(**data)

        # Handle nested relationships
        for field_name, nested_values in nested_data.items():
            if hasattr(instance, field_name):
                related_manager = getattr(instance, field_name)
                if hasattr(related_manager, 'create'):
                    await related_manager.create(**nested_values)

        return instance

    @classmethod
    def from_model(cls, instance: Model) -> 'ModelSchema':
        """Create a schema instance from a model instance."""
        data = {}
        for field_name in cls.model_fields:
            if hasattr(instance, field_name):
                value = getattr(instance, field_name)
                # Convert UUID to string for JSON compatibility
                if isinstance(value, uuid.UUID):
                    value = str(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()
                data[field_name] = value

        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary."""
        return self.model_dump()

    def to_json_response(self, status_code: int = 200) -> JSONResponse:
        """Convert schema to JSON response."""
        return JSONResponse(self.to_dict(), status_code=status_code)

# Convenience function for creating schemas
def create_schema(
    model_cls: Type[Model],
    name: Optional[str] = None,
    exclude_fields: Optional[List[str]] = None,
    read_only_fields: Optional[List[str]] = None,
    required_fields: Optional[List[str]] = None,
    nested_fields: Optional[List[str]] = None,
) -> Type[ModelSchema]:
    """
    Create a ModelSchema class for the given model.

    This is a convenience function for creating simple schemas without
    defining a custom class.
    """

    class_name = name or f"{model_cls.__name__}Schema"

    config = SchemaConfig(
        model=model_cls,
        exclude_fields=exclude_fields or [],
        read_only_fields=read_only_fields or ['id', 'created_at', 'updated_at'],
        required_fields=required_fields or [],
        nested_fields=nested_fields or [],
    )

    # Create the schema class
    schema_cls = type(
        class_name,
        (ModelSchema,),
        {
            'Meta': lambda: config,
            '__module__': __name__,
        }
    )

    return schema_cls

# Example usage decorators for async validation
def async_validator(field_name: str):
    """Decorator for async field validators."""
    def decorator(func: Callable) -> Callable:
        # Store the async validator for later execution
        func._async_validator = True
        func._field_name = field_name
        return func
    return decorator