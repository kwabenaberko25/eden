"""
Eden — Tenancy Testing Utilities

Provides fixtures and context managers for mocking tenant environments 
during integration testing.
"""

from contextlib import contextmanager
from typing import Generator
import uuid

from eden.tenancy.models import Tenant
from eden.tenancy.context import _tenant_ctx


@contextmanager
def mock_tenant(
    name: str = "Test Corp",
    slug: str = "test-corp",
    plan: str = "test",
    schema_name: str | None = None,
    tenant_id: str | uuid.UUID | None = None
) -> Generator[Tenant, None, None]:
    """
    Context manager that creates a mock Tenant instance and temporarily
    injects it into the active execution context.

    This bypasses the need for the TenantMiddleware to resolve the tenant,
    allowing unit/integration tests to run in isolation.

    Args:
        name: Organization name for the mock tenant.
        slug: The routing slug.
        plan: Subscription plan.
        schema_name: Target postgres schema. Defaults to 'tenant_test'.
        tenant_id: The UUID for the tenant. If None, one is generated.

    Yields:
        Tenant: The constructed mock tenant instance.
    """
    # Build the mock tenant
    tenant = Tenant(
        id=tenant_id or uuid.uuid4(),
        name=name,
        slug=slug,
        plan=plan,
        schema_name=schema_name or f"tenant_{slug.replace('-', '_')}",
        is_active=True
    )

    # Inject into context
    token = _tenant_ctx.set(tenant)
    try:
        yield tenant
    finally:
        _tenant_ctx.reset(token)

