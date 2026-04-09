from __future__ import annotations
"""
Eden Typed Forms - HTML form generation from field definitions.

Phase 4 of the field/form/model architecture provides a typed form system
that generates HTML forms from field definitions with proper validation,
error rendering, and accessibility support.
"""


import importlib.util
import pathlib
from types import ModuleType

from eden.forms.base import Form, BoundForm, FormField
from eden.forms.fields import CharField, IntegerField, EmailField, ChoiceField
from eden.forms.widgets import Widget, TextInput, NumberInput, EmailInput, Select
from eden.forms.rendering import FormRenderer


def _load_forms_module() -> ModuleType:
    module_path = pathlib.Path(__file__).parent.parent / "forms.py"
    spec = importlib.util.spec_from_file_location("eden.forms_module", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load the eden.forms module from forms.py")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

_forms_module = _load_forms_module()

Schema = _forms_module.Schema
BaseForm = _forms_module.BaseForm
ModelForm = _forms_module.ModelForm
FormField = _forms_module.FormField
field = _forms_module.field
v = _forms_module.v
FileField = _forms_module.FileField
UploadedFile = _forms_module.UploadedFile
ProgressCallback = _forms_module.ProgressCallback
EmailStr = _forms_module.EmailStr
AnyUrl = _forms_module.AnyUrl

__all__ = [
    "Form",
    "BoundForm",
    "FormField",
    "CharField",
    "IntegerField",
    "EmailField",
    "ChoiceField",
    "Widget",
    "TextInput",
    "NumberInput",
    "EmailInput",
    "Select",
    "FormRenderer",
    "Schema",
    "BaseForm",
    "ModelForm",
    "field",
    "v",
    "FileField",
    "UploadedFile",
    "ProgressCallback",
    "EmailStr",
    "AnyUrl",
]
