"""
Eden — Admin Panel Options

Configuration classes for how models appear in the admin interface.
"""



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

    # Custom display name (defaults to model __tablename__)
    verbose_name: str | None = None
    verbose_name_plural: str | None = None

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
            return self.verbose_name
        
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
            return self.verbose_name_plural
        
        name = self.get_verbose_name(model)
        
        # Basic pluralization rules
        if name.endswith(("s", "x", "z", "ch", "sh")):
            return f"{name}es"
        if name.endswith("y") and not name.endswith(("ay", "ey", "iy", "oy", "uy")):
            return f"{name[:-1]}ies"
        
        return f"{name}s"

    def get_list_header_stats(self, model) -> list[dict]:
        """Override to return a list of stat cards for the list view header."""
        return []
