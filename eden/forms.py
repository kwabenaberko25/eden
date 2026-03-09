from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, List, Union, Iterator

from markupsafe import Markup
from pydantic import BaseModel, ValidationError


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
    def __init__(self, name: str, value: Any = None, error: str = None, required: bool = False, label: str = None, widget: str = None, **kwargs):
        self.name = name
        self.value = value
        self.error = error
        self.required = required
        self.label = label or name.replace("_", " ").title()
        self.widget = widget or kwargs.pop("widget", "input")
        self.attributes = kwargs
        if "input_type" in self.attributes:
            self.attributes["type"] = self.attributes.pop("input_type")
        self.css_classes = []

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

    def render(self, **kwargs) -> str:
        # Combine overrides with default attributes
        # Putting kwargs first allows as_hidden to put type="hidden" at the start
        attrs = {**kwargs}
        if "name" not in attrs:
            attrs["name"] = self.name
        if "id" not in attrs:
            attrs["id"] = f"id_{self.name}"
            
        attrs.update(self.attributes)
        
        classes = list(self.css_classes)
        if self.error:
            classes.append("border-red-500")
        
        if classes:
            attrs["class"] = " ".join(classes)
        
        attr_str = " ".join([f'{k}="{v}"' for k, v in attrs.items()])
        val_str = f'value="{self.value}"' if self.value is not None else ""
        
        return Markup(f'<input {attr_str} {val_str} />')

    def as_textarea(self, **kwargs) -> Markup:
        attrs = {**self.attributes, **kwargs}
        classes = list(self.css_classes)
        if self.error:
            classes.append("border-red-500")
        if classes:
            attrs["class"] = " ".join(classes)
        attr_str = " ".join([f'{k}="{v}"' for k, v in attrs.items()])
        content = self.value or ""
        return Markup(f'<textarea name="{self.name}" id="id_{self.name}" {attr_str}>{content}</textarea>')

    def as_select(self, choices: List[tuple[str, str]], **kwargs) -> Markup:
        attrs = {**self.attributes, **kwargs}
        classes = list(self.css_classes)
        if self.error:
            classes.append("border-red-500")
        if classes:
            attrs["class"] = " ".join(classes)
        attr_str = " ".join([f'{k}="{v}"' for k, v in attrs.items()])
        
        options = []
        for val, label in choices:
            selected = " selected" if str(val) == str(self.value) else ""
            options.append(f'<option value="{val}"{selected}>{label}</option>')
        
        return Markup(f'<select name="{self.name}" id="id_{self.name}" {attr_str}>\n  ' + "\n  ".join(options) + '\n</select>')

    def as_hidden(self, **kwargs) -> Markup:
        return self.render(type="hidden", **kwargs)

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

class BaseForm:
    """
    Base class for Eden forms, wrapping Pydantic schemas.
    """
    def __init__(self, schema: Type[BaseModel], data: Optional[Dict[str, Any]] = None):
        self.schema = schema
        self.data = data or {}
        self.errors = {}
        self.model_instance = None
        self._fields = {}

    def is_valid(self) -> bool:
        """Validates the form data against the Pydantic schema."""
        try:
            self.model_instance = self.schema(**self.data)
            self.errors = {}
            return True
        except ValidationError as e:
            for err in e.errors():
                field_name = str(err["loc"][0])
                self.errors[field_name] = err["msg"]
            return False

    def __getitem__(self, name: str) -> FormField:
        """Access a FormField by name."""
        if name not in self._fields:
            field_def = self.schema.model_fields.get(name)
            if not field_def:
                raise KeyError(name)
            self._fields[name] = FormField(
                name=name,
                value=self.data.get(name),
                error=self.errors.get(name),
                required=field_def.is_required()
            )
        return self._fields[name]

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
            raise ValueError(f"Could not determine Pydantic schema for {instance.__class__.__name__}")

        return cls(schema=schema, data=data)

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

        Usage::

            @app.post("/profile")
            async def update_profile(request):
                form = await BaseForm.from_multipart(ProfileSchema, request)
                if form.is_valid():
                    avatar: UploadedFile = form.files.get("avatar")
                    if avatar:
                        await storage.save(avatar.filename, avatar.data)
                    await Profile.update(...)
        """
        multipart = await request.form()

        data: dict[str, Any] = {}
        files: dict[str, UploadedFile] = {}

        for key, value in multipart.items():
            # Starlette UploadFile has a .filename attribute
            if hasattr(value, "filename") and value.filename:
                raw = await value.read()
                content_type = getattr(value, "content_type", "application/octet-stream") or "application/octet-stream"
                files[key] = UploadedFile(
                    filename=value.filename,
                    content_type=content_type,
                    data=raw,
                    size=len(raw),
                )
            else:
                data[key] = value

        instance = cls(schema=schema, data=data)
        instance.files: dict[str, UploadedFile] = files  # type: ignore[attr-defined]
        return instance

    def render_all(self) -> str:
        """Renders all fields in the form."""
        html = ""
        for name in self.schema.model_fields:
            html += self[name].render_composite()
            html += "\n"
        return html

    def __iter__(self) -> Iterator[FormField]:
        """Allows iterating over form fields in a template."""
        for name in self.schema.model_fields:
            yield self[name]
