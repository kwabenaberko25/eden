"""
Eden Performance Module - Integration API

Complete performance measurement and optimization suite:
  - Integrated profiler with all metrics
  - Query analyzer with optimization suggestions
  - Benchmark suite with regression detection
  - Performance report generation
  - Bottleneck detection and analysis

Main API:
  - PerformanceManager: Coordinates all performance operations
  - get_performance_report(): Quick report generation
  - suggest_optimizations(): Get optimization recommendations
  - run_benchmarks(): Execute performance benchmarks
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .profiler import (
    Profiler, OperationType, MetricsCollector,
    PerformanceReport, BottleneckDetector
)
from .optimizer import (
    QueryAnalyzer, OptimizationAdvisor, OptimizationApplier,
    QueryOperation, OptimizationSuggestion
)
from .benchmarks import (
    BenchmarkSuite, BenchmarkResult, BenchmarkTemplates
)


@dataclass
class PerformanceAnalysis:
    """Complete performance analysis result."""
    
    timestamp: str
    total_operations: int
    avg_operation_time_ms: float
    throughput_ops_per_sec: float
    bottlenecks: List[Dict[str, Any]]
    optimization_suggestions: List[OptimizationSuggestion]
    benchmark_results: List[BenchmarkResult]
    estimated_speedup_percent: float


class PerformanceManager:
    """Manages all performance measurement and optimization."""
    
    def __init__(self):
        self.profiler = Profiler(enabled=True)
        self.analyzer = QueryAnalyzer()
        self.advisor = OptimizationAdvisor(self.analyzer)
        self.applier = OptimizationApplier(self.advisor)
        self.benchmark_suite = BenchmarkSuite(self.profiler)
    
    def profile_operation(self, op_type: OperationType) -> Any:
        """Get timer context manager for operation profiling."""
        return self.profiler.timer(op_type)
    
    def analyze_performance(self) -> PerformanceAnalysis:
        """Perform complete performance analysis."""
        # Get metrics
        report = self.profiler.get_report()
        metrics = report.summary()
        
        # Detect bottlenecks
        detector = BottleneckDetector(self.profiler)
        bottlenecks = []
        for op_type in [OperationType.PARSE, OperationType.COMPILE,
                       OperationType.RENDER, OperationType.FILTER]:
            slow_ops = detector.detect_slow_operations(
                operation_type=op_type,
                threshold_ms=5.0
            )
            if slow_ops:
                bottlenecks.append({
                    'operation': op_type.value,
                    'slow_count': len(slow_ops),
                    'slowest': slow_ops[0] if slow_ops else None
                })
        
        # Get optimization suggestions
        suggestions = self.advisor.analyze()
        
        # Apply safe optimizations
        applied = self.applier.apply_safe_optimizations()
        estimated_speedup, _ = self.applier.estimate_speedup()
        
        # Run benchmarks
        benchmark_results = self.benchmark_suite.run_all_benchmarks()
        
        return PerformanceAnalysis(
            timestamp=datetime.now().isoformat(),
            total_operations=metrics.get('total_samples', 0),
            avg_operation_time_ms=metrics.get('avg_time_ms', 0),
            throughput_ops_per_sec=metrics.get('throughput_ops_sec', 0),
            bottlenecks=bottlenecks,
            optimization_suggestions=suggestions,
            benchmark_results=benchmark_results,
            estimated_speedup_percent=estimated_speedup
        )
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report."""
        analysis = self.analyze_performance()
        
        report = "=" * 80 + "\n"
        report += "EDEN PERFORMANCE ANALYSIS REPORT\n"
        report += f"Generated: {analysis.timestamp}\n"
        report += "=" * 80 + "\n\n"
        
        # Overall metrics
        report += "OVERALL METRICS\n"
        report += "-" * 80 + "\n"
        report += f"Total Operations:       {analysis.total_operations}\n"
        report += f"Avg Operation Time:     {analysis.avg_operation_time_ms:.3f}ms\n"
        report += f"Throughput:             {analysis.throughput_ops_per_sec:.0f} ops/sec\n"
        report += "\n"
        
        # Bottlenecks
        if analysis.bottlenecks:
            report += "PERFORMANCE BOTTLENECKS\n"
            report += "-" * 80 + "\n"
            for bottleneck in analysis.bottlenecks:
                report += f"\n{bottleneck['operation'].upper()}:\n"
                report += f"  Slow operations found: {bottleneck['slow_count']}\n"
                if bottleneck['slowest']:
                    report += f"  Slowest: {bottleneck['slowest']}\n"
        else:
            report += "No significant bottlenecks detected.\n\n"
        
        # Optimization suggestions
        if analysis.optimization_suggestions:
            report += "\nOPTIMIZATION RECOMMENDATIONS\n"
            report += "-" * 80 + "\n"
            
            # Sort by estimated savings
            suggestions = sorted(
                analysis.optimization_suggestions,
                key=lambda s: s.estimated_savings_percent,
                reverse=True
            )
            
            for suggestion in suggestions[:10]:  # Top 10
                report += f"\n[{suggestion.difficulty.upper()}] {suggestion.optimization_type.value}\n"
                report += f"  Location: {suggestion.location}\n"
                report += f"  Action: {suggestion.description}\n"
                report += f"  Est. Speedup: {suggestion.estimated_savings_percent:.0f}%\n"
        
        # Estimated speedup
        report += "\n" + "=" * 80 + "\n"
        report += f"ESTIMATED TOTAL SPEEDUP: {analysis.estimated_speedup_percent:.0f}%\n"
        report += "=" * 80 + "\n"
        
        # Benchmark results
        report += "\nBENCHMARK RESULTS\n"
        report += "-" * 80 + "\n"
        for result in analysis.benchmark_results:
            report += f"\n{result}\n"
        
        return report
    
    def get_bottleneck_report(self) -> str:
        """Get detailed bottleneck analysis."""
        detector = BottleneckDetector(self.profiler)
        report = detector.generate_report()
        return report
    
    def get_optimization_suggestions(self, top_n: int = 10) -> List[OptimizationSuggestion]:
        """Get top N optimization suggestions."""
        suggestions = self.advisor.analyze()
        return sorted(
            suggestions,
            key=lambda s: s.estimated_savings_percent,
            reverse=True
        )[:top_n]
    
    def run_benchmarks(self) -> Dict[str, Any]:
        """Run performance benchmarks."""
        results = self.benchmark_suite.run_all_benchmarks()
        
        return {
            'results': results,
            'report': self.benchmark_suite.generate_report(),
            'count': len(results)
        }


