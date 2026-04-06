
from __future__ import annotations
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from eden.app import Eden

class ServiceBootstrapper:
    """Handles auto-configuration of core services."""
    
    @staticmethod
    def bootstrap_database(app: "Eden") -> None:
        """Configure database if database_url is present in config or state."""
        db_url = getattr(app.config, "database_url", None) or getattr(app.state, "database_url", None)
        if db_url:
            from eden.db import Model, init_db
            if not hasattr(Model, "_db") or Model._db is None:
                db = init_db(db_url, app)
                Model._bind_db(db)

                @app.on_startup
                async def _connect_db() -> None:
                    await db.connect(create_tables="sqlite" in db_url)

    @staticmethod
    def bootstrap_cache(app: Eden) -> None:
        """Configure cache if redis_url is present in config or state."""
        redis_url = (
            getattr(app.config, "redis_url", None) or 
            getattr(app.state, "redis_url", None) or
            os.environ.get("REDIS_URL")
        )
        if redis_url and not app.cache:
            from eden.cache.redis import RedisCache
            app.cache = RedisCache(url=redis_url)
            app.cache.mount(app)

    @classmethod
    def bootstrap_all(cls, app: Eden) -> None:
        """Run all bootstrap steps."""
        cls.bootstrap_database(app)
        cls.bootstrap_cache(app)
