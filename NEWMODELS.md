# Eden Framework: New Models, Forms & Schema Architecture

## 🎯 Vision

Modernize Eden's model, form, and schema system with:
- **@model.define** decorator for clean, dataclass-like model definitions
- **Composable validators** with async-first design
- **TypedForm** class-based forms with type safety
- **Form builder** fluent API (InlineForm) for rapid form creation

## 📋 Architectural Decisions (APPROVED)

✅ **Full migration to @model.define only** - Clean break from old syntax  
✅ **Structured FieldMetadata dataclass** - Type-safe metadata with ORM/Form/Validation layers  
✅ **Validator as first-class objects** - Context-aware, composable with `|` operator  
✅ **Use Pydantic FieldInfo directly** - Extend with `json_schema_extra={'eden': {...}}`  
✅ **Dataclass-like syntax** - Clean, familiar type hints  
✅ **Forms both declarative & imperative** - TypedForm + Form builder  
✅ **Async-first validators** - Async by default, sync wrapper for convenience  
✅ **TDD for implementation** - Tests first, then implementation  

---

## 💡 Architecture Overview

### Field Definition System
```python
from eden import field

# Field creation with metadata
email_field = field.email(unique=True, index=True, label="Email Address")
# Returns: Pydantic FieldInfo with Eden metadata in json_schema_extra

# Validators attach to fields
password_field = field.password(min_length=8) | v.custom(check_complexity)

# Metadata preserved for ORM, forms, validation
# - ORM: unique, index, nullable, default
# - Forms: widget, label, placeholder, help_text, css_classes
# - Validation: validators, error_messages
```

### Model Definition
```python
from eden import model, field

@model.define
class User:
    id: UUID = field.id()
    email: str = field.email(unique=True, index=True)
    name: str = field.string(max_length=100)
    bio: str | None = field.text(nullable=True)
    is_active: bool = field.bool(default=True)
    created_at: datetime = field.auto_now()
    updated_at: datetime = field.auto_now_update()
    
    # Built-in model methods (auto-generated):
    # .save(), .delete(), .refresh(), .as_form(), etc.
```

### Form - Typed Class
```python
from eden import form, validators as v

class UserSignupForm(form.TypedForm):
    email: str = v.email() | v.unique(User, "email")
    password: str = v.password(min_length=8)
    confirm: str = v.match("password")
    
    async def on_valid(self):
        """Hook called after validation passes"""
        user = User(email=self.email)
        user.set_password(self.password)
        await user.save()
    
    async def on_error(self, errors):
        """Hook called if validation fails"""
        # Log, send alerts, etc.
        pass
```

### Form - Builder (InlineForm)
```python
from eden import Form, field, validators as v

form = (
    Form("user_signup")
    .field("email", field.email(unique=True))
    .field("password", field.password(min_length=8))
    .field("confirm_password", field.string(max_length=100))
    .validate("password", "confirm_password", match=True)
    .help("password", "Must be at least 8 characters")
    .required("email", "password", "confirm_password")
    .on_submit(handle_signup)
    .csrf_protection(True)
)

# Usage
if await form.validate(request.data):
    user_data = form.validated_data()
else:
    errors = form.errors()
```

---

## 📊 Implementation Phases

### Phase 1: Field Types System (10 Sub-Phases)

#### 1.1: Core Infrastructure
- **1.1.1:** FieldMetadata dataclass with ORM/Form/Validation layers
- **1.1.2:** Validator protocol, ValidationContext, ValidationResult, __or__ composability
- **1.1.3:** Field base class, FieldRegistry, validator attachment
- **1.1.4:** Comprehensive tests for base infrastructure

**Files to Create:**
```
eden/fields/
├── __init__.py
├── base.py           # FieldMetadata, ValidationResult, ValidationContext
├── validator.py      # Validator ABC, CompositeValidator
└── registry.py       # FieldRegistry
tests/
├── test_fields_base.py
└── test_fields_validators_base.py
```

#### 1.2: String & Text Fields
- **1.2.1:** `field.string()`, `field.email()`, `field.url()`, `field.slug()`, `field.phone()`, `field.text()`, `field.password()`, `field.uuid()`
- **1.2.2:** Comprehensive tests for all string field types

**Files to Create:**
```
eden/fields/
└── string_fields.py  # All string field helpers
tests/
└── test_fields_string.py
```

#### 1.3: Numeric & Boolean Fields
- **1.3.1:** `field.int()`, `field.float()`, `field.decimal()`, `field.bool()`
- **1.3.2:** Tests for constraints (min/max, unique, index)

