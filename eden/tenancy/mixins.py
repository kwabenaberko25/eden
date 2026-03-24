"""
Eden — Tenant Mixin

Add to any Model to scope it to the current tenant.
Automatically filters queries and sets tenant_id on create.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from eden.db import f


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
    def _apply_default_filters(cls, target_cls: type, stmt: Any, **kwargs: Any) -> Any:
        """Cooperative filter hook for tenant isolation."""
        return cls._apply_tenant_filter(target_cls, stmt, **kwargs)

    @classmethod
    def _apply_tenant_filter(cls, target_cls, stmt, **kwargs):
        """
        Applies tenant isolation to the query using Fail-Secure logic.
        """
        from sqlalchemy import false
        from eden.tenancy.context import get_current_tenant_id, is_across_tenants

        # Skip if explicitly requested (via kwarg or AcrossTenants context manager)
        if kwargs.get("include_tenantless", False) or is_across_tenants():
            return stmt

        tenant_id = get_current_tenant_id()
        if tenant_id is None:
            from eden.tenancy.registry import tenancy_registry
            from eden.tenancy.exceptions import TenancyIsolationError
            
            if tenancy_registry.strict_mode:
                raise TenancyIsolationError(
                    f"Attempted to query tenant-isolated model {target_cls.__name__} "
                    "without a valid tenant context in strict mode."
                )
            
            # FAIL-SECURE: Return empty result if no tenant in context
            return stmt.where(false())

        return stmt.where(getattr(target_cls, "tenant_id") == tenant_id)

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

    def get_sync_channels(self) -> list[str]:
        """Return tenant-scoped channels for this instance."""
        table = getattr(self, "__tablename__")
        return [
            f"tenant:{self.tenant_id}:{table}",
            f"tenant:{self.tenant_id}:{table}:{self.id}"
        ]


class OrganizationMixin:
    """
    Mixin that adds organization-level isolation to any Model.
    """

    __eden_org_isolated__ = True
    __allow_unmapped__ = True

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)

    @classmethod
    def _apply_default_filters(cls, target_cls: type, stmt: Any, **kwargs: Any) -> Any:
        """Cooperative filter hook for organization isolation."""
        # Mixins can chain filters
        if hasattr(super(), "_apply_default_filters"):
            stmt = super()._apply_default_filters(target_cls, stmt, **kwargs)
        return cls._apply_organization_filter(target_cls, stmt, **kwargs)

    @classmethod
    def _apply_organization_filter(cls, target_cls, stmt, **kwargs):
        """
        Applies organization isolation to the query.
        """
        from sqlalchemy import false
        from eden.context import get_organization_id

        # Skip if explicitly requested
        if kwargs.get("include_all_orgs", False):
            return stmt

        org_id = get_organization_id()
        if org_id is None:
            # FAIL-SECURE: Return empty result if no organization in context
            return stmt.where(false())

        return stmt.where(getattr(target_cls, "organization_id") == org_id)

    async def before_create(self, session):
        """Auto-set organization_id from context."""
        from eden.context import get_organization_id

        if not getattr(self, "organization_id", None):
            org_id = get_organization_id()
            if org_id:
                self.organization_id = org_id

        if hasattr(super(), "before_create"):
            await super().before_create(session)

    def get_sync_channels(self) -> list[str]:
        """Return org-scoped channels for this instance."""
        table = getattr(self, "__tablename__")
        return [
            f"org:{self.organization_id}:{table}",
            f"org:{self.organization_id}:{table}:{self.id}"
        ]
