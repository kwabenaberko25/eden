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
