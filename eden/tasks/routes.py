from __future__ import annotations
"""
Eden — Task Status & Management API

Provides endpoints for polling task progress, listing tasks, managing
dead-letter queue, revoking and retrying tasks.

These routes are auto-mounted at ``/api/eden/tasks/`` when the app builds.
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
        "completed": result.status in ("success", "failed", "dead_letter", "revoked"),
    }
    
    if result.status == "success":
        data["result"] = result.result
    elif result.status in ("failed", "dead_letter"):
        data["error"] = result.error
        
    # HTMX handling
    if request.headers.get("HX-Request"):
        return HtmlResponse(TaskProgress.render_update(data))
        
    return JsonResponse(data)


@router.get("/", name="eden.tasks.list")
async def list_tasks(request: Request) -> JsonResponse:
    """
    List recent task results from the result backend.
    
    Query params:
        - status: Filter by status (pending, running, success, failed, dead_letter)
        - limit: Max results (default 50)
    """
    broker = EdenBroker.get_current()
    if not broker:
        return JsonResponse({"error": "Broker not initialized"}, status_code=500)
    
    status_filter = request.query_params.get("status")
    limit = int(request.query_params.get("limit", "50"))
    
    # Collect from local results (the primary accessible store)
    results = []
    backend = broker._result_backend
    for task_id, result in list(backend._local_results.items())[:limit]:
        if status_filter and result.status != status_filter:
            continue
        results.append({
            "task_id": result.task_id,
            "task_name": result.task_name,
            "status": result.status,
            "progress": result.progress,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        })
    
    return JsonResponse({"tasks": results, "count": len(results)})


@router.post("/{task_id}/revoke", name="eden.tasks.revoke")
async def revoke_task(request: Request, task_id: str) -> JsonResponse:
    """
    Revoke a pending or running task.
    
    The task will be marked as revoked and skipped if a worker picks it up.
    Already completed tasks are unaffected.
    """
    broker = EdenBroker.get_current()
    if not broker:
        return JsonResponse({"error": "Broker not initialized"}, status_code=500)
    
    await broker.revoke(task_id)
    return JsonResponse({"task_id": task_id, "status": "revoked"})


@router.post("/{task_id}/retry", name="eden.tasks.retry")
async def retry_task(request: Request, task_id: str) -> JsonResponse:
    """
    Retry a failed or dead-letter task by re-dispatching it.
    
    Looks up the original task result to find the task name, then
    dispatches a new execution. The original result is NOT deleted.
    """
    broker = EdenBroker.get_current()
    if not broker:
        return JsonResponse({"error": "Broker not initialized"}, status_code=500)
    
    result = await broker.get_result(task_id)
    if not result:
        return JsonResponse({"error": "Task not found"}, status_code=404)
    
    if result.status not in ("failed", "dead_letter"):
        return JsonResponse(
            {"error": f"Cannot retry task with status '{result.status}'"},
            status_code=400
        )
    
    # We can't re-dispatch the original args since they're not stored in the result.
    # This endpoint is primarily for admin visibility. For full retry support,
    # the task args would need to be stored in the result backend.
    return JsonResponse({
        "task_id": task_id,
        "task_name": result.task_name,
        "status": "retry_requested",
        "note": "Task retry requires original arguments. Use 'eden tasks retry' CLI with args.",
    })


@router.get("/dead-letter", name="eden.tasks.dead_letter")
async def list_dead_letter(request: Request) -> JsonResponse:
    """
    List tasks in the dead-letter queue.
    """
    broker = EdenBroker.get_current()
    if not broker:
        return JsonResponse({"error": "Broker not initialized"}, status_code=500)
    
    dl_tasks = []
    backend = broker._result_backend
    
    # Check distributed backend for DLQ list
    if backend._distributed:
        dl_ids = await backend._distributed.get("eden:tasks:dead_letter") or []
        for dl_id in dl_ids[-100:]:  # Last 100
            result = await backend.get_result(dl_id)
            if result:
                dl_tasks.append({
                    "task_id": result.task_id,
                    "task_name": result.task_name,
                    "error": result.error,
                    "retries": result.retries,
                    "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                })
    else:
        # Local fallback
        for task_id, result in backend._local_results.items():
            if result.status == "dead_letter":
                dl_tasks.append({
                    "task_id": result.task_id,
                    "task_name": result.task_name,
                    "error": result.error,
                    "retries": result.retries,
                    "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                })
    
    return JsonResponse({"dead_letter_tasks": dl_tasks, "count": len(dl_tasks)})
