import sys
import importlib
import logging
import inspect
from pathlib import Path
from typing import Type, Any

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

    # 3. Scan for models.py files or models/ packages dynamically
    discovery_targets = list(cwd.rglob("models.py")) + list(cwd.rglob("models/__init__.py"))
    
    for path in discovery_targets:
        # Skip hidden directories, virtual environments, etc.
        parts = path.relative_to(cwd).parts
        if any(p.startswith(".") or p in _SKIP_DIRS for p in parts):
            continue
        
        # For a models.py file, the parent must be a package or the root.
        # For a models/__init__.py, the models directory itself is the package.
        is_init = path.name == "__init__.py"
        parent = path.parent
        
        if not is_init:
            # Standard models.py
            if parent != cwd and not (parent / "__init__.py").exists():
                logger.debug(
                    f"Skipping {path}: parent directory is not a Python package "
                    f"(missing __init__.py)"
                )
                continue
        else:
            # models/__init__.py - the 'models' directory is the package.
            # We already know it has __init__.py because we found it.
            pass
            
        try:
            rel_path = path.relative_to(cwd)
            # Convert path to module dotted name
            if is_init:
                # For app/models/__init__.py, module name is app.models
                module_name = ".".join(rel_path.parent.parts)
            else:
                # For app/models.py, module name is app.models
                module_name = ".".join(rel_path.with_suffix("").parts)
            
            if module_name:
                importlib.import_module(module_name)
                logger.debug(f"Automatically imported models module: {module_name}")
        except Exception as e:
            logger.warning(f"Failed to import {path}: {e}")


def discover_managers() -> None:
    """
    Dynamically discover and register all managers/actions within the project.
    
    Scans for classes inheriting from BaseManager in files named:
    - actions.py
    - managers.py
    - service.py
    - services.py
    """
    from eden.db.context import BaseManager, EdenDbContext
    
    cwd = Path.cwd()
    
    # 1. Framework default actions
    framework_actions = [
        "eden.auth.actions",
        "eden.admin.actions",
    ]
    for module in framework_actions:
        try:
            mod = importlib.import_module(module)
            _register_from_module(mod, BaseManager, EdenDbContext)
        except ImportError:
            pass

    # 2. Scan project for managers.py or actions.py
    patterns = ["managers.py", "actions.py", "services.py", "service.py"]
    discovery_targets = []
    for pattern in patterns:
        discovery_targets.extend(list(cwd.rglob(pattern)))

    for path in discovery_targets:
        parts = path.relative_to(cwd).parts
        if any(p.startswith(".") or p in _SKIP_DIRS for p in parts):
            continue
            
        try:
            rel_path = path.relative_to(cwd)
            module_name = ".".join(rel_path.with_suffix("").parts)
            
            if module_name:
                mod = importlib.import_module(module_name)
                _register_from_module(mod, BaseManager, EdenDbContext)
        except Exception as e:
            logger.warning(f"Failed to import managers from {path}: {e}")


def _register_from_module(module: Any, base_cls: Type, ctx_cls: Type) -> None:
    """Helper to inspect a module and register any found managers."""
    for name, obj in inspect.getmembers(module):
        if (
            inspect.isclass(obj) and 
            issubclass(obj, base_cls) and 
            obj is not base_cls
        ):
            # Resolve name: explicitly set or derived
            manager_name = getattr(obj, "manager_name", None)
            if not manager_name:
                # e.g. UserManager -> users, AuthActions -> auth
                manager_name = obj.__name__.lower()
                for suffix in ["manager", "actions", "service"]:
                    if manager_name.endswith(suffix):
                        manager_name = manager_name.removesuffix(suffix)
                        break
            
            if manager_name:
                ctx_cls.register_manager(manager_name, obj)

