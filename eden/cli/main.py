"""
Eden CLI — Command-line interface for the Eden framework.

Commands:
    eden run       — Start the development server
    eden new       — Scaffold a new Eden project
    eden version   — Print Eden version
    eden db        — Database management (init, migrate, upgrade, downgrade)
    eden auth      — Authentication management (createsuperuser, changepassword)
    eden generate  — Code generation (model, form, resource)
    eden tasks     — Task queue management (worker, scheduler)
    eden shell     — Start an interactive Python shell
    eden test      — Run the project test suite
    eden sync      — Synchronize database schema and assets
"""

import os
import sys

# Force UTF-8 encoding for Windows terminals to support emojis
try:
    if sys.stdout and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, Exception):
    pass

# Ensure the current directory is in sys.path so we can import the user's project files
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

import click
from pathlib import Path

import eden
from eden.cli.utils import discover_app


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
@click.option(
    "--app", "--app-path", "app_path", default=None, help="App import path (module:variable)."
)
def run(
    host: str,
    port: int,
    reload: bool,
    no_browser_reload: bool,
    workers: int,
    app_path: str | None = None,
) -> None:
    """Start the Eden development server."""
    import json
    import subprocess

    from eden.port import find_available_port

    # Smart discovery if no app path provided
    if app_path is None:
        app_path = discover_app()
        if app_path:
            click.echo(f"  📖 Using app: {app_path}")
        else:
            app_path = "app:app"
            click.echo(f"  ℹ️  No app detected, using default: {app_path}")

    # Set environment for browser reload control
    if no_browser_reload:
        os.environ["EDEN_BROWSER_RELOAD"] = "false"

    # Auto-detect an available port
    resolved_port = find_available_port(host, port)
    if resolved_port != port:
        click.echo(f"\n  ⚠️  Port {port} in use → using {resolved_port}")

    click.secho(f"\n  🌿 Eden v{eden.__version__}", fg="green", bold=True)
    click.echo(f"  📡 Running on ", nl=False)
    click.secho(f"http://{host}:{resolved_port}", fg="cyan", nl=False)
    click.echo("")
    click.echo(f"  🔄 Auto-reload: ", nl=False)
    click.secho(f"{'enabled' if reload else 'disabled'}", fg="yellow")
    click.echo("")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        app_path,
        "--host",
        host,
        "--port",
        str(resolved_port),
        "--log-level",
        "info",
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
            click.echo(
                "\n  💡 Tip: Try specifying the app instance manually: eden run --app your_file:your_app_instance"
            )


@cli.command()
def version() -> None:
    """Print the Eden framework version."""
    click.echo(f"  🌿 Eden v{eden.__version__}")


@cli.command("help")
@click.argument("command", required=False)
@click.pass_context
def help(ctx: click.Context, command: str | None) -> None:
    """Show help for Eden or a subcommand."""
    if command:
        cmd = cli.get_command(ctx, command)
        if cmd is None:
            click.echo(f"Command '{command}' not found.")
            ctx.exit(1)
        with click.Context(cmd, info_name=command, parent=ctx) as command_ctx:
            click.echo(cmd.get_help(command_ctx))
    else:
        click.echo(cli.get_help(ctx))


