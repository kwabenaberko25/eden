from __future__ import annotations
"""
Eden Forms — Unified form system for validation, rendering, and model binding.

This package provides:
- Schema/field(): Pydantic-based validation with ORM integration
- BaseForm: Request-aware form with file upload support
- ModelForm: Django-style declarative model-bound forms
- FormField: Rich HTML rendering for templates
- Form: Typed generic forms for programmatic construction
- Widget hierarchy: Extensible widget system
- FormRenderer: Standalone form rendering utility
"""

# Core form classes
from eden.forms.base import (
    Form,
    BaseForm,
    BoundForm,
    FormField,
    FileField,
    BasicFormField,
    BoundFormField,
)

# Typed fields (for builder subsystem)
from eden.forms.fields import CharField, IntegerField, EmailField, ChoiceField

# Widgets
from eden.forms.widgets import Widget, TextInput, NumberInput, EmailInput, Select

# Rendering
from eden.forms.rendering import FormRenderer

# Schema system
from eden.forms.schema import Schema, SchemaMeta, field, v, f

# Model-bound forms
from eden.forms.model_form import ModelForm

# File upload types
from eden.forms.uploads import UploadedFile, ProgressCallback

# Re-export Pydantic types used in form schemas
from pydantic import EmailStr, AnyUrl


__all__ = [
    # Core
    "Form",
    "BaseForm",
    "BoundForm",
    "FormField",
    "FileField",
    "BasicFormField",
    "BoundFormField",
    # Typed fields
    "CharField",
    "IntegerField",
    "EmailField",
    "ChoiceField",
    # Widgets
    "Widget",
    "TextInput",
    "NumberInput",
    "EmailInput",
    "Select",
    # Rendering
    "FormRenderer",
    # Schema
    "Schema",
    "SchemaMeta",
    "field",
    "v",
    "f",
    # Model form
    "ModelForm",
    # Uploads
    "UploadedFile",
    "ProgressCallback",
    # Pydantic re-exports
    "EmailStr",
    "AnyUrl",
]
