"""
Eden CLI — Main entry point.

Commands:
    eden run       — Start the development server
    eden new       — Scaffold a new Eden project
    eden version   — Print Eden version
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
    import subprocess
    from pathlib import Path

    from eden.port import find_available_port

    # Smart discovery if no app path provided
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
        else:
            # Fallback to default if nothing found to avoid breaking changes, but warn
            app_path = "app:app"

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
        # Exclude noisy files that cause reload loops (like the DB or venv)
        cmd.extend(["--reload-exclude", "*.sqlite3"])
        cmd.extend(["--reload-exclude", ".venv"])
        cmd.extend(["--reload-exclude", ".git"])
        cmd.extend(["--reload-exclude", "__pycache__"])

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
@click.argument("project_name")
@click.argument("project_dir_raw", required=False, default=None)
@click.option("--db", "db_choice", type=click.Choice(["sqlite", "postgresql", "mysql"], case_sensitive=False), default="sqlite", help="Primary database engine")
def new(project_name: str, project_dir_raw: str | None, db_choice: str) -> None:
    """Scaffold a premium Eden project."""
    if project_dir_raw and project_dir_raw == ".":
        project_dir = Path.cwd()
    elif project_dir_raw:
        project_dir = Path(project_dir_raw)
    else:
        project_dir = Path(project_name)

    if project_dir.exists() and project_dir_raw != ".":
        click.echo(f"  ❌ Directory '{project_name}' already exists.", err=True)
        sys.exit(1)


    # Configure Database Drivers and Default URLs
    db_url = "sqlite+aiosqlite:///db.sqlite3"
    db_driver = "aiosqlite>=0.20.0\n"

    if db_choice == "postgresql":
        db_url = f"postgresql+asyncpg://postgres:postgres@localhost:5432/{project_name}"
        db_driver = "asyncpg>=0.29.0\n"
    elif db_choice == "mysql":
        db_url = f"mysql+aiomysql://root:root@localhost:3306/{project_name}"
        db_driver = "aiomysql>=0.2.0\n"

    click.echo(f"\n  🌿 Creating premium Eden project: {project_name}")

    # Create directory structure
    (project_dir / "routes").mkdir(parents=True, exist_ok=True)
    (project_dir / "static").mkdir(parents=True, exist_ok=True)
    (project_dir / "templates").mkdir(parents=True, exist_ok=True)
    (project_dir / "tests").mkdir(parents=True, exist_ok=True)

    # 1. app.py (The heart of the app)
    app_py = f'''from eden import Eden
from eden.middleware import get_middleware_class
import os

# 1. Initialize with Premium Branding
app = Eden(
    title="{project_name}",
    version="1.0.0",
    secret_key="your-ultra-secure-key", # Required for Session & CSRF
    debug=True
)

# 2. Database Configuration (The "Auto" Way)
# By setting this in state, Eden auto-initializes the ORM 
# and handles connections/disconnections in the lifespan hooks.
app.state.database_url = "sqlite+aiosqlite:///database.db"

# 3. Setting Up the Middleware Stack
# Order matters: RequestContext should always be first (Eden adds this automatically)

# 🔒 Security Headers (XSS, Clickjacking, HSTS)
app.add_middleware("security")

# 🍪 Session Management
app.add_middleware("session", secret_key=app.secret_key)

# 🛡️ CSRF Protection (Requires Session middleware above it)
app.add_middleware("csrf")

# 🚀 Compression (Speed up responses)
app.add_middleware("gzip")

# 🌐 CORS (If building an API)
app.add_middleware("cors", allow_origins=["*"])

@app.get("/")
async def welcome():
    return {{"status": "Eden is online", "database": "Connected ⚡"}}

if __name__ == "__main__":
    app.run()
'''
    (project_dir / "app.py").write_text(app_py, encoding="utf-8")

    # 2. routes/__init__.py
    routes_init = f'''from eden import Router

main_router = Router()

@main_router.get("/")
async def index():
    return {{"message": "Welcome to {project_name}! 🌿"}}

@main_router.get("/health")
async def health():
    return {{"status": "healthy"}}
'''
    (project_dir / "routes" / "__init__.py").write_text(routes_init, encoding="utf-8")

    # 3. models.py (Flat models starting point)
    models_content = '''from eden import Model, StringField, IntField

# Define your models here!
# class Task(Model):
#     title = StringField(max_length=100)
#     completed = IntField(default=0)
'''
    (project_dir / "models.py").write_text(models_content, encoding="utf-8")

    # 4. settings.py
    settings_content = '''import os

# ── Core ─────────────────────────────────────────────────────────────────
DEBUG = os.getenv("EDEN_DEBUG", "true").lower() == "true"
SECRET_KEY = os.getenv("EDEN_SECRET_KEY", "generate-a-secure-key-for-prod")
DATABASE_URL = os.getenv("DATABASE_URL", "''' + db_url + '''")

# ── Security ─────────────────────────────────────────────────────────────
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# ── Logging ──────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "text" if DEBUG else "json")
'''
    (project_dir / "settings.py").write_text(settings_content, encoding="utf-8")

    # 5. Dockerfile (multi-stage)
    dockerfile = '''# ── Build Stage ─────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime Stage ───────────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Non-root user for security
RUN adduser --disabled-password --no-create-home eden
USER eden

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["eden", "run", "--host", "0.0.0.0", "--no-reload", "--app", "app:app"]
'''
    (project_dir / "Dockerfile").write_text(dockerfile, encoding="utf-8")

    # 6. docker-compose.yml (with DB service)
    db_service = ""
    db_env = ""
    db_depends = ""

    if db_choice == "postgresql":
        db_service = f'''  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: {project_name}
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
'''
        db_env = f'      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/{project_name}'
        db_depends = '''    depends_on:
      - db
'''
    elif db_choice == "mysql":
        db_service = f'''  db:
    image: mysql:8.0
    restart: unless-stopped
    environment:
      MYSQL_DATABASE: {project_name}
      MYSQL_ROOT_PASSWORD: root
    ports:
      - "3306:3306"
    volumes:
      - mysqldata:/var/lib/mysql
'''
        db_env = f'      DATABASE_URL: mysql+aiomysql://root:root@db:3306/{project_name}'
        db_depends = '''    depends_on:
      - db
'''

    volumes_section = ""
    if db_choice == "postgresql":
        volumes_section = "\nvolumes:\n  pgdata:\n"
    elif db_choice == "mysql":
        volumes_section = "\nvolumes:\n  mysqldata:\n"

    docker_compose = f'''services:
  web:
    build: .
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      EDEN_DEBUG: "true"
      EDEN_SECRET_KEY: "change-me-in-production"
{db_env}
{db_depends}
{db_service}{volumes_section}'''
    (project_dir / "docker-compose.yml").write_text(docker_compose, encoding="utf-8")

    # 6b. .dockerignore
    dockerignore = '''__pycache__/
*.pyc
.env
*.sqlite3
.venv/
venv/
.git/
.github/
tests/
*.md
.dockerignore
Dockerfile
docker-compose.yml
'''
    (project_dir / ".dockerignore").write_text(dockerignore, encoding="utf-8")

    # 6c. .env.example
    env_example = f'''# Eden Environment Variables
EDEN_DEBUG=true
EDEN_SECRET_KEY=generate-a-secure-key-for-prod
DATABASE_URL={db_url}
LOG_LEVEL=INFO
LOG_FORMAT=text
ALLOWED_HOSTS=*
'''
    (project_dir / ".env.example").write_text(env_example, encoding="utf-8")

    # 7. tests/conftest.py
    conftest = '''import pytest
from httpx import ASGITransport, AsyncClient
from app import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
'''
    (project_dir / "tests" / "conftest.py").write_text(conftest, encoding="utf-8")

    # 8. tests/test_api.py
    test_api = '''import pytest

@pytest.mark.asyncio
async def test_index(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Welcome" in resp.json()["message"]
'''
    (project_dir / "tests" / "test_api.py").write_text(test_api, encoding="utf-8")

    # 9. requirements.txt
    reqs = f"eden-framework>=0.1.0\nuvicorn[standard]>=0.29.0\npytest>=8.0.0\npytest-asyncio>=0.23.0\n{db_driver}"
    (project_dir / "requirements.txt").write_text(reqs, encoding="utf-8")

    # 10. .gitignore
    gitignore = "__pycache__/\n*.pyc\n.env\n*.sqlite3\n.venv/\nvenv/\ndist/\n*.egg-info/\n"
    (project_dir / ".gitignore").write_text(gitignore, encoding="utf-8")

    # 11. README.md
    readme = f'''# {project_name}

Built with [Eden](https://github.com/eden-framework/eden) 🌿

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Run server: `eden run`
3. Run tests: `pytest`

## Docker

`docker-compose up`
'''
    (project_dir / "README.md").write_text(readme, encoding="utf-8")

    click.echo(f"  ✨ Project '{project_name}' scaffolded with premium features.")
    click.echo("  🐋 Docker & 🧪 Pytest integrated.")
    click.echo("\n  🚀 Get started:")
    if project_dir_raw != ".":
        click.echo(f"      cd {project_name}")
    click.echo("      eden run\n")


@cli.command()
def version() -> None:
    """Print the Eden version."""
    click.echo(f"🌿 Eden v{eden.__version__}")


# ── Auth Commands ────────────────────────────────────────────────────────


from eden.cli.auth import auth as auth_cli
from eden.cli.db import db as db_cli
from eden.cli.forge import generate as generate_cli
from eden.cli.tasks import scheduler, worker

cli.add_command(auth_cli)
cli.add_command(db_cli)
cli.add_command(generate_cli, name="generate")
cli.add_command(generate_cli, name="forge")
cli.add_command(worker)
cli.add_command(scheduler)


if __name__ == "__main__":
    cli()