**Files to Create:**
```
eden/fields/
└── numeric_fields.py
tests/
└── test_fields_numeric.py
```

#### 1.4: Datetime & Temporal Fields
- **1.4.1:** `field.datetime()`, `field.date()`, `field.time()`, `field.auto_now()`, `field.auto_now_update()`
- **1.4.2:** Tests with timezone handling, auto-update behavior

**Files to Create:**
```
eden/fields/
└── datetime_fields.py
tests/
└── test_fields_datetime.py
```

#### 1.5: Complex Fields
- **1.5.1:** `field.json()`, `field.array()`, `field.enum()`, `field.file()`, `field.image()`
- **1.5.2:** Tests for serialization, file validation, array constraints

**Files to Create:**
```
eden/fields/
└── complex_fields.py
tests/
└── test_fields_complex.py
```

#### 1.6: Relationship & Foreign Key Fields
- **1.6.1:** `field.foreign_key()`, `field.one_to_one()`, `field.many_to_many()`
- **1.6.2:** Tests with lazy loading, cascading, through tables

**Files to Create:**
```
eden/fields/
└── relationship_fields.py
tests/
└── test_fields_relationships.py
```

#### 1.7: Field-Level Validators
- **1.7.1:** Attach validators to fields, store in FieldMetadata
- **1.7.2:** Tests for validator chaining, error messages, async validators

**Files to Create:**
```
tests/
└── test_fields_validators.py
```

#### 1.8: SQLAlchemy Column Mapping
- **1.8.1:** Field → SQLAlchemy Column mapping layer
- **1.8.2:** Tests for round-trip: Field → Column → DB

**Files to Create:**
```
eden/fields/
└── sqlalchemy_mapping.py
tests/
└── test_fields_sqlalchemy_mapping.py
```

#### 1.9: Form Widget Mapping
- **1.9.1:** Widget hints in FieldMetadata, HTML rendering support
- **1.9.2:** Tests for form rendering, CSS classes, custom widgets

**Files to Create:**
```
eden/fields/
└── form_widget_mapping.py
tests/
└── test_fields_form_widgets.py
```

#### 1.10: Comprehensive Use Case Tests
- **1.10.1:** Complex field combinations, edge cases, full workflows

**Files to Create:**
```
tests/
└── test_use_cases_fields.py
```

---

### Phase 2: Model Decorator (@model.define)

- Create `eden/models/decorator.py` with `@model.define`
- Auto-generate `__tablename__` from class name (snake_case)
- Map field annotations to `Mapped[type]` internally
- Ensure all existing CRUD methods work (.save(), .delete(), .refresh(), etc.)
- Support model inheritance
- Auto-generate migrations with Alembic

**Files to Create:**
```
eden/models/
├── __init__.py
└── decorator.py      # @model.define implementation
```

**Tests:**
```
tests/
└── test_model_decorator.py
```

---

### Phase 3: Composable Validators System

Build comprehensive validator library with:

**String Validators:**
- `v.string()` - Type check
- `v.email()` - Email format
- `v.url()` - URL format
- `v.slug()` - URL-friendly slug
- `v.phone()` - Phone number
- `v.uuid()` - UUID format

**Length Validators:**
- `v.min_length(n)` - Minimum string length
- `v.max_length(n)` - Maximum string length
- `v.length_between(min, max)` - Range

**Numeric Validators:**
- `v.min(n)` - Minimum value
- `v.max(n)` - Maximum value
- `v.range(min, max)` - Value range
- `v.positive()` - Positive number
- `v.negative()` - Negative number

**Pattern Validators:**
- `v.pattern(regex)` - Regex pattern
- `v.alphanumeric()` - Alphanumeric only
- `v.alpha()` - Letters only
- `v.numeric()` - Numbers only

**Type Validators:**
- `v.type(typ)` - Type check
- `v.instance_of(cls)` - Instance check

**Database Validators (Async):**
- `v.unique(Model, field)` - Database uniqueness check
- `v.exists(Model, field)` - Record exists check

**Comparison Validators:**
- `v.match(field_name)` - Field equality (e.g., password confirm)
- `v.gt(field_name)` - Greater than field
- `v.lt(field_name)` - Less than field
- `v.gte(field_name)` - Greater than or equal
- `v.lte(field_name)` - Less than or equal

**Custom Validators:**
- `v.custom(callable)` - Sync custom validator
- `v.custom_async(async_callable)` - Async custom validator

**Conditional Validators:**
- `v.required_if(field, value)` - Required if condition
- `v.required_unless(field, value)` - Required unless condition
- `v.required_when(predicate)` - Required when predicate true

