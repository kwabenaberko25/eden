"""
Eden — Observability & Metrics

Provides a lightweight metrics registry for tracking application performance, 
task execution, and websocket connections.
"""

from __future__ import annotations

import time
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from eden.core.backends.base import DistributedBackend
    from typing_extensions import ParamSpec

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
    
    This can be configured to synchronize with a DistributedBackend
    for cluster-wide metrics (work in progress).
    """
    def __init__(self) -> None:
        # Counter metrics
        self._counters: Dict[str, Union[int, float]] = {}
        # Gauge metrics (last value)
        self._gauges: Dict[str, Union[int, float]] = {}
        # Histogram/Summary metrics (could be expanded)
        self._histograms: Dict[str, List[float]] = {}
        
        self._distributed_backend: Optional[DistributedBackend] = None

    def increment(self, name: str, value: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        key = self._get_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        key = self._get_key(name, labels)
        self._gauges[key] = value

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value for a histogram/summary metric."""
        key = self._get_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
        # Keep only last 1000 observations to prevent memory issues
        if len(self._histograms[key]) > 1000:
            current = self._histograms[key]
            self._histograms[key] = current[len(current)-1000:]

    def _get_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Generate a unique key for a metric based on its name and labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_all_metrics(self) -> Dict[str, Any]:
        """Return all collected metrics as a dictionary."""
        return {
            "counters": self._counters,
            "gauges": self._gauges,
            "summaries": {
                k: {
                    "count": len(v),
                    "sum": sum(v),
                    "avg": sum(v) / len(v) if v else 0,
                    "max": max(v) if v else 0,
                    "min": min(v) if v else 0,
                }
                for k, v in self._histograms.items()
            }
        }

    def set_distributed_backend(self, backend: DistributedBackend) -> None:
        """Optionally set a distributed backend for cross-worker metrics integration."""
        self._distributed_backend = backend

# Global instance
metrics = MetricsRegistry()
