# Installation

This guide covers how to install and configure Eden Framework for development and production.

---

## Requirements

- Python 3.11 or higher
- pip or uv package manager
- (Optional) PostgreSQL, MySQL, or Redis for production

---

## Installation Methods

### Using pip

```bash
pip install eden-framework
```

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a modern, fast Python package manager:

```bash
uv pip install eden-framework
```

### Development Installation

To install in editable mode (for contributing or using the latest code):

```bash
# Clone the repository
git clone https://github.com/eden-framework/eden
cd eden

# Install in editable mode
pip install -e .
# or with uv
uv pip install -e .
```

---

## Dependencies

Eden automatically installs these dependencies:

| Package | Purpose |
|---------|---------|
| `starlette` | ASGI framework |
| `uvicorn` | ASGI server |
| `pydantic` | Data validation |
| `click` | CLI framework |
| `jinja2` | Templating |
| `sqlalchemy[asyncio]` | Database ORM |
| `aiosqlite` | SQLite async driver |
| `alembic` | Database migrations |
| `argon2-cffi` | Password hashing |
| `PyJWT` | JWT authentication |
| `taskiq` | Background tasks |
| `aiofiles` | Async file operations |

---

## Optional Dependencies

Install extras for specific features:

```bash
# PostgreSQL support
pip install eden-framework[postgresql]
# Requires: asyncpg

# Redis support  
pip install eden-framework[redis]
# Requires: taskiq-redis, aioboto3

# Email support
pip install eden-framework[email]
# Requires: aiosmtplib

# All extras
pip install eden-framework[all]
```

---

## Project Setup

### Quick Setup with Scaffolding

The easiest way to start:

```bash
eden new my_project
cd my_project
```

This creates:
- Project structure
- Configuration files
- Database setup
- Docker configuration
- Test suite

### Manual Setup

For more control:

1. **Create your app file**:

```python
# app.py
from eden import Eden

app = Eden\(title="My App", debug=True)
```

2. **Create requirements.txt**:

```
eden-framework>=0.1.0
uvicorn[standard]>=0.29.0
```

3. **Install and run**:

```bash
pip install -r requirements.txt
eden run
```

---

## Environment Configuration

Eden respects these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `EDEN_DEBUG` | Debug mode | `false` |
| `EDEN_SECRET_KEY` | Secret key | (auto-generated) |
| `DATABASE_URL` | Database URL | `sqlite+aiosqlite:///db.sqlite3` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `REDIS_URL` | Redis URL | (not set) |

---

## Database Setup

### SQLite (Development)

Default. No setup required. Database file created automatically.

### PostgreSQL (Production)

1. Install the driver:
```bash
pip install asyncpg
```

2. Set the database URL:
```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/mydb"
```

### MySQL

1. Install the driver:
```bash
pip install aiomysql
```

2. Set the database URL:
```bash
export DATABASE_URL="mysql+aiomysql://user:pass@localhost/mydb"
```

---

## Verifying Installation

Verify your installation:

```bash
eden version
```

Should output:
```
🌿 Eden v0.1.0
```

---

## Next Steps

- [Quick Start](quickstart.md) - Create your first app
- [CLI Reference](cli/index.md) - Learn all commands
- [Phase 1 Tutorial](phase1.md) - Build a complete app