**List Validators:**
- `v.min_items(n)` - Minimum items in list
- `v.max_items(n)` - Maximum items
- `v.unique_items()` - Unique items only
- `v.contains(value)` - Contains value

**Date Validators:**
- `v.before_date(date)` - Before date
- `v.after_date(date)` - After date
- `v.date_range(start, end)` - Date range

**Composition:**
```python
# Chain validators with |
v.email() | v.unique(User, "email") | v.custom(lambda x: not x.startswith("+"))

# Custom error messages
(v.email() | v.unique(User, "email")).with_message("Email must be unique")
```

**Files to Create:**
```
eden/validators/
├── __init__.py
├── base.py           # Validator ABC, ValidationResult, ValidationContext
├── composable.py     # Validator implementations, composition logic
├── string.py         # String validators
├── numeric.py        # Numeric validators
├── date.py          # Date validators
├── database.py      # Async DB validators
├── comparison.py    # Comparison validators
└── custom.py        # Custom/conditional validators
```

**Tests:**
```
tests/
├── test_validators_base.py
├── test_validators_string.py
├── test_validators_numeric.py
├── test_validators_date.py
├── test_validators_database.py
├── test_validators_composition.py
└── test_validators_use_cases.py
```

---

### Phase 4: TypedForm Class

Build class-based typed forms with:
- Inherit from Pydantic BaseModel for type safety
- Support composable validators
- `on_valid()` hook - called after validation passes
- `on_error()` hook - called if validation fails
- Form rendering methods (`.render()`, `.render_field()`)
- Model-to-form auto-generation (`.from_model()`)
- CSRF protection
- File upload handling
- Field grouping/sections

**Example:**
```python
class UserSignupForm(form.TypedForm):
    email: str = v.email() | v.unique(User, "email")
    password: str = v.password(min_length=8)
    confirm: str = v.match("password")
    
    class Config:
        model = User
        exclude = ["id", "created_at", "updated_at"]
        csrf_protection = True
    
    async def on_valid(self):
        user = User(email=self.email)
        user.set_password(self.password)
        await user.save()
        return user
```

**Files to Create:**
```
eden/forms/
├── __init__.py
├── typed.py          # TypedForm base class
├── rendering.py      # Form field rendering
└── auto.py          # Model-to-form auto-generation
```

**Tests:**
```
tests/
├── test_forms_typed.py
├── test_forms_validation.py
└── test_forms_use_cases.py
```

---

### Phase 5: Form Builder (InlineForm)

Build fluent API for rapid form creation:
```python
form = (
    Form("user_signup")
    .field("email", field.email(unique=True))
    .field("password", field.password(min_length=8))
    .validate("password", "confirm_password", match=True)
    .help("password", "Must be at least 8 characters")
    .required("email", "password")
    .on_submit(handle_signup)
    .csrf_protection(True)
)
```

**Features:**
- `.field(name, FieldType)` - Add field
- `.validate(fields, rule)` - Add validation rule
- `.help(field, text)` - Add help text
- `.label(field, text)` - Set label
- `.placeholder(field, text)` - Set placeholder
- `.required(fields)` - Mark required
- `.optional(fields)` - Mark optional
- `.on_submit(handler)` - Register submit handler
- `.on_error(handler)` - Register error handler
- `.csrf_protection(bool)` - Enable/disable CSRF
- `.group(name, fields)` - Group related fields
- `.render()` - Render form HTML
- `.render_field(name)` - Render single field
- `.validate(data)` - Validate data
- `.validated_data()` - Get clean data
- `.errors()` - Get error dict

**Files to Create:**
```
eden/forms/
└── builder.py        # Form builder fluent API
```

**Tests:**
```
tests/
└── test_forms_builder.py
```

---

### Phase 6: Integration & Documentation

- Update existing models to demonstrate @model.define
- Create comprehensive documentation
- Add examples to docs/
- Create migration guide from old syntax
- Integration tests combining all phases
- CLI tool for scaffolding new models/forms

**Files to Create:**
```
docs/models-forms/
├── quick-start.md
├── field-types.md
├── validators.md
├── forms-typed.md
├── forms-builder.md
├── migration-guide.md
└── examples.md

examples/
├── user-model.py
├── user-signup-form.py
├── blog-model.py
└── blog-forms.py
```

**Tests:**
```
tests/
├── test_integration.py
└── test_use_cases_full.py
```

---

## 📁 Complete File Structure

