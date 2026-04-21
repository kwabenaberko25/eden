from __future__ import annotations

"""
Core form classes for the Eden framework.

This module contains:
- BasicFormField: Simple dataclass form field with validator support (used by eden/builder/)
- FormField: Rich HTML-rendering form field with XSS protection (used by views/templates)
- Form: Generic typed form class (used by eden/builder/)
- BaseForm: Pydantic schema-wrapping form with request parsing (used by framework core)
- BoundForm / BoundFormField: Data-bound form wrappers
"""

import io
from dataclasses import dataclass, field as dataclass_field
from typing import Any, Callable, Awaitable, Dict, Generic, Iterator, List, Optional, Type, TypeVar, Union, get_type_hints
from uuid import uuid4

from markupsafe import Markup, escape
from pydantic import BaseModel

from eden.context import get_request
from eden.validators.base import ValidationContext, ValidationResult

T = TypeVar("T")


# ── BasicFormField (formerly the package FormField) ──────────────────────────

@dataclass
class BasicFormField:
    """
    A lightweight field in a form, with validator support.

    Used by the eden/builder/ subsystem for programmatic form construction.
    For template rendering, use FormField instead.
    """

    name: str
    label: str | None = None
    required: bool = False
    help_text: str | None = None
    error_messages: dict[str, str] = dataclass_field(default_factory=dict)
    validators: list = dataclass_field(default_factory=list)
    value: Any = None
    errors: list[str] = dataclass_field(default_factory=list)

    def validate(self) -> ValidationResult:
        """Validate the field value."""
        context = ValidationContext(
            field_name=self.name,
            field_label=self.label or self.name,
            value=self.value,
        )

        result = ValidationResult(is_valid=True)

        for validator in self.validators:
            sub_result = validator.validate(self.value, context)
            result.merge(sub_result)

        self.errors = result.errors
        return result


# ── FormField (rich HTML renderer from monolith) ─────────────────────────────


