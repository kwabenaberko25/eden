from __future__ import annotations
"""
Eden — Task Status API

Provides endpoints for polling task progress and results.
"""


from typing import Any, Dict

from eden.responses import JsonResponse, HtmlResponse
from eden.routing import Router
from eden.requests import Request
from eden.tasks import EdenBroker
from eden.tasks.components import TaskProgress
router = Router(prefix="/api/eden/tasks")
@router.get("/{task_id}/status", name="eden.tasks.status")
async def get_task_status(request: Request, task_id: str) -> JsonResponse | HtmlResponse:
    """
    Get the current status and progress of a background task.
    Supports both JSON and HTMX (HTML snippet) based on Request headers.
    """
    broker = EdenBroker.get_current()
    if not broker:
        if request.headers.get("HX-Request"):
            return HtmlResponse("<div>Broker not initialized</div>", status_code=500)
        return JsonResponse({"error": "Broker not initialized"}, status_code=500)
        
    result = await broker.get_result(task_id)
    if not result:
        if request.headers.get("HX-Request"):
            return HtmlResponse(f"<div>Task {task_id} not found</div>", status_code=404)
        return JsonResponse({"status": "not_found", "task_id": task_id}, status_code=404)
        
    data = {
        "task_id": result.task_id,
        "task_name": result.task_name,
        "status": result.status,
        "progress": result.progress,
        "status_message": result.status_message,
        "metadata": result.metadata,
        "completed": result.status in ("success", "failed", "dead_letter"),
    }
    
    if result.status == "success":
        data["result"] = result.result
    elif result.status in ("failed", "dead_letter"):
        data["error"] = result.error
        
    # HTMX handling
    if request.headers.get("HX-Request"):
        return HtmlResponse(TaskProgress.render_update(data))
        
    return JsonResponse(data)
