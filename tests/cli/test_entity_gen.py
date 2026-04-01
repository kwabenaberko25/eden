import os
import shutil
from pathlib import Path
from click.testing import CliRunner
from eden.cli.forge import generate


def test_generate_model_flat_layout():
    """Test generating a model in a flat project layout."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Setup: A project without an 'app' directory is considered 'flat'
        result = runner.invoke(generate, ["model", "User"])

        assert result.exit_code == 0
        assert "Updated model: models.py" in result.output

        models_file = Path("models.py")
        assert models_file.exists()
        content = models_file.read_text()
        assert "class User(Model):" in content
        assert "from eden.db import Model, f" in content


def test_generate_model_package_layout():
    """Test generating a model in a package (app/) project layout."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Setup: Create app/models directory
        os.makedirs("app/models")
        Path("app/models/__init__.py").touch()

        result = runner.invoke(generate, ["model", "Profile"])

        assert result.exit_code == 0
        assert "Created model: app/models/profile.py" in result.output

        model_file = Path("app/models/profile.py")
        assert model_file.exists()
        content = model_file.read_text()
        assert "class Profile(Model):" in content

        init_content = Path("app/models/__init__.py").read_text()
        assert "from .profile import Profile" in init_content


def test_generate_entity_package_layout():
    """Test generating a full entity stack (model, schema, router)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Setup
        os.makedirs("app/models")
        os.makedirs("app/schemas")
        os.makedirs("app/routes")
        Path("app/models/__init__.py").touch()
        Path("app/schemas/__init__.py").touch()
        Path("app/routes/__init__.py").touch()

        result = runner.invoke(generate, ["entity", "Product"])

        assert result.exit_code == 0
        assert "Created model: app/models/product.py" in result.output
        assert "Created schema: app.schemas/product.py" in result.output
        assert "Created router: app.routes/product.py" in result.output

        # Verify Model
        assert Path("app/models/product.py").exists()
        # Verify Schema
        assert Path("app/schemas/product.py").exists()
        schema_content = Path("app/schemas/product.py").read_text()
        assert "class ProductBase(Schema):" in schema_content
        # Verify Router
        assert Path("app/routes/product.py").exists()
        router_content = Path("app/routes/product.py").read_text()
        assert "product_router = Router()" in router_content
        assert "from app.models.product import Product" in router_content


def test_generate_route_auto_registration():
    """Test that generating a route updates the routes/__init__.py for auto-registration."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        os.makedirs("app/routes")
        init_file = Path("app/routes/__init__.py")
        init_file.write_text("from eden import Router\nmain_router = Router()\n")

        result = runner.invoke(generate, ["router", "Billing"])

        assert result.exit_code == 0
        assert "Created route: app/routes/billing.py" in result.output

        init_content = init_file.read_text()
        assert "from .billing import billing_router" in init_content
        assert "main_router.include_router(billing_router)" in init_content
