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
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from eden.core.backends.base import DistributedBackend
    from typing_extensions import ParamSpec

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
    
    Example:
        >>> from eden.core.metrics import metrics
        >>> metrics.increment("http_requests_total", labels={"method": "GET"})
        >>> metrics.set_gauge("active_connections", 42)
        >>> metrics.observe("response_time_seconds", 0.35)
        >>> print(metrics.export_prometheus())
    """
    
    # Maximum raw observations to store per histogram key.
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
        
        self._distributed_backend: Optional[DistributedBackend] = None

    def increment(self, name: str, value: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Metric name (e.g., 'http_requests_total').
            value: Amount to increment by. Default: 1.
            labels: Optional label key-value pairs.
        """
        key = self._get_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric to a specific value.
        
        Args:
            name: Metric name (e.g., 'active_connections').
            value: The current gauge value.
            labels: Optional label key-value pairs.
        """
        key = self._get_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Observe a value for a histogram metric.
        
        Values are bucketed for efficient storage and export. The bucket
        boundaries default to Prometheus-standard values.
        
        Args:
            name: Metric name (e.g., 'response_time_seconds').
            value: The observed value.
            labels: Optional label key-value pairs.
        """
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
            
            # Increment bucket counts (cumulative)
            for bound in self._buckets:
                if value <= bound:
                    hist["buckets"][bound] += 1

    def _get_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Generate a unique key for a metric based on its name and labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _parse_key(self, key: str) -> Tuple[str, Dict[str, str]]:
        """Parse a metric key back into name and labels."""
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
        """Format labels for Prometheus text format."""
        all_labels = {**labels}
        if extra:
            all_labels.update(extra)
        if not all_labels:
            return ""
        parts = [f'{k}="{v}"' for k, v in sorted(all_labels.items())]
        return "{" + ",".join(parts) + "}"

    def get_all_metrics(self) -> Dict[str, Any]:
        """Return all collected metrics as a dictionary."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: {
                    "count": v["count"],
                    "sum": v["sum"],
                    "avg": v["sum"] / v["count"] if v["count"] > 0 else 0,
                    "buckets": {
                        str(b): c for b, c in v["buckets"].items()
                    },
                }
                for k, v in self._histograms.items()
            },
        }

    def export_json(self) -> Dict[str, Any]:
        """
        Export all metrics as a JSON-serializable dict.
        
        Suitable for internal dashboard endpoints or health checks.
        
        Returns:
            Dict with 'counters', 'gauges', and 'histograms' keys.
        """
        return self.get_all_metrics()

    def export_prometheus(self) -> str:
        """
        Export all metrics in Prometheus text exposition format.
        
        This format is compatible with the Prometheus /metrics endpoint.
        See: https://prometheus.io/docs/instrumenting/exposition_formats/
        
        Returns:
            String in Prometheus text format, ready to serve via HTTP.
            
        Example output:
            # TYPE http_requests_total counter
            http_requests_total{method="GET"} 42
            # TYPE active_connections gauge
            active_connections 5
        """
        lines: List[str] = []
        
        # Track which metric names we've already emitted TYPE headers for
        seen_types: Dict[str, str] = {}
        
        # Counters
        for key, value in sorted(self._counters.items()):
            name, labels = self._parse_key(key)
            if name not in seen_types:
                lines.append(f"# TYPE {name} counter")
                seen_types[name] = "counter"
            label_str = self._format_labels(labels)
            lines.append(f"{name}{label_str} {value}")
        
        # Gauges
        for key, value in sorted(self._gauges.items()):
            name, labels = self._parse_key(key)
            if name not in seen_types:
                lines.append(f"# TYPE {name} gauge")
                seen_types[name] = "gauge"
            label_str = self._format_labels(labels)
            lines.append(f"{name}{label_str} {value}")
        
        # Histograms
        for key, hist_data in sorted(self._histograms.items()):
            name, labels = self._parse_key(key)
            if name not in seen_types:
                lines.append(f"# TYPE {name} histogram")
                seen_types[name] = "histogram"
            
            # Bucket lines (cumulative)
            cumulative = 0
            for bound in sorted(b for b in hist_data["buckets"] if b != float("inf")):
                cumulative += hist_data["buckets"][bound]
                le_label = f"+Inf" if bound == float("inf") else f"{bound}"
                label_str = self._format_labels(labels, {"le": le_label})
                lines.append(f"{name}_bucket{label_str} {cumulative}")
            
            # +Inf bucket (always equals total count)
            inf_count = hist_data["buckets"].get(float("inf"), 0)
            cumulative += inf_count
            label_str = self._format_labels(labels, {"le": "+Inf"})
            lines.append(f"{name}_bucket{label_str} {cumulative}")
            
            # Sum and count
            label_str = self._format_labels(labels)
            lines.append(f"{name}_sum{label_str} {hist_data['sum']}")
            lines.append(f"{name}_count{label_str} {hist_data['count']}")
        
        # Trailing newline per spec
        if lines:
            lines.append("")
        
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics to zero/empty state."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()

    def set_distributed_backend(self, backend: DistributedBackend) -> None:
        """Optionally set a distributed backend for cross-worker metrics integration."""
        self._distributed_backend = backend


# Global instance
metrics = MetricsRegistry()
