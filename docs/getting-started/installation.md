# Installation 🛠️

Setting up Eden is straightforward. We recommend using a virtual environment to keep your project dependencies isolated.

## Prerequisites

- **Python**: 3.11 or higher.
- **Node.js** (Optional): Only required if you plan to use advanced asset pipelines (e.g., Vite/Tailwind) or specific `npx` execution wrappers.

## Installation Options

### Minimal Installation (Core Only)

For a lightweight installation with just the essentials (~12 dependencies):

```bash
pip install eden-framework
```

This includes:
- Web framework (Starlette-based Eden)
- Async ORM (SQLAlchemy 2.0+)
- Database drivers (SQLite, PostgreSQL, MySQL)
- CLI tools and scaffolding
- Security, authentication, middleware
- Templating engine (Jinja2)

**Perfect for**: REST APIs, small web apps, monoliths

### Database-Only Extras

For PostgreSQL and MySQL support without async drivers bundled:

```bash
pip install eden-framework[databases]
```

Adds: `asyncpg` (PostgreSQL), `aiomysql` (MySQL)

### Full-Featured Installation

To include all optional features:

```bash
pip install eden-framework[all]
```

This adds the following optional extras:

| Extra | Use Case |
|-------|----------|
| `[payments]` | Stripe payments integration |
| `[storage]` | AWS S3 or compatible storage |
| `[tasks]` | Background jobs (Taskiq + Redis) |
| `[mail]` | Email sending (SMTP support) |
| `[ai]` | AI/ML features (pgvector embeddings) |
| `[databases]` | PostgreSQL & MySQL async drivers |

### Mix-and-Match Installation

Install only what you need:

```bash
# REST API with PostgreSQL
pip install eden-framework[databases]

# Web app with Stripe + S3 storage
pip install eden-framework[payments,storage]

# Everything except payments
pip install eden-framework[tasks,mail,storage,ai,databases]
```

## Creating a New Project (Scaffolding)

The recommended way to start a new Eden project is using the native `eden new` command:

```bash
# 1. Install eden-framework
pip install eden-framework

# 2. Scaffold a new project
eden new my_app

# Pick your profile:
#   1. minimal    - Just the essentials (fastest to get started)
#   2. standard   - Recommended structure (most flexible)
#   3. production - Enterprise-ready (Docker, tests, CI)
```

**Project profiles:**

- **Minimal** (8 files, runs in <2 minutes)
  - `app.py`, `models.py`, `templates/`, `requirements.txt`, `.env.example`
  - Perfect for getting started quickly

- **Standard** (16 files)
  - Includes `routes/`, `static/`, `tests/`, `settings.py`
  - Recommended for most projects

- **Production** (full setup)
  - Dockerfile, docker-compose.yml, comprehensive test suite
  - Ready to deploy to cloud

### Manual Setup

If you prefer to build your project from scratch:

1. Create a new directory:

   ```bash
   mkdir eden_app && cd eden_app
   ```

2. Set up a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install Eden:

   ```bash
   pip install eden-framework
   ```

4. Create your first app file (`app.py`):

   ```python
   from eden import Eden

   app = Eden(
       title="My Eden App",
       secret_key="your-secret-key-here",
       debug=True
   )

   @app.get("/")
   async def hello():
       return {"message": "Welcome to Eden! 🌿"}

   if __name__ == "__main__":
       app.run(host="127.0.0.1", port=8000)
   ```

5. Create requirements file:

   ```bash
   pip freeze > requirements.txt
   ```

6. Run the app:

   ```bash
   python app.py
   ```

---

## Upgrading Eden

To upgrade to the latest version:

```bash
pip install --upgrade eden-framework
```

Check your installed version:

```bash
pip show eden-framework
eden --version
```

---

## Dependency Management

### Understanding the Dependency Tree

When you install `eden-framework`, you get:

**Core Dependencies** (always included):
- `starlette` - Web server framework
- `sqlalchemy>=2.0` - Database ORM
- `pydantic>=2.0` - Data validation
- `jinja2` - Template rendering
- `uvicorn` - ASGI server
- `click` - CLI framework

**Optional Dependencies**:
- `[databases]` - PostgreSQL and MySQL async drivers
- `[payments]` - Stripe integration
- `[storage]` - AWS S3 and cloud storage
- `[tasks]` - Background task queue (Taskiq + Redis)
- `[mail]` - Email sending (SMTP)
- `[ai]` - AI/ML features (pgvector embeddings)

