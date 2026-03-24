"""
Eden — Real-time Performance Telemetry

Provides request-scoped metrics collection for app and database performance.
"""

from __future__ import annotations
import contextvars
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class TelemetryData:
    """Container for performance metrics in a single request."""
    start_time: float = field(default_factory=time.perf_counter)
    start_memory: float = 0.0
    db_queries: int = 0
    db_time_ms: float = 0.0
    template_time_ms: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    @property
    def total_duration_ms(self) -> float:
        return (time.perf_counter() - self.start_time) * 1000
    
    @property
    def memory_delta_mb(self) -> float:
        """Memory usage change since start of request."""
        try:
            import psutil
            process = psutil.Process()
            current_mem = process.memory_info().rss / 1024 / 1024
            return current_mem - self.start_memory
        except ImportError:
            return 0.0

# Context variable to store telemetry data per request/task
_telemetry_ctx: contextvars.ContextVar[Optional[TelemetryData]] = contextvars.ContextVar(
    "telemetry", default=None
)

def start_telemetry() -> contextvars.Token:
    """Initialize telemetry context for the current request."""
    initial_mem = 0.0
    try:
        import psutil
        process = psutil.Process()
        initial_mem = process.memory_info().rss / 1024 / 1024
    except ImportError:
        pass
    return _telemetry_ctx.set(TelemetryData(start_memory=initial_mem))

def get_telemetry() -> Optional[TelemetryData]:
    """Retrieve the current telemetry data."""
    return _telemetry_ctx.get()

def record_query(duration_ms: float) -> None:
    """Record a database query execution."""
    data = _telemetry_ctx.get()
    if data:
        data.db_queries += 1
        data.db_time_ms += duration_ms

def record_template_render(duration_ms: float) -> None:
    """Record a template rendering operation."""
    data = _telemetry_ctx.get()
    if data:
        data.template_time_ms += duration_ms

def record_metric(name: str, value: float) -> None:
    """Record a custom performance metric."""
    data = _telemetry_ctx.get()
    if data:
        data.custom_metrics[name] = value

def reset_telemetry(token: contextvars.Token) -> None:
    """Reset the telemetry context."""
    _telemetry_ctx.reset(token)

def setup_sentry(dsn: str, environment: str = "production", **kwargs: Any) -> None:
    """Configure Sentry for error tracking and performance monitoring."""
    try:
        import sentry_sdk
        from sentry_sdk.integrations.starlette import StarletteIntegration
        
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            integrations=[StarletteIntegration()],
            **kwargs
        )
    except ImportError:
        import logging
        logger = logging.getLogger("eden")
        logger.warning("sentry-sdk not found. Install it to enable error tracking.")
