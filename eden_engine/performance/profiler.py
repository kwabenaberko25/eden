"""
Eden Performance Profiler

Measures and analyzes template rendering performance:
  - Individual operation timing
  - Bottleneck detection
  - Metrics collection
  - Performance reports

Architecture:
  - Profiler: Main profiling interface
  - OperationTimer: Measure operation duration
  - MetricsCollector: Aggregate metrics
  - PerformanceReport: Generate analysis reports
  - BottleneckDetector: Identify slow operations
"""

import time
import functools
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics


class OperationType(Enum):
    """Types of operations that can be profiled."""
    PARSE = "parse"
    COMPILE = "compile"
    RENDER = "render"
    FILTER = "filter"
    TEST = "test"
    BLOCK_RESOLVE = "block_resolve"
    INHERITANCE_RESOLVE = "inheritance_resolve"
    CACHE_LOOKUP = "cache_lookup"
    CACHE_WRITE = "cache_write"
    TEMPLATE_LOAD = "template_load"
    EXPRESSION_EVAL = "expression_eval"
    DIRECTIVE_EXEC = "directive_exec"


@dataclass
class TimingData:
    """Data from a single operation timing."""
    
    operation_type: OperationType
    duration_ms: float  # Milliseconds
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    
    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"{status} {self.operation_type.value}: {self.duration_ms:.3f}ms"


@dataclass
class OperationStats:
    """Aggregated statistics for an operation type."""
    
    operation_type: OperationType
    count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    
    @property
    def avg_time_ms(self) -> float:
        """Calculate average time."""
        if self.count == 0:
            return 0.0
        return self.total_time_ms / self.count
    
    @property
    def throughput(self) -> float:
        """Throughput in ops/second."""
        if self.total_time_ms == 0:
            return 0.0
        return (self.count / self.total_time_ms) * 1000
    
    def add_timing(self, duration_ms: float) -> None:
        """Add timing data."""
        self.count += 1
        self.total_time_ms += duration_ms
        self.min_time_ms = min(self.min_time_ms, duration_ms)
        self.max_time_ms = max(self.max_time_ms, duration_ms)
    
    def __repr__(self) -> str:
        return (f"{self.operation_type.value}: "
                f"count={self.count}, avg={self.avg_time_ms:.3f}ms, "
                f"min={self.min_time_ms:.3f}ms, max={self.max_time_ms:.3f}ms")


