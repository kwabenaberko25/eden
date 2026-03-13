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
@click.option("--profile", "profile_choice", type=click.Choice(["minimal", "standard", "production"], case_sensitive=False), default=None, help="Project profile (minimal, standard, production)")
def new(project_name: str, project_dir_raw: str | None, db_choice: str, profile_choice: str | None) -> None:
    """
    Scaffold a new Eden project.
    
    Profiles:
      minimal     - Just the essentials (app.py, models, templates)
      standard    - Recommended structure (routes, static, tests, settings)
      production  - Enterprise ready (Docker, compose, comprehensive tests)
    """
    # Resolve project directory
    if project_dir_raw and project_dir_raw == ".":
        project_dir = Path.cwd()
    elif project_dir_raw:
        project_dir = Path(project_dir_raw)
    else:
        project_dir = Path(project_name)

    if project_dir.exists() and project_dir_raw != ".":
        click.echo(f"  ❌ Directory '{project_name}' already exists.", err=True)
        sys.exit(1)

    # Determine profile
    if profile_choice is None:
        click.echo("\n  📁 Select project profile:")
        click.echo("    1. minimal     - Just the essentials (fastest to get started)")
        click.echo("    2. standard    - Recommended structure (most flexible)")
        click.echo("    3. production  - Enterprise-ready (Docker, tests, CI)")
        profile_input = click.prompt("  Choose profile", type=click.Choice(["1", "2", "3"]))
        profile_choice = ["minimal", "standard", "production"][int(profile_input) - 1]

    # Configure database
    db_url = "sqlite+aiosqlite:///db.sqlite3"
    db_driver = "aiosqlite>=0.20.0"

    if db_choice == "postgresql":
        db_url = f"postgresql+asyncpg://postgres:postgres@localhost:5432/{project_name}"
        db_driver = "asyncpg>=0.31.0"
    elif db_choice == "mysql":
        db_url = f"mysql+aiomysql://root:root@localhost:3306/{project_name}"
        db_driver = "aiomysql>=0.2.0"

    click.echo(f"\n  🌿 Creating {profile_choice} Eden project: {project_name}")

    # Create base directories
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "templates").mkdir(parents=True, exist_ok=True)

    # ────────────────────────────────────────────────────────────────────────
    # CORE FILES (all profiles)
    # ────────────────────────────────────────────────────────────────────────

    # 1. app.py
    app_py_content = f'''"""
{project_name} - Web Application
Built with Eden Framework 🌿
"""

from eden import Eden
import os

# Initialize application
app = Eden(
    title="{project_name}",
    version="1.0.0",
    secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
    debug=os.getenv("DEBUG", "true").lower() == "true"
)

# Database configuration
app.state.database_url = os.getenv("DATABASE_URL", "{db_url}")

# Middleware stack (order matters!)
app.add_middleware("security")        # Security headers first
app.add_middleware("session", secret_key=app.secret_key)
app.add_middleware("csrf")            # CSRF requires session
app.add_middleware("gzip")            # Compression
app.add_middleware("cors", allow_origins=["*"])

@app.get("/")
async def index():
    """Welcome endpoint."""
    return {{"message": "Welcome to {project_name}! 🌿"}}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {{"status": "healthy"}}

if __name__ == "__main__":
    app.run()
'''
    (project_dir / "app.py").write_text(app_py_content, encoding="utf-8")

    # 2. models.py
    models_content = '''"""
Database models for the application.
"""

from eden import Model, StringField, IntField

# Define your models here
# Example:
# class Task(Model):
#     title = StringField(max_length=200)
#     completed = IntField(default=0)
'''
    (project_dir / "models.py").write_text(models_content, encoding="utf-8")

    # 3. .env.example
    env_content = f'''# Eden Application Environment Variables
DEBUG=true
SECRET_KEY=your-super-secret-key-here
DATABASE_URL={db_url}
'''
    (project_dir / ".env.example").write_text(env_content, encoding="utf-8")

    # 4. .gitignore
    gitignore_content = '''__pycache__/
*.pyc
*.pyo
.env
.venv/
venv/
env/
*.sqlite3
*.db
dist/
build/
*.egg-info/
.DS_Store
.idea/
.vscode/
'''
    (project_dir / ".gitignore").write_text(gitignore_content, encoding="utf-8")

    # 5. README.md
    readme_content = f'''# {project_name}

Built with [Eden Framework](https://eden-framework.dev) 🌿

## Getting Started

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

3. **Run development server**:
   ```bash
   eden run
   ```

Visit `http://localhost:8000` to see your app!

## Project Structure

```
{project_name}/
├── app.py              # Application entry point
├── models.py           # Database models
├── templates/          # HTML templates
├── .env                # Environment variables (git-ignored)
└── .env.example        # Example environment file
```

## Learn More

- [Eden Documentation](https://eden-framework.dev)
- [Quick Start Guide](https://eden-framework.dev/docs/getting-started)
'''
    (project_dir / "README.md").write_text(readme_content, encoding="utf-8")

    # 6. requirements.txt (profile-dependent)
    reqs = ["eden-framework>=0.1.0", "uvicorn[standard]>=0.29.0", db_driver]
    (project_dir / "requirements.txt").write_text("\n".join(reqs), encoding="utf-8")

    # 7. eden.json (configuration metadata)
    eden_json_content = f'''{{
  "name": "{project_name}",
  "version": "1.0.0",
  "profile": "{profile_choice}",
  "database_engine": "{db_choice}",
  "created_with_eden": "1.0.0"
}}
'''
    (project_dir / "eden.json").write_text(eden_json_content, encoding="utf-8")

    # ────────────────────────────────────────────────────────────────────────
    # STANDARD & PRODUCTION PROFILE FILES
    # ────────────────────────────────────────────────────────────────────────

    if profile_choice in ("standard", "production"):
        # Create additional directories
        (project_dir / "routes").mkdir(parents=True, exist_ok=True)
        (project_dir / "static").mkdir(parents=True, exist_ok=True)
        (project_dir / "tests").mkdir(parents=True, exist_ok=True)

        # routes/__init__.py
        routes_content = f'''"""
Application routes.
"""

from eden import Router

main_router = Router()

@main_router.get("/")
async def index():
    return {{"message": "Welcome to {project_name}! 🌿"}}

@main_router.get("/health")
async def health():
    return {{"status": "healthy"}}
'''
        (project_dir / "routes" / "__init__.py").write_text(routes_content, encoding="utf-8")

        # settings.py
        settings_content = '''"""
Application settings and configuration.
"""

import os

# Core
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "text" if DEBUG else "json")

# Security
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
'''
        (project_dir / "settings.py").write_text(settings_content, encoding="utf-8")

        # tests/conftest.py
        conftest_content = '''"""
Test configuration and fixtures.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app import app

@pytest.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

@pytest.fixture
async def async_client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
'''
        (project_dir / "tests" / "conftest.py").write_text(conftest_content, encoding="utf-8")

        # tests/__init__.py (empty, makes tests a package)
        (project_dir / "tests" / "__init__.py").write_text("", encoding="utf-8")

        # tests/test_api.py
        test_api_content = '''"""
API tests.
"""

import pytest

@pytest.mark.asyncio
async def test_index(client):
    """Test index endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_health(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
'''
        (project_dir / "tests" / "test_api.py").write_text(test_api_content, encoding="utf-8")

        # Create templates directory with example template
        index_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Welcome</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            min-height: 100vh;
        }
        h1 {
            font-size: 2.5rem;
            margin: 0 0 10px 0;
        }
        p { margin: 0 0 20px 0; }
        code {
            background: rgba(255,255,255,0.1);
            padding: 2px 6px;
            border-radius: 3px;
        }
        a {
            color: #fff;
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>🌿 Welcome to Eden</h1>
    <p>Your application is running!</p>
    <p>Edit <code>app.py</code> to start building your app.</p>
    <p><a href="https://eden-framework.dev">Learn more →</a></p>
</body>
</html>
'''
        (project_dir / "templates" / "index.html").write_text(index_template, encoding="utf-8")

    # ────────────────────────────────────────────────────────────────────────
    # PRODUCTION PROFILE FILES
    # ────────────────────────────────────────────────────────────────────────

    if profile_choice == "production":
        # Dockerfile
        dockerfile_content = f'''# Multi-stage build
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application
COPY . .

# Create non-root user
RUN adduser --disabled-password --no-create-home eden
USER eden

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["eden", "run", "--host", "0.0.0.0", "--no-reload"]
'''
        (project_dir / "Dockerfile").write_text(dockerfile_content, encoding="utf-8")

        # docker-compose.yml
        db_service_yaml = ""
        db_env_yaml = ""
        db_depends_yaml = ""
        volumes_yaml = ""

        if db_choice == "postgresql":
            db_service_yaml = f'''  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: {project_name}
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
'''
            db_env_yaml = f"      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/{project_name}\n"
            db_depends_yaml = "    depends_on:\n      db:\n        condition: service_healthy\n"
            volumes_yaml = "\nvolumes:\n  pgdata:\n"

        elif db_choice == "mysql":
            db_service_yaml = f'''  db:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: {project_name}
      MYSQL_ROOT_PASSWORD: root
    ports:
      - "3306:3306"
    volumes:
      - mysqldata:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
'''
            db_env_yaml = f"      DATABASE_URL: mysql+aiomysql://root:root@db:3306/{project_name}\n"
            db_depends_yaml = "    depends_on:\n      db:\n        condition: service_healthy\n"
            volumes_yaml = "\nvolumes:\n  mysqldata:\n"

        docker_compose_content = f'''services:
  web:
    build: .
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      DEBUG: "false"
      SECRET_KEY: "change-me-in-production"
{db_env_yaml}{db_depends_yaml}{db_service_yaml}{volumes_yaml}'''
        (project_dir / "docker-compose.yml").write_text(docker_compose_content, encoding="utf-8")

        # .dockerignore
        dockerignore_content = '''__pycache__/
*.pyc
.env
*.sqlite3
.venv/
venv/
.git/
.github/
.gitignore
README.md
*.md
tests/
.dockerignore
Dockerfile
docker-compose.yml
.pytest_cache/
.ruff_cache/
'''
        (project_dir / ".dockerignore").write_text(dockerignore_content, encoding="utf-8")

        # Update requirements.txt with test dependencies
        reqs = ["eden-framework>=0.1.0", "uvicorn[standard]>=0.29.0", db_driver, "pytest>=8.0", "pytest-asyncio>=0.23.0", "httpx>=0.27.0"]
        (project_dir / "requirements.txt").write_text("\n".join(reqs), encoding="utf-8")

    # ────────────────────────────────────────────────────────────────────────
    # SUCCESS MESSAGE
    # ────────────────────────────────────────────────────────────────────────

    click.echo(f"  ✨ Project '{project_name}' created successfully!")
    click.echo(f"  📋 Profile: {profile_choice}")
    click.echo(f"  🗄️  Database: {db_choice}")

    next_steps = f"""
  🚀 Get started:
      cd {project_name if project_dir_raw != '.' else '..'}
      pip install -r requirements.txt
      eden run

  📚 Next steps:
      - Edit app.py to add routes
      - Create models in models.py
      - Add HTML templates in templates/
      - Run tests: pytest (for standard/production profiles only)
"""
    if profile_choice == "production":
        next_steps += "      - Deploy with Docker: docker-compose up\n"

    click.echo(next_steps)


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

# Register command groups
cli.add_command(db)
cli.add_command(auth)
cli.add_command(tasks)
cli.add_command(generate)


if __name__ == "__main__":
    cli()
