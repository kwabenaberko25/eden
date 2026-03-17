import sys
import importlib
import logging
from pathlib import Path

logger = logging.getLogger("eden.db.discovery")

def discover_models() -> None:
    """
    Dynamically discover and import all models.py within the current project.
    
    This ensures that Alembic and Eden metadata registries are aware of all
    defined models, without requiring explicit imports in env.py.
    """
    cwd = Path.cwd()
    
    # 1. Gracefully import standard framework models.
    framework_models = [
        "eden.auth.models",
        "eden.tenancy.models",
        "eden.admin.models",
    ]
    for module in framework_models:
        try:
            importlib.import_module(module)
        except ImportError:
            pass
            
    # 2. Add cwd to sys.path to ensure local absolute imports work
    if str(cwd) not in sys.path:
        sys.path.insert(0, str(cwd))

    # 3. Scan for models.py files dynamically
    for path in cwd.rglob("models.py"):
        # Skip virtual environments, hidden directories, etc.
        parts = path.parts
        if any(p.startswith(".") or p in ("venv", "env", "__pycache__", "migrations", "node_modules", "tests") for p in parts):
            continue
            
        try:
            rel_path = path.relative_to(cwd)
            # Convert path to module dotted name
            module_name = ".".join(rel_path.with_suffix("").parts)
            importlib.import_module(module_name)
            logger.debug(f"Automatically imported models module: {module_name}")
        except Exception as e:
            logger.warning(f"Failed to import {path}: {e}")
