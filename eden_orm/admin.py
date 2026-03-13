"""
Admin Panel Auto-Generation - Generate admin interfaces automatically from models

Allows auto-generating admin CRUD interfaces from model definitions:
- ModelAdmin class auto-creates list, detail, edit views
- Field introspection for appropriate form widgets
- Bulk actions support
- Filtering and search capabilities

Usage:
    from eden_orm.admin import ModelAdmin, site
    
    class UserAdmin(ModelAdmin):
        list_display = ['name', 'email', 'is_active']
        search_fields = ['name', 'email']
        filters = ['is_active', 'created_at']
    
    site.register(User, UserAdmin)
    
    # Admin routes auto-created:
    # GET /admin/user/ - List view
    # GET /admin/user/<id>/ - Detail view
    # POST /admin/user/ - Create
    # PUT /admin/user/<id>/ - Edit
    # DELETE /admin/user/<id>/ - Delete
"""

from typing import List, Dict, Any, Optional, Type, Callable
from dataclasses import dataclass, field as dc_field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModelPermission:
    """Model-level permissions."""
    
    model_name: str
    can_view: bool = True
    can_add: bool = True
    can_change: bool = True
    can_delete: bool = True


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
        # Default: all fields except excluded
        all_fields = [f.name for f in self.model_class._fields if hasattr(self.model_class, '_fields')]
        return [f for f in all_fields if f not in self.excluded_fields]
    
    def get_editable_fields(self) -> List[str]:
        """Get fields that can be edited."""
        all_fields = [f.name for f in self.model_class._fields if hasattr(self.model_class, '_fields')]
        return [f for f in all_fields if f not in self.readonly_fields + self.excluded_fields]


