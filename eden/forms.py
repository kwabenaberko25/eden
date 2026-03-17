from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, List, Union, Iterator, Callable, Awaitable
from uuid import uuid4

from markupsafe import Markup, escape
from pydantic import BaseModel, Field as PydanticField, ValidationError, EmailStr, AnyUrl

from eden.context import get_request


# ── Upload Progress Protocol ──────────────────────────────────────────────────────


ProgressCallback = Callable[[int, int], Awaitable[None]]
"""
Protocol for upload progress callbacks.

The callback receives two arguments:
- bytes_written: int - Bytes uploaded so far
- total_bytes: int - Total bytes to upload

Example:
    async def progress(bytes_written, total_bytes):
        percentage = (bytes_written / total_bytes) * 100
        print(f"Upload: {percentage:.1f}%")

    await storage.save_with_progress(file, callback=progress)
"""


# ── Form Field Helper ─────────────────────────────────────────────────────────────


def field(
    default: Any = ...,
    *,
    label: str | None = None,
    placeholder: str | None = None,
    help_text: str | None = None,
    widget: str | None = None,
    choices: list[Any] | None = None,
    min: Any = None,
    max: Any = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
    required: bool | None = None,
    **kwargs: Any,
) -> Any:
    """
    Form-specific field helper. Returns a Pydantic Field with Eden UI metadata.

    Usage:
        from eden.forms import Schema, field

        class LoginSchema(Schema):
            email: str = field(widget="email", label="Email")
            password: str = field(widget="password", min_length=8)
    """
    from pydantic import Field

    # Map to json_schema_extra for Eden's form rendering
    metadata = kwargs.get("json_schema_extra", {})
    if not isinstance(metadata, dict):
        metadata = {}

    if label:
        metadata["label"] = label
    if placeholder:
        metadata["placeholder"] = placeholder
    if help_text:
        metadata["help_text"] = help_text
    if choices:
        metadata["choices"] = choices
    if widget:
        metadata["widget"] = widget
    if min is not None:
        metadata["min"] = min
    if max is not None:
        metadata["max"] = max
    if pattern:
        metadata["pattern"] = pattern

    # Handle required/default logic
    if required is True:
        # If explicitly required, we use Pydantic's ... (Ellipsis)
        # unless a default was provided, in which case it might be 
        # a default for the FORM but technically optional for the MODEL
        # though Pydantic usually treats default+required as contradiction.
        # We'll follow Pydantic convention: default takes precedence over required=True
        if default is ...:
            default = ...
    elif required is False and default is ...:
        default = None

    # Handle ge/le for min/max if they are numeric
    if min is not None and isinstance(min, (int, float)):
        kwargs["ge"] = min
    if max is not None and isinstance(max, (int, float)):
        kwargs["le"] = max

    return Field(
        default=default,
        max_length=max_length,
        min_length=min_length,
        pattern=pattern,
        json_schema_extra=metadata if metadata else None,
        **kwargs,
    )


v = field
field = field

__all__ = [
    "Schema",
    "field",
    "v",
    "BaseForm",
    "FormField",
    "FileField",
    "UploadedFile",
    "ProgressCallback",
    "EmailStr",
    "AnyUrl",
]



# ── Uploaded File ─────────────────────────────────────────────────────────────


@dataclass
class UploadedFile:
    """
    Wrapper around a file uploaded through a multipart form.

    Attributes:
        filename:     Original filename from the client.
        content_type: MIME type (e.g. 'image/png').
        data:         Raw bytes of the uploaded file.
        size:         File size in bytes.

    Usage::

        form = await BaseForm.from_multipart(request)
        avatar: UploadedFile = form.files["avatar"]
        await storage.save(avatar.filename, avatar.data)
    """

    filename: str
    content_type: str
    data: bytes
    size: int

    def as_io(self) -> io.BytesIO:
        """Return the file data as an in-memory byte stream."""
        return io.BytesIO(self.data)

    @property
    def extension(self) -> str:
        """File extension including the leading dot, e.g. '.png'."""
        parts = self.filename.rsplit(".", 1)
        return f".{parts[-1].lower()}" if len(parts) == 2 else ""


