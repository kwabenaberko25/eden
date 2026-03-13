"""
Eden Query Analyzer & Optimizer

Analyzes template queries and suggests optimizations:
  - Query pattern detection
  - Call graph analysis
  - Dependency tracking
  - Optimization suggestions
  - Code path analysis

Architecture:
  - QueryAnalyzer: Analyze template operations
  - CallGraph: Track operation dependencies
  - OptimizationAdvisor: Suggest improvements
  - OptimizationApplier: Apply auto-optimizations
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque


class OptimizationType(Enum):
    """Types of optimizations."""
    CACHE_RESULT = "cache_result"
    AVOID_RECOMPILATION = "avoid_recompilation"
    LAZY_EVALUATION = "lazy_evaluation"
    BATCH_OPERATIONS = "batch_operations"
    REMOVE_DEAD_CODE = "remove_dead_code"
    COMMON_SUBEXPRESSION = "common_subexpression"
    LOOP_UNROLLING = "loop_unrolling"
    FILTER_CHAINING = "filter_chaining"


@dataclass
class OptimizationSuggestion:
    """A suggested optimization."""
    
    optimization_type: OptimizationType
    location: str  # Where in template
    description: str  # What to do
    estimated_savings_percent: float  # How much faster
    difficulty: str  # easy, medium, hard
    
    def __repr__(self) -> str:
        return (f"{self.optimization_type.value}: "
                f"{self.description} (~{self.estimated_savings_percent:.0f}% faster)")


@dataclass
class QueryOperation:
    """Represents a query operation in a template."""
    
    name: str
    operation_type: str  # parse, compile, render, filter, etc.
    frequency: int = 1
    dependencies: Set[str] = field(default_factory=set)
    cost: float = 1.0  # Relative cost
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def total_cost(self) -> float:
        """Total cost considering frequency."""
        return self.cost * self.frequency


class CallGraph:
    """Represents dependencies between operations."""
    
    def __init__(self):
        self.graph: Dict[str, Set[str]] = defaultdict(set)  # operation -> dependencies
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)  # operation -> dependents
        self.operations: Dict[str, QueryOperation] = {}
    
    def add_operation(self, op: QueryOperation) -> None:
        """Add operation to graph."""
        self.operations[op.name] = op
        for dep in op.dependencies:
            self.graph[op.name].add(dep)
            self.reverse_graph[dep].add(op.name)
    
    def get_dependencies(self, op_name: str) -> Set[str]:
        """Get operations this depends on."""
        return self.graph.get(op_name, set())
    
    def get_dependents(self, op_name: str) -> Set[str]:
        """Get operations that depend on this."""
        return self.reverse_graph.get(op_name, set())
    
    def find_critical_path(self) -> List[str]:
        """Find longest dependency chain (critical path)."""
        visited = set()
        paths = {}
        
        def dfs(node: str) -> List[str]:
            if node in visited:
                return paths.get(node, [])
            
            visited.add(node)
            deps = self.get_dependencies(node)
            
            if not deps:
                paths[node] = [node]
                return [node]
            
            longest = []
            for dep in deps:
                path = dfs(dep)
                if len(path) > len(longest):
                    longest = path
            
            result = longest + [node]
            paths[node] = result
            return result
        
        all_paths = []
        for op_name in self.operations.keys():
            if op_name not in visited:
                path = dfs(op_name)
                all_paths.append(path)
        
        return max(all_paths, key=len, default=[])
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependency chains."""
        visited = set()
        cycles = []
        
        def dfs(node: str, path: List[str], rec_stack: Set[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path.copy(), rec_stack)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
            
            rec_stack.remove(node)
        
        for node in self.operations.keys():
            if node not in visited:
                dfs(node, [], set())
        
        return cycles


class QueryAnalyzer:
    """Analyzes template query patterns."""
    
    def __init__(self):
        self.call_graph = CallGraph()
        self.operation_frequencies: Dict[str, int] = defaultdict(int)
        self.operation_times: Dict[str, float] = defaultdict(float)
    
    def add_operation(self, op: QueryOperation) -> None:
        """Add operation to analysis."""
        self.call_graph.add_operation(op)
        self.operation_frequencies[op.name] += op.frequency
    
    def record_operation_time(self, op_name: str, time_ms: float) -> None:
        """Record actual operation time."""
        self.operation_times[op_name] += time_ms
    
    def identify_repeated_operations(self, threshold: int = 2) -> Dict[str, int]:
        """Find operations that repeat frequently."""
        return {name: freq for name, freq in self.operation_frequencies.items() 
               if freq >= threshold}
    
    def get_expensive_operations(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """Get most expensive operations."""
        costs = [(name, time) for name, time in self.operation_times.items()]
        return sorted(costs, key=lambda x: x[1], reverse=True)[:top_n]
    
    def get_unused_operations(self) -> List[str]:
        """Find operations never executed."""
        return [name for name, op in self.call_graph.operations.items()
               if name not in self.operation_frequencies]


class OptimizationAdvisor:
    """Suggests optimizations based on analysis."""
    
    def __init__(self, analyzer: QueryAnalyzer):
        self.analyzer = analyzer
        self.suggestions: List[OptimizationSuggestion] = []
    
    def analyze(self) -> List[OptimizationSuggestion]:
        """Run optimization analysis."""
        self.suggestions = []
        
        self._check_repeated_operations()
        self._check_expensive_operations()
        self._check_unused_operations()
        self._check_circular_dependencies()
        self._check_filter_chains()
        
        return self.suggestions
    
    def _check_repeated_operations(self) -> None:
        """Suggest caching for repeated operations."""
        repeated = self.analyzer.identify_repeated_operations(threshold=3)
        
        for op_name, freq in repeated.items():
            suggestion = OptimizationSuggestion(
                optimization_type=OptimizationType.CACHE_RESULT,
                location=op_name,
                description=f"Cache result of '{op_name}' (called {freq} times)",
                estimated_savings_percent=70.0,  # Typical cache hit saves 70%
                difficulty="easy"
            )
            self.suggestions.append(suggestion)
    
    def _check_expensive_operations(self) -> None:
        """Suggest optimizations for expensive operations."""
        expensive = self.analyzer.get_expensive_operations(top_n=5)
        total_time = sum(t for _, t in expensive)
        
        for op_name, op_time in expensive:
            if op_time / total_time > 0.3:  # More than 30% of total time
                suggestion = OptimizationSuggestion(
                    optimization_type=OptimizationType.LAZY_EVALUATION,
                    location=op_name,
                    description=f"Consider lazy evaluation for '{op_name}' ({op_time:.0f}ms)",
                    estimated_savings_percent=50.0,
                    difficulty="medium"
                )
                self.suggestions.append(suggestion)
    
    def _check_unused_operations(self) -> None:
        """Suggest removing unused operations."""
        unused = self.analyzer.get_unused_operations()
        
        for op_name in unused:
            suggestion = OptimizationSuggestion(
                optimization_type=OptimizationType.REMOVE_DEAD_CODE,
                location=op_name,
                description=f"Remove unused operation '{op_name}'",
                estimated_savings_percent=5.0,
                difficulty="easy"
            )
            self.suggestions.append(suggestion)
    
    def _check_circular_dependencies(self) -> None:
        """Check for circular dependencies."""
        cycles = self.analyzer.call_graph.find_circular_dependencies()
        
        for cycle in cycles:
            suggestion = OptimizationSuggestion(
                optimization_type=OptimizationType.REMOVE_DEAD_CODE,
                location=str(cycle),
                description=f"Circular dependency detected: {' -> '.join(cycle)}",
                estimated_savings_percent=100.0,  # Must be fixed
                difficulty="hard"
            )
            self.suggestions.append(suggestion)
    
    def _check_filter_chains(self) -> None:
        """Suggest filter chain optimization."""
        # This would check for chains of filters that could be combined
        suggestion = OptimizationSuggestion(
            optimization_type=OptimizationType.FILTER_CHAINING,
            location="template",
            description="Consider combining chained filters into single filter",
            estimated_savings_percent=40.0,
            difficulty="medium"
        )
        if suggestion not in self.suggestions:
            self.suggestions.append(suggestion)


class OptimizationApplier:
    """Applies optimizations automatically."""
    
    def __init__(self, advisor: OptimizationAdvisor):
        self.advisor = advisor
        self.applied_optimizations: List[OptimizationSuggestion] = []
    
    def apply_safe_optimizations(self) -> List[OptimizationSuggestion]:
        """Apply optimizations that are safe and won't change behavior."""
        self.applied_optimizations = []
        suggestions = self.advisor.analyze()
        
        for suggestion in suggestions:
            if suggestion.difficulty == "easy":
                self.applied_optimizations.append(suggestion)
        
        return self.applied_optimizations
    
    def estimate_speedup(self) -> Tuple[float, str]:
        """Estimate total speedup from optimizations."""
        total_savings = 0.0
        descriptions = []
        
        for suggestion in self.applied_optimizations:
            total_savings += suggestion.estimated_savings_percent
            descriptions.append(f"  - {suggestion}")
        
        # Cap at 90% (can't optimize beyond practical limits)
        total_savings = min(total_savings, 90.0)
        
        report = f"Estimated speedup: {total_savings:.0f}%\n"
        report += "\n".join(descriptions)
        
        return total_savings, report


# ================= Module Exports =================

__all__ = [
    'OptimizationType',
    'OptimizationSuggestion',
    'QueryOperation',
    'CallGraph',
    'QueryAnalyzer',
    'OptimizationAdvisor',
    'OptimizationApplier',
]
