"""
Eden — Observability & Metrics

Provides a lightweight metrics registry for tracking application performance, 
task execution, and websocket connections.

Supports export in:
- Prometheus text exposition format (/metrics endpoint)
- JSON format (for internal dashboards)
"""

from __future__ import annotations

import time
import asyncio
import math
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from eden.core.backends.base import DistributedBackend

logger = logging.getLogger("eden.metrics")

# Default Prometheus-style histogram buckets
DEFAULT_BUCKETS: Tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")
)


@dataclass
class MetricValue:
    """A single metric value with timestamp."""
    name: str
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsRegistry:
    """
    In-memory metrics registry for tracking application health.
    
    Supports three metric types:
        - **Counters**: Monotonically increasing values (e.g., total requests).
        - **Gauges**: Point-in-time values that go up and down (e.g., active connections).
        - **Histograms**: Distribution of observed values with bucketing.
    
    Export formats:
        - ``export_prometheus()``: Prometheus text exposition format.
        - ``export_json()``: JSON-serializable dict.
    """
    
    MAX_OBSERVATIONS = 10000
    
    def __init__(self, buckets: Tuple[float, ...] = DEFAULT_BUCKETS) -> None:
        import threading
        self._lock = threading.Lock()
        
        # Counter metrics
        self._counters: Dict[str, Union[int, float]] = {}
        # Gauge metrics (last value)
        self._gauges: Dict[str, Union[int, float]] = {}
        # Histogram metrics: stores (sum, count, bucket_counts)
        self._histograms: Dict[str, Dict[str, Any]] = {}
        # Histogram configuration
        self._buckets = buckets
        
        # Distributed sync
        self._distributed_backend: Optional[DistributedBackend] = None
        self._unflushed_counters: Dict[str, Union[int, float]] = {}
        self._sync_task: Optional[asyncio.Task] = None
        self._sync_interval: float = 10.0 

    def increment(self, name: str, value: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        key = self._get_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value
            if self._distributed_backend:
                self._unflushed_counters[key] = self._unflushed_counters.get(key, 0) + value

    def set_gauge(self, name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        key = self._get_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value for a histogram metric."""
        key = self._get_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = {
                    "sum": 0.0,
                    "count": 0,
                    "buckets": {b: 0 for b in self._buckets},
                }
            hist = self._histograms[key]
            hist["sum"] += value
            hist["count"] += 1
            for bound in self._buckets:
                if value <= bound:
                    hist["buckets"][bound] += 1

    def _get_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        if not labels: return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _parse_key(self, key: str) -> Tuple[str, Dict[str, str]]:
        if "{" in key:
            name, label_str = key.split("{", 1)
            label_str = label_str.rstrip("}")
            labels = {}
            for pair in label_str.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    labels[k] = v
            return name, labels
        return key, {}

    def _format_labels(self, labels: Dict[str, str], extra: Optional[Dict[str, str]] = None) -> str:
        all_labels = {**labels}
        if extra: all_labels.update(extra)
        if not all_labels: return ""
        parts = [f'{k}="{v}"' for k, v in sorted(all_labels.items())]
        return "{" + ",".join(parts) + "}"

    def get_all_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    k: {
                        "count": v["count"],
                        "sum": v["sum"],
                        "avg": v["sum"] / v["count"] if v["count"] > 0 else 0,
                        "buckets": {str(b): c for b, c in v["buckets"].items()},
                    }
                    for k, v in self._histograms.items()
                },
            }

    def export_json(self) -> Dict[str, Any]:
        return self.get_all_metrics()

    def export_prometheus(self) -> str:
        lines: List[str] = []
        seen_types: Dict[str, str] = {}
        
        with self._lock:
            for key, value in sorted(self._counters.items()):
                name, labels = self._parse_key(key)
                if name not in seen_types:
                    lines.append(f"# TYPE {name} counter")
                    seen_types[name] = "counter"
                lines.append(f"{name}{self._format_labels(labels)} {value}")
            
            for key, value in sorted(self._gauges.items()):
                name, labels = self._parse_key(key)
                if name not in seen_types:
                    lines.append(f"# TYPE {name} gauge")
                    seen_types[name] = "gauge"
                lines.append(f"{name}{self._format_labels(labels)} {value}")
            
            for key, hist_data in sorted(self._histograms.items()):
                name, labels = self._parse_key(key)
                if name not in seen_types:
                    lines.append(f"# TYPE {name} histogram")
                    seen_types[name] = "histogram"
                cumulative = 0
                for bound in sorted(b for b in hist_data["buckets"] if b != float("inf")):
                    cumulative += hist_data["buckets"][bound]
                    lines.append(f"{name}_bucket{self._format_labels(labels, {'le': str(bound)})} {cumulative}")
                inf_count = hist_data["buckets"].get(float("inf"), 0)
                lines.append(f"{name}_bucket{self._format_labels(labels, {'le': '+Inf'})} {cumulative + inf_count}")
                lines.append(f"{name}_sum{self._format_labels(labels)} {hist_data['sum']}")
                lines.append(f"{name}_count{self._format_labels(labels)} {hist_data['count']}")
        
        if lines: lines.append("")
        return "\n".join(lines)

    def set_distributed_backend(self, backend: DistributedBackend, sync_interval: float = 10.0) -> None:
        self._distributed_backend = backend
        self._sync_interval = sync_interval
        if self._sync_task is None or self._sync_task.done():
            self._sync_task = asyncio.create_task(self._sync_loop())

    async def _sync_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._sync_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics sync loop: {e}")

    async def flush(self) -> None:
        backend = self._distributed_backend
        if not backend: return
        with self._lock:
            if not self._unflushed_counters: return
            deltas = dict(self._unflushed_counters)
            self._unflushed_counters.clear()
        for key, value in deltas.items():
            await backend.incr(f"eden:metric:counter:{key}", int(value))

    async def shutdown(self) -> None:
        """Gracefully shutdown the metrics background sync."""
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            self._sync_task = None
        await self.flush()

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._unflushed_counters.clear()

metrics = MetricsRegistry()
