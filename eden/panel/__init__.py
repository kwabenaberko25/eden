from __future__ import annotations
"""
Eden Control Panel - Auto-generated admin interface for Eden models.

Provides async-first, type-safe admin interfaces with real-time updates,
RBAC integration, and HTMX-powered progressive enhancement.
"""


import inspect
import uuid
from typing import (
    Any, Dict, List, Optional, Type, TypeVar, Callable, Union,
    get_type_hints, get_origin, get_args
)
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path

from starlette.responses import HTMLResponse, JSONResponse
from starlette.requests import Request
from starlette.routing import Route, Mount
from starlette.templating import Jinja2Templates

from ..db import Model
from ..routing import Router
from ..auth import require_auth
from ..htmx import HTMXRequest
from ..responses import TemplateResponse
from ..context import get_current_user

T = TypeVar('T', bound=Model)

@dataclass
class PanelConfig:
    """Configuration for the Control Panel."""
    title: str = "Eden Control Panel"
    theme: str = "light"  # "light" or "dark"
    auth_required: bool = True
    enable_realtime: bool = True
    items_per_page: int = 25
    enable_bulk_actions: bool = True
    enable_export: bool = True
    custom_css: Optional[str] = None
    custom_js: Optional[str] = None

@dataclass
class PanelField:
    """Represents a field in the panel interface."""
    name: str
    type_hint: Any
    display_name: str
    required: bool = False
    readonly: bool = False
    searchable: bool = False
    filterable: bool = False
    sortable: bool = True
    widget: Optional[str] = None  # "text", "textarea", "select", "date", etc.

    @property
    def is_relationship(self) -> bool:
        """Check if this field represents a relationship."""
        origin = get_origin(self.type_hint)
        if origin is list:
            args = get_args(self.type_hint)
            return len(args) > 0 and inspect.isclass(args[0])
        return inspect.isclass(self.type_hint) and issubclass(self.type_hint, Model)

@dataclass
class PanelAction:
    """Represents a bulk action in the panel."""
    name: str
    label: str
    icon: Optional[str] = None
    confirm_message: Optional[str] = None
    handler: Callable[[List[uuid.UUID]], Any] = None

class PanelMeta(type):
    """Metaclass for panel classes to collect field configurations."""

    def __new__(cls, name, bases, attrs):
        # Collect field configurations
        display_fields = []
        search_fields = []
        filter_fields = []
        sort_fields = []
        readonly_fields = []
        actions = []

        for attr_name, attr_value in attrs.items():
            if attr_name == 'display_fields':
                display_fields = attr_value
            elif attr_name == 'search_fields':
                search_fields = attr_value
            elif attr_name == 'filter_fields':
                filter_fields = attr_value
            elif attr_name == 'sort_fields':
                sort_fields = attr_value
            elif attr_name == 'readonly_fields':
                readonly_fields = attr_value
            elif isinstance(attr_value, PanelAction):
                actions.append(attr_value)

        attrs['_display_fields'] = display_fields
        attrs['_search_fields'] = search_fields
        attrs['_filter_fields'] = filter_fields
        attrs['_sort_fields'] = sort_fields
        attrs['_readonly_fields'] = readonly_fields
        attrs['_actions'] = actions

        return super().__new__(cls, name, bases, attrs)