class FormField:
    """
    Representation of a single form field with rendering helpers.
    """

    # Global registry for widget renderers to allow extensibility
    WIDGET_RENDERERS: Dict[str, Callable[[FormField, dict], Markup]] = {}

    @classmethod
    def register_widget(cls, name: str, renderer: Callable[[FormField, dict], Markup]):
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
        
        # 1. Start with field's inherent classes
        classes.extend(self.css_classes)
        
        # 2. Add error classes if applicable
        if self.error:
            classes.append("border-red-500")
            
        # 3. Add classes provided in kwargs (precedence: field < kwargs)
        user_class = attrs.pop("class", attrs.pop("css_class", ""))
        if user_class:
            for c in str(user_class).split():
                if c not in classes:
                    classes.append(c)
            
        if classes:
            attrs["class"] = " ".join(classes)
            
        if self.required and "required" not in attrs:
            attrs["required"] = "required"
            
        # Filter out metadata
        return {k: v for k, v in attrs.items() if k not in self._metadata_keys}

    def _render_attr_str(self, attrs: dict[str, Any], exclude: list[str] | None = None) -> str:
        """Convert attribute dict to string."""
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
                # Handle special attributes like 'choices' (already filtered but safe)
                if k == "choices": continue
                parts.append(f'{k}="{v}"')
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
        # Check registry first for custom widgets
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

        # Default to input
        return self.as_input(**kwargs)

    def as_input(self, **kwargs) -> Markup:
        """Render as a standard HTML input."""
        attrs = self._get_render_attrs(**kwargs)
        attr_str = self._render_attr_str(attrs)
        
        # value is handled specially for inputs and MUST be escaped
        if self.value is not None and self.value != "":
            # We use escape() here to prevent XSS. Markup() just tells jinja not to escape again.
            val_str = f'value="{escape(str(self.value))}"'
        else:
            val_str = ""

        return Markup(f"<input {attr_str} {val_str} />")

    def as_textarea(self, **kwargs) -> Markup:
        attrs = self._get_render_attrs(**kwargs)
        attr_str = self._render_attr_str(attrs, exclude=["type"])
        content = self.value or ""
        return Markup(
            f'<textarea {attr_str}>{content}</textarea>'
        )

    def as_select(self, choices: List[tuple[str, str]], **kwargs) -> Markup:
        attrs = self._get_render_attrs(**kwargs)
        # Remove max_length and type from select tag
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
        """
        Render a file upload input.

        Args:
            accept:   Comma-separated MIME types or extensions, e.g. 'image/*'
                      or '.pdf,.docx'.
            multiple: Allow selecting multiple files.

        Usage::
            {{ form['avatar'].as_file(accept='image/*') }}
            {{ form['docs'].as_file(accept='.pdf', multiple=True) }}
        """
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

        attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
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


