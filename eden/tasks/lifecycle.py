"""
Eden Task System - App Lifecycle Integration

Provides hooks to integrate the task broker with Eden app startup/shutdown.

Example::

    from eden import Eden
    from eden.tasks.lifecycle import setup_task_broker
    
    app = Eden()
    setup_task_broker(app)  # Automatically hook broker startup/shutdown
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eden import Eden

logger = logging.getLogger("eden.tasks.lifecycle")


def setup_task_broker(app: "Eden") -> None:
    """
    Register broker startup/shutdown with Eden app lifecycle.

    This function registers @app.on_startup and @app.on_shutdown handlers
    to automatically manage the task broker.

    Args:
        app: The Eden application instance

    Example::

        app = Eden()
        setup_task_broker(app)
        # Now broker will start/stop automatically with the app
    """

    @app.on_startup
    async def startup_broker() -> None:
        """Start the task broker and periodic tasks at app startup."""
        logger.debug("App startup: initializing task broker")
        await app.broker.startup()

    @app.on_shutdown
    async def shutdown_broker() -> None:
        """Stop the task broker and periodic tasks at app shutdown."""
        logger.debug("App shutdown: cleaning up task broker")
        await app.broker.shutdown()

    logger.debug("Task broker lifecycle hooks registered")


__all__ = ["setup_task_broker"]