# ================= Convenience Functions =================

_default_manager: Optional[PerformanceManager] = None


def get_performance_manager() -> PerformanceManager:
    """Get singleton performance manager."""
    global _default_manager
    if _default_manager is None:
        _default_manager = PerformanceManager()
    return _default_manager


def profile_operation(op_type: OperationType) -> Any:
    """Convenience function to profile an operation."""
    manager = get_performance_manager()
    return manager.profile_operation(op_type)


def get_performance_report() -> str:
    """Get complete performance report."""
    manager = get_performance_manager()
    return manager.generate_performance_report()


def get_bottleneck_report() -> str:
    """Get bottleneck analysis report."""
    manager = get_performance_manager()
    return manager.get_bottleneck_report()


def suggest_optimizations(top_n: int = 10) -> List[OptimizationSuggestion]:
    """Get optimization suggestions."""
    manager = get_performance_manager()
    return manager.get_optimization_suggestions(top_n=top_n)


def run_benchmarks() -> Dict[str, Any]:
    """Run performance benchmarks."""
    manager = get_performance_manager()
    return manager.run_benchmarks()


def analyze_performance() -> PerformanceAnalysis:
    """Perform complete performance analysis."""
    manager = get_performance_manager()
    return manager.analyze_performance()


# ================= Module Exports =================

__all__ = [
    'PerformanceAnalysis',
    'PerformanceManager',
    'get_performance_manager',
    'profile_operation',
    'get_performance_report',
    'get_bottleneck_report',
    'suggest_optimizations',
    'run_benchmarks',
    'analyze_performance',
]
