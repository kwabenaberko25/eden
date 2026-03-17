
from __future__ import annotations
import inspect
import logging
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from .base import Model

logger = logging.getLogger("eden.db.lifecycle")

class LifecycleMixin:
    """
    Mixin that provides lifecycle management (save, delete) and hook execution.
    """

    async def save(self: Model, session: Optional[AsyncSession] = None, validate: bool = True, commit: bool = True) -> Model:
        """
        Save the current instance state to the database.
        """
        from sqlalchemy.orm.attributes import instance_state
        from sqlalchemy import inspect as sa_inspect
        from sqlalchemy.orm import attributes
        from sqlalchemy import JSON
        from sqlalchemy.orm.attributes import flag_modified
        from eden.db.base import slugify

        # Determine if this is a new instance
        try:
            state = instance_state(self)
            is_new = state.key is None
        except Exception:
            is_new = True

        # Phase C.1: Change detection for Audit Log
        changes = {}
        if not is_new:
            try:
                insp = sa_inspect(self)
                for attr in insp.attrs:
                    history = attributes.get_history(self, attr.key)
                    if history.has_changes():
                        changes[attr.key] = {
                            "old": self._make_json_safe(history.deleted[0]) if history.deleted else None,
                            "new": self._make_json_safe(history.added[0]) if history.added else None
                        }
            except Exception:
                pass

        # Detect and flag JSON fields as modified
        if not is_new:
            mapper = sa_inspect(self.__class__)
            for column in mapper.columns:
                if isinstance(column.type, JSON):
                    flag_modified(self, column.key)

        # Handle Auto-Slugging
        await self._auto_slugify()

        if session:
            # Lifecycle hooks - Phase 1: Before
            if is_new:
                await self._call_hook("before_create", session)
            await self._call_hook("before_save", session)
            
            # Eden Validation Hooks & Rules
            await self._trigger_hooks(self._pre_save_hooks)

            if validate:
                await self.full_clean()
            
            # Re-check is_new if ID was assigned in hooks
            is_new = self.id is None or not await session.get(self.__class__, self.id)

            session.add(self)
            await session.flush()

            # Lifecycle hooks - Phase 2: After
            if is_new:
                await self._call_hook("after_create", session)
            await self._call_hook("after_save", session)
            await self._trigger_hooks(self._post_save_hooks)

            await session.refresh(self)
            await self._log_audit(is_new, self._make_json_safe(changes) if not is_new else None)
            return self

        async with self._provide_session() as sess:
            if is_new:
                await self._call_hook("before_create", sess)
            await self._call_hook("before_save", sess)
            await self._trigger_hooks(self._pre_save_hooks)

            if validate:
                await self.full_clean()

            sess.add(self)
            await sess.flush()

            if is_new:
                await self._call_hook("after_create", sess)
            await self._call_hook("after_save", sess)
            await self._trigger_hooks(self._post_save_hooks)

            if commit:
                await sess.commit()
                await sess.refresh(self)
            else:
                await sess.flush()
                await sess.refresh(self)

        await self._log_audit(is_new, self._make_json_safe(changes) if not is_new else None)
        return self

    async def _auto_slugify(self) -> None:
        """Automatically generate slugs for fields marked as SlugField."""
        from sqlalchemy import inspect as sa_inspect
        from eden.db.base import slugify
        
        mapper = sa_inspect(self.__class__)
        for column in mapper.columns:
            if "populate_from" in column.info:
                current_val = getattr(self, column.key, None)
                if not current_val:
                    source_field = column.info["populate_from"]
                    source_val = getattr(self, source_field, None)
                    if source_val:
                        setattr(self, column.key, slugify(str(source_val)))

    async def full_clean(self) -> None:
        """Run comprehensive validation."""
        if hasattr(self, 'clean'):
            self.clean()

        errors = await self.validate()
        if errors:
            from eden.exceptions import ValidationError
            formatted_errors = [{"loc": [err.field or "__all__"], "msg": err.message, "type": "validation"} for err in errors]
            raise ValidationError(detail="Model validation failed", errors=formatted_errors)

    async def delete(self, session: Optional[AsyncSession] = None, hard: bool = False, commit: bool = True) -> None:
        """Delete the current record."""""
        try:
            from eden.db.file_reference import FileReference
            await FileReference.cleanup_by_model(self.__class__, self.id)
        except Exception as exc:
            logger.warning(f"File cleanup failed for {self.__class__.__name__}({self.id}): {exc}")
        
        if hasattr(self, "deleted_at") and not hard:
            from datetime import datetime
            self.deleted_at = datetime.utcnow()
            await self.save(session, commit=commit)
            return

        if not hard:
            await self.hard_delete(session=session, commit=commit)
            return

        if session:
            await self._call_hook("before_delete", session)
            await session.delete(self)
            await session.flush()
            if commit:
                await session.commit()
            return

        async with self._provide_session() as sess:
            await self._call_hook("before_delete", sess)
            await sess.delete(self)
            await sess.flush()
            if commit:
                await sess.commit()

    async def hard_delete(self, session: Optional[AsyncSession] = None, commit: bool = True) -> None:
        """Permanently delete the record."""
        await self.delete(session=session, hard=True, commit=commit)

    async def _call_hook(self, hook_name: str, session: AsyncSession) -> None:
        """Call a lifecycle hook."""
        hook = getattr(self, hook_name, None)
        if hook and callable(hook):
            res = hook(session)
            if inspect.isawaitable(res):
                await res

    async def _log_audit(self, is_new: bool, changes: dict | None = None) -> None:
        """Helper to record audit trail of changes."""
        try:
            from eden.admin.models import AuditLog
            from eden.context import get_user
        except Exception:
            return
        
        if isinstance(self, AuditLog):
            return

        try:
            user = get_user()
            user_id = str(getattr(user, "id", user)) if user else None
            action = "create" if is_new else "update"
            
            if is_new and not changes:
                changes = {}
                from sqlalchemy import inspect as sa_inspect
                insp = sa_inspect(self)
                for attr in insp.attrs:
                    val = getattr(self, attr.key)
                    if val is not None:
                        changes[attr.key] = {"old": None, "new": self._make_json_safe(val)}

            await AuditLog.log(
                user_id=user_id,
                action=action,
                model=self.__class__,
                record_id=str(self.id),
                changes=changes
            )
        except Exception as e:
            logger.warning(f"Audit logging failed for {self.__class__.__name__}: {e}")

    def _make_json_safe(self, val: Any) -> Any:
        """Helper to convert non-JSON types to primitives."""
        import uuid
        from datetime import datetime
        
        if isinstance(val, (str, int, float, bool, type(None))):
            return val
        if isinstance(val, uuid.UUID):
            return str(val)
        if isinstance(val, datetime):
            return val.isoformat()
        if isinstance(val, dict):
            return {str(k): self._make_json_safe(v) for k, v in val.items()}
        if isinstance(val, (list, tuple, set)):
            return [self._make_json_safe(v) for v in val]
        return str(val)
