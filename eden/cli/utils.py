from __future__ import annotations
"""
Eden CLI — Shared Utilities
"""

import json
import os
from pathlib import Path
from typing import Optional

def discover_app() -> Optional[str]:
    """
    Discover the Eden application entry point in the current directory.
    Checks:
    1. eden.json (saved config)
    2. Common file patterns (app.py, main.py, etc.)
    3. Default fallback (app:app)
    """
    # 1. Check environment variable
    env_app = os.environ.get("EDEN_APP")
    if env_app:
        return env_app

    eden_json_path = Path("eden.json")
    
    # 2. First check if eden.json has a saved app_path
    if eden_json_path.exists():
        try:
            config = json.loads(eden_json_path.read_text(encoding="utf-8"))
            app_path = config.get("app_path")
            if app_path:
                return app_path
        except (json.JSONDecodeError, KeyError):
            pass

    # 2. If not found in eden.json, auto-detect
    discovery_order = ["app.py", "main.py", "nexus.py", "run.py"]
    for filename in discovery_order:
        file_path = Path(filename)
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8")
                # Look for common Eden initialization patterns
                if "app = Eden(" in content or "app: Eden =" in content or "app = create_app" in content:
                    module_name = file_path.stem
                    app_path = f"{module_name}:app"
                    
                    # Store discovery result in eden.json for persistence
                    try:
                        if eden_json_path.exists():
                            config = json.loads(eden_json_path.read_text(encoding="utf-8"))
                        else:
                            config = {}
                        config["app_path"] = app_path
                        eden_json_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
                    except Exception as e:
                        from eden.logging import get_logger
                        get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)
                    return app_path
            except Exception:
                continue
    
    # 3. Default fallback
    return "app:app"
