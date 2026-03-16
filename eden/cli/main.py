"""
Eden CLI — Command-line interface for the Eden framework.

Commands:
    eden run       — Start the development server
    eden new       — Scaffold a new Eden project
    eden version   — Print Eden version
    eden db        — Database management (init, migrate, upgrade, downgrade)
    eden auth      — Authentication management (createsuperuser)
    eden generate  — Code generation (model, form, resource)
    eden tasks     — Task queue management (worker, scheduler)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

import eden


@click.group()
def cli() -> None:
    """🌿 Eden — A batteries-included async Python web framework."""
    pass


@cli.command()
@click.option("--host", default="127.0.0.1", help="Bind address.")
@click.option("--port", default=8000, type=int, help="Bind port.")
@click.option("--reload/--no-reload", default=True, help="Enable auto-reload.")
@click.option("--no-browser-reload", is_flag=True, help="Disable browser auto-reload.")
@click.option("--workers", default=1, type=int, help="Number of workers.")
@click.option("--app", "--app-path", "app_path", default=None, help="App import path (module:variable).")
def run(host: str, port: int, reload: bool, no_browser_reload: bool, workers: int, app_path: str | None) -> None:
    """Start the Eden development server."""
    import json
    import subprocess

    from eden.port import find_available_port

    # Smart discovery if no app path provided
    if app_path is None:
        # First check if eden.json has a saved app_path
        eden_json_path = Path("eden.json")
        if eden_json_path.exists():
            try:
                config = json.loads(eden_json_path.read_text(encoding="utf-8"))
                app_path = config.get("app_path")
                if app_path:
                    click.echo(f"  📖 Using app from eden.json: {app_path}")
            except (json.JSONDecodeError, KeyError):
                app_path = None

        # If not found in eden.json, auto-detect
        if app_path is None:
            discovery_order = ["app.py", "main.py", "nexus.py", "run.py"]
            found_file = None
            for filename in discovery_order:
                if Path(filename).exists():
                    content = Path(filename).read_text(encoding="utf-8")
                    if "app = Eden(" in content or "app: Eden =" in content or "app = create_app" in content:
                        found_file = filename
                        break
            
            if found_file:
                module_name = Path(found_file).stem
                app_path = f"{module_name}:app"
                click.echo(f"  🔍 Auto-detected app entry: {app_path}")
                
                # Update eden.json with discovered app_path
                if eden_json_path.exists():
                    try:
                        config = json.loads(eden_json_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        config = {}
                else:
                    config = {}
                
                config["app_path"] = app_path
                eden_json_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
                click.echo(f"  💾 Saved to eden.json for faster startup")
            else:
                # Fallback to default if nothing found
                app_path = "app:app"
                click.echo(f"  ℹ️  No app detected, using default: {app_path}")

    # Set environment for browser reload control
    if no_browser_reload:
        os.environ["EDEN_BROWSER_RELOAD"] = "false"

    # Auto-detect an available port
    resolved_port = find_available_port(host, port)
    if resolved_port != port:
        click.echo(f"\n  ⚠️  Port {port} in use → using {resolved_port}")

    click.echo(f"\n  🌿 Eden v{eden.__version__}")
    click.echo(f"  📡 Running on http://{host}:{resolved_port}")
    click.echo(f"  🔄 Auto-reload: {'enabled' if reload else 'disabled'}\n")

    cmd = [
        sys.executable, "-m", "uvicorn", app_path,
        "--host", host,
        "--port", str(resolved_port),
        "--log-level", "info",
    ]
    if reload:
        cmd.append("--reload")
        # Ensure templates also trigger a reload
        cmd.extend(["--reload-dir", "."])
        cmd.extend(["--reload-include", "*.html"])
        cmd.extend(["--reload-include", "*.j2"])
        cmd.extend(["--reload-include", "*.css"])
        cmd.extend(["--reload-include", "*.js"])
        cmd.extend(["--reload-include", "*.env"])
        cmd.extend(["--reload-include", "*.yaml"])
        cmd.extend(["--reload-include", "*.yml"])
        cmd.extend(["--reload-include", "*.json"])
        cmd.extend(["--reload-include", "*.ini"])
        # Exclude noisy files that cause reload loops
        cmd.extend(["--reload-exclude", "eden.json"])
        cmd.extend(["--reload-exclude", "*.sqlite*"])
        cmd.extend(["--reload-exclude", "*.db"])
        cmd.extend(["--reload-exclude", "*.log"])
        cmd.extend(["--reload-exclude", "*.tmp"])
        cmd.extend(["--reload-exclude", "*.bak"])
        cmd.extend(["--reload-exclude", ".venv"])
        cmd.extend(["--reload-exclude", ".git"])
        cmd.extend(["--reload-exclude", ".pytest_cache"])
        cmd.extend(["--reload-exclude", ".ruff_cache"])
        cmd.extend(["--reload-exclude", ".mypy_cache"])
        cmd.extend(["--reload-exclude", ".idea"])
        cmd.extend(["--reload-exclude", ".vscode"])
        cmd.extend(["--reload-exclude", "__pycache__"])
        cmd.extend(["--reload-exclude", "node_modules"])
        cmd.extend(["--reload-exclude", "site-packages"])
        cmd.extend(["--reload-exclude", "logs"])

    if workers > 1:
        cmd.extend(["--workers", str(workers)])

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        click.echo(f"  ❌ Error: {e}", err=True)
        if "Could not import module" in str(e) and ":" not in app_path:
             click.echo("\n  💡 Tip: Try specifying the app instance manually: eden run --app your_file:your_app_instance")


@cli.command()
def version() -> None:
    """Print Eden version."""
    click.echo(f"🌿 Eden Framework v{eden.__version__}")


# ────────────────────────────────────────────────────────────────────────────
# Command Groups — Consolidated sub-commands
# ────────────────────────────────────────────────────────────────────────────

# Import sub-command groups
from eden.cli.db import db
from eden.cli.auth import auth
from eden.cli.tasks import tasks
from eden.cli.forge import generate
from eden.cli.new import new

# Register command groups
cli.add_command(db)
cli.add_command(auth)
cli.add_command(tasks)
cli.add_command(generate, name="generate")
cli.add_command(generate, name="forge")
cli.add_command(new)


if __name__ == "__main__":
    cli()
