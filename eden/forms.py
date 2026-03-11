from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, List, Union, Iterator

from markupsafe import Markup
from pydantic import BaseModel, Field as PydanticField, ValidationError, EmailStr, AnyUrl


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
    "UploadedFile",
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

    def __init__(
        self,
        name: Optional[str] = None,
        value: Any = None,
        error: str = None,
        required: bool = False,
        label: str = None,
        widget: str = None,
        **kwargs,
    ):
        self.name = name or ""
        self.value = value
        self.error = error
        self.required = required
        self.label = label or (name.replace("_", " ").title() if name else "")
        self.widget = widget or kwargs.get("widget", "input")
        self.attributes = kwargs
        # If widget is set but type isn't, use widget as type
        if "type" not in self.attributes and self.widget:
            self.attributes["type"] = self.widget
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
        """Render the field using its associated widget."""
        if self.widget == "textarea":
            return self.as_textarea(**kwargs)
        if self.widget == "select":
            choices = kwargs.pop("choices", self.attributes.get("choices", []))
            return self.as_select(choices, **kwargs)
        if self.widget == "file":
            return self.as_file(**kwargs)

        # Default to input
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

        attr_str = " ".join([f'{k}="{v}"' for k, v in attrs.items() if k != "choices"])
        val_str = f'value="{self.value}"' if self.value is not None else ""

        return Markup(f"<input {attr_str} {val_str} />")

    def as_textarea(self, **kwargs) -> Markup:
        attrs = {**self.attributes, **kwargs}
        classes = list(self.css_classes)
        if self.error:
            classes.append("border-red-500")
        if classes:
            attrs["class"] = " ".join(classes)
        attr_str = " ".join([f'{k}="{v}"' for k, v in attrs.items()])
        content = self.value or ""
        return Markup(
            f'<textarea name="{self.name}" id="id_{self.name}" {attr_str}>{content}</textarea>'
        )

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

        return Markup(
            f'<select name="{self.name}" id="id_{self.name}" {attr_str}>\n  '
            + "\n  ".join(options)
            + "\n</select>"
        )

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

    def __init__(
        self, schema: Type[BaseModel] | Type[Schema], data: Optional[Dict[str, Any]] = None
    ):
        self.schema = schema
        self.data = data or {}
        self.errors = {}
        self.model_instance = None
        self._fields = {}
        self.files: dict[str, UploadedFile] = {}

    def is_valid(self) -> bool:
        """Validates the form data against the Pydantic schema."""
        try:
            # Pydantic 2.0+ uses model_validate
            if hasattr(self.schema, "model_validate"):
                self.model_instance = self.schema.model_validate(self.data)
            else:
                self.model_instance = self.schema(**self.data)
            self.errors = {}
            return True
        except ValidationError as e:
            for err in e.errors():
                # Handle nested locations or missing loc
                loc = err.get("loc", ["__all__"])
                field_name = str(loc[0]) if loc else "__all__"
                self.errors[field_name] = err.get("msg", "Validation error")
            return False

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

        for key, value in multipart.items():
            # Starlette UploadFile has a .filename attribute
            if hasattr(value, "filename") and value.filename:
                raw = await value.read()
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
        except Exception:
            try:
                data = dict(await request.form())
            except Exception:
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

                self._fields[name] = FormField(
                    name=name,
                    value=self.data.get(name),
                    error=self.errors.get(name),
                    required=field_def.is_required() if field_def else False,
                    **kwargs,
                )
        return self._fields[name]

    def render_all(self) -> str:
        """Renders all fields in the form."""
        html = ""
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

                        # Clear the DB-specific default value
                        field.default = None

        # Declarative Model Integration
        meta = getattr(cls, "Meta", None)
        if meta and hasattr(meta, "model"):
            model = meta.model
            include = getattr(meta, "include", None)
            exclude = set(getattr(meta, "exclude", []))

            # Use model metadata to populate fields
            # We bypass Pydantic's normal class creation and inject fields
            dynamic_schema = model.to_schema(include=include, exclude=exclude)

            # Pull fields from generated schema and inject them into this class
            for name, field in dynamic_schema.model_fields.items():
                if name not in cls.__annotations__:
                    cls.__annotations__[name] = field.annotation
                    setattr(cls, name, field)

            # Rebuild model if needed - pydantic usually handles this automatically
            # if we modify annotations before Pydantic finishes its logic.
            # However, since __init_subclass__ runs after, we might need to
            # trigger model rebuild.
            if hasattr(cls, "model_rebuild"):
                cls.model_rebuild(force=True)

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
