"""
Eden Framework — Feature Flags Database Persistence

Persistent storage backend for flags with history tracking,
change logs, and audit trails.

**Usage:**

    from eden.flags_db import DatabaseFlagBackend
    from eden.db import SessionLocal
    
    backend = DatabaseFlagBackend(session_factory=SessionLocal)
    flags = await backend.get_all_flags()
    await backend.save_flag(flag)
    history = await backend.get_flag_history("flag_id")
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from eden.db import Model, StringField, IntField, BoolField, DateTimeField, TextField, JSONField
from datetime import datetime

# ============================================================================
# Database Models
# ============================================================================

class FlagModel(Model):
    """Feature flag database model."""
    __tablename__ = "feature_flags"
    
    id = StringField(100, primary_key=True)
    name = StringField(255, required=True, unique=True)
    description = TextField(nullable=True)
    strategy = StringField(50, required=True)  # Enum string
    percentage = IntField(nullable=True)
    user_ids = JSONField(nullable=True)
    segments = JSONField(nullable=True)
    tenant_ids = JSONField(nullable=True)
    environments = JSONField(nullable=True)
    enabled = BoolField(default=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    created_by = StringField(255, nullable=True)
    updated_by = StringField(255, nullable=True)


class FlagHistoryModel(Model):
    """Flag change history."""
    __tablename__ = "feature_flag_history"
    
    id = IntField(primary_key=True)
    flag_id = StringField(100, required=True)
    action = StringField(50, required=True)  # created, updated, deleted, enabled, disabled
    old_value = JSONField(nullable=True)
    new_value = JSONField(nullable=True)
    changed_by = StringField(255, nullable=True)
    changed_at = DateTimeField(default=datetime.now)
    reason = TextField(nullable=True)


class FlagMetricsModel(Model):
    """Flag usage metrics."""
    __tablename__ = "feature_flag_metrics"
    
    id = IntField(primary_key=True)
    flag_id = StringField(100, required=True)
    total_checks = IntField(default=0)
    enabled_count = IntField(default=0)
    disabled_count = IntField(default=0)
    error_count = IntField(default=0)
    last_checked = DateTimeField(nullable=True)


# ============================================================================
# Database Backend
# ============================================================================

class DatabaseFlagBackend:
    """Database backend for feature flags."""
    
    def __init__(self, session_factory, enable_history: bool = True):
        """
        Initialize database backend.
        
        Args:
            session_factory: SQLAlchemy session factory
            enable_history: Enable change history tracking
        """
        self.session_factory = session_factory
        self.enable_history = enable_history
    
    def _get_session(self) -> Session:
        """Get database session."""
        return self.session_factory()
    
    # ========================================================================
    # Flag Operations
    # ========================================================================
    
    async def get_flag(self, flag_id: str) -> Optional[Dict[str, Any]]:
        """Get a flag by ID."""
        session = self._get_session()
        try:
            flag = session.query(FlagModel).filter_by(id=flag_id).first()
            if flag:
                return self._flag_to_dict(flag)
            return None
        finally:
            session.close()
    
    async def get_all_flags(self) -> Dict[str, Dict[str, Any]]:
        """Get all flags."""
        session = self._get_session()
        try:
            flags = session.query(FlagModel).all()
            return {f.id: self._flag_to_dict(f) for f in flags}
        finally:
            session.close()
    
    async def save_flag(self, flag_id: str, flag_data: Dict[str, Any], user_id: str = None) -> bool:
        """Save a flag."""
        session = self._get_session()
        try:
            existing = session.query(FlagModel).filter_by(id=flag_id).first()
            
            if existing:
                # Update
                old_data = self._flag_to_dict(existing)
                
                for key, value in flag_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                
                existing.updated_at = datetime.now()
                existing.updated_by = user_id
                
                # Log history
                if self.enable_history:
                    await self._log_change(
                        flag_id, "updated", old_data, flag_data, user_id
                    )
            else:
                # Create
                flag_data["id"] = flag_id
                flag_data["created_at"] = datetime.now()
                flag_data["updated_at"] = datetime.now()
                flag_data["created_by"] = user_id
                
                new_flag = FlagModel(**flag_data)
                session.add(new_flag)
                
                # Log history
                if self.enable_history:
                    await self._log_change(flag_id, "created", {}, flag_data, user_id)
            
            session.commit()
            logger.info(f"Flag saved: {flag_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving flag: {e}")
            return False
        finally:
            session.close()
    
    async def delete_flag(self, flag_id: str, user_id: str = None) -> bool:
        """Delete a flag."""
        session = self._get_session()
        try:
            flag = session.query(FlagModel).filter_by(id=flag_id).first()
            
            if not flag:
                return False
            
            old_data = self._flag_to_dict(flag)
            
            session.delete(flag)
            session.commit()
            
            # Log history
            if self.enable_history:
                await self._log_change(flag_id, "deleted", old_data, {}, user_id)
            
            logger.info(f"Flag deleted: {flag_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting flag: {e}")
            return False
        finally:
            session.close()
    
    async def update_percentage(self, flag_id: str, percentage: int, user_id: str = None):
        """Update rollout percentage (common operation)."""
        session = self._get_session()
        try:
            flag = session.query(FlagModel).filter_by(id=flag_id).first()
            
            if not flag:
                return False
            
            old_percentage = flag.percentage
            flag.percentage = percentage
            flag.updated_at = datetime.now()
            flag.updated_by = user_id
            
            session.commit()
            
            if self.enable_history:
                await self._log_change(
                    flag_id, "percentage_updated",
                    {"percentage": old_percentage},
                    {"percentage": percentage},
                    user_id
                )
            
            logger.info(f"Flag percentage updated: {flag_id} -> {percentage}%")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating percentage: {e}")
            return False
        finally:
            session.close()
    
    # ========================================================================
    # History Operations
    # ========================================================================
    
    async def get_flag_history(
        self, flag_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get change history for a flag."""
        session = self._get_session()
        try:
            history = session.query(FlagHistoryModel)\
                .filter_by(flag_id=flag_id)\
                .order_by(FlagHistoryModel.changed_at.desc())\
                .limit(limit)\
                .offset(offset)\
                .all()
            
            return [self._history_to_dict(h) for h in history]
        finally:
            session.close()
    
    async def get_all_history(self, limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all change history."""
        session = self._get_session()
        try:
            history = session.query(FlagHistoryModel)\
                .order_by(FlagHistoryModel.changed_at.desc())\
                .limit(limit)\
                .offset(offset)\
                .all()
            
            return [self._history_to_dict(h) for h in history]
        finally:
            session.close()
    
    # ========================================================================
    # Metrics Operations
    # ========================================================================
    
    async def get_metrics(self, flag_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a flag."""
        session = self._get_session()
        try:
            metrics = session.query(FlagMetricsModel).filter_by(flag_id=flag_id).first()
            
            if metrics:
                return self._metrics_to_dict(metrics)
            
            # Create default metrics
            metrics = FlagMetricsModel(flag_id=flag_id)
            session.add(metrics)
            session.commit()
            
            return self._metrics_to_dict(metrics)
        finally:
            session.close()
    
    async def increment_check(self, flag_id: str, enabled: bool = True):
        """Record a flag check."""
        session = self._get_session()
        try:
            metrics = session.query(FlagMetricsModel).filter_by(flag_id=flag_id).first()
            
            if not metrics:
                metrics = FlagMetricsModel(flag_id=flag_id)
                session.add(metrics)
            
            metrics.total_checks += 1
            if enabled:
                metrics.enabled_count += 1
            else:
                metrics.disabled_count += 1
            metrics.last_checked = datetime.now()
            
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error recording check: {e}")
        finally:
            session.close()
    
    # ========================================================================
    # Internal Methods
    # ========================================================================
    
    def _flag_to_dict(self, flag: FlagModel) -> Dict[str, Any]:
        """Convert flag model to dict."""
        return {
            "id": flag.id,
            "name": flag.name,
            "description": flag.description,
            "strategy": flag.strategy,
            "percentage": flag.percentage,
            "user_ids": flag.user_ids,
            "segments": flag.segments,
            "tenant_ids": flag.tenant_ids,
            "environments": flag.environments,
            "enabled": flag.enabled,
            "created_at": flag.created_at.isoformat(),
            "updated_at": flag.updated_at.isoformat(),
            "created_by": flag.created_by,
            "updated_by": flag.updated_by,
        }
    
    def _history_to_dict(self, history: FlagHistoryModel) -> Dict[str, Any]:
        """Convert history model to dict."""
        return {
            "id": history.id,
            "flag_id": history.flag_id,
            "action": history.action,
            "old_value": history.old_value,
            "new_value": history.new_value,
            "changed_by": history.changed_by,
            "changed_at": history.changed_at.isoformat(),
            "reason": history.reason,
        }
    
    def _metrics_to_dict(self, metrics: FlagMetricsModel) -> Dict[str, Any]:
        """Convert metrics model to dict."""
        return {
            "flag_id": metrics.flag_id,
            "total_checks": metrics.total_checks,
            "enabled_count": metrics.enabled_count,
            "disabled_count": metrics.disabled_count,
            "error_count": metrics.error_count,
            "last_checked": metrics.last_checked.isoformat() if metrics.last_checked else None,
        }
    
    async def _log_change(
        self, flag_id: str, action: str, old_value: Dict, new_value: Dict,
        user_id: str = None
    ):
        """Log a change to history."""
        session = self._get_session()
        try:
            history = FlagHistoryModel(
                flag_id=flag_id,
                action=action,
                old_value=old_value if old_value else None,
                new_value=new_value if new_value else None,
                changed_by=user_id,
            )
            session.add(history)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging change: {e}")
        finally:
            session.close()