class ModelAdmin:
    """
    Auto-generated admin interface for a model.
    
    Usage:
        class UserAdmin(ModelAdmin):
            list_display = ['id', 'name', 'email', 'created_at']
            search_fields = ['name', 'email']
            filters = ['is_active']
            readonly_fields = ['created_at', 'updated_at']
    """
    
    model_class: Type[Any] = None
    list_display: List[str] = []
    search_fields: List[str] = []
    filters: List[str] = []
    ordering: List[str] = []
    readonly_fields: List[str] = []
    excluded_fields: List[str] = []
    actions: Dict[str, Callable] = {}
    
    def __init__(self, model_class: Type[Any]):
        self.model_class = model_class
        self.options = ModelAdminOptions(
            model_class=model_class,
            list_display=self.list_display,
            search_fields=self.search_fields,
            filters=self.filters,
            ordering=self.ordering,
            readonly_fields=self.readonly_fields,
            excluded_fields=self.excluded_fields,
            actions=self.actions
        )
        logger.info(f"ModelAdmin initialized for {model_class.__name__}")
    
    async def get_list(
        self,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get paginated list of model instances.
        
        Args:
            page: Page number (1-indexed)
            per_page: Records per page
            search: Search query for search_fields
            filters: Filter conditions
        
        Returns:
            Dict with 'objects', 'total', 'page', 'pages'
        """
        try:
            # Query the model
            query = self.model_class.select()
            
            # Apply filters
            if filters:
                for field_name, value in filters.items():
                    if hasattr(self.model_class, field_name):
                        query = query.where(getattr(self.model_class, field_name) == value)
            
            # Apply search across search_fields
            if search and self.options.search_fields:
                from eden_orm import SearchQuery
                search_conditions = []
                for field_name in self.options.search_fields:
                    if hasattr(self.model_class, field_name):
                        field = getattr(self.model_class, field_name)
                        search_conditions.append(field.contains(search))
                if search_conditions:
                    query = query.where(*search_conditions)
            
            # Get total count
            total = query.count()
            
            # Apply ordering
            if self.options.ordering:
                for order_field in self.options.ordering:
                    if hasattr(self.model_class, order_field):
                        query = query.order_by(getattr(self.model_class, order_field))
            
            # Apply pagination
            offset = (page - 1) * per_page
            objects = query.offset(offset).limit(per_page).all()
            
            # Calculate pages
            pages = (total + per_page - 1) // per_page
            
            return {
                "objects": objects,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": pages,
                "display_fields": self.options.get_display_fields()
            }
        except Exception as e:
            logger.error(f"Error getting list for {self.model_class.__name__}: {e}")
            return {
                "objects": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "pages": 0,
                "display_fields": self.options.get_display_fields(),
                "error": str(e)
            }
    
    async def get_detail(self, object_id: Any) -> Optional[Any]:
        """Get single object by ID."""
        try:
            # Query by primary key (assuming 'id' field)
            obj = self.model_class.select().where(self.model_class.id == object_id).first()
            return obj
        except Exception as e:
            logger.error(f"Error getting detail for {self.model_class.__name__} id={object_id}: {e}")
            return None
    
    async def save_object(self, data: Dict[str, Any]) -> Optional[Any]:
        """Save (create or update) object."""
        try:
            # Extract ID if provided (update) or None (create)
            object_id = data.pop('id', None)
            
            # Filter data to only include fields that exist on model
            valid_data = {}
            if hasattr(self.model_class, '_fields'):
                field_names = {f.name for f in self.model_class._fields}
                valid_data = {k: v for k, v in data.items() if k in field_names}
            else:
                valid_data = data
            
            if object_id:
                # Update existing object
                obj = self.model_class.select().where(self.model_class.id == object_id).first()
                if obj:
                    for key, value in valid_data.items():
                        setattr(obj, key, value)
                    obj.save()
                    return obj
                return None
            else:
                # Create new object
                obj = self.model_class.create(**valid_data)
                return obj
        except Exception as e:
            logger.error(f"Error saving {self.model_class.__name__}: {e}")
            return None
    
    async def delete_object(self, object_id: Any) -> bool:
        """Delete object by ID."""
        try:
            obj = self.model_class.select().where(self.model_class.id == object_id).first()
            if obj:
                obj.delete_instance()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting {self.model_class.__name__} id={object_id}: {e}")
            return False
    
    def get_field_widget(self, field_name: str) -> str:
        """Determine appropriate form widget for field."""
        try:
            # Get field from model
            if hasattr(self.model_class, '_fields'):
                field_map = {f.name: f for f in self.model_class._fields}
                if field_name in field_map:
                    field = field_map[field_name]
                    field_type = field.__class__.__name__
                    
                    # Map field types to widget types
                    widget_map = {
                        'DateField': 'date',
                        'DateTimeField': 'datetime',
                        'IntegerField': 'number',
                        'FloatField': 'number',
                        'BooleanField': 'checkbox',
                        'TextField': 'textarea',
                        'ForeignKeyField': 'select',
                        'ManyToManyField': 'multi-select',
                    }
                    
                    return widget_map.get(field_type, 'text')
            
            return 'text'
        except Exception as e:
            logger.error(f"Error determining widget for {field_name}: {e}")
            return 'text'
    
    def perform_action(self, action_name: str, objects: List[Any]) -> bool:
        """Execute bulk action on objects."""
        if action_name not in self.actions:
            return False
        
        try:
            action_func = self.actions[action_name]
            # Execute action
            result = action_func(objects)
            return True
        except Exception as e:
            logger.error(f"Error performing action {action_name}: {e}")
            return False
    
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


class AdminSite:
    """
    Admin site that manages multiple model admins.
    
    Usage:
        site = AdminSite()
        site.register(User, UserAdmin)
        site.register(Post, PostAdmin)
        
        # Access at /admin/
    """
    
    def __init__(self, name: str = "Admin"):
        self.name = name
        self.admins: Dict[Type[Any], ModelAdmin] = {}
        logger.info(f"AdminSite '{name}' created")
    
    def register(
        self,
        model_class: Type[Any],
        admin_class: Optional[Type[ModelAdmin]] = None
    ) -> None:
        """
        Register a model admin.
        
        Args:
            model_class: The model class
            admin_class: Optional ModelAdmin subclass (auto-created if not provided)
        """
        if admin_class is None:
            admin_class = type(f"{model_class.__name__}Admin", (ModelAdmin,), {})
        
        admin_instance = admin_class(model_class)
        self.admins[model_class] = admin_instance
        
        logger.info(f"Registered {model_class.__name__} with admin site")
    
    def unregister(self, model_class: Type[Any]) -> None:
        """Unregister a model admin."""
        if model_class in self.admins:
            del self.admins[model_class]
            logger.info(f"Unregistered {model_class.__name__} from admin site")
    
    def get_admin(self, model_class: Type[Any]) -> Optional[ModelAdmin]:
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


# Default admin site instance
site = AdminSite(name="Eden Admin")