class FormField:
    """
    Representation of a single form field with rendering helpers.

    This is the primary field class used in Eden views and templates.
    Provides XSS-safe HTML rendering for inputs, textareas, selects,
    file uploads, checkboxes, radio buttons, and custom widgets.

    Usage in templates::

        {{ form['email'].as_input() }}
        {{ form['bio'].as_textarea() }}
        {{ form['avatar'].as_file(accept='image/*') }}
    """

    # Global registry for widget renderers to allow extensibility
    WIDGET_RENDERERS: Dict[str, Callable[["FormField", dict], Markup]] = {}

    @classmethod
    def register_widget(cls, name: str, renderer: Callable[["FormField", dict], Markup]):
        """Register a custom widget renderer."""
        cls.WIDGET_RENDERERS[name] = renderer

    def __init__(
        self,
        name: str | None = None,
        value: Any = None,
        error: str | None = None,
        required: bool = False,
        label: str | None = None,
        widget: str | None = None,
        **kwargs,
    ):
        self.name = name or ""
        self.value = value
        self.error = error
        self.required = required
        self.label = label or (name.replace("_", " ").title() if name else "")
        self.widget = widget or kwargs.get("widget", "input")
        self.attributes = kwargs
        # Keys that should not be rendered as HTML attributes on the input tag
        self._metadata_keys = {
            "widget", "label", "help_text", "choices", "org_id",
            "is_reference", "is_m2m", "searchable", "immutable",
            "encrypted", "on_delete", "back_populates", "target_model"
        }

        # If widget is set but type isn't, use widget as type
        if "type" not in self.attributes and self.widget:
            self.attributes["type"] = self.widget
        if "input_type" in self.attributes:
            self.attributes["type"] = self.attributes.pop("input_type")
        self.css_classes = []

    def _get_render_attrs(self, **kwargs) -> dict[str, Any]:
        """Merge and filter attributes for HTML rendering."""
        attrs = {**self.attributes, **kwargs}
        if "name" not in attrs:
            attrs["name"] = self.name
        if "id" not in attrs:
            attrs["id"] = f"id_{self.name}"

        classes = []
        classes.extend(self.css_classes)

        if self.error:
            classes.append("border-red-500")

        user_class = attrs.pop("class", attrs.pop("css_class", ""))
        if user_class:
            for c in str(user_class).split():
                if c not in classes:
                    classes.append(c)

        if classes:
            attrs["class"] = " ".join(classes)

        if self.required and "required" not in attrs:
            attrs["required"] = "required"

        return {k: v for k, v in attrs.items() if k not in self._metadata_keys}

    def _render_attr_str(self, attrs: dict[str, Any], exclude: list[str] | None = None) -> str:
        """Convert attribute dict to string with XSS-safe escaping."""
        exclude = exclude or []
        parts = []
        for k, v in attrs.items():
            if k in exclude:
                continue
            if v is True:
                parts.append(k)
            elif v is False or v is None:
                continue
            else:
                if k == "choices":
                    continue
                parts.append(f'{k}="{escape(str(v))}"')
        return " ".join(parts)

    @property
    def field_type(self) -> str:
        return self.attributes.get("type", "text")

    @property
    def widget_type(self) -> str:
        return self.widget

    def _clone(self) -> FormField:
        import copy
        new_obj = copy.copy(self)
        new_obj.css_classes = list(self.css_classes)
        new_obj.attributes = dict(self.attributes)
        return new_obj

    def add_class(self, css_class: str) -> FormField:
        new_obj = self._clone()
        if css_class not in new_obj.css_classes:
            new_obj.css_classes.append(css_class)
        return new_obj

    def remove_class(self, css_class: str) -> FormField:
        new_obj = self._clone()
        if css_class in new_obj.css_classes:
            new_obj.css_classes.remove(css_class)
        return new_obj

    def add_error_class(self, css_class: str) -> FormField:
        if self.error:
            return self.add_class(css_class)
        return self

    def attr(self, key: str, value: str) -> FormField:
        new_obj = self._clone()
        new_obj.attributes[key] = str(value)
        return new_obj

    def set_attr(self, key: str, value: str) -> FormField:
        return self.attr(key, value)

    def append_attr(self, key: str, value: str) -> FormField:
        new_obj = self._clone()
        current = new_obj.attributes.get(key, "")
        new_obj.attributes[key] = (current + " " + str(value)).strip()
        return new_obj

    def remove_attr(self, key: str) -> FormField:
        new_obj = self._clone()
        new_obj.attributes.pop(key, None)
        return new_obj

    def add_error_attr(self, key: str, value: str) -> FormField:
        if self.error:
            return self.attr(key, value)
        return self

    def render_label(self) -> str:
        return f'<label for="id_{self.name}">{self.label}</label>'

    def render(self, **kwargs) -> Markup:
        """Render the field using its associated widget."""
        if self.widget in self.WIDGET_RENDERERS:
            return self.WIDGET_RENDERERS[self.widget](self, kwargs)

        if self.widget == "textarea":
            return self.as_textarea(**kwargs)
        if self.widget == "select":
            choices = kwargs.pop("choices", self.attributes.get("choices", []))
            return self.as_select(choices, **kwargs)
        if self.widget == "file":
            return self.as_file(**kwargs)
        if self.widget == "checkbox":
            return self.as_checkbox(**kwargs)
        if self.widget == "radio":
            choices = kwargs.pop("choices", self.attributes.get("choices", []))
            return self.as_radio(choices, **kwargs)
        if self.widget in ("date", "datetime-local", "time", "color", "range"):
            return self.as_input(type=self.widget, **kwargs)

        return self.as_input(**kwargs)

    def as_input(self, **kwargs) -> Markup:
        """Render as a standard HTML input."""
        attrs = self._get_render_attrs(**kwargs)
        attr_str = self._render_attr_str(attrs)

        if self.value is not None and self.value != "":
            val_str = f'value="{escape(str(self.value))}"'
        else:
            val_str = ""

        return Markup(f"<input {attr_str} {val_str} />")

    def as_textarea(self, **kwargs) -> Markup:
        attrs = self._get_render_attrs(**kwargs)
        attr_str = self._render_attr_str(attrs, exclude=["type"])
        content = escape(str(self.value)) if self.value else ""
        return Markup(
            f'<textarea {attr_str}>{content}</textarea>'
        )

    def as_select(self, choices: List[tuple[str, str]], **kwargs) -> Markup:
        attrs = self._get_render_attrs(**kwargs)
        attr_str = self._render_attr_str(attrs, exclude=["max_length", "type"])

        options = []
        for val, label in choices:
            selected = " selected" if str(val) == str(self.value) else ""
            options.append(f'<option value="{val}"{selected}>{label}</option>')

        return Markup(
            f'<select {attr_str}>\n  '
            + "\n  ".join(options)
            + "\n</select>"
        )

    def as_hidden(self, **kwargs) -> Markup:
        return self.as_input(type="hidden", **kwargs)

    def as_checkbox(self, **kwargs) -> Markup:
        attrs = self._get_render_attrs(**kwargs)
        attrs["type"] = "checkbox"
        if self.value:
            attrs["checked"] = "checked"
        attr_str = self._render_attr_str(attrs)
        return Markup(f"<input {attr_str} />")

    def as_radio(self, choices: List[tuple[str, str]], **kwargs) -> Markup:
        attrs = self._get_render_attrs(**kwargs)
        base_id = attrs.pop("id", f"id_{self.name}")

        items = []
        for i, (val, label) in enumerate(choices):
            checked = ' checked="checked"' if str(val) == str(self.value) else ""
            item_id = f"{base_id}_{i}"
            items.append(
                f'<label class="eden-radio-item"><input type="radio" name="{self.name}" id="{item_id}" value="{val}"{checked}> {label}</label>'
            )
        return Markup("\n".join(items))

    def as_file(
        self,
        accept: str = "",
        multiple: bool = False,
        **kwargs: Any,
    ) -> Markup:
        """Render a file upload input."""
        attrs: dict[str, str] = {**self.attributes, **kwargs}
        attrs["type"] = "file"
        attrs["name"] = self.name
        attrs["id"] = attrs.get("id", f"id_{self.name}")
        if accept:
            attrs["accept"] = accept
        if multiple:
            attrs["multiple"] = "multiple"

        classes = list(self.css_classes)
        if self.error:
            classes.append("border-red-500")
        if classes:
            attrs["class"] = " ".join(classes)

        attr_str = " ".join(f'{k}="{escape(str(v))}"' for k, v in attrs.items())
        return Markup(f"<input {attr_str} />")

    def render_composite(self, **kwargs) -> str:
        """Renders label, input, and error message in sequence."""
        html = f'<div class="eden-field-group">\n  {self.render_label()}\n  {self.render(**kwargs)}'
        if self.error:
            html += f'\n  <span class="error">{self.error}</span>'
        html += "\n</div>"
        return Markup(html)

    def __str__(self) -> str:
        return str(self.render())

    def __html__(self) -> str:
        return self.render()


