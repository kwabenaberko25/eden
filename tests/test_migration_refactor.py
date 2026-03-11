import pytest
from click.testing import CliRunner
from eden.cli.main import cli
from eden.orm import MigrationManager
from eden.orm import Model, f
from eden.tenancy.mixins import TenantMixin

def test_cli_structure_separation():
    """Verify that eden db and eden forge are distinct and correctly registered."""
    runner = CliRunner()
    
    # Check 'eden db'
    result = runner.invoke(cli, ["db", "--help"])
    assert result.exit_code == 0
    assert "Eden Database" in result.output
    assert "init" in result.output
    assert "generate" in result.output
    assert "migrate" in result.output
    
    # Check 'eden forge'
    result = runner.invoke(cli, ["forge", "--help"])
    assert result.exit_code == 0
    assert "Eden Generate" in result.output
    assert "model" in result.output
    assert "route" in result.output
    # Should NOT have 'init' or 'migrate' anymore
    assert "init" not in result.output
    assert "migrate" not in result.output

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Uuid

class SharedModel(Model):
    __tablename__ = "shared_table"
    name: Mapped[str] = mapped_column(String)

class IsolatedModel(TenantMixin, Model):
    __tablename__ = "tenant_table"
    data: Mapped[str] = mapped_column(String)

def test_migration_isolation_filtering():
    """Verify that MigrationManager correctly filters metadata based on isolation."""
    manager = MigrationManager("sqlite:///:memory:")
    
    # Include object filter for Shared
    shared_filter = manager._make_include_object(tenant_isolated=False)
    assert shared_filter(None, "shared_table", "table", False, None) is True
    assert shared_filter(None, "tenant_table", "table", False, None) is False
    
    # Include object filter for Tenant
    tenant_filter = manager._make_include_object(tenant_isolated=True)
    assert tenant_filter(None, "shared_table", "table", False, None) is False
    assert tenant_filter(None, "tenant_table", "table", False, None) is True
