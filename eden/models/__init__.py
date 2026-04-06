"""
Eden Model Config - Enhanced model configuration options.

Provides comprehensive model configuration similar to Django's Meta class,
with additional Eden-specific options for API, admin, and database behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union
from pathlib import Path

from ..db import Model

@dataclass
class ModelConfig:
    """
    Comprehensive model configuration.

    Extends Django's Meta concept with Eden-specific options for
    API generation, admin interfaces, database behavior, and more.
    """

    # Core Django-like options
    app_label: str = ""
    db_table: str = ""
    db_tablespace: str = ""
    get_latest_by: str = ""
    order_with_respect_to: str = ""
    ordering: List[str] = field(default_factory=list)
    permissions: List[tuple] = field(default_factory=list)
    default_permissions: List[str] = field(default_factory=lambda: ["add", "change", "delete", "view"])
    unique_together: List[List[str]] = field(default_factory=list)
    index_together: List[List[str]] = field(default_factory=list)
    constraints: List[Any] = field(default_factory=list)

    # Eden-specific database options
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    db_schema: str = ""  # PostgreSQL schema
    tenant_isolated: bool = True  # Auto-filter by tenant
    audit_changes: bool = False  # Track all changes
    cache_timeout: int = 0  # Cache timeout in seconds

    # API options
    api_resource: bool = True  # Auto-generate REST endpoints
    api_readonly_fields: List[str] = field(default_factory=list)
    api_exclude_fields: List[str] = field(default_factory=list)
    api_nested_fields: List[str] = field(default_factory=list)
    api_required_fields: List[str] = field(default_factory=list)
    api_extra_actions: List[Dict[str, Any]] = field(default_factory=list)

    # Admin panel options
    admin_list_display: List[str] = field(default_factory=list)
    admin_list_filter: List[str] = field(default_factory=list)
    admin_search_fields: List[str] = field(default_factory=list)
    admin_ordering: List[str] = field(default_factory=list)
    admin_readonly_fields: List[str] = field(default_factory=list)
    admin_exclude_fields: List[str] = field(default_factory=list)
    admin_list_per_page: int = 25
    admin_show_full_result_count: bool = True
    admin_date_hierarchy: str = ""
    admin_list_editable: List[str] = field(default_factory=list)
    admin_list_display_links: Optional[List[str]] = None
    admin_save_as: bool = False
    admin_save_on_top: bool = False
    admin_preserve_filters: bool = True
    admin_inlines: List[Any] = field(default_factory=list)

    # Validation options
    validators: List[callable] = field(default_factory=list)

    # File handling options
    upload_to: str = ""
    file_size_limit: int = 0

    # Internationalization
    verbose_name: str = ""
    verbose_name_plural: str = ""

    # Legacy options (for compatibility)
    abstract: bool = False

    def __post_init__(self):
        """Post-initialization setup."""
        # Set defaults based on model if available
        if hasattr(self, '_model_cls'):
            self._apply_defaults()

    def _apply_defaults(self):
        """Apply sensible defaults based on the model."""
        model_cls = getattr(self, '_model_cls', None)
        if not model_cls:
            return

        # Auto-generate verbose names
        if not self.verbose_name:
            self.verbose_name = model_cls.__name__.replace('_', ' ').title()

        if not self.verbose_name_plural:
            self.verbose_name_plural = f"{self.verbose_name}s"

        # Auto-generate table name
        if not self.db_table:
            self.db_table = model_cls.__name__.lower() + 's'

        # Default ordering
        if not self.ordering and hasattr(model_cls, 'created_at'):
            self.ordering = ['-created_at']

        # Default API readonly fields
        if not self.api_readonly_fields:
            readonly = []
            if hasattr(model_cls, 'id'):
                readonly.append('id')
            if hasattr(model_cls, 'created_at'):
                readonly.append('created_at')
            if hasattr(model_cls, 'updated_at'):
                readonly.append('updated_at')
            self.api_readonly_fields = readonly

        # Default admin display fields
        if not self.admin_list_display:
            display_fields = []
            # Add some common fields
            for attr_name in dir(model_cls):
                if not attr_name.startswith('_') and attr_name not in ['metadata', 'registry']:
                    try:
                        attr = getattr(model_cls, attr_name)
                        if hasattr(attr, 'type') or hasattr(attr, 'column'):  # SQLAlchemy column
                            display_fields.append(attr_name)
                    except:
                        pass
            # Limit to first 5 fields
            self.admin_list_display = display_fields[:5]

    @property
    def api_fields(self) -> List[str]:
        """Get fields that should be included in API serialization."""
        model_cls = getattr(self, '_model_cls', None)
        if not model_cls:
            return []

        all_fields = []
        for attr_name in dir(model_cls):
            if not attr_name.startswith('_'):
                try:
                    attr = getattr(model_cls, attr_name)
                    if hasattr(attr, 'type') or hasattr(attr, 'column'):
                        all_fields.append(attr_name)
                except:
                    pass

        # Exclude specified fields
        api_fields = [f for f in all_fields if f not in self.api_exclude_fields]

        return api_fields

    @property
    def admin_fields(self) -> List[str]:
        """Get fields that should be included in admin interface."""
        model_cls = getattr(self, '_model_cls', None)
        if not model_cls:
            return []

        all_fields = []
        for attr_name in dir(model_cls):
            if not attr_name.startswith('_'):
                try:
                    attr = getattr(model_cls, attr_name)
                    if hasattr(attr, 'type') or hasattr(attr, 'column'):
                        all_fields.append(attr_name)
                except:
                    pass

        # Exclude specified fields
        admin_fields = [f for f in all_fields if f not in self.admin_exclude_fields]

        return admin_fields

    def get_api_field_info(self, field_name: str) -> Dict[str, Any]:
        """Get API field information."""
        return {
            'name': field_name,
            'readonly': field_name in self.api_readonly_fields,
            'required': field_name in self.api_required_fields,
            'nested': field_name in self.api_nested_fields,
        }

    def get_admin_field_info(self, field_name: str) -> Dict[str, Any]:
        """Get admin field information."""
        return {
            'name': field_name,
            'readonly': field_name in self.admin_readonly_fields,
            'editable': field_name in self.admin_list_editable,
            'link': field_name in (self.admin_list_display_links or [self.admin_list_display[0] if self.admin_list_display else None]),
        }

# Convenience function for creating model configs
def model_config(**kwargs) -> ModelConfig:
    """Create a ModelConfig instance with the given options."""
    return ModelConfig(**kwargs)

# Example usage patterns
def create_model_with_config(
    name: str,
    fields: Dict[str, Any],
    config: ModelConfig,
    base_classes: tuple = (Model,)
) -> Type[Model]:
    """
    Create a model class with the given configuration.

    This demonstrates how ModelConfig integrates with Eden models.
    """

    # Create the class attributes
    attrs = dict(fields)
    attrs['model_config'] = config

    # Set the model class on config for defaults
    config._model_cls = None  # Will be set after class creation

    # Create the class
    model_cls = type(name, base_classes, attrs)

    # Now set the model class on config
    config._model_cls = model_cls
    config._apply_defaults()

    return model_cls

# Example model with config (conceptual)
"""
class Article(Model):
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = ChoiceField(choices=Status, default="draft")
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Eden ModelConfig (like Django Meta but more comprehensive)
    model_config = ModelConfig(
        # Database
        ordering = ["-published_at", "-created_at"],
        get_latest_by = "published_at",
        indexes = [
            {"fields": ["status", "published_at"]},
            {"fields": ["author_id"]},
        ],
        tenant_isolated = True,

        # API
        api_resource = True,
        api_exclude_fields = ["internal_notes"],
        api_nested_fields = ["author", "tags"],

        # Admin
        admin_list_display = ["title", "status", "author", "published_at"],
        admin_list_filter = ["status", "published_at", "author"],
        admin_search_fields = ["title", "content"],
        admin_ordering = ["-published_at"],
        admin_list_editable = ["status"],
        admin_date_hierarchy = "published_at",

        # Validation
        unique_together = [["title", "author_id"]],

        # UI
        verbose_name = "Article",
        verbose_name_plural = "Articles",
    )

# Usage examples:

# API automatically excludes internal_notes field
article_dict = article.to_dict()  # No internal_notes

# Admin shows custom display fields
# GET /admin/articles/ -> shows title, status, author, published_at

# Database queries respect ordering
articles = await Article.query().all()  # Ordered by -published_at, -created_at

# Tenant isolation automatic
user_articles = await Article.query().all()  # Only current tenant's articles
"""