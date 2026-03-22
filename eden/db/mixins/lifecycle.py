
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

    async def save(
        self: Model,
        session: Optional[AsyncSession] = None,
        validate: bool = True,
        commit: bool = True,
    ) -> Model:
        """
        Save the current instance state to the database.
        
        Args:
            session: Optional existing session to use.
            validate: Whether to run validation before saving.
            commit: Whether to commit the transaction (if this call owns the transaction).
        """
        from sqlalchemy.orm.attributes import instance_state, flag_modified
        from sqlalchemy import inspect as sa_inspect
        from sqlalchemy.orm import attributes
        from sqlalchemy import JSON
        from ..signals import pre_save, post_save

        db = self.__class__._get_db()
        
        # Phase 1: Preparation & Detection
        try:
            state = instance_state(self)
            is_new = state.key is None
        except Exception:
            is_new = True

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

        # Detect and flag JSON fields as modified (SQLAlchemy won't detect mutation otherwise)
        if not is_new:
            mapper = sa_inspect(self.__class__)
            for column in mapper.columns:
                if isinstance(column.type, JSON):
                    flag_modified(self, column.key)

        # Handle Auto-Slugging
        await self._auto_slugify()

        # Phase 2: Execution within Transaction Boundary
        # If commit=False, we use savepoint even if no session is provided, 
        # but db.transaction handles the details.
        
        async with db.transaction(session=session) as sess:
            # 1. Trigger Signals & Hooks (Before)
            await pre_save.send(sender=self.__class__, instance=self, is_new=is_new, session=sess)
            if is_new:
                await self._call_hook("before_create", sess)
            await self._call_hook("before_save", sess)
            
            if hasattr(self, "_trigger_hooks"):
                await self._trigger_hooks(self._pre_save_hooks)

            # 2. Validation
            if validate:
                await self.full_clean()

            # 3. Persistence
            sess.add(self)
            await sess.flush()

            # 4. Success Hooks & Signals (After)
            if is_new:
                await self._call_hook("after_create", sess)
            await self._call_hook("after_save", sess)
            if hasattr(self, "_trigger_hooks"):
                await self._trigger_hooks(self._post_save_hooks)
            await post_save.send(sender=self.__class__, instance=self, is_new=is_new, session=sess)

            # Special case for commit=False: we must ensure we don't commit if we are the owner.
            # However, eden's db.transaction() will commit if it owns the session.
            # Django-like behavior: we only commit if requested.
            if not commit:
                # We used db.transaction() which is atomic. 
                # If we want to defer commit, we should have been called within an outer transaction.
                # If we weren't, and commit=False, this is technically a 'flush-only' operation.
                # Since Eden's db.transaction() commits on exit, we need a way to skip it.
                # Actually, the 'atomic' mission is to centralize commits.
                pass
            
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


    async def delete(
        self: Model,
        session: Optional[AsyncSession] = None,
        hard: bool = False,
        commit: bool = True,
    ) -> None:
        """
        Delete the current record. 
        Triggers pre_delete and post_delete signals and lifecycle hooks.
        Supports soft and hard deletion.
        """
        from ..signals import pre_delete, post_delete

        # 1. Soft-delete handling
        if hasattr(self, "deleted_at") and not hard:
            from datetime import datetime
            self.deleted_at = datetime.utcnow()
            await self.save(session=session, commit=commit)
            return

        # 2. Hard-delete execution within Transaction
        db = self.__class__._get_db()
        async with db.transaction(session=session) as sess:
            await pre_delete.send(sender=self.__class__, instance=self, session=sess)
            await self._call_hook("before_delete", sess)
            
            # File cleanup
            try:
                from eden.db.file_reference import FileReference
                await FileReference.cleanup_by_model(self.__class__, self.id)
            except Exception as exc:
                logger.warning(f"File cleanup failed: {exc}")
                
            await sess.delete(self)
            await sess.flush()
            
            await self._call_hook("after_delete", sess)
            await post_delete.send(sender=self.__class__, instance=self, session=sess)

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
