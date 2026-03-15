"""
Eden — Real-time Performance Telemetry

Provides request-scoped metrics collection for app and database performance.
"""

from __future__ import annotations
import contextvars
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class TelemetryData:
    """Container for performance metrics in a single request."""
    start_time: float = field(default_factory=time.perf_counter)
    db_queries: int = 0
    db_time_ms: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    @property
    def total_duration_ms(self) -> float:
        return (time.perf_counter() - self.start_time) * 1000

# Context variable to store telemetry data per request/task
_telemetry_ctx: contextvars.ContextVar[Optional[TelemetryData]] = contextvars.ContextVar(
    "telemetry", default=None
)

def start_telemetry() -> contextvars.Token:
    """Initialize telemetry context for the current request."""
    return _telemetry_ctx.set(TelemetryData())

def get_telemetry() -> Optional[TelemetryData]:
    """Retrieve the current telemetry data."""
    return _telemetry_ctx.get()

def record_query(duration_ms: float) -> None:
    """Record a database query execution."""
    data = _telemetry_ctx.get()
    if data:
        data.db_queries += 1
        data.db_time_ms += duration_ms

def record_metric(name: str, value: float) -> None:
    """Record a custom performance metric."""
    data = _telemetry_ctx.get()
    if data:
        data.custom_metrics[name] = value

def reset_telemetry(token: contextvars.Token) -> None:
    """Reset the telemetry context."""
    _telemetry_ctx.reset(token)