# ── FileField ────────────────────────────────────────────────────────────────


class FileField(FormField):
    """
    Specialized form field for file uploads with progress tracking support.

    Extends FormField to provide:
    - Accept filter specification (MIME types/extensions)
    - Multiple file support
    - Progress bar rendering for real-time upload tracking
    - WebSocket integration template for client-side progress
    """

    def __init__(
        self,
        name: str | None = None,
        value: Any = None,
        error: str | None = None,
        required: bool = False,
        label: str | None = None,
        accept: str = "",
        multiple: bool = False,
        show_progress: bool = False,
        progress_element_id: str | None = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            value=value,
            error=error,
            required=required,
            label=label,
            widget="file",
            **kwargs,
        )
        self.accept = accept
        self.multiple = multiple
        self.show_progress = show_progress
        self.progress_element_id = progress_element_id or f"progress_{uuid4().hex[:12]}"

    def as_file(
        self,
        accept: str = "",
        multiple: bool = False,
        show_progress: bool = False,
        **kwargs: Any,
    ) -> Markup:
        """Render a file upload input with optional progress bar."""
        accept = accept or self.accept
        multiple = multiple or self.multiple
        show_progress = show_progress or self.show_progress

        attrs: dict[str, str] = {**self.attributes, **kwargs}
        attrs["type"] = "file"
        attrs["name"] = self.name
        attrs["id"] = attrs.get("id", f"id_{self.name}")
        if accept:
            attrs["accept"] = accept
        if multiple:
            attrs["multiple"] = "multiple"

        attrs["data-progress-element"] = self.progress_element_id

        classes = list(self.css_classes)
        if self.error:
            classes.append("border-red-500")
        if classes:
            attrs["class"] = " ".join(classes)

        attr_str = " ".join(f'{k}="{escape(str(v))}"' for k, v in attrs.items())
        html = f"<input {attr_str} />"

        if show_progress:
            progress_html = f'''
<div id="{self.progress_element_id}" style="display:none;">
  <progress id="{self.progress_element_id}_bar" value="0" max="100" style="width:100%;"></progress>
  <span id="{self.progress_element_id}_text">0%</span>
</div>
'''
            html += progress_html

        return Markup(html)

    def render(self, **kwargs) -> str:
        """Render file field (delegates to as_file)."""
        return self.as_file(**kwargs)

    def render_with_progress(self, **kwargs) -> Markup:
        """Render file field with progress bar enabled."""
        return self.as_file(show_progress=True, **kwargs)