@cli.command()
@click.option("--app", "app_path", default=None, help="App import path.")
def shell(app_path: str | None) -> None:
    """Start an interactive Python shell with Eden context."""
    import IPython
    from traitlets.config import Config

    click.echo(f"  🌿 Eden Shell v{eden.__version__}")
    click.echo("  📜 Context: app, db, config, models, f, Q")

    # Auto-detect app if not provided
    if app_path is None:
        app_path = discover_app()

    try:
        import importlib
        from types import SimpleNamespace
        from inspect import isclass, getmembers
        from eden.db import Model, Database

        module_name, obj_name = app_path.split(":")
        module = importlib.import_module(module_name)
        app = getattr(module, obj_name)

        from eden.responses import Response, JsonResponse
        from eden.db import AsyncSession as Session
        from eden import status

        # 1. Resolve Database (Standard locations)
        db = getattr(app, "db", getattr(getattr(app, "state", None), "db", None))

        # 2. Deep Discovery fallback (look for ANY Database instance in module or app)
        if db is None:
            # Check module members
            for name, member in getmembers(module):
                if isinstance(member, Database):
                    db = member
                    break

            # If still nothing, check app members (in case it was attached but not to 'db')
            if db is None:
                for name, member in getmembers(app):
                    if isinstance(member, Database):
                        db = member
                        break

        # 3. Auto-create Database from database_url if available
        if db is None:
            database_url = getattr(app, "database_url", None) or getattr(
                getattr(app, "state", None), "database_url", None
            )
            if database_url:
                import asyncio
                from eden.db.session import init_db
                db = init_db(database_url)
                # Connect synchronously using a new event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(db.connect())
                    else:
                        loop.run_until_complete(db.connect())
                except RuntimeError:
                    asyncio.run(db.connect())

                click.echo(f"  ✓ Auto-connected to database")

        # Build context
        context = {
            "app": app,
            "db": db,
            "Session": Session,
            "config": getattr(app, "config", None),
            "f": eden.db.f,
            "Q": eden.db.Q,
            "Response": Response,
            "JsonResponse": JsonResponse,
            "status": status,
        }

        # Bind an active global session to the context for REPL await execution
        if db:
            from eden.db.session import set_session
            _shell_session = db.session_factory()
            set_session(_shell_session)
            context["session"] = _shell_session

        # 3. Resolve and Bind Models
        discovered_models = {}

        def _is_model_cls(obj):
            try:
                return isclass(obj) and issubclass(obj, Model) and obj != Model
            except Exception:
                return False

        # A. Explicit models from app
        app_models = getattr(app, "models", None)
        if app_models:
            if isinstance(app_models, dict):
                discovered_models.update({k: v for k, v in app_models.items() if _is_model_cls(v)})
            else:
                for name, member in getmembers(app_models):
                    if _is_model_cls(member):
                        discovered_models[name] = member

        # B. Implicit discovery via subclasses (Recursive) - only from user app module
        def _get_all_subclasses(cls):
            all_subs = []
            for sub in cls.__subclasses__():
                all_subs.append(sub)
                all_subs.extend(_get_all_subclasses(sub))
            return all_subs

        app_module_name = module_name.split(".")[0] if module_name else None
        for sub in _get_all_subclasses(Model):
            if not getattr(sub, "__abstract__", False) and hasattr(sub, "__tablename__"):
                sub_module = getattr(sub, "__module__", "")
                if app_module_name and not sub_module.startswith(app_module_name):
                    continue
                if sub.__name__ not in discovered_models:
                    discovered_models[sub.__name__] = sub

        # C. Critical Binding
        if db:
            # Force set on base Model
            Model._db = db

            for name, model_cls in discovered_models.items():
                # Direct bind to subclass to bypass inheritance quirks in REPL
                model_cls._db = db
                try:
                    model_cls._bind_db(db)
                except Exception as e:
                    from eden.logging import get_logger
                    get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)
                context[name] = model_cls
        else:
            # Even if no db was found, populate context with model classes
            for name, model_cls in discovered_models.items():
                context[name] = model_cls

        # Restore dot-notation access via SimpleNamespace (replaces the 'dict' version)
        context["models"] = SimpleNamespace(**discovered_models)

        # Banner and Diagnostics
        from rich.console import Console

        console = Console()

        db_banner = (
            f"[bold green]✓ Database bound:[/] [dim]{db.url}[/]"
            if db
            else "[bold yellow]⚠ No database bound. Queries may fail.[/]"
        )

        banner = (
            "\n[bold magenta]🌿 Welcome to the Eden Shell[/]\n"
            f"{db_banner}\n"
            "[dim]Pre-imported: Session, Response, JsonResponse, status[/]\n"
            "[green]Happy debugging! Type 'exit()' to leave.[/]\n"
        )
        console.print(banner)

        c = Config()
        c.InteractiveShellApp.extensions = ["eden.auth", "eden.db"]
        IPython.start_ipython(argv=[], user_ns=context, config=c)
    except Exception as e:
        click.echo(f"  ❌ Shell Error: {e}", err=True)


@cli.command()
@click.argument("files", nargs=-1)
@click.option("--fail-fast", is_flag=True, help="Stop on first failure.")
def test(files: tuple[str, ...], fail_fast: bool) -> None:
    """Run the project test suite using pytest."""
    import pytest

    args = list(files) if files else ["tests/"]
    if fail_fast:
        args.append("-x")

    click.echo(f"  🧪 Running Eden tests: {' '.join(args)}")
    sys.exit(pytest.main(args))


@cli.command()
@click.option("--all-tenants", is_flag=True, help="Sync all tenant schemas.")
def sync(all_tenants: bool) -> None:
    """Synchronize database schema and core assets."""
    from eden.cli.db import db_migrate, db_check

    click.echo("  🔄 Synchronizing Eden environment...")

    # Pass context to db_check and db_migrate
    ctx = click.get_current_context()

    click.echo("  🕵️  Checking for schema drift...")
    ctx.invoke(db_check)

    click.echo(f"  ⬆️  Applying migrations{' (all tenants)' if all_tenants else ''}...")
    ctx.invoke(db_migrate, all_tenants=all_tenants)

    click.echo("  ✅ Environment synchronized.")


# ────────────────────────────────────────────────────────────────────────────
# Command Groups — Consolidated sub-commands
# ────────────────────────────────────────────────────────────────────────────

# Import sub-command groups
from eden.cli.db import db
from eden.cli.auth import auth
from eden.cli.tasks import tasks
from eden.cli.forge import generate
from eden.cli.new import new
from eden.cli.doctor import doctor
from eden.cli.tenant import tenant

# Register command groups
cli.add_command(db)
cli.add_command(auth)
cli.add_command(tasks)
cli.add_command(generate, name="generate")
cli.add_command(generate, name="forge")
cli.add_command(new)
cli.add_command(doctor)
cli.add_command(tenant)


if __name__ == "__main__":
    cli()
