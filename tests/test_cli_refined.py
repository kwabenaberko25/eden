import tempfile
from pathlib import Path
from click.testing import CliRunner
from eden.cli.new import generate_complete, generate_minimal
from eden.cli.forge import generate as forge_generate

def test_requirements_with_extras():
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        extras = ["Payments (Stripe)", "Chats/Websockets", "Mail Support"]
        
        # Test Complete
        generate_complete(project_path, "test_complete", "Postgres", extras)
        reqs = (project_path / "requirements.txt").read_text()
        assert "stripe" in reqs
        assert "websockets" in reqs
        assert "aiosmtplib" in reqs
        assert "asyncpg" in reqs
        
        # Clear and Test Minimal
        for f in project_path.iterdir():
            if f.is_file(): f.unlink()
            else: import shutil; shutil.rmtree(f)
            
        generate_minimal(project_path, "test_minimal", "SQLite", extras)
        reqs = (project_path / "requirements.txt").read_text()
        assert "stripe" in reqs
        assert "websockets" in reqs
        assert "aiosmtplib" in reqs
        assert "aiosqlite" in reqs

def test_forge_model_refined():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Mock a flat layout project
        project_path = Path(tmp_dir)
        (project_path / "models.py").write_text("from eden.db import Model, f\n", encoding="utf-8")
        
        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_dir)
        try:
            result = runner.invoke(forge_generate, ["model", "UserAccount"])
            assert result.exit_code == 0
            
            content = (project_path / "models.py").read_text()
            assert "class UserAccount(Model):" in content
            assert "__tablename__ = \"user_accounts\"" in content
            assert "def __repr__(self) -> str:" in content
        finally:
            os.chdir(old_cwd)

def test_forge_route_refined():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        (project_path / "routes").mkdir()
        (project_path / "routes" / "__init__.py").write_text("from eden import Router\nmain_router = Router()\n", encoding="utf-8")
        
        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_dir)
        try:
            result = runner.invoke(forge_generate, ["route", "Billing"])
            assert result.exit_code == 0
            
            route_file = project_path / "routes" / "billing.py"
            assert route_file.exists()
            content = route_file.read_text()
            assert "async def index() -> Dict[str, Any]:" in content
            assert '"status": "ok"' in content
            assert "billing_router" in content
        finally:
            os.chdir(old_cwd)