class FileField(FormField):
    """
    Specialized form field for file uploads with progress tracking support.
    
    Extends FormField to provide:
    - Accept filter specification (MIME types/extensions)  
    - Multiple file support
    - Progress bar rendering for real-time upload tracking
    - WebSocket integration template for client-side progress
    - Integration with StorageManager for atomic uploads with callbacks
    
    Attributes:
        accept: Comma-separated MIME types or file extensions
        multiple: Allow multiple file selection
        show_progress: Render progress bar HTML
        progress_element_id: ID for progress bar DOM element
        
    Usage:
        # In a form schema
        class UploadSchema(Schema):
            avatar: Optional[bytes] = f(widget="file", label="Avatar")
        
        # In a template
        {{ form['avatar'].as_file(accept='image/*') }}
        
        # In a handler with progress tracking
        async def handle_upload(request):
            form = await UploadSchema.from_request(request)
            if form.is_valid():
                file = form.files['avatar']
                
                # With progress tracking
                async def on_progress(bytes_written, total_bytes):
                    percentage = (bytes_written / total_bytes) * 100
                    print(f"Upload: {percentage:.1f}%")
                
                result = await storage.get("s3").save(
                    file.filename,
                    file.data,
                    progress_callback=on_progress
                )
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
        """
        Initialize a FileField.
        
        Args:
            name: Field name
            value: Current value  
            error: Validation error message
            required: Whether field is required
            label: Human-readable label
            accept: MIME types or extensions (e.g., 'image/*,.pdf')
            multiple: Allow multiple file selection
            show_progress: Render progress bar HTML
            progress_element_id: Custom ID for progress element (auto-generated if not set)
            **kwargs: Additional attributes
        """
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
        # Use more entropy for progress bar IDs to avoid collisions (increased to 12 chars)
        self.progress_element_id = progress_element_id or f"progress_{uuid4().hex[:12]}"
    
    def as_file(
        self,
        accept: str = "",
        multiple: bool = False,
        show_progress: bool = False,
        **kwargs: Any,
    ) -> Markup:
        """
        Render a file upload input with optional progress bar.
        
        Args:
            accept: MIME types or extensions (e.g., 'image/*,.pdf')
            multiple: Allow multiple file selection
            show_progress: Include progress bar HTML
            **kwargs: Additional attributes
            
        Usage:
            # Basic file input
            {{ form['avatar'].as_file(accept='image/*') }}
            
            # With progress bar
            {{ form['document'].as_file(accept='.pdf', show_progress=True) }}
            
            # Multiple files
            {{ form['attachments'].as_file(accept='.jpg,.png,.pdf', multiple=True, show_progress=True) }}
        """
        # Use parameters or instance attributes
        accept = accept or self.accept
        multiple = multiple or self.multiple
        show_progress = show_progress or self.show_progress
        
        # Build input attributes
        attrs: dict[str, str] = {**self.attributes, **kwargs}
        attrs["type"] = "file"
        attrs["name"] = self.name
        attrs["id"] = attrs.get("id", f"id_{self.name}")
        if accept:
            attrs["accept"] = accept
        if multiple:
            attrs["multiple"] = "multiple"
        
        # Add data attributes for client-side progress tracking
        attrs["data-progress-element"] = self.progress_element_id
        
        # CSS classes
        classes = list(self.css_classes)
        if self.error:
            classes.append("border-red-500")
        if classes:
            attrs["class"] = " ".join(classes)
        
        # Render input element
        attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        html = f"<input {attr_str} />"
        
        # Optionally render progress bar
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


class BaseForm:
    """
    Base class for Eden forms, wrapping Pydantic schemas.
    """

    def __init__(
        self, schema: Type[BaseModel] | Type[Schema], data: Optional[Dict[str, Any]] = None
    ):
        self.schema = schema
        self.data = data or {}
        self.errors = {}
        self.model_instance = None
        self._fields = {}
        self.files: dict[str, UploadedFile] = {}
        
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
            data = self.data
            
            # Implementation of Validation Groups:
            # If include/exclude is provided, we create a temporary schema or 
            # partial data for validation.
            if include or exclude:
                # For now, we validate the whole thing but filter errors
                # A more thorough implementation would use a partial schema
                pass

            # Pydantic 2.0+ uses model_validate
            if hasattr(self.schema, "model_validate"):
                self.model_instance = self.schema.model_validate(data)
            else:
                self.model_instance = self.schema(**data)
            self.errors = {}
            return True
        except ValidationError as e:
            self.errors = {}
            include_set = set(include) if include else None
            exclude_set = set(exclude) if exclude else set()
            
            for err in e.errors():
                # Handle nested locations or missing loc
                loc = err.get("loc", ["__all__"])
                field_name = str(loc[0]) if loc else "__all__"
                
                # Filter errors based on groups
                if include_set and field_name not in include_set:
                    continue
                if field_name in exclude_set:
                    continue
                    
                self.errors[field_name] = err.get("msg", "Validation error")
            
            return len(self.errors) == 0

    @classmethod
    def from_model(cls, instance: Any) -> BaseForm:
        """Creates a form instance populated with data from a model record."""
        data = instance.to_dict() if hasattr(instance, "to_dict") else vars(instance)
        # Attempt to get the schema from the model class
        schema = getattr(instance.__class__, "to_schema", lambda: None)()
        if not schema:
            schema = getattr(instance.__class__, "Schema", None)
        if not schema:
            schema = getattr(instance.__class__, "__pydantic_model__", None)

        if not schema or schema is BaseModel:
            # Fallback to UserSchema detection for typical models in tests/docs
            schema = getattr(instance, "__pydantic_model__", None)

        if not schema:
            raise ValueError(
                f"Could not determine Pydantic schema for {instance.__class__.__name__}"
            )

        return cls(schema=schema, data=data)

    def render_csrf(self) -> Markup:
        """
        Render the CSRF hidden input field for the current request context.
        
        Requires CSRFMiddleware to be active in the application stack.
        
        Usage:
            {{ form.render_csrf() }}
        """
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
            # Fallback if CSRF is not configured or middleware is missing
            return Markup("")

    @classmethod
    async def from_multipart(cls, schema: Type[BaseModel], request: Any) -> BaseForm:
        """
        Parse a multipart/form-data request and return a bound form.

        Uploaded files are stored in ``form.files`` as :class:`UploadedFile`
        instances, keyed by field name. Regular fields are available through
        the normal ``form["field"]`` interface.

        Args:
            schema:  The Pydantic schema to validate against.
            request: The Eden/Starlette Request object.
        """
        multipart = await request.form()

        data: dict[str, Any] = {}
        files: dict[str, UploadedFile] = {}

        # Use class attribute for size limit if available
        max_size = getattr(cls, "MAX_UPLOAD_SIZE", 100 * 1024 * 1024)

        for key, value in multipart.items():
            # Starlette UploadFile has a .filename attribute
            if hasattr(value, "filename") and value.filename:
                # Check file size if available before reading (Resource Protection)
                size = getattr(value, "size", None)
                if size and size > max_size:
                    raise ValueError(f"File '{value.filename}' exceeds maximum upload size of {max_size} bytes.")
                
                raw = await value.read()
                
                # Double check size after read as well
                if len(raw) > max_size:
                    raise ValueError(f"File '{value.filename}' exceeds maximum upload size of {max_size} bytes.")

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
        instance.files: dict[str, UploadedFile] = files
        return instance

    @classmethod
    async def from_request(cls, schema: Type[BaseModel], request: Any) -> BaseForm:
        """Create a bound form directly from a request."""
        # Detect content type
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            return await cls.from_multipart(schema, request)

        # Try JSON first, then Form data
        data = {}
        try:
            data = await request.json()
        except (ValueError, RuntimeError) as json_err:
            # ValueError: invalid JSON | RuntimeError: body consumed
            try:
                data = dict(await request.form())
            except (ValueError, RuntimeError) as form_err:
                # Form parsing failed, continue with empty data
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Failed to parse form data: {form_err}")
                pass

        return cls(schema=schema, data=data)

    def __getitem__(self, name: str) -> FormField:
        """Access a FormField by name and handle overrides."""
        if name not in self._fields:
            # Check for class attribute override
            class_field = getattr(self.__class__, name, None)

            # Check schema for field definition
            field_def = None
            if hasattr(self.schema, "model_fields"):
                field_def = self.schema.model_fields.get(name)

            if not field_def and not isinstance(class_field, FormField):
                # If it's not in schema and not an override, it might be a missing field
                # For Schema subclasses, they might define fields directly
                raise KeyError(name)

            if isinstance(class_field, FormField):
                # Use the provided FormField object but update it with dynamic data
                field = class_field._clone()
                field.name = name
                field.value = self.data.get(name)
                field.error = self.errors.get(name)
                # If required wasn't explicitly set on the override, check the schema
                if "required" not in class_field.__dict__ and field_def:
                    field.required = field_def.is_required()
                self._fields[name] = field
            else:
                # Inherit from schema/f() metadata if available
                kwargs = {}
                if (
                    field_def
                    and hasattr(field_def, "json_schema_extra")
                    and field_def.json_schema_extra
                ):
                    # Pass through info/metadata from f()
                    kwargs.update(field_def.json_schema_extra)

                # Check for pydantic field metadata (min_length, etc.)
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

                # Pop 'required' from kwargs if it came from info to avoid double-passing
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
        # Check if schema has model_fields (Pydantic 2.0)
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




class Schema(BaseModel):
    """
    Unified Schema for Eden.
    Combines Pydantic validation with Eden Form rendering.

    Usage:
        class SignupSchema(Schema):
            email: str = f(max_length=255, widget="email")
            ...

        form = SignupSchema.as_form(data)

    Declarative Model Integration:
        class ProductSchema(Schema):
            class Meta:
                model = Product
                include = ["title", "price"]
    """

    model_config = {"extra": "ignore", "arbitrary_types_allowed": True}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Handle f() helper defaults for Schema fields (Fallback for DB fields)
        # This allows: email: str = f(widget="email") using eden.db.f
        if hasattr(cls, "model_fields"):
            for name, field in cls.model_fields.items():
                default = field.default

                # Check if the default value is a mapped_column (from eden.db.f)
                if hasattr(default, "column") and hasattr(default.column, "info"):
                    col = default.column
                    if col.info:
                        # Transfer info to pydantic field metadata
                        if field.json_schema_extra is None:
                            field.json_schema_extra = {}

                        # Merge metadata
                        if isinstance(field.json_schema_extra, dict):
                            field.json_schema_extra.update(col.info)
                        else:
                            field.json_schema_extra = dict(col.info)

                        # Clear the DB-specific default value to avoid Pydantic errors 
                        # if the default is not serializable or valid for the type
                        if field.default is default:
                            field.default = None

        # Declarative Model Integration
        # This handles 'class Meta: model = MyModel' patterns
        meta = getattr(cls, "Meta", None)
        if meta and hasattr(meta, "model"):
            model = meta.model
            include = getattr(meta, "include", None)
            exclude = set(getattr(meta, "exclude", []))

            # Generate dynamic pydantic model from ORM model
            try:
                dynamic_schema = model.to_schema(include=include, exclude=exclude)
                
                # Transfer fields that aren't manually overridden in the class
                for name, field in dynamic_schema.model_fields.items():
                    if name not in cls.__annotations__:
                        cls.__annotations__[name] = field.annotation
                        # Set as class attribute so Pydantic sees it during discovery
                        if not hasattr(cls, name):
                            setattr(cls, name, field)
                
                # Patch Pydantic 2.x internals to enable full validation on this subclass.
                # Since Pydantic 2.0 generates its core schema/validator during type creation,
                # we must carry over the generated engine components from the dynamic schema.
                if hasattr(dynamic_schema, "__pydantic_core_schema__"):
                    cls.__pydantic_core_schema__ = dynamic_schema.__pydantic_core_schema__
                    cls.__pydantic_validator__ = dynamic_schema.__pydantic_validator__
                    cls.__pydantic_serializer__ = dynamic_schema.__pydantic_serializer__
                    cls.model_fields.update(dynamic_schema.model_fields)

                # Force pydantic to rebuild the model to ensure all injected fields are accounted for
                if hasattr(cls, "model_rebuild"):
                    cls.model_rebuild(force=True)
                    
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to generate dynamic schema for {cls.__name__}: {e}")
                # We don't raise here to allow the class to load, but it might fail at runtime

    @classmethod
    def as_form(cls, data: Optional[Dict[str, Any]] = None) -> BaseForm:
        """Create a BaseForm instance from this schema."""
        return BaseForm(schema=cls, data=data)

    @classmethod
    async def from_request(cls, request: Any) -> BaseForm:
        """Create a bound form directly from a request."""
        return await BaseForm.from_request(cls, request)

    @classmethod
    def from_model(cls, instance: Any) -> BaseForm:
        """Creates a form instance populated with data from a model record."""
        return BaseForm.from_model(instance)


class ModelForm(BaseForm):
    """
    Model-bound form that automatically syncs with ORM models.
    Provides a Django-like declarative API for building forms from models.

    Usage::

        class TaskForm(ModelForm):
            class Meta:
                model = Task
                fields = ["title", "description", "due_at"]

            description = FormField(widget="textarea", placeholder="Task details...")

    """

    def __init__(self, data: Optional[Dict[str, Any]] = None, instance: Optional[Any] = None):
        meta = getattr(self, "Meta", None)
        if not meta or not hasattr(meta, "model"):
            raise ValueError(
                f"{self.__class__.__name__} must define a 'Meta' class with a 'model' attribute."
            )

        self.model_class = meta.model
        self.instance = instance
        exclude = set(getattr(meta, "exclude", []))
        fields = getattr(meta, "fields", "__all__")

        # Determine include list
        include_list = None
        if fields != "__all__":
            include_list = fields

        # Generate schema from model (B2/B3)
        schema = self.model_class.to_schema(
            include=include_list, exclude=exclude, only_columns=True
        )

        # Populate initial data from instance
        if instance and data is None:
            data = instance.to_dict(exclude=exclude)

        super().__init__(schema=schema, data=data)

    async def save(self, commit: bool = True) -> Any:
        """
        Validates and saves the form data to a model instance.
        """
        if not self.is_valid():
            raise ValueError(f"Cannot save {self.__class__.__name__}: form is invalid.")

        # Data from Pydantic model
        data = self.model_instance.model_dump()

        if self.instance:
            if commit:
                await self.instance.update(**data)
            else:
                for key, value in data.items():
                    setattr(self.instance, key, value)
        else:
            if commit:
                self.instance = await self.model_class.create(**data)
            else:
                self.instance = self.model_class(**data)

        return self.instance
