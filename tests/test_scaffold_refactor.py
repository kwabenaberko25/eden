import os
import shutil
import tempfile
from pathlib import Path
from click.testing import CliRunner
from eden.cli.main import cli

def test_scaffold_flat_structure():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_name = "test_flat_project"
        project_path = Path(tmp_dir) / project_name
        
        # Run eden new
        result = runner.invoke(cli, ["new", project_name, str(project_path)])
        if result.exit_code != 0:
            print(f"EXIT CODE: {result.exit_code}")
            print(f"OUTPUT: {result.output}")
            if result.exception:
                import traceback
                traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
        assert result.exit_code == 0
        
        # Verify root files exist
        assert (project_path / "app.py").exists()
        assert (project_path / "models.py").exists()
        assert (project_path / "settings.py").exists()
        assert (project_path / "routes" / "__init__.py").exists()
        assert (project_path / "Dockerfile").exists()
        assert (project_path / "docker-compose.yml").exists()
        assert (project_path / "tests" / "conftest.py").exists()
        
        # Verify content of app.py refers to settings and routes correctly
        app_content = (project_path / "app.py").read_text(encoding="utf-8")
        assert "from eden import Eden" in app_content
        
        # Verify Dockerfile refers to app:app
        docker_content = (project_path / "Dockerfile").read_text(encoding="utf-8")
        assert "app:app" in docker_content

def test_scaffold_dot_directory():
    runner = CliRunner()
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Move to tmp_dir
            os.chdir(tmp_dir)
            project_name = "dot_project"
            
            # Run eden new .
            result = runner.invoke(cli, ["new", project_name, "."])
            if result.exit_code != 0:
                print(result.output)
            assert result.exit_code == 0
            
            # Verify files are in the current directory
            assert Path("app.py").exists()
            assert Path("models.py").exists()
            assert Path("settings.py").exists()
            assert Path("routes/__init__.py").exists()
        finally:
            os.chdir(original_cwd)


def test_generate_complete_extras_do_not_require_runtime_extras_variable():
    from eden.cli.new import generate_complete

    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = Path(tmp_dir)
        generate_complete(project_path, "test_project", "SQLite", ["Admin UI", "Chats/Websockets", "Mail Support"])

        content = (project_path / "app" / "__init__.py").read_text(encoding="utf-8")
        assert 'if "Chats/Websockets" in extras' not in content
        assert "ws_router" in content
        assert "app.mount_admin" in content
        assert "Mail Support" not in content  # a comment is fine, but no runtime extras needed


def test_help_command_and_root_help():
    runner = CliRunner()

    result = runner.invoke(cli, ["help"])
    assert result.exit_code == 0
    assert "Eden" in result.output

    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output

    result = runner.invoke(cli, ["help", "run"])
    assert result.exit_code == 0
    assert "Start the Eden development server" in result.output
