# Task 2: Configure Application Core

**Goal**: Initialize the Eden app instance, configure the environment, and run your first "Hello World" service.

---

## 🏗️ Step 2.1: Review the App Factory

Eden uses a "Factory Pattern" for application initialization. This makes testing and multi-environment deployment seamless.

**File**: `app/__init__.py`

```python
from eden import Eden, setup_logging
from .settings import DEBUG, SECRET_KEY, DATABASE_URL, LOG_LEVEL, LOG_FORMAT
from .routes import main_router

def create_app() -> Eden:
    # 1. Configure Structured Logging
    setup_logging(level=LOG_LEVEL, json_format=(LOG_FORMAT == "json"))

    # 2. Initialize Eden App
    app = Eden(
        title="My Eden App",
        description="A high-performance SaaS engine.",
        debug=DEBUG,
        secret_key=SECRET_KEY
    )

    # 3. Mount Application Routes
    app.include_router(main_router)

    # 4. Global Middleware Layers
    app.add_middleware("security")
    app.add_middleware("ratelimit", max_requests=200, window_seconds=60)
    app.add_middleware("logging")

    # 5. Native Health Checks
    app.enable_health_checks()

    return app

app = create_app()
```

### Key Technical Concepts

- **`setup_logging`**: Switches between human-readable text (Dev) and structured JSON (Prod).
- **`debug=True`**: Enables the **Eden Premium Debug UI**, offering deep-dive diagnostics for errors.
- **`include_router`**: Plugs in your modular routing logic.

---

## ⚙️ Step 2.2: Environment Configuration

Eden follows the **Twelve-Factor App** methodology by using environment variables for settings.

**File**: `app/settings.py`

```python
import os

# ── Core ─────────────────────────────────────────────────────────────────
DEBUG = os.getenv("EDEN_DEBUG", "true").lower() == "true"
SECRET_KEY = os.getenv("EDEN_SECRET_KEY", "generate-a-secure-key-for-prod")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3")

# ── Security ─────────────────────────────────────────────────────────────
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# ── Logging ──────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "text" if DEBUG else "json")
```

> [!NOTE]
> In production, you should always set `EDEN_DEBUG=false` and provide a unique `EDEN_SECRET_KEY`.

---

## 🚀 Step 2.3: Launching the App

Start the development server with hot-reloading enabled.

```bash
eden run
```

### Verification
Once the server starts, visit `http://127.0.0.1:8000`. You should receive a welcome JSON:

```json
{
  "message": "Welcome to My Eden App! 🌿"
}
```

### 🛰️ Checking Health
Visit the built-in health endpoint at `http://127.0.0.1:8000/health`:

```json
{
  "status": "healthy",
  "app": "My Eden App",
  "version": "0.1.0"
}
```

---

### **Next Task**: [Defining Data Models (ORM)](./task3_orm.md)