```
eden/
├── fields/
│   ├── __init__.py
│   ├── base.py                  # FieldMetadata, ValidationResult, ValidationContext
│   ├── validator.py             # Validator ABC, CompositeValidator
│   ├── registry.py              # FieldRegistry
│   ├── string_fields.py          # String field helpers
│   ├── numeric_fields.py         # Numeric field helpers
│   ├── datetime_fields.py        # Datetime field helpers
│   ├── complex_fields.py         # JSON, array, enum, file, image
│   ├── relationship_fields.py    # FK, O2O, M2M
│   ├── sqlalchemy_mapping.py     # Field → SQLAlchemy Column
│   └── form_widget_mapping.py    # Field → Form widget
├── models/
│   ├── __init__.py
│   └── decorator.py             # @model.define implementation
├── validators/
│   ├── __init__.py
│   ├── base.py                  # Validator ABC, composition
│   ├── composable.py            # Validator implementations
│   ├── string.py                # String validators
│   ├── numeric.py               # Numeric validators
│   ├── date.py                  # Date validators
│   ├── database.py              # Async DB validators
│   ├── comparison.py            # Comparison validators
│   └── custom.py                # Custom/conditional validators
├── forms/
│   ├── __init__.py
│   ├── typed.py                 # TypedForm base class
│   ├── builder.py               # Form builder fluent API
│   ├── rendering.py             # Form rendering
│   └── auto.py                  # Model-to-form auto-generation
└── db/
    └── base.py                  # Existing Model class (unchanged)

tests/
├── test_fields_base.py
├── test_fields_string.py
├── test_fields_numeric.py
├── test_fields_datetime.py
├── test_fields_complex.py
├── test_fields_relationships.py
├── test_fields_validators.py
├── test_fields_sqlalchemy_mapping.py
├── test_fields_form_widgets.py
├── test_use_cases_fields.py
├── test_model_decorator.py
├── test_validators_base.py
├── test_validators_string.py
├── test_validators_numeric.py
├── test_validators_date.py
├── test_validators_database.py
├── test_validators_composition.py
├── test_validators_use_cases.py
├── test_forms_typed.py
├── test_forms_validation.py
├── test_forms_use_cases.py
├── test_forms_builder.py
├── test_integration.py
└── test_use_cases_full.py

docs/models-forms/
├── quick-start.md
├── field-types.md
├── validators.md
├── forms-typed.md
├── forms-builder.md
├── migration-guide.md
└── examples.md

examples/
├── user-model.py
├── user-signup-form.py
├── blog-model.py
└── blog-forms.py
```

---

## 🧪 Testing Strategy (TDD)

**For each sub-phase:**
1. Write tests FIRST in `tests/`
2. Implement code to pass tests
3. Run full test suite
4. Verify coverage (target: >95%)

**Test categories per phase:**
- **Unit tests:** Individual validators, fields, etc.
- **Integration tests:** Field → ORM, Field → Form, etc.
- **Use case tests:** Real-world scenarios, edge cases
- **End-to-end tests:** Complete model → form → validation flow

**Example test structure:**
```python
# tests/test_fields_string.py
import pytest
from eden import field, validators as v
from eden.fields.base import FieldMetadata

@pytest.mark.asyncio
async def test_email_field_creation():
    """Test email field is created with correct metadata"""
    email_field = field.email(unique=True, index=True)
    assert email_field.metadata.widget == "email"
    assert email_field.metadata.unique == True

@pytest.mark.asyncio
async def test_email_field_with_validator():
    """Test email field with validator chain"""
    field_with_validator = field.email() | v.unique(User, "email")
    result = await field_with_validator.validate("test@example.com", context)
    assert result.ok == True
```

---

## ⚠️ Breaking Changes

- **Old syntax no longer supported:** `class User(Model)` with `Mapped[type]` deprecated
- **Field creation API changed:** Use `field.string()` instead of `StringField()`
- **Form syntax changed:** TypedForm and Form builder replace old form system
- **Migration path:** See Phase 6 documentation

---

## 🚀 Getting Started

### Phase 1.1: Core Infrastructure (Start Here)

```bash
# Create field base infrastructure
# Tests define the API, then implement

# 1. Run tests to see what needs implementing
pytest tests/test_fields_base.py -v

# 2. Implement eden/fields/base.py
# 3. Run tests again until all pass
pytest tests/test_fields_base.py -v

# Repeat for 1.1.2, 1.1.3, 1.1.4
```

---

## 📈 Success Criteria

- ✅ All tests pass (>95% coverage)
- ✅ Examples work without modification
- ✅ Documentation is complete and accurate
- ✅ Performance matches or exceeds old system
- ✅ New system feels intuitive to use
- ✅ Error messages are helpful
- ✅ IDE autocomplete works seamlessly

---

**Last Updated:** 2026-04-06  
**Status:** Ready for Phase 1.1 Implementation
