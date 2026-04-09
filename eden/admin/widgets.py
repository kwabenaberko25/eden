# NOTE: This file consolidates the admin.py orphaned code into the admin package
# Previously located in: eden/admin.py (unreachable due to file/directory conflict)
# Now integrated into: eden/admin/widgets.py

"""
Eden Admin Panel — Field Widgets, Actions, and Audit Trail

This module provides:
- Custom field widgets (text, email, password, select, datetime, image, etc.)
- Bulk actions (delete, deactivate, export, approve)
- Audit trail tracking for compliance

**Usage:**

    from eden.admin import AdminPanel
    from eden.admin.widgets import TextField, EmailField, DeleteAction

    class UserAdmin(AdminPanel):
        fields = {
            'email': EmailField(),
            'password': PasswordField(),
        }
        actions = [DeleteAction()]
"""

import logging
from typing import Optional, List, Dict, Any, Callable, Type
from dataclasses import dataclass, asdict, field as dataclass_field
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# ADMIN FIELD WIDGETS
# ============================================================================

class FieldWidget(ABC):
    """Base class for admin field widgets."""
    
    def __init__(
        self,
        label: str = "",
        help_text: str = "",
        required: bool = True,
        read_only: bool = False,
        hidden: bool = False,
    ):
        self.label = label
        self.help_text = help_text
        self.required = required
        self.read_only = read_only
        self.hidden = hidden
    
    @abstractmethod
    def render(self, name: str, value: Any) -> str:
        """Render widget as HTML."""
        raise NotImplementedError("Subclasses must implement render()")
    
    def process_form_data(self, name: str, data: dict) -> Any:
        """Process value from form data."""
        value = data.get(name)
        return self.clean(value)
    
    @abstractmethod
    def clean(self, value: Any) -> Any:
        """Validate and clean value."""
        raise NotImplementedError("Subclasses must implement clean()")


