# Eden CLI Reference

The `eden` command provides a complete toolkit for developing, deploying, and managing Eden applications.

## Table of Contents

- [Overview](#overview)
- [Global Options](#global-options)
- [Commands](#commands)
  - [`eden run`](#eden-run)
  - [`eden new`](#eden-new)
  - [`eden version`](#eden-version)
  - [`eden db`](#eden-forge)
  - [`eden auth`](#eden-auth)
  - [`eden worker`](#eden-worker)
  - [`eden scheduler`](#eden-scheduler)

---

## Overview

Eden's CLI is built on Click and provides subcommands for different aspects of application management.

```bash
# Show help
eden --help

# Show version
eden --version
```

---

## Global Options

| Option | Description |
|--------|-------------|
| `--help` | Show help message and exit |
| `--version` | Show version and exit |

---

## Commands

### `eden run`

Start the Eden development server.

```bash
eden run [OPTIONS]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--host` | Bind address | `127.0.0.1` |
| `--port` | Bind port | `8000` |
| `--reload` / `--no-reload` | Enable auto-reload | `true` |
| `--no-browser-reload` | Disable browser auto-reload | `false` |
| `--workers` | Number of workers | `1` |
| `--app` | App import path (module:variable) | auto-detect |

#### Examples

```bash
# Start server on default port
eden run

# Custom port
eden run --port 9000

# Production mode (no reload)
eden run --no-reload --workers 4

# Specify app explicitly
eden run --app myapp:app
```

#### Auto-Detection

The `run` command automatically discovers your application file. It searches for:
1. `app.py`
2. `main.py`
3. `Eden.py`
4. `run.py`

It looks for `app = Eden(` or `app: Eden =` within the file.

---

### `eden new`

Scaffold a new Eden project with a complete structure.

```bash
eden new PROJECT_NAME
```

#### Interactive Prompts

1. **Database Engine**: Choose between `sqlite`, `postgresql`, or `mysql`

#### Examples

```bash
# Create new project
eden new my_awesome_app

# After creation
cd my_awesome_app
eden run
```

#### Generated Structure

```
project_name/
├── app/
│   ├── __init__.py      # App factory
│   ├── models/          # Database models
│   ├── routes/          # Route modules
│   └── settings.py      # Configuration
├── static/              # Static files
├── templates/           # Jinja2 templates
├── tests/               # Test suite
│   ├── conftest.py
│   └── test_api.py
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── README.md
└── requirements.txt
```

#### Features Included

- Pre-configured security middleware
- Rate limiting
- Logging middleware
- Health check endpoints
- Docker & Docker Compose support
- Pytest configuration

---

### `eden version`

Print the installed Eden version.

```bash
eden version
```

Output:
```
🌿 Eden v0.1.0
```

---

### `eden db`

Database migration management. A wrapper around Alembic with Eden-friendly commands.

```bash
eden db <subcommand>
```

#### Subcommands

##### `eden db init`

Initialize the migrations directory.

```bash
eden db init [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--db-url` | Database URL | `sqlite+aiosqlite:///db.sqlite3` |

Example:
```bash
eden db init --db-url postgresql://user:pass@localhost/mydb
```

##### `eden db generate`

Generate a new migration based on model changes.

```bash
eden db generate -m "MESSAGE" [OPTIONS]
```

| Option | Description | Required |
|--------|-------------|----------|
| `-m`, `--message` | Migration message | Yes |
| `--db-url` | Database URL | No |

Example:
```bash
eden db generate -m "Add user avatar field"
eden db generate -m "Create products table" --db-url postgresql://localhost/mydb
```

##### `eden db migrate`

Apply all pending migrations.

```bash
eden db migrate [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--db-url` | Database URL | `sqlite+aiosqlite:///db.sqlite3` |

Example:
```bash
eden db migrate
```

##### `eden db upgrade`

Upgrade to a specific migration revision.

```bash
eden db upgrade [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--revision` | Target revision | `head` |
| `--db-url` | Database URL | `sqlite+aiosqlite:///db.sqlite3` |

Example:
```bash
# Upgrade to latest
eden db upgrade

# Upgrade to specific revision
eden db upgrade --revision abc123
```

##### `eden db downgrade`

Revert migrations.

```bash
eden db downgrade [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--revision` | Target revision | `-1` (previous) |
| `--db-url` | Database URL | `sqlite+aiosqlite:///db.sqlite3` |

Example:
```bash
# Revert one migration
eden db downgrade

# Revert to specific revision
eden db downgrade --revision abc123
```

##### `eden db history`

Show all migrations with their status.

```bash
eden db history [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--db-url` | Database URL | `sqlite+aiosqlite:///db.sqlite3` |

Example:
```bash
eden db history
```

---

### `eden auth`

Manage authentication (users, roles, passwords).

```bash
eden auth <subcommand>
```

#### Subcommands

##### `eden auth create-user`

Create a new user.

```bash
eden auth create-user [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--email` | User email (required) |
| `--password` | User password (required) |
| `--name` | Full name |
| `--role` | User role (can be repeated) |

Example:
```bash
eden auth create-user --email admin@example.com --password secret123 --role admin
```

##### `eden auth change-password`

Change a user's password.

```bash
eden auth change-password [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--email` | User email (required) |
| `--new-password` | New password (required) |

Example:
```bash
eden auth change-password --email admin@example.com --new-password newsecret
```

---

### `eden worker`

Start a background task worker.

```bash
eden worker [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--broker` | Broker URL | Redis URL from env |
| `--modules` | Modules to scan for tasks | Current directory |

Example:
```bash
eden worker
eden worker --broker redis://localhost:6379
```

---

### `eden scheduler`

Start the task scheduler.

```bash
eden scheduler [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--broker` | Broker URL | Redis URL from env |
| `--modules` | Modules to scan | Current directory |

Example:
```bash
eden scheduler
```

---

## Environment Variables

The CLI respects these environment variables:

| Variable | Description |
|----------|-------------|
| `EDEN_DEBUG` | Enable debug mode |
| `EDEN_SECRET_KEY` | Application secret key |
| `DATABASE_URL` | Default database URL |
| `LOG_LEVEL` | Logging level |
| `REDIS_URL` | Redis broker URL |

---

## Troubleshooting

### "Could not import module" error

If you see this error, ensure your app instance is properly exported:

```python
# Correct
app = Eden()

# Then run
eden run --app your_file:app
```

### Port already in use

Eden will automatically find an available port if the default is taken:

```
⚠️ Port 8000 in use → using 8001
```

### Migration errors

If migrations fail to generate, ensure:
1. You've run `eden db init` first
2. Your models inherit from `Model`
3. Models are imported in `migrations/env.py`

