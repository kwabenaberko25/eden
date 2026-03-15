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
    def render(self, value: Any) -> str:
        """Render widget as HTML."""
        raise NotImplementedError("Subclasses must implement render()")
    
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
    
    def render(self, value: Any) -> str:
        value_str = value or ""
        attrs = f' maxlength="{self.max_length}"' if self.max_length else ""
        if self.pattern:
            attrs += f' pattern="{self.pattern}"'
        return f'<input type="text" value="{value_str}"{attrs}>'
    
    def clean(self, value: Any) -> Any:
        value = str(value) if value else ""
        if self.max_length is not None and len(value) > self.max_length:
            raise ValueError(f"Max length is {self.max_length}")
        return value


class EmailField(FieldWidget):
    """Email input with validation."""
    
    def render(self, value: Any) -> str:
        return f'<input type="email" value="{value or ""}">'
    
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
    
    def render(self, value: Any) -> str:
        return '<input type="password" value="">'
    
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
    
    def render(self, value: Any) -> str:
        return f'<textarea rows="{self.rows}">{value or ""}</textarea>'
    
    def clean(self, value: Any) -> Any:
        return str(value) if value else ""


class SelectField(FieldWidget):
    """Dropdown select."""
    
    def __init__(self, choices: Optional[List[tuple]] = None, multiple: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.choices = choices or []
        self.multiple = multiple
    
    def render(self, value: Any) -> str:
        tag = "select multiple" if self.multiple else "select"
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
    
    def render(self, value: Any) -> str:
        checked = "checked" if value else ""
        return f'<input type="checkbox" {checked}>'
    
    def clean(self, value: Any) -> Any:
        return bool(value)


class DateTimeField(FieldWidget):
    """Date/time input."""
    
    def render(self, value: Any) -> str:
        if isinstance(value, datetime):
            value = value.isoformat()
        return f'<input type="datetime-local" value="{value or ""}">'
    
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
    
    def render(self, value: Any) -> str:
        accept = ",".join(f".{fmt}" for fmt in self.allowed_formats)
        current = f'<p>Current: <img src="{value}" max-width="200"></p>' if value else ""
        return f'{current}<input type="file" accept="{accept}">'
    
    def clean(self, value: Any) -> Any:
        if not value:
            if self.required:
                raise ValueError("Image required")
            return None
        return value


# ============================================================================
# ADMIN ACTIONS
# ============================================================================

class Action(ABC):
    """Base class for bulk actions."""
    
    name: str = "action"
    description: str = "Perform action"
    confirmation_required: bool = False
    permission_required: Optional[str] = None
    
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
    """Export selected records."""
    
    name = "export"
    description = "Export selected items"
    permission_required = "export"
    
    def __init__(self, format: str = "csv"):
        self.format = format
    
    async def execute(self, selected_ids: List[Any], model: Type = None, **kwargs) -> Dict[str, Any]:
        if not model:
            raise ValueError("Model required")
        
        items = []
        for item_id in selected_ids:
            item = await model.get(id=item_id)
            if item:
                items.append(item)
        
        logger.info(f"Exported {len(items)} items as {self.format}")
        return {"success": True, "message": f"Exported {len(items)} item(s)", "count": len(items)}


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

_registry = AdminRegistry()
register_admin = _registry.register
get_admin = _registry.get

__all__ = [
    "FieldWidget", "TextField", "EmailField", "PasswordField", "TextAreaField",
    "SelectField", "CheckboxField", "DateTimeField", "ImageField",
    "Action", "DeleteAction", "DeactivateAction", "ExportAction", "ApproveAction",
    "AuditEntry", "AuditTrail",
    "AdminPanel", "AdminRegistry", "register_admin", "get_admin",
]
