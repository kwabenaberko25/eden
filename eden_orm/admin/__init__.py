"""
Eden ORM - Admin Panel

Auto-generated CRUD admin interface.
"""

from typing import Type, List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field as dc_field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModelAdminOptions:
    """Configuration for model admin."""
    
    model_class: Any
    list_display: List[str] = dc_field(default_factory=list)
    search_fields: List[str] = dc_field(default_factory=list)
    filters: List[str] = dc_field(default_factory=list)
    ordering: List[str] = dc_field(default_factory=lambda: ['id'])
    readonly_fields: List[str] = dc_field(default_factory=list)
    excluded_fields: List[str] = dc_field(default_factory=list)
    actions: Dict[str, Callable] = dc_field(default_factory=dict)
    
    def get_display_fields(self) -> List[str]:
        """Get fields to display in list view."""
        if self.list_display:
            return self.list_display
        return []
    
    def get_editable_fields(self) -> List[str]:
        """Get fields that can be edited."""
        all_fields = [f.name for f in getattr(self.model_class, '_fields', [])]
        return [f for f in all_fields if f not in self.readonly_fields + self.excluded_fields]


class ModelAdmin:
    """Configuration for model admin interface."""
    
    list_display: List[str] = []
    list_filter: List[str] = []
    search_fields: List[str] = []
    
    def __init__(self, model_class: Type):
        self.model_class = model_class
        self.options = ModelAdminOptions(
            model_class=model_class,
            list_display=self.list_display,
            search_fields=self.search_fields,
            filters=self.list_filter
        )
    
    def get_urls(self) -> List[Dict[str, str]]:
        """Generate URL routes for admin interface."""
        model_name = self.model_class.__name__.lower()
        
        urls = [
            {"method": "GET", "path": f"/admin/{model_name}/", "handler": "list_view"},
            {"method": "GET", "path": f"/admin/{model_name}/<id>/", "handler": "detail_view"},
            {"method": "POST", "path": f"/admin/{model_name}/", "handler": "create_view"},
            {"method": "PUT", "path": f"/admin/{model_name}/<id>/", "handler": "edit_view"},
            {"method": "DELETE", "path": f"/admin/{model_name}/<id>/", "handler": "delete_view"},
        ]
        
        return urls
    
    async def get_list(
        self,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get paginated list of model instances."""
        offset = (page - 1) * per_page
        
        return {
            "objects": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "pages": 0,
            "display_fields": self.options.get_display_fields()
        }


class AdminSite:
    """Admin site for managing models."""
    
    def __init__(self, title: str = "Admin", name: str = None):
        self.title = title
        self.name = name or title
        self.registry: Dict[Type, ModelAdmin] = {}
        self.admins: Dict[Type, ModelAdmin] = {}
        logger.info(f"AdminSite '{self.name}' created")
    
    def register(self, model_class: Type, admin_class=None):
        """Register model in admin."""
        if admin_class is None:
            admin_class = ModelAdmin
        
        admin_instance = admin_class(model_class)
        self.registry[model_class] = admin_instance
        self.admins[model_class] = admin_instance
        logger.info(f"Registered {model_class.__name__} in admin")
    
    def unregister(self, model_class: Type):
        """Unregister model from admin."""
        self.registry.pop(model_class, None)
        self.admins.pop(model_class, None)
    
    def get_admin(self, model_class: Type) -> Optional[ModelAdmin]:
        """Get admin for a model class."""
        return self.admins.get(model_class)
    
    def get_urls(self) -> List[Dict[str, str]]:
        """Generate all admin URLs."""
        urls = [
            {"method": "GET", "path": "/admin/", "handler": "index"}
        ]
        
        for model_class, admin in self.admins.items():
            urls.extend(admin.get_urls())
        
        return urls


# Global admin site instance
admin = AdminSite()
site = AdminSite(title="Eden Admin")

