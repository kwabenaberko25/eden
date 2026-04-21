from __future__ import annotations

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

from typing import Any, Dict, Optional, Type

from pydantic import BaseModel


class ModelForm:
    """
    Model-bound form that automatically syncs with ORM models.
    Provides a Django-like declarative API for building forms from models.
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None, instance: Optional[Any] = None):
        from eden.forms.base import BaseForm

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

        # Generate schema from model
        schema = self.model_class.to_schema(
            include=include_list, exclude=exclude, only_columns=True
        )

        # Populate initial data from instance
        if instance and data is None:
            data = instance.to_dict(exclude=exclude)

        # Delegate to BaseForm for all form behavior
        self._base_form = BaseForm(schema=schema, data=data)

        # Expose BaseForm interface
        self.schema = self._base_form.schema
        self.data = self._base_form.data
        self.errors = self._base_form.errors
        self.model_instance = self._base_form.model_instance
        self.files = self._base_form.files

    def is_valid(self, **kwargs) -> bool:
        """Validate the form data."""
        result = self._base_form.is_valid(**kwargs)
        self.errors = self._base_form.errors
        self.model_instance = self._base_form.model_instance
        return result

    def __getitem__(self, name: str):
        """Access a FormField by name."""
        return self._base_form[name]

    def __iter__(self):
        """Iterate over form fields."""
        return iter(self._base_form)

    def render_csrf(self):
        """Render CSRF token."""
        return self._base_form.render_csrf()

    def render_all(self) -> str:
        """Render all fields."""
        return self._base_form.render_all()

    async def save(self, commit: bool = True, partial: bool = False) -> Any:
        """
        Validates and saves the form data to a model instance.

        Args:
            commit: If True, persist to database. If False, only update instance.
            partial: If True, allow saving partially-validated data (from validation groups).
        """
        if not self._base_form.model_instance:
            if not self.is_valid():
                raise ValueError(f"Cannot save {self.__class__.__name__}: form is invalid.")

        # Guard: prevent saving partially-validated data without explicit opt-in
        if getattr(self._base_form, '_partially_validated', False) and not partial:
            raise ValueError(
                f"Cannot save {self.__class__.__name__}: form was validated with "
                f"include/exclude groups. Only fields {self._base_form._validated_fields} were "
                f"validated. Call save(partial=True) to explicitly save partial data, "
                f"or validate all fields first."
            )

        # Data from Pydantic model
        data = self._base_form.model_instance.model_dump()

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
