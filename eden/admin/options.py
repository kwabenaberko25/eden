from typing import Any



class ModelAdmin:
    """
    Configuration for how a model appears in the admin panel.

    Override fields to customize the admin interface for each model.

    Usage:
        from eden.admin import admin, ModelAdmin

        class UserAdmin(ModelAdmin):
            list_display = ["email", "full_name", "is_active", "created_at"]
            search_fields = ["email", "full_name"]
            list_filter = ["is_active", "is_staff"]
            readonly_fields = ["id", "created_at"]

        admin.register(User, UserAdmin)
    """

    # Columns shown in list view (default: all non-relationship columns)
    list_display: list[str] = []

    # Fields that can be filtered in list view
    list_filter: list[str] = []

    # Fields searchable via the search box
    search_fields: list[str] = []

    # Fields that cannot be edited
    readonly_fields: list[str] = []

    # Default ordering
    ordering: list[str] = ["-created_at"]

    # Records per page
    per_page: int = 25

    # Fields to exclude from forms
    exclude_fields: list[str] = ["id", "created_at", "updated_at"]

    # Custom actions (list of function names or callables)
    actions: list[str] = ["delete_selected"]

    # Icon for sidebar (fontawesome 6.x class)
    icon: str = "fa-solid fa-box"

    # Human-readable names
    verbose_name: str | None = None
    verbose_name_plural: str | None = None

    # URL segment for this model in admin (default: model.__tablename__)
    slug: str | None = None

    # Organize fields into groups: [("Section Title", {"fields": ["f1", "f2"], "description": "..."}), ...]
    fieldsets: list[tuple[str, dict[str, Any]]] = []

    # Related models to show inline
    inlines: list[type["InlineModelAdmin"]] = []

    def get_list_display(self, model) -> list[str]:
        """Get columns to display in list view."""
        if self.list_display:
            return self.list_display

        # Auto-detect from model columns
        from sqlalchemy import inspect as sa_inspect
        try:
            mapper = sa_inspect(model)
            return [col.key for col in mapper.columns if col.key != "id"][:6]
        except Exception:
            return ["id"]

    def get_form_fields(self, model) -> list[str]:
        """Get fields to show in create/edit forms."""
        from sqlalchemy import inspect as sa_inspect
        try:
            mapper = sa_inspect(model)
            all_fields = [col.key for col in mapper.columns]
            return [f for f in all_fields if f not in self.exclude_fields]
        except Exception:
            return []

    def get_verbose_name(self, model) -> str:
        """Get human-readable model name."""
        if self.verbose_name:
            return str(self.verbose_name)
        
        # Use class name if it doesn't look like a generic Model
        name = model.__name__
        if name.endswith("Model") and name != "Model":
            name = name[:-5]
            
        # Add spaces between CamelCase
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', ' ', name)
        return name

    def get_verbose_name_plural(self, model) -> str:
        """Return the plural name for the model."""
        if self.verbose_name_plural:
            return str(self.verbose_name_plural)
        
        name = self.get_verbose_name(model)
        
        # Basic pluralization rules
        if name.endswith(("s", "x", "z", "ch", "sh")):
            return f"{name}es"
        if name.endswith("y") and not name.endswith(("ay", "ey", "iy", "oy", "uy")):
            return f"{name[:-1]}ies"
        
        return f"{name}s"

    def get_slug(self, model) -> str:
        """Return the URL slug for the model."""
        if self.slug:
            return self.slug
        return str(getattr(model, "__tablename__", model.__name__.lower()))

    def get_list_header_stats(self, model) -> list[dict]:
        """Override to return a list of stat cards for the list view header."""
        return []

    async def save_model(self, request, obj, form_data, change) -> None:
        """Handle saving of the model instance."""
        await obj.save()

    async def delete_model(self, request, obj) -> None:
        """Handle deletion of the model instance."""
        await obj.delete()

    async def get_queryset(self, request) -> Any:
        """Return the base queryset for this admin."""
        # By default returns all, but can be filtered for multi-tenancy
        from eden.db import _MISSING
        session = getattr(request.state, "db", _MISSING)
        # Assuming the model class is available via self or passed in
        # We'll need the model class. In views we usually have it.
        pass # To be handled in views if needed or pass model as arg
    
    def has_add_permission(self, request) -> bool:
        return True

    def has_change_permission(self, request, obj=None) -> bool:
        return True

    def has_delete_permission(self, request, obj=None) -> bool:
        return True


class InlineModelAdmin:
    """Base class for inline editors for related models."""
    model: type | None = None
    extra: int = 3
    exclude_fields: list[str] = ["id", "created_at", "updated_at"]
    
    def __init__(self):
        if self.model is None:
            raise ValueError("InlineModelAdmin must define a 'model'")

    def get_form_fields(self) -> list[str]:
        from sqlalchemy import inspect as sa_inspect
        try:
            mapper = sa_inspect(self.model)
            all_fields = [col.key for col in mapper.columns]
            return [f for f in all_fields if f not in self.exclude_fields]
        except Exception:
            return []


class TabularInline(InlineModelAdmin):
    """Table-style inline editor."""
    template = "tabular_inline"


class StackedInline(InlineModelAdmin):
    """Stacked (block) style inline editor."""
    template = "stacked_inline"