# ── Form (typed generic, for builder subsystem) ─────────────────────────────


class Form(Generic[T]):
    """Base typed form class, used by the eden/builder/ subsystem."""

    def __init__(self, data: dict[str, Any] | None = None):
        self.data = data or {}
        self.fields: dict[str, BasicFormField] = {}
        self.errors: dict[str, list[str]] = {}
        self._init_fields()

    def _init_fields(self) -> None:
        """Initialize form fields from type hints."""
        hints = get_type_hints(self.__class__)
        for name, type_hint in hints.items():
            if not name.startswith("_"):
                self.fields[name] = BasicFormField(name=name)

    def bind(self, data: dict[str, Any]) -> BoundForm:
        """Bind data to the form."""
        return BoundForm(self, data)

    def is_valid(self) -> bool:
        """Check if form is valid."""
        if not self.data:
            return False

        for name, field in self.fields.items():
            field.value = self.data.get(name)
            result = field.validate()
            if not result.is_valid:
                self.errors[name] = result.errors

        return len(self.errors) == 0

    def get_field(self, name: str) -> BasicFormField | None:
        """Get a form field by name."""
        return self.fields.get(name)


# ── BoundForm / BoundFormField ───────────────────────────────────────────────


class BoundForm:
    """A form bound to data."""

    def __init__(self, form: Form[Any], data: dict[str, Any]):
        self.form = form
        self.data = data
        self.errors: dict[str, list[str]] = {}
        self.bound_fields: dict[str, BoundFormField] = {}
        self._bind_fields()

    def _bind_fields(self) -> None:
        """Bind each field to data."""
        for name, field in self.form.fields.items():
            field.value = self.data.get(name)
            result = field.validate()
            if not result.is_valid:
                self.errors[name] = result.errors

            self.bound_fields[name] = BoundFormField(field, result)

    def is_valid(self) -> bool:
        """Check if bound form is valid."""
        return len(self.errors) == 0

    def get_field(self, name: str) -> "BoundFormField | None":
        """Get a bound field by name."""
        return self.bound_fields.get(name)


@dataclass
class BoundFormField:
    """A form field bound to a form and data."""

    field: BasicFormField
    validation_result: ValidationResult

    @property
    def value(self) -> Any:
        """Get the field value."""
        return self.field.value

    @property
    def errors(self) -> list[str]:
        """Get field errors."""
        return self.validation_result.errors

    @property
    def is_valid(self) -> bool:
        """Check if field is valid."""
        return self.validation_result.is_valid


# ── BaseForm (Pydantic schema wrapper from monolith) ────────────────────────