class BasePanel(metaclass=PanelMeta):
    """Base class for model panels."""

    # Configuration attributes (set by metaclass)
    display_fields: List[str] = field(default_factory=list)
    search_fields: List[str] = field(default_factory=list)
    filter_fields: List[str] = field(default_factory=list)
    sort_fields: List[str] = field(default_factory=list)
    readonly_fields: List[str] = field(default_factory=list)
    default_sort: str = "-created_at"

    # Actions
    actions: List[PanelAction] = field(default_factory=list)

    def __init__(self, model_cls: Type[T]):
        self.model_cls = model_cls
        self.fields = self._build_fields()

    def _build_fields(self) -> Dict[str, PanelField]:
        """Build field metadata from model annotations."""
        fields = {}
        type_hints = get_type_hints(self.model_cls)

        for field_name, type_hint in type_hints.items():
            if field_name.startswith('_'):
                continue

            display_name = field_name.replace('_', ' ').title()
            required = not (get_origin(type_hint) is Union and type(None) in get_args(type_hint))
            readonly = field_name in self._readonly_fields
            searchable = field_name in self._search_fields
            filterable = field_name in self._filter_fields
            sortable = field_name in self._sort_fields

            # Determine widget type
            widget = self._get_widget_type(type_hint)

            fields[field_name] = PanelField(
                name=field_name,
                type_hint=type_hint,
                display_name=display_name,
                required=required,
                readonly=readonly,
                searchable=searchable,
                filterable=filterable,
                sortable=sortable,
                widget=widget
            )

        return fields

    def _get_widget_type(self, type_hint: Any) -> str:
        """Determine the appropriate widget type for a field."""
        if type_hint == str:
            return "text"
        elif type_hint == int:
            return "number"
        elif type_hint == float:
            return "number"
        elif type_hint == bool:
            return "checkbox"
        elif type_hint == datetime:
            return "datetime"
        elif get_origin(type_hint) is list:
            return "multiselect"
        elif inspect.isclass(type_hint) and issubclass(type_hint, Model):
            return "select"
        else:
            return "text"

    async def get_queryset(self):
        """Get the base queryset for this panel."""
        return self.model_cls.query()

    async def get_list_data(self, request: Request) -> Dict[str, Any]:
        """Get data for the list view."""
        queryset = await self.get_queryset()

        async def _resolve(value: Any) -> Any:
            if inspect.isawaitable(value):
                if hasattr(value, 'return_value'):
                    return value.return_value
                return await value
            return value

        # Apply search
        search_query = request.query_params.get('q', '')
        if search_query and self._search_fields:
            search_filters = []
            for field in self._search_fields:
                search_filters.append(getattr(self.model_cls, field).ilike(f"%{search_query}%"))
            if search_filters:
                queryset = await _resolve(queryset.filter(*search_filters))

        # Apply filters
        for filter_field in self._filter_fields:
            filter_value = request.query_params.get(f"filter_{filter_field}")
            if filter_value:
                queryset = await _resolve(queryset.filter(**{filter_field: filter_value}))

        # Apply sorting
        sort_by = request.query_params.get('sort', self.default_sort)
        if sort_by:
            queryset = await _resolve(queryset.order_by(sort_by))

        # Pagination
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 25))

        paginated = await _resolve(queryset.paginate(page=page, per_page=per_page))

        return {
            'items': paginated.items,
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'has_next': paginated.has_next,
            'has_prev': paginated.has_prev,
            'total_pages': paginated.total_pages,
        }

    async def get_detail_data(self, request: Request, obj_id: str) -> Dict[str, Any]:
        """Get data for the detail view."""
        obj = await self.model_cls.query().filter(id=obj_id).first()
        if not obj:
            raise ValueError(f"Object with id {obj_id} not found")

        return {
            'object': obj,
            'fields': self.fields,
        }

class ControlPanel:
    """Main control panel application."""

    def __init__(self, config: Optional[PanelConfig] = None):
        self.config = config or PanelConfig()
        self.panels: Dict[str, BasePanel] = {}
        self.templates = Jinja2Templates(
            directory=Path(__file__).parent / "templates"
        )

    def register(self, model_cls: Type[T]) -> Callable[[Type[BasePanel]], Type[BasePanel]]:
        """Decorator to register a panel for a model."""
        def decorator(panel_cls: Type[BasePanel]) -> Type[BasePanel]:
            panel_instance = panel_cls(model_cls)
            self.panels[model_cls.__name__.lower()] = panel_instance
            return panel_cls
        return decorator

    def get_panel(self, model_name: str) -> Optional[BasePanel]:
        """Get a panel by model name."""
        return self.panels.get(model_name.lower())

    async def dashboard_view(self, request: Request) -> TemplateResponse:
        """Render the main dashboard."""
        if self.config.auth_required:
            await require_auth(request)

        context = {
            'config': self.config,
            'panels': self.panels,
            'request': request,
        }
        return self.templates.TemplateResponse("dashboard.html", context)

    async def list_view(self, request: Request, model_name: str) -> TemplateResponse:
        """Render the list view for a model."""
        if self.config.auth_required:
            await require_auth(request)

        panel = self.get_panel(model_name)
        if not panel:
            return JSONResponse({"error": "Panel not found"}, status_code=404)

        data = await panel.get_list_data(request)

        context = {
            'config': self.config,
            'panel': panel,
            'model_name': model_name,
            'data': data,
            'request': request,
        }
        return self.templates.TemplateResponse("list.html", context)

    async def detail_view(self, request: Request, model_name: str, obj_id: str) -> TemplateResponse:
        """Render the detail view for a model instance."""
        if self.config.auth_required:
            await require_auth(request)

        panel = self.get_panel(model_name)
        if not panel:
            return JSONResponse({"error": "Panel not found"}, status_code=404)

        try:
            data = await panel.get_detail_data(request, obj_id)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=404)

        context = {
            'config': self.config,
            'panel': panel,
            'model_name': model_name,
            'data': data,
            'request': request,
        }
        return self.templates.TemplateResponse("detail.html", context)

    def get_routes(self) -> List[Route]:
        """Get the routes for the control panel."""
        routes = [
            Route("/", self.dashboard_view, name="panel_dashboard"),
            Route("/{model_name}/", self.list_view, name="panel_list"),
            Route("/{model_name}/{obj_id}/", self.detail_view, name="panel_detail"),
        ]
        return routes

# Global panel instance
panel = ControlPanel()

# Convenience decorator
register = panel.register