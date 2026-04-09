from __future__ import annotations
"""
Eden — Task Context Tracking

Provides access to the currently executing task's information (ID, broker)
from within the task function itself.
"""


import contextvars
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from eden.tasks import EdenBroker

# Context variables for the current task
_CURRENT_TASK_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_task_id", default=None)
_CURRENT_BROKER: contextvars.ContextVar[EdenBroker | None] = contextvars.ContextVar("current_broker", default=None)


async def update_task_state(
    progress: float | None = None,
    status_message: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> None:
    """
    Update the state of the currently executing task.
    
    This function can be called from within an @app.task function to 
    report progress and status updates to the broker's result backend.
    
    Args:
        progress: Progress percentage (0 to 100)
        status_message: A human-readable status message (e.g., "Importing rows...")
        metadata: Arbitrary dictionary of data to associated with the task status
    """
    task_id = _CURRENT_TASK_ID.get()
    broker = _CURRENT_BROKER.get()
    
    if not task_id or not broker:
        return  # Not in a task context
        
    result = await broker._result_backend.get_result(task_id)
    if not result:
        from eden.tasks import TaskResult
        # If no result exists yet, we don't know the task name, so we can't create a full one here
        # But usually the wrap_task_function records 'pending' or 'running' at the start.
        return

    if progress is not None:
        result.progress = float(progress)
    if status_message is not None:
        result.status_message = status_message
    if metadata is not None:
        if result.metadata is None:
            result.metadata = {}
        result.metadata.update(metadata)
        
    await broker._result_backend.store_result(task_id, result)
