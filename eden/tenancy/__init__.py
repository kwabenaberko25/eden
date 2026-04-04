"""
Eden — Multi-Tenancy Package

Row-level tenant isolation for SaaS applications.
"""

from .context import (
    get_current_tenant,
    get_current_tenant_id,
    reset_current_tenant,
    set_current_tenant,
    AcrossTenants,
    is_across_tenants,
    spawn_safe_task,
)
from .decorators import tenant_required
from .middleware import TenantMiddleware
from .models import AnonymousTenant, Tenant
from .mixins import TenantMixin, OrganizationMixin
from .testing import mock_tenant
from .signals import (
    tenant_created,
    tenant_schema_provisioned,
    tenant_deactivated,
    tenant_deleted,
)


__all__ = [
    "Tenant",
    "AnonymousTenant",
    "TenantMixin",
    "OrganizationMixin",
    "TenantMiddleware",
    "set_current_tenant",
    "get_current_tenant",
    "get_current_tenant_id",
    "reset_current_tenant",
    "AcrossTenants",
    "is_across_tenants",
    "spawn_safe_task",
    "tenant_required",
    "mock_tenant",
    "tenant_created",
    "tenant_schema_provisioned",
    "tenant_deactivated",
    "tenant_deleted",
]