### Troubleshooting Installation Issues

**Issue**: `ModuleNotFoundError: No module named 'eden'`

**Solution**: Ensure the virtual environment is activated:
```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

**Issue**: `pip: command not found`

**Solution**: Use Python's module installer directly:
```bash
python -m pip install eden-framework
```

**Issue**: Conflicting dependencies

**Solution**: Use a fresh virtual environment:
```bash
python -m venv .venv_fresh
source .venv_fresh/bin/activate
pip install eden-framework
```

**Issue**: Port 8000 already in use

**Solution**: Use a different port:
```bash
eden run --port 8001
# Or in code:
app.run(port=8001)
```

---

## Post-Installation Verification

### 1. Check Installation

```bash
python -c "import eden; print(eden.__version__)"
```

Expected output: `0.1.0` (or current version)

### 2. Create a Test App

Create `test_app.py`:

```python
from eden import Eden

app = Eden(title="Test", debug=True, secret_key="test")

@app.get("/test")
async def test():
    return {"status": "Eden is working! 🌿"}

if __name__ == "__main__":
    app.run()
```

Run it:
```bash
python test_app.py
```

Visit `http://localhost:8000/test` - you should see:
```json
{"status": "Eden is working! 🌿"}
```

### 3. Verify Database Support

```bash
python -c "import sqlalchemy; print(f'SQLAlchemy {sqlalchemy.__version__} installed')"
python -c "import aiosqlite; print('SQLite driver ready')"
```

### 4. Check CLI Integration

```bash
eden --help
# Should show Eden command options
```

---

## Development Environment Setup

### Recommended Tools

**Code Editor**: VS Code with extensions:
- Python (Microsoft)
- Pylance (for type hints)
- Thunder Client or REST Client (for API testing)

**Database GUI**: 
- DBeaver (free, works with any database)
- pgAdmin (PostgreSQL)
- MySQL Workbench (MySQL)

**API Testing**:
- Postman
- Insomnia
- Thunder Client (VS Code extension)

### Environment Configuration

Create `.env` file in your project root:

```env
# Application
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
APP_NAME=My Eden App

# Database
DATABASE_URL=sqlite+aiosqlite:///db.sqlite3
# Or for PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/myapp

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Security
ALLOWED_HOSTS=localhost,127.0.0.1

# Features
ENABLE_EMAIL=False
ENABLE_PAYMENTS=False
```

Load in your app:

```python
from dotenv import load_dotenv
import os

load_dotenv()

DEBUG = os.getenv("DEBUG") == "True"
SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
```

---

## Next Steps

1. **Run the Quick Start**: See [Quick Start Guide](quickstart.md) for your first application
2. **Explore Examples**: Check [Learning Path](learning-path.md) with progressive examples
3. **Read the Guides**: Dive into [Core Guides](../guides/routing.md) for deep dives
4. **Follow Tutorials**: Step through [Task Tutorials](../tutorial/task1_setup.md) for hands-on learning

---

**Happy coding! 🌿**
   ```

4. Create your first app (`app.py`):

   ```python
   from eden import Eden

   app = Eden(title="My App", debug=True)

   @app.get("/")
   async def hello():
       return {"message": "Welcome to Eden! 🌿"}

   if __name__ == "__main__":
       app.run()
   ```

5. Run the development server:

   ```bash
   eden run
   ```

---

## Dependency Breakdown

| Component | Core? | Purpose |
|-----------|-------|---------|
| Starlette | ✅ | ASGI web framework |
| Uvicorn | ✅ | ASGI server |
| SQLAlchemy 2.0+ | ✅ | Async ORM |
| Click | ✅ | CLI framework |
| Jinja2 | ✅ | Template engine |
| Pydantic | ✅ | Data validation |
| python-multipart | ✅ | Form parsing |
| itsdangerous | ✅ | Secure tokens (CSRF, sessions) |
| argon2-cffi | ✅ | Password hashing |
| PyJWT | ✅ | JWT tokens |
| aiofiles | ✅ | Async file operations |
| email-validator | ✅ | Email validation |
| asyncpg | Optional | PostgreSQL driver |
| aiomysql | Optional | MySQL driver |
| stripe | Optional | Payment processing |
| taskiq* | Optional | Background jobs |
| aioboto3 | Optional | AWS S3 storage |
| aiosmtplib | Optional | Email sending |
| pgvector | Optional | Vector embeddings |

---

**Next Steps**: [Quick Start Guide](quickstart.md) or [Learning Path](learning-path.md)
