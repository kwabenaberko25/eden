import asyncio
import uuid
import click
from click.testing import CliRunner

from eden.tenancy.context import get_current_tenant
from eden.tenancy.testing import mock_tenant
from eden.tenancy.decorators import tenant_required
from eden.tenancy.signals import tenant_created, tenant_schema_provisioned
from eden.cli.tenant import tenant_create
from eden.exceptions import Forbidden

async def test_mock_tenant():
    print("Running test_mock_tenant...")
    assert get_current_tenant() is None
    
    with mock_tenant(name="Acme", slug="acme") as t:
        current = get_current_tenant()
        assert current is not None
        assert current.slug == "acme"
        assert current.name == "Acme"
    
    assert get_current_tenant() is None
    print("✅ mock_tenant passed")

async def test_tenant_required():
    print("Running test_tenant_required...")
    
    @tenant_required
    async def restricted_action():
        return "success"
        
    @tenant_required(allow_anonymous=True)
    async def semi_restricted():
        return "success_anon"

    # 1. No tenant -> restricted_action should fail
    try:
        await restricted_action()
        assert False, "Should have raised Forbidden"
    except Forbidden as e:
        assert "active tenant" in str(e)
        
    # 2. No tenant -> semi_restricted should pass
    res = await semi_restricted()
    assert res == "success_anon"

    # 3. With tenant -> restricted_action should pass
    with mock_tenant():
        res2 = await restricted_action()
        assert res2 == "success"

    print("✅ tenant_required passed")

async def test_signals():
    print("Running test_signals...")
    # Register receivers
    created_called = False
    
    @tenant_created.connect
    async def on_create(tenant, **kwargs):
        nonlocal created_called
        created_called = True
        assert tenant.name == "SignalCorp"
        
    # Manually fire rather than hitting DB for simple unit test
    class DummyTenant:
        name = "SignalCorp"
        
    await tenant_created.send(tenant=DummyTenant())
    assert created_called
    print("✅ signals passed")

def test_cli():
    print("Running test_cli (basic syntax check)...")
    runner = CliRunner()
    # Create requires DB, so we'll just check help syntax to make sure command loads
    result = runner.invoke(tenant_create, ["--help"])
    assert result.exit_code == 0
    assert "--name" in result.output
    assert "--slug" in result.output
    assert "--provision" in result.output
    print("✅ CLI loaded correctly")


async def main():
    await test_mock_tenant()
    await test_tenant_required()
    await test_signals()
    test_cli()
    print("All P0 verification tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
