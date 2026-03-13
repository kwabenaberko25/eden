"""
Eden ORM - Audit Trails

Track all changes to model instances with full audit history.
"""

import json
import logging
from typing import Optional, Any, Dict, List, Type
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Types of audit actions."""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    RESTORE = "RESTORE"


class AuditEntry:
    """Represents a single audit log entry."""
    
    def __init__(
        self,
        model_name: str,
        record_id: str,
        action: AuditAction,
        user_id: Optional[str] = None,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, tuple]] = None,
    ):
        self.id = None
        self.model_name = model_name
        self.record_id = record_id
        self.action = action
        self.user_id = user_id
        self.old_data = old_data or {}
        self.new_data = new_data or {}
        self.changes = changes or {}  # {field: (old, new)}
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "model_name": self.model_name,
            "record_id": str(self.record_id),
            "action": self.action.value,
            "user_id": self. user_id,
            "old_data": self.old_data,
            "new_data": self.new_data,
            "changes": {k: [v[0], v[1]] for k, v in self.changes.items()},
            "created_at": self.created_at.isoformat(),
        }


class AuditLogger:
    """Manages audit trail recording."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.entries: List[AuditEntry] = []
    
    def enable(self):
        """Enable audit logging."""
        self.enabled = True
    
    def disable(self):
        """Disable audit logging."""
        self.enabled = False
    
    def log_create(
        self,
        model_name: str,
        record_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> AuditEntry:
        """Log CREATE action."""
        entry = AuditEntry(
            model_name=model_name,
            record_id=record_id,
            action=AuditAction.CREATE,
            user_id=user_id,
            new_data=data,
        )
        
        if self.enabled:
            self.entries.append(entry)
            logger.info(f"Audit: {model_name} {record_id} created by {user_id}")
        
        return entry
    
    def log_update(
        self,
        model_name: str,
        record_id: str,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> AuditEntry:
        """Log UPDATE action."""
        # Calculate field-level changes
        changes = {}
        for key in set(list(old_data.keys()) + list(new_data.keys())):
            old_val = old_data.get(key)
            new_val = new_data.get(key)
            if old_val != new_val:
                changes[key] = (old_val, new_val)
        
        entry = AuditEntry(
            model_name=model_name,
            record_id=record_id,
            action=AuditAction.UPDATE,
            user_id=user_id,
            old_data=old_data,
            new_data=new_data,
            changes=changes,
        )
        
        if self.enabled:
            self.entries.append(entry)
            logger.info(f"Audit: {model_name} {record_id} updated by {user_id}")
        
        return entry
    
    def log_delete(
        self,
        model_name: str,
        record_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> AuditEntry:
        """Log DELETE action."""
        entry = AuditEntry(
            model_name=model_name,
            record_id=record_id,
            action=AuditAction.DELETE,
            user_id=user_id,
            old_data=data,
        )
        
        if self.enabled:
            self.entries.append(entry)
            logger.info(f"Audit: {model_name} {record_id} deleted by {user_id}")
        
        return entry
    
    async def save_to_database(self, session):
        """Persist audit entries to database."""
        if not self.entries:
            return
        
        # Create audit table if needed
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            model_name VARCHAR(255) NOT NULL,
            record_id VARCHAR(36) NOT NULL,
            action VARCHAR(50) NOT NULL,
            user_id VARCHAR(36),
            old_data JSONB,
            new_data JSONB,
            changes JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        create_index_sql_1 = """
        CREATE INDEX IF NOT EXISTS idx_audit_model_record 
        ON audit_logs (model_name, record_id)
        """
        
        create_index_sql_2 = """
        CREATE INDEX IF NOT EXISTS idx_audit_created_at 
        ON audit_logs (created_at)
        """
        
        try:
            await session.execute(create_table_sql)
            await session.execute(create_index_sql_1)
            await session.execute(create_index_sql_2)
        except Exception:
            pass  # Table/indices might already exist
        
        # Insert entries
        for entry in self.entries:
            sql = """
            INSERT INTO audit_logs 
            (model_name, record_id, action, user_id, old_data, new_data, changes)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            
            try:
                await session.execute(
                    sql,
                    entry.model_name,
                    str(entry.record_id),
                    entry.action.value,
                    entry.user_id,
                    json.dumps(entry.old_data, default=str),
                    json.dumps(entry.new_data, default=str),
                    json.dumps(entry.changes, default=str),
                )
            except Exception as e:
                logger.error(f"Failed to save audit entry: {e}")
        
        self.entries.clear()


# Global audit logger
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def set_audit_logger(logger_inst: AuditLogger):
    """Set global audit logger instance."""
    global _audit_logger
    _audit_logger = logger_inst


class AuditMixin:
    """
    Mixin to add audit trail tracking to models.
    
    Usage:
        class Post(Model, AuditMixin):
            title: str
            content: str
    """
    
    __audit_enabled__ = True
    
    async def get_audit_history(self) -> list:
        """Get audit trail for this record."""
        from .connection import get_session
        
        session = await get_session()
        model_name = self.__class__.__name__
        record_id = str(self.id)
        
        sql = """
        SELECT * FROM audit_logs 
        WHERE model_name = $1 AND record_id = $2 
        ORDER BY created_at DESC
        """
        
        try:
            rows = await session.fetch(sql, model_name, record_id)
            return [dict(row) for row in rows]
        except Exception:
            return []
    
    async def save(self):
        """Save with audit logging."""
        if self.__audit_enabled__:
            audit_logger = get_audit_logger()
            audit_logger.log_update(
                self.__class__.__name__,
                str(self.id),
                self._get_old_data(),
                self.to_dict(),
            )
        
        return await super().save()
    
    async def delete(self):
        """Delete with audit logging."""
        if self.__audit_enabled__:
            audit_logger = get_audit_logger()
            audit_logger.log_delete(
                self.__class__.__name__,
                str(self.id),
                self.to_dict(),
            )
        
        return await super().delete()
    
    def _get_old_data(self) -> Dict[str, Any]:
        """Get previous data (if tracking enabled)."""
        return getattr(self, "_old_data", {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary (must be implemented by subclass)."""
        return {}