class TextField(FieldWidget):
    """Single-line text input."""
    
    def __init__(self, max_length: Optional[int] = None, pattern: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length
        self.pattern = pattern
    
    def render(self, name: str, value: Any) -> str:
        value_str = value or ""
        attrs = f' name="{name}"'
        if self.max_length:
            attrs += f' maxlength="{self.max_length}"'
        if self.pattern:
            attrs += f' pattern="{self.pattern}"'
        return f'<input type="text" value="{value_str}"{attrs} class="admin-input">'
    
    def clean(self, value: Any) -> Any:
        value = str(value) if value else ""
        if self.max_length is not None and len(value) > self.max_length:
            raise ValueError(f"Max length is {self.max_length}")
        return value


class EmailField(FieldWidget):
    """Email input with validation."""
    
    def render(self, name: str, value: Any) -> str:
        return f'<input type="email" name="{name}" value="{value or ""}" class="admin-input">'
    
    def clean(self, value: Any) -> Any:
        if not value:
            if self.required:
                raise ValueError("Email required")
            return None
        import re
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', str(value)):
            raise ValueError("Invalid email format")
        return value.lower()


class PasswordField(FieldWidget):
    """Password input."""
    
    def render(self, name: str, value: Any) -> str:
        return f'<input type="password" name="{name}" value="" class="admin-input" autocomplete="new-password">'
    
    def clean(self, value: Any) -> Any:
        if not value:
            raise ValueError("Password required")
        if len(str(value)) < 8:
            raise ValueError("Password must be at least 8 characters")
        return value


class TextAreaField(FieldWidget):
    """Multi-line text input."""
    
    def __init__(self, rows: int = 4, **kwargs):
        super().__init__(**kwargs)
        self.rows = rows
    
    def render(self, name: str, value: Any) -> str:
        return f'<textarea name="{name}" rows="{self.rows}" class="admin-input">{value or ""}</textarea>'
    
    def clean(self, value: Any) -> Any:
        return str(value) if value else ""


class SelectField(FieldWidget):
    """Dropdown select."""
    
    def __init__(self, choices: Optional[List[tuple]] = None, multiple: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.choices = choices or []
        self.multiple = multiple
    
    def render(self, name: str, value: Any) -> str:
        tag = f'select name="{name}" class="admin-input"'
        if self.multiple:
            tag += " multiple"
        options = "\n".join(
            f'<option value="{k}" {"selected" if value == k else ""}>{v}</option>'
            for k, v in self.choices
        )
        return f"<{tag}>\n{options}\n</select>"
    
    def clean(self, value: Any) -> Any:
        if not value and self.required:
            raise ValueError("Selection required")
        if value:
            valid_values = [k for k, _ in self.choices]
            if value not in valid_values:
                raise ValueError(f"Invalid choice: {value}")
        return value


class CheckboxField(FieldWidget):
    """Checkbox boolean input."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.required = False
    
    def render(self, name: str, value: Any) -> str:
        checked = "checked" if value else ""
        return f'<input type="checkbox" name="{name}" {checked} class="admin-checkbox">'
    
    def clean(self, value: Any) -> Any:
        return bool(value)


class DateTimeField(FieldWidget):
    """Date/time input."""
    
    def render(self, name: str, value: Any) -> str:
        if isinstance(value, datetime):
            value = value.isoformat()
        return f'<input type="datetime-local" name="{name}" value="{value or ""}" class="admin-input">'
    
    def clean(self, value: Any) -> Any:
        if not value:
            if self.required:
                raise ValueError("Date/time required")
            return None
        if isinstance(value, datetime):
            return value
        try:
            if "T" in str(value):
                return datetime.fromisoformat(str(value))
            else:
                return datetime.fromisoformat(f"{value}T00:00:00")
        except ValueError:
            raise ValueError("Invalid date/time format")


class ImageField(FieldWidget):
    """File upload for images."""
    
    def __init__(self, allowed_formats: Optional[List[str]] = None, max_size_mb: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.allowed_formats = allowed_formats or ["jpg", "png", "gif"]
        self.max_size_mb = max_size_mb
    
    def render(self, name: str, value: Any) -> str:
        accept = ",".join(f".{fmt}" for fmt in self.allowed_formats)
        current = f'<div class="mb-2"><img src="{value}" class="h-20 w-20 object-cover rounded border"></div>' if value else ""
        return f'{current}<input type="file" name="{name}" accept="{accept}" class="admin-input">'
    
    def clean(self, value: Any) -> Any:
        if not value:
            if self.required:
                raise ValueError("Image required")
            return None
        return value


class CodeWidget(FieldWidget):
    """Monaco Editor powered code input."""
    
    def __init__(self, language: str = "python", height: str = "300px", **kwargs):
        super().__init__(**kwargs)
        self.language = language
        self.height = height
    
    def render(self, name: str, value: Any) -> str:
        value_str = value or ""
        return f"""
        <div class="code-editor-container" style="height: {self.height}; border: 1px solid #334155; border-radius: 8px; overflow: hidden;">
            <div id="editor_{name}" class="monaco-editor-instance" data-language="{self.language}" data-name="{name}" style="height: 100%;"></div>
            <textarea name="{name}" id="textarea_{name}" style="display:none;">{value_str}</textarea>
        </div>
        """
    
    def clean(self, value: Any) -> Any:
        return str(value) if value else ""


class JsonWidget(CodeWidget):
    """Monaco Editor powered JSON input."""
    
    def __init__(self, **kwargs):
        kwargs.setdefault("language", "json")
        super().__init__(**kwargs)
    
    def clean(self, value: Any) -> Any:
        if not value:
            return {} if not self.required else None
        
        import json
        if isinstance(value, (dict, list)):
            return value
            
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")


# ============================================================================
# ADMIN ACTIONS
# ============================================================================

class Action(ABC):
    """Base class for bulk actions."""
    
    name: str = "action"
    description: str = "Perform action"
    confirmation_required: bool = False
    permission_required: str | None = None
    
    @abstractmethod
    async def execute(self, selected_ids: List[Any], **kwargs) -> Dict[str, Any]:
        """Execute action on selected items."""
        pass


class DeleteAction(Action):
    """Delete selected records."""
    
    name = "delete"
    description = "Delete selected items"
    confirmation_required = True
    permission_required = "delete"
    
    async def execute(self, selected_ids: List[Any], model: Type = None, **kwargs) -> Dict[str, Any]:
        if not model:
            raise ValueError("Model required")
        
        count = 0
        for item_id in selected_ids:
            item = await model.get(id=item_id)
            if item:
                await item.delete()
                count += 1
        
        logger.info(f"Deleted {count} items")
        return {"success": True, "message": f"Deleted {count} item(s)", "count": count}


class DeactivateAction(Action):
    """Deactivate selected records."""
    
    name = "deactivate"
    description = "Deactivate selected items"
    confirmation_required = True
    
    async def execute(self, selected_ids: List[Any], model: Type = None, **kwargs) -> Dict[str, Any]:
        if not model:
            raise ValueError("Model required")
        
        count = 0
        for item_id in selected_ids:
            item = await model.get(id=item_id)
            if item and hasattr(item, 'is_active'):
                item.is_active = False
                await item.save()
                count += 1
        
        logger.info(f"Deactivated {count} items")
        return {"success": True, "message": f"Deactivated {count} item(s)", "count": count}


class ExportAction(Action):
    """Export selected records to CSV, JSON, or Excel format.
    
    Provides bulk export capability with support for multiple formats.
    Integrates with Eden's export utilities for full data serialization.
    
    Args:
        format: Export format - "csv" (default), "json", or "xlsx"/"excel"
    
    Example:
        export_csv = ExportAction(format="csv")
        export_excel = ExportAction(format="xlsx")
    """
    
    name = "export"
    description = "Export selected items"
    permission_required = "export"
    
    def __init__(self, format: str = "csv"):
        """
        Initialize export action with desired format.
        
        Args:
            format: One of "csv", "json", "xlsx", or "excel"
        """
        format_lower = format.lower()
        if format_lower in ("excel", "xls"):
            format_lower = "xlsx"
        
        if format_lower not in ("csv", "json", "xlsx"):
            raise ValueError(f"Unsupported export format: {format}. Use csv, json, or xlsx.")
        
        self.format = format_lower
    
    async def execute(
        self,
        selected_ids: List[Any],
        model: Type = None,
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute the export action and return exported data.
        
        Returns a dictionary with:
        - success: bool indicating success
        - data: The exported data (CSV string, JSON string, or Excel bytes)
        - format: The export format used
        - count: Number of records exported
        - filename: Suggested download filename
        - content_type: MIME type for response headers
        
        Args:
            selected_ids: List of record IDs to export
            model: The model class
            fields: Optional list of field names to include
        
        Raises:
            ValueError: If model not provided or no records found
        
        Returns:
            Dictionary with export data and metadata
        """
        if not model:
            raise ValueError("Model required for export")
        
        if not selected_ids:
            return {
                "success": False,
                "message": "No records selected for export",
                "count": 0
            }
        
        # Fetch all selected records
        items = []
        for item_id in selected_ids:
            try:
                item = await model.get(id=item_id)
                if item:
                    items.append(item)
            except Exception as e:
                logger.warning(f"Failed to fetch record {item_id}: {e}")
        
        if not items:
            return {
                "success": False,
                "message": "No valid records found for export",
                "count": 0
            }
        
        # Import export utilities
        from eden.admin.export import (
            to_csv, to_json, to_excel,
            generate_export_filename,
            get_export_response_headers
        )
        
        # Generate export based on format
        model_name = getattr(model, "__tablename__", model.__name__.lower())
        filename = await generate_export_filename(model_name, self.format)
        headers = await get_export_response_headers(filename, self.format)
        
        try:
            if self.format == "csv":
                data = await to_csv(items, model, fields)
                content_type = headers["Content-Type"]
            elif self.format == "json":
                data = await to_json(items, model, fields, pretty=True)
                content_type = headers["Content-Type"]
            elif self.format == "xlsx":
                data = await to_excel(items, model, fields)
                content_type = headers["Content-Type"]
            else:
                raise ValueError(f"Unsupported format: {self.format}")
            
            logger.info(
                f"Exported {len(items)} records from {model_name} as {self.format.upper()}"
            )
            
            return {
                "success": True,
                "message": f"Successfully exported {len(items)} record(s) as {self.format.upper()}",
                "count": len(items),
                "data": data,
                "format": self.format,
                "filename": filename,
                "content_type": content_type,
                "content_disposition": headers["Content-Disposition"],
            }
        
        except ImportError as e:
            logger.error(f"Export failed - missing dependency: {e}")
            return {
                "success": False,
                "message": f"Export format '{self.format}' not available: {str(e)}",
                "count": 0
            }
        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Export failed: {str(e)}",
                "count": 0
            }


class ApproveAction(Action):
    """Approve selected records."""
    
    name = "approve"
    description = "Approve selected items"
    confirmation_required = True
    permission_required = "approve"
    
    async def execute(self, selected_ids: List[Any], model: Type = None, **kwargs) -> Dict[str, Any]:
        if not model:
            raise ValueError("Model required")
        
        count = 0
        for item_id in selected_ids:
            item = await model.get(id=item_id)
            if item and hasattr(item, 'is_approved'):
                item.is_approved = True
                await item.save()
                count += 1
        
        logger.info(f"Approved {count} items")
        return {"success": True, "message": f"Approved {count} item(s)", "count": count}


# ============================================================================
# AUDIT TRAIL
# ============================================================================

@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: datetime = dataclass_field(default_factory=datetime.utcnow)
    user_id: Optional[Any] = None
    action: str = ""
    model_name: str = ""
    record_id: Any = None
    changes: Dict[str, tuple] = dataclass_field(default_factory=dict)
    details: str = ""


class AuditTrail:
    """Tracks all admin changes for compliance and debugging."""
    
    def __init__(self):
        self._entries: List[AuditEntry] = []
    
    def log_create(
        self, user_id: Optional[Any], model_name: str, record_id: Any, details: str = ""
    ) -> AuditEntry:
        """Log record creation."""
        entry = AuditEntry(user_id=user_id, action="create", model_name=model_name, record_id=record_id, details=details)
        self._entries.append(entry)
        logger.info(f"Audit: {model_name}#{record_id} created by user {user_id}")
        return entry
    
    def log_update(
        self, user_id: Optional[Any], model_name: str, record_id: Any, 
        changes: Dict[str, tuple], details: str = ""
    ) -> AuditEntry:
        """Log record update."""
        entry = AuditEntry(
            user_id=user_id, action="update", model_name=model_name, record_id=record_id,
            changes=changes, details=details
        )
        self._entries.append(entry)
        logger.info(f"Audit: {model_name}#{record_id} updated by user {user_id}")
        return entry
    
    def log_delete(
        self, user_id: Optional[Any], model_name: str, record_id: Any, details: str = ""
    ) -> AuditEntry:
        """Log record deletion."""
        entry = AuditEntry(user_id=user_id, action="delete", model_name=model_name, record_id=record_id, details=details)
        self._entries.append(entry)
        logger.warning(f"Audit: {model_name}#{record_id} deleted by user {user_id}")
        return entry
    
    def get_history(
        self, model_name: Optional[str] = None, record_id: Optional[Any] = None, limit: int = 100
    ) -> List[AuditEntry]:
        """Retrieve audit history."""
        results = self._entries
        if model_name:
            results = [e for e in results if e.model_name == model_name]
        if record_id:
            results = [e for e in results if e.record_id == record_id]
        return list(reversed(results))[-limit:]


class AdminPanel:
    """Configuration for a model admin dashboard."""
    fields: Dict[str, FieldWidget] = {}
    actions: List[Action] = []
    ordering: List[str] = []
    search_fields: List[str] = []

class AdminRegistry:
    """Registry for modern admin panels."""
    def __init__(self):
        self._panels: Dict[Type, Type[AdminPanel]] = {}
        self._instances: Dict[Type, AdminPanel] = {}

    def register(self, model: Type, panel_class: Type[AdminPanel]):
        self._panels[model] = panel_class
        self._instances[model] = panel_class()
        return panel_class

    def get(self, model: Type) -> Optional[AdminPanel]:
        return self._instances.get(model)

class DashboardRegistry:
    """Registry for admin dashboards."""
    def __init__(self):
        self._dashboards: List[Any] = []

    def register(self, dashboard_cls: Type):
        self._dashboards.append(dashboard_cls())
        return dashboard_cls

    def get_dashboards(self) -> List[Any]:
        return self._dashboards

_registry = AdminRegistry()
_dashboard_registry = DashboardRegistry()
register_admin = _registry.register
get_admin = _registry.get
register_dashboard = _dashboard_registry.register


# ============================================================================
# DASHBOARD WIDGETS
# ============================================================================

@dataclass
class DashboardWidget(ABC):
    """Base class for dashboard components."""
    label: str
    icon: Optional[str] = None
    
    @abstractmethod
    def render(self) -> str:
        raise NotImplementedError()

@dataclass
class StatWidget(DashboardWidget):
    """Simple counter or metric card."""
    value: Any = "0"
    trend: Optional[str] = None # e.g. "+12%" or "up"
    
    def render(self) -> str:
        return f'<div class="stat-card"><h3>{self.label}</h3><p>{self.value}</p></div>'

@dataclass
class ChartWidget(DashboardWidget):
    """Data visualization widget."""
    endpoint: Optional[str] = None
    type: str = "line" # line, bar, area, pie
    data: Optional[List[Dict[str, Any]]] = None
    
    def render(self) -> str:
         return f'<div class="chart-card" data-type="{self.type}" data-endpoint="{self.endpoint}"><h3>{self.label}</h3></div>'


__all__ = [
    "FieldWidget", "TextField", "EmailField", "PasswordField", "TextAreaField",
    "SelectField", "CheckboxField", "DateTimeField", "ImageField",
    "CodeWidget", "JsonWidget",
    "Action", "DeleteAction", "DeactivateAction", "ExportAction", "ApproveAction",
    "AuditEntry", "AuditTrail",
    "AdminPanel", "AdminRegistry", "register_admin", "get_admin",
    "DashboardWidget", "StatWidget", "ChartWidget", "register_dashboard",
]
