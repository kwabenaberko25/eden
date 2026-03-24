import sys
import importlib
import logging
from pathlib import Path

logger = logging.getLogger("eden.db.discovery")

# Directories that should never be scanned for model discovery
_SKIP_DIRS = frozenset({
    "venv", "env", ".venv", ".env", "__pycache__", "migrations",
    "node_modules", "tests", "test", "docs", "dist", "build",
    "site-packages", ".git", ".hg", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "alembic",
})


def discover_models() -> None:
    """
    Dynamically discover and import all models.py within the current project.
    
    This ensures that Alembic and Eden metadata registries are aware of all
    defined models, without requiring explicit imports in env.py.
    
    Safety measures:
        - Only imports models.py files that are inside proper Python packages
          (i.e., directories with __init__.py) to avoid importing unrelated files
        - Skips virtual environments, hidden directories, test directories,
          and other non-application paths
        - Does NOT modify sys.path if the cwd is already importable
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
    #    (only if not already present to avoid import shadowing)
    cwd_str = str(cwd)
    if cwd_str not in sys.path:
        sys.path.insert(0, cwd_str)

    # 3. Scan for models.py files dynamically
    for path in cwd.rglob("models.py"):
        # Skip hidden directories, virtual environments, etc.
        parts = path.relative_to(cwd).parts
        if any(p.startswith(".") or p in _SKIP_DIRS for p in parts):
            continue
        
        # Only import if the models.py is inside a proper Python package
        # (i.e., its parent directory has an __init__.py)
        parent = path.parent
        if parent != cwd and not (parent / "__init__.py").exists():
            logger.debug(
                f"Skipping {path}: parent directory is not a Python package "
                f"(missing __init__.py)"
            )
            continue
            
        try:
            rel_path = path.relative_to(cwd)
            # Convert path to module dotted name
            module_name = ".".join(rel_path.with_suffix("").parts)
            importlib.import_module(module_name)
            logger.debug(f"Automatically imported models module: {module_name}")
        except Exception as e:
            logger.warning(f"Failed to import {path}: {e}")