class OperationTimer:
    """Context manager for timing operations."""
    
    def __init__(self, operation_type: OperationType, metadata: Dict[str, Any] = None):
        self.operation_type = operation_type
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None
        self.timing_data: Optional[TimingData] = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record."""
        elapsed = (time.time() - self.start_time) * 1000  # Convert to ms
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        
        self.timing_data = TimingData(
            operation_type=self.operation_type,
            duration_ms=elapsed,
            metadata=self.metadata,
            success=success,
            error=error
        )
        return False  # Don't suppress exceptions


class MetricsCollector:
    """Collects and aggregates performance metrics."""
    
    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self.timings: List[TimingData] = []
        self.stats: Dict[OperationType, OperationStats] = {}
        self.percentiles: Dict[OperationType, Dict[int, float]] = {}
    
    def record_timing(self, timing: TimingData) -> None:
        """Record a timing measurement."""
        if len(self.timings) >= self.max_samples:
            # Keep recent samples
            self.timings = self.timings[1:]
        
        self.timings.append(timing)
        
        # Update stats
        if timing.operation_type not in self.stats:
            self.stats[timing.operation_type] = OperationStats(timing.operation_type)
        
        self.stats[timing.operation_type].add_timing(timing.duration_ms)
    
    def get_stats(self, op_type: OperationType) -> Optional[OperationStats]:
        """Get stats for operation type."""
        return self.stats.get(op_type)
    
    def get_all_stats(self) -> Dict[OperationType, OperationStats]:
        """Get stats for all operation types."""
        return self.stats.copy()
    
    def calculate_percentiles(self, op_type: OperationType) -> Dict[int, float]:
        """Calculate percentiles for operation type."""
        timings = [t.duration_ms for t in self.timings 
                  if t.operation_type == op_type]
        
        if not timings:
            return {}
        
        timings.sort()
        return {
            50: statistics.median(timings),
            90: self._percentile(timings, 90),
            95: self._percentile(timings, 95),
            99: self._percentile(timings, 99),
        }
    
    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        index = (percentile / 100) * (len(data) - 1)
        lower = int(index)
        upper = lower + 1
        if upper >= len(data):
            return data[lower]
        weight = index - lower
        return data[lower] * (1 - weight) + data[upper] * weight
    
    def total_time_ms(self) -> float:
        """Get total measured time."""
        return sum(t.duration_ms for t in self.timings)
    
    def sample_count(self) -> int:
        """Get number of samples."""
        return len(self.timings)
    
    def clear(self) -> None:
        """Clear all data."""
        self.timings = []
        self.stats = {}
        self.percentiles = {}


class Profiler:
    """
    Main profilation interface.
    
    Provides profiling capabilities for the template engine.
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.collector = MetricsCollector()
    
    def timer(self, operation_type: OperationType, 
             metadata: Dict[str, Any] = None) -> OperationTimer:
        """Create operation timer."""
        return OperationTimer(operation_type, metadata)
    
    def profile_operation(self, operation_type: OperationType):
        """Decorator for profiling functions."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                with self.timer(operation_type) as timer:
                    result = func(*args, **kwargs)
                
                if timer.timing_data:
                    self.collector.record_timing(timer.timing_data)
                return result
            
            return wrapper
        return decorator
    
    def profile_operation_async(self, operation_type: OperationType):
        """Decorator for profiling async functions."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                
                with self.timer(operation_type) as timer:
                    result = await func(*args, **kwargs)
                
                if timer.timing_data:
                    self.collector.record_timing(timer.timing_data)
                return result
            
            return wrapper
        return decorator
    
    def record(self, operation_type: OperationType, duration_ms: float, 
              metadata: Dict[str, Any] = None) -> None:
        """Manually record timing."""
        timing = TimingData(operation_type, duration_ms, metadata=metadata or {})
        self.collector.record_timing(timing)
    
    def get_stats(self, op_type: OperationType) -> Optional[OperationStats]:
        """Get stats for operation type."""
        return self.collector.get_stats(op_type)
    
    def get_report(self) -> 'PerformanceReport':
        """Generate performance report."""
        return PerformanceReport(self.collector)
    
    def reset(self) -> None:
        """Clear all collected data."""
        self.collector.clear()
    
    def enable(self) -> None:
        """Enable profiling."""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable profiling."""
        self.enabled = False


class PerformanceReport:
    """Generates human-readable performance reports."""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
    
    def summary(self) -> str:
        """Get summary report."""
        lines = []
        lines.append("=" * 60)
        lines.append("PERFORMANCE REPORT")
        lines.append("=" * 60)
        lines.append(f"Total samples: {self.collector.sample_count()}")
        lines.append(f"Total time: {self.collector.total_time_ms():.2f}ms")
        lines.append("")
        
        for op_type, stats in sorted(self.collector.get_all_stats().items(),
                                    key=lambda x: x[1].total_time_ms, reverse=True):
            lines.append(f"{stats.operation_type.value.upper()}")
            lines.append(f"  Count:       {stats.count}")
            lines.append(f"  Avg:         {stats.avg_time_ms:.3f}ms")
            lines.append(f"  Min:         {stats.min_time_ms:.3f}ms")
            lines.append(f"  Max:         {stats.max_time_ms:.3f}ms")
            lines.append(f"  Total:       {stats.total_time_ms:.2f}ms")
            lines.append(f"  Throughput:  {stats.throughput:.1f} ops/sec")
            lines.append("")
        
        return "\n".join(lines)
    
    def percentiles_report(self) -> str:
        """Get percentiles report."""
        lines = []
        lines.append("=" * 60)
        lines.append("PERCENTILES REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        for op_type in sorted(self.collector.get_all_stats().keys()):
            percentiles = self.collector.calculate_percentiles(op_type)
            if not percentiles:
                continue
            
            lines.append(f"{op_type.value.upper()}")
            for p, value in sorted(percentiles.items()):
                lines.append(f"  P{p}: {value:.3f}ms")
            lines.append("")
        
        return "\n".join(lines)
    
    def slowest_operations(self, top_n: int = 10) -> str:
        """Get report of slowest operations."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"TOP {top_n} SLOWEST OPERATIONS")
        lines.append("=" * 60)
        lines.append("")
        
        timings = sorted(self.collector.timings, 
                        key=lambda t: t.duration_ms, reverse=True)[:top_n]
        
        for i, timing in enumerate(timings, 1):
            lines.append(f"{i}. {timing}")
        
        return "\n".join(lines)
    
    def operation_breakdown(self) -> str:
        """Get breakdown of time by operation type."""
        lines = []
        lines.append("=" * 60)
        lines.append("OPERATION TIME BREAKDOWN")
        lines.append("=" * 60)
        lines.append("")
        
        total = self.collector.total_time_ms()
        if total == 0:
            return "No data"
        
        for op_type, stats in sorted(self.collector.get_all_stats().items(),
                                    key=lambda x: x[1].total_time_ms, reverse=True):
            pct = (stats.total_time_ms / total) * 100
            bar_width = int(pct / 2)
            bar = "█" * bar_width
            lines.append(f"{op_type.value.upper():20} {pct:5.1f}% {bar}")
        
        return "\n".join(lines)
    
    def __str__(self) -> str:
        """String representation."""
        return self.summary() + "\n" + self.operation_breakdown()


class BottleneckDetector:
    """Detects performance bottlenecks."""
    
    def __init__(self, profiler: Profiler):
        self.profiler = profiler
    
    def detect_slow_operations(self, threshold_ms: float = 10.0) -> List[TimingData]:
        """Find operations slower than threshold."""
        return [t for t in self.profiler.collector.timings 
               if t.duration_ms > threshold_ms]
    
    def detect_outliers(self, op_type: OperationType, 
                       sigma: float = 2.0) -> List[TimingData]:
        """Find statistical outliers (using std dev)."""
        timings = [t for t in self.profiler.collector.timings 
                  if t.operation_type == op_type]
        
        if len(timings) < 2:
            return []
        
        durations = [t.duration_ms for t in timings]
        mean = statistics.mean(durations)
        stdev = statistics.stdev(durations)
        
        outliers = []
        for timing in timings:
            z_score = abs((timing.duration_ms - mean) / stdev)
            if z_score > sigma:
                outliers.append(timing)
        
        return outliers
    
    def get_bottlenecks(self) -> Dict[OperationType, str]:
        """Get textual bottleneck report."""
        report = {}
        
        for op_type in self.profiler.collector.get_all_stats().keys():
            outliers = self.detect_outliers(op_type)
            if outliers:
                report[op_type] = (
                    f"Found {len(outliers)} outlier(s) "
                    f"with avg duration {sum(t.duration_ms for t in outliers) / len(outliers):.2f}ms"
                )
        
        return report


# ================= Module Exports =================

__all__ = [
    'OperationType',
    'TimingData',
    'OperationStats',
    'OperationTimer',
    'MetricsCollector',
    'Profiler',
    'PerformanceReport',
    'BottleneckDetector',
]
