"""
Eden — Tenant Mixin

Add to any Model to scope it to the current tenant.
Automatically filters queries and sets tenant_id on create.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from eden.orm import f


class TenantMixin:
    """
    Mixin that adds multi-tenant row-level isolation to any Model.
        class Project(Model, TenantMixin):
            __tablename__ = "projects"
            name: str = f()

        # All queries auto-filter by current tenant:
        projects = await Project.all(session)  # Only this tenant's projects
    """

    __eden_tenant_isolated__ = True
    __allow_unmapped__ = True

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("eden_tenants.id", ondelete="CASCADE"), index=True
    )

    @classmethod
    def _base_select(cls, **kwargs):
        """Override to auto-filter by the current tenant from context."""
        from sqlalchemy import select

        from eden.tenancy.context import get_current_tenant_id

        stmt = select(cls)

        # Apply soft-delete filter if SoftDeleteMixin is present
        if hasattr(cls, "deleted_at") and not kwargs.get("include_deleted", False):
            stmt = stmt.where(cls.deleted_at.is_(None))

        # Apply tenant filter using the robust hook
        stmt = cls._apply_tenant_filter(stmt)

        return stmt

    @classmethod
    def _apply_tenant_filter(cls, stmt):
        """
        Applies tenant isolation to the query.
        This method is robust against MRO issues and ensures Fail-Secure behavior.
        """
        from eden.tenancy.context import get_current_tenant_id

        tenant_id = get_current_tenant_id()

        if tenant_id is None:
            # FAIL-SECURE: If tenant context is missing, deny access explicitly.
            # This prevents data leakage in background tasks or misconfigured middleware.
            # To bypass for background tasks, use Project.all(session, include_tenantless=True)
            # or query directly with a session that has no context.
            from sqlalchemy import false

            return stmt.where(false())

        return stmt.where(cls.tenant_id == tenant_id)

    async def before_create(self, session):
        """Auto-set tenant_id from context if not already set."""
        from eden.tenancy.context import get_current_tenant_id

        if not self.tenant_id:
            tenant_id = get_current_tenant_id()
            if tenant_id:
                self.tenant_id = tenant_id

        # Preserve hook chaining
        if hasattr(super(), "before_create"):
            await super().before_create(session)