class BaseForm:
    """
    Base class for Eden forms, wrapping Pydantic schemas.

    Handles:
    - Pydantic-based validation with include/exclude groups
    - Request body parsing (JSON, form-data, multipart)
    - File upload handling with size limits
    - CSRF token rendering
    - FormField generation from schema metadata
    """

    def __init__(
        self, schema: Type[BaseModel], data: Optional[Dict[str, Any]] = None
    ):
        self.schema = schema
        self.data = data or {}
        self.errors = {}
        self.model_instance = None
        self._fields = {}
        self.files: dict[str, Any] = {}

        # Max upload size (100MB by default to prevent DoS)
        self.MAX_UPLOAD_SIZE = 100 * 1024 * 1024

    def is_valid(self, include: list[str] | None = None, exclude: list[str] | None = None) -> bool:
        """
        Validates the form data against the Pydantic schema.

        Args:
            include: Optional list of field names to validate (Validation Groups support).
            exclude: Optional list of field names to skip during validation.
        """
        try:
            data = self.data.copy()

            if hasattr(self, "files") and self.files:
                for key, file in self.files.items():
                    if key not in data:
                        data[key] = file.data

            if include or exclude:
                include_set = set(include) if include else None
                exclude_set = set(exclude) if exclude else set()

                fields = getattr(self.schema, "model_fields", {})
                for field_name, field_def in fields.items():
                    in_scope = (not include_set or field_name in include_set) and (field_name not in exclude_set)

            if hasattr(self.schema, "model_validate"):
                from_attr = not isinstance(data, dict)
                self.model_instance = self.schema.model_validate(data, from_attributes=from_attr)
            else:
                self.model_instance = self.schema(**data)

            self.errors = {}
            return True
        except Exception as e:
            from pydantic import ValidationError
            if not isinstance(e, ValidationError):
                raise e

            self.errors = {}
            include_set = set(include) if include else None
            exclude_set = set(exclude) if exclude else set()

            for err in e.errors():
                loc = err.get("loc", [])
                if not loc:
                    field_key = "__all__"
                    root_field = "__all__"
                else:
                    field_key = ".".join(str(p) for p in loc)
                    root_field = str(loc[0])

                in_scope = (not include_set or root_field in include_set) and (root_field not in exclude_set)

                if in_scope:
                    self.errors[field_key] = err.get("msg", "Validation error")
                    if root_field != field_key:
                        self.errors[root_field] = f"Error in {field_key}: {self.errors[field_key]}"

            if len(self.errors) == 0:
                if hasattr(self.schema, "model_construct"):
                    self.model_instance = self.schema.model_construct(**data)
                    self._partially_validated = True
                    self._validated_fields = set(include) if include else set(data.keys()) - set(exclude or [])
                else:
                    self.model_instance = self.schema.construct(**data)
                    self._partially_validated = True
                    self._validated_fields = set(include) if include else set(data.keys()) - set(exclude or [])
                return True

            return False

    @classmethod
    def from_model(cls, instance: Any) -> "BaseForm":
        """Creates a form instance populated with data from a model record."""
        data = instance.to_dict() if hasattr(instance, "to_dict") else vars(instance)

        schema = None
        to_schema = getattr(instance.__class__, "to_schema", None)
        if to_schema is not None:
            try:
                schema = to_schema()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"to_schema() failed for {instance.__class__.__name__}: {e}. "
                    f"Falling back to Schema/pydantic_model attribute."
                )

        if not schema:
            schema = getattr(instance.__class__, "Schema", None)
        if not schema:
            schema = getattr(instance.__class__, "__pydantic_model__", None)

        if not schema or schema is BaseModel:
            schema = getattr(instance, "__pydantic_model__", None)

        if not schema:
            raise ValueError(
                f"Could not determine Pydantic schema for {instance.__class__.__name__}"
            )

        return cls(schema=schema, data=data)

    def render_csrf(self) -> Markup:
        """Render the CSRF hidden input field for the current request context."""
        request = get_request()
        if not request:
            import warnings
            warnings.warn("render_csrf() called outside of request context. No token will be produced.")
            return Markup("")

        try:
            from eden.middleware import get_csrf_token
            token = get_csrf_token(request)
            return Markup(f'<input type="hidden" name="csrf_token" value="{token}">')
        except (ImportError, AttributeError):
            return Markup("")

    @classmethod
    async def from_multipart(cls, schema: Type[BaseModel], request: Any) -> "BaseForm":
        """Parse a multipart/form-data request and return a bound form."""
        from eden.forms.uploads import UploadedFile

        multipart = await request.form()

        data: dict[str, Any] = {}
        files: dict[str, UploadedFile] = {}

        max_size = getattr(cls, "MAX_UPLOAD_SIZE", 100 * 1024 * 1024)

        for key, value in multipart.items():
            if hasattr(value, "filename") and value.filename:
                size = getattr(value, "size", None)
                if size and size > max_size:
                    raise ValueError(f"File '{value.filename}' exceeds maximum upload size of {max_size} bytes.")

                chunks = []
                total_read = 0
                chunk_size = 64 * 1024

                while True:
                    chunk = await value.read(chunk_size)
                    if not chunk:
                        break
                    total_read += len(chunk)
                    if total_read > max_size:
                        raise ValueError(
                            f"File '{value.filename}' exceeds maximum upload size of {max_size} bytes."
                        )
                    chunks.append(chunk)

                raw = b"".join(chunks)

                content_type = (
                    getattr(value, "content_type", "application/octet-stream")
                    or "application/octet-stream"
                )
                files[key] = UploadedFile(
                    filename=value.filename,
                    content_type=content_type,
                    data=raw,
                    size=len(raw),
                )
            else:
                data[key] = value

        instance = cls(schema=schema, data=data)
        instance.files = files
        return instance

    @classmethod
    async def from_request(cls, schema: Type[BaseModel], request: Any) -> "BaseForm":
        """Create a bound form directly from a request."""
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            return await cls.from_multipart(schema, request)

        data = {}
        try:
            data = await request.json()
        except (ValueError, RuntimeError):
            try:
                data = dict(await request.form())
            except (ValueError, RuntimeError) as form_err:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Failed to parse form data: {form_err}")
                pass

        return cls(schema=schema, data=data)

    def __getitem__(self, name: str) -> FormField:
        """Access a FormField by name and handle overrides."""
        if name not in self._fields:
            class_field = getattr(self.__class__, name, None)

            field_def = None
            if hasattr(self.schema, "model_fields"):
                field_def = self.schema.model_fields.get(name)

            if not field_def and not isinstance(class_field, FormField):
                raise KeyError(name)

            if isinstance(class_field, FormField):
                field = class_field._clone()
                field.name = name
                field.value = self.data.get(name)
                field.error = self.errors.get(name)
                if "required" not in class_field.__dict__ and field_def:
                    field.required = field_def.is_required()
                self._fields[name] = field
            else:
                kwargs = {}
                if (
                    field_def
                    and hasattr(field_def, "json_schema_extra")
                    and field_def.json_schema_extra
                ):
                    kwargs.update(field_def.json_schema_extra)

                if field_def:
                    if hasattr(field_def, "metadata"):
                        for m in field_def.metadata:
                            if hasattr(m, "max_length"):
                                kwargs["max_length"] = m.max_length
                            if hasattr(m, "min_length"):
                                kwargs["min_length"] = m.min_length
                            if hasattr(m, "ge"):
                                kwargs["min"] = m.ge
                            if hasattr(m, "le"):
                                kwargs["max"] = m.le

                is_req = kwargs.pop("required", field_def.is_required() if field_def else False)

                self._fields[name] = FormField(
                    name=name,
                    value=self.data.get(name),
                    error=self.errors.get(name),
                    required=is_req,
                    **kwargs,
                )
        return self._fields[name]

    def render_all(self) -> str:
        """Renders all fields in the form, including CSRF token."""
        html = self.render_csrf()
        html += "\n"
        fields = getattr(self.schema, "model_fields", {})
        for name in fields:
            html += self[name].render_composite()
            html += "\n"
        return html

    def __iter__(self) -> Iterator[FormField]:
        """Allows iterating over form fields in a template."""
        fields = getattr(self.schema, "model_fields", {})
        for name in fields:
            yield self[name]
