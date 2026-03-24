"""
Eden — Database Mixins

Helper mixins to add common functionality to Eden models.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Optional, TYPE_CHECKING, TypeVar, Type
from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from ..base import Model

from eden.context import get_user
from ..fields import f


class SoftDeleteMixin:
    """
    Adds a `deleted_at` field and filters out soft-deleted records by default.
    Using `delete()` will set `deleted_at` instead of dropping the row.
    """
    __allow_unmapped__ = True

    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True, default=None
    )

    @classmethod
    def _apply_default_filters(cls, target_cls: type, stmt: Any, **kwargs: Any) -> Any:
        """
        Cooperative filter hook for soft-delete.
        Automatically filters out records where deleted_at is set.
        """
        if not kwargs.get("include_deleted", False):
            # We use target_cls.deleted_at directly for the clause
            return stmt.where(getattr(target_cls, "deleted_at").is_(None))
        return stmt

    async def delete(self, session: Optional[AsyncSession] = None, *, commit: bool = True, hard: bool = False) -> None:
        """
        Soft deletes the record by setting deleted_at to the current timestamp.
        Use `hard=True` to permanently delete the row.
        """
        from ..base import Model
        db = Model._get_db()
        
        async with db.transaction(session=session, commit=commit) as tx_session:
            if hard:
                await tx_session.delete(self)
            else:
                self.deleted_at = datetime.datetime.now(datetime.UTC)
                await tx_session.merge(self)


class TimestampMixin:
    """
    Adds `created_at` and `updated_at` fields.
    Already included in `Model`, but extracted here for reuse.
    """
    __allow_unmapped__ = True
    created_at: datetime.datetime = f(default=datetime.datetime.now)
    updated_at: datetime.datetime = f(
        default=datetime.datetime.now, onupdate=datetime.datetime.now
    )


class BlameMixin:
    """
    Automatically tracks who created and updated a record.
    Requires `AuthenticationMiddleware` and `User` model.
    """
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(native_uuid=True), nullable=True
    )
    updated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(native_uuid=True), nullable=True
    )

    async def before_save(self, session):
        """Set updated_by_id from context."""
        user = get_user()
        if user:
            self.updated_by_id = user.id

        # Call super if it exists to preserve hook chaining
        if hasattr(super(), "before_save"):
            await super().before_save(session)

    async def before_create(self, session):
        """Set created_by_id from context."""
        user = get_user()
        if user:
            self.created_by_id = user.id
            self.updated_by_id = user.id

        if hasattr(super(), "before_create"):
            await super().before_create(session)
