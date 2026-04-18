from __future__ import annotations
"""
Eden — Task UI Components

Provides HTMX-powered components for real-time task progress tracking.
"""


from typing import Any, Dict, Optional

from eden.components import Component

class TaskProgress(Component):
    """
    A premium HTMX-powered progress bar for background tasks.
    
    Attributes:
        task_id: The ID of the task to track.
        poll_interval: How often to poll the status (in seconds). Default: 2s.
        on_complete: Optional JavaScript to execute when the task completes.
    """
    
    def __init__(
        self, 
        task_id: str, 
        poll_interval: int = 2,
        on_complete: Optional[str] = None
    ) -> None:
        super().__init__()
        self.task_id = task_id
        self.poll_interval = poll_interval
        self.on_complete = on_complete

    def render(self) -> str:
        """Render the progress component using HTMX for polling."""
        # Note: In a real Eden app, this would use an .eden template.
        # Here we provide a high-fidelity inline implementation.
        
        status_url = f"/api/eden/tasks/{self.task_id}/status"
        
        return f'''
        <div id="task-progress-{self.task_id}" 
             class="eden-task-progress p-6 bg-slate-900/50 backdrop-blur-md border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden"
             hx-get="{status_url}" 
             hx-trigger="load, every {self.poll_interval}s" 
             hx-swap="outerHTML"
             hx-target="this">
            
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center space-x-3">
                    <div class="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                    <span class="text-sm font-semibold text-slate-300 tracking-wider uppercase">Processing Task</span>
                </div>
                <span class="text-xs font-mono text-slate-500">ID: {self.task_id[:8]}...</span>
            </div>

            <div class="relative h-2 w-full bg-slate-800 rounded-full overflow-hidden mb-4">
                <div id="progress-bar-{self.task_id}" 
                     class="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-600 transition-all duration-500 ease-out"
                     style="width: 0%">
                    <div class="absolute inset-0 bg-white/20 animate-shimmer"></div>
                </div>
            </div>

            <div class="flex items-center justify-between">
                <p id="status-message-{self.task_id}" class="text-sm text-slate-400 font-medium italic">
                    Initializing...
                </p>
                <span id="progress-percent-{self.task_id}" class="text-lg font-bold text-white tabular-nums">
                    0%
                </span>
            </div>
            
            <style>
                @keyframes shimmer {{
                    0% {{ transform: translateX(-100%) }}
                    100% {{ transform: translateX(100%) }}
                }}
                .animate-shimmer {{
                    animation: shimmer 2s infinite;
                }}
            </style>
        </div>
        '''

    @classmethod
    def render_update(cls, data: Dict[str, Any]) -> str:
        """
        Render the updated state of the progress bar based on status data.
        Used by the API endpoint to return partial HTML for HTMX updates.
        """
        task_id = data.get("task_id")
        progress = data.get("progress", 0)
        status = data.get("status", "pending")
        message = data.get("status_message", "Processing...")
        completed = data.get("completed", False)
        
        # Color logic based on status
        color_classes = "from-blue-600 via-indigo-500 to-purple-600"
        pulse_color = "bg-blue-500"
        
        if status == "success":
            color_classes = "bg-emerald-500"
            pulse_color = "bg-emerald-500"
            message = message or "Task Completed Successfully"
        elif status in ("failed", "dead_letter"):
            color_classes = "bg-rose-500"
            pulse_color = "bg-rose-500"
            message = data.get("error", "Task Failed")

        # If completed, we stop polling
        hx_attrs = "" if completed else f'hx-get="/api/eden/tasks/{task_id}/status" hx-trigger="every 2s" hx-swap="outerHTML" hx-target="this"'
        
        return f'''
        <div id="task-progress-{task_id}" 
             class="eden-task-progress p-6 bg-slate-900/50 backdrop-blur-md border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden"
             {hx_attrs}>
            
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center space-x-3">
                    <div class="w-2 h-2 rounded-full {pulse_color} {'animate-pulse' if not completed else ''}"></div>
                    <span class="text-sm font-semibold text-slate-300 tracking-wider uppercase">
                        {status.replace("_", " ")}
                    </span>
                </div>
                <span class="text-xs font-mono text-slate-500">ID: {task_id[:8]}...</span>
            </div>

            <div class="relative h-2 w-full bg-slate-800 rounded-full overflow-hidden mb-4">
                <div id="progress-bar-{task_id}" 
                     class="absolute top-0 left-0 h-full bg-gradient-to-r {color_classes} transition-all duration-500 ease-out"
                     style="width: {progress}%">
                    {'<div class="absolute inset-0 bg-white/20 animate-shimmer"></div>' if not completed else ''}
                </div>
            </div>

            <div class="flex items-center justify-between">
                <p id="status-message-{task_id}" class="text-sm text-slate-400 font-medium italic">
                    {message}
                </p>
                <span id="progress-percent-{task_id}" class="text-lg font-bold text-white tabular-nums">
                    {int(progress)}%
                </span>
            </div>
            
            {f'<script>if(window.onTaskComplete) window.onTaskComplete("{task_id}", "{status}");</script>' if completed else ''}
        </div>
        '''
