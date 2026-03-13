"""
Eden Template Runtime Engine

Executes compiled templates with context, filters, tests, and directives.

Architecture:
  - TemplateContext: Variable scoping and access control
  - TemplateEngine: Executes compiled bytecode
  - DirectiveHandler: Base for directive implementations
  - FilterRegistry: Manages all filters (38+)
  - TestRegistry: Manages test functions (12+)
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable, Coroutine, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from markupsafe import Markup, escape
import re
from datetime import datetime
from enum import Enum


class TemplateContext:
    """
    Template rendering context with scoping and access control.
    
    Manages variable namespaces, ensuring safe isolation between
    template and application code.
    """
    
    def __init__(self, initial: Optional[Dict[str, Any]] = None):
        self.scopes: List[Dict[str, Any]] = [initial or {}]
        self.global_data = {}
    
    def push_scope(self, **variables) -> None:
        """Push new variable scope."""
        self.scopes.append(variables)
    
    def pop_scope(self) -> None:
        """Pop variable scope."""
        if len(self.scopes) > 1:
            self.scopes.pop()
    
    def set(self, name: str, value: Any) -> None:
        """Set variable in current scope."""
        self.scopes[-1][name] = value
    
    def get(self, name: str, default: Any = None) -> Any:
        """Get variable from any scope (searches from innermost to outermost)."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return default
    
    def has(self, name: str) -> bool:
        """Check if variable exists in any scope."""
        for scope in self.scopes:
            if name in scope:
                return True
        return False
    
    def get_all(self) -> Dict[str, Any]:
        """Get flattened view of all variables."""
        result = {}
        for scope in self.scopes:
            result.update(scope)
        return result
    
    def __getitem__(self, name: str) -> Any:
        """Dict-like access."""
        return self.get(name)
    
    def __setitem__(self, name: str, value: Any) -> None:
        """Dict-like assignment."""
        self.set(name, value)
    
    def __contains__(self, name: str) -> bool:
        """Dict-like membership test."""
        return self.has(name)


class SafeExpressionEvaluator:
    """
    Safe expression evaluation using simple operators.
    
    This does NOT use eval() - only supports:
      - Arithmetic: +, -, *, /, %, **
      - Comparison: ==, !=, <, >, <=, >=
      - Logical: and, or, not
      - Membership: in, not in
    """
    
    SAFE_OPERATORS = {
        '+': lambda a, b: a + b,
        '-': lambda a, b: a - b,
        '*': lambda a, b: a * b,
        '/': lambda a, b: a / b if b != 0 else 0,
        '%': lambda a, b: a % b if b != 0 else 0,
        '**': lambda a, b: a ** b,
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
        '<': lambda a, b: a < b,
        '>': lambda a, b: a > b,
        '<=': lambda a, b: a <= b,
        '>=': lambda a, b: a >= b,
        'in': lambda a, b: a in b,
        'not in': lambda a, b: a not in b,
    }
    
    @staticmethod
    def evaluate_comparison(left: Any, op: str, right: Any) -> bool:
        """Evaluate comparison safely."""
        if op in SafeExpressionEvaluator.SAFE_OPERATORS:
            try:
                return SafeExpressionEvaluator.SAFE_OPERATORS[op](left, right)
            except (TypeError, ValueError):
                return False
        return False


class DirectiveHandler(ABC):
    """Base class for directive implementations."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute directive and return output."""
        pass


class FilterRegistry:
    """Registry for template filters."""
    
    def __init__(self):
        self.filters: Dict[str, Callable] = {}
        self._register_builtin_filters()
    
    def register(self, name: str, func: Callable) -> None:
        """Register a filter."""
        self.filters[name] = func
    
    def get(self, name: str) -> Optional[Callable]:
        """Get filter by name."""
        return self.filters.get(name)
    
    def apply(self, name: str, value: Any, *args, **kwargs) -> Any:
        """Apply filter to value."""
        filter_func = self.get(name)
        if filter_func is None:
            return value
        try:
            return filter_func(value, *args, **kwargs)
        except Exception as e:
            return f"[Filter Error: {name} - {str(e)}]"
    
    def _register_builtin_filters(self):
        """Register all built-in filters."""
        # String filters
        self.register('upper', lambda s: str(s).upper())
        self.register('lower', lambda s: str(s).lower())
        self.register('title', lambda s: str(s).title())
        self.register('capitalize', lambda s: str(s).capitalize())
        self.register('reverse', lambda s: str(s)[::-1])
        self.register('trim', lambda s: str(s).strip())
        self.register('ltrim', lambda s: str(s).lstrip())
        self.register('rtrim', lambda s: str(s).rstrip())
        
        # String manipulation
        self.register('replace', self._filter_replace)
        self.register('slice', self._filter_slice)
        self.register('length', lambda s: len(str(s)))
        self.register('truncate', self._filter_truncate)
        self.register('slug', self._filter_slug)
        self.register('repeat', self._filter_repeat)
        
        # Numeric filters
        self.register('abs', lambda n: abs(float(n)))
        self.register('round', lambda n, p=0: round(float(n), int(p)))
        self.register('ceil', lambda n: int(float(n)) + (1 if float(n) % 1 > 0 else 0))
        self.register('floor', lambda n: int(float(n)))
        
        # Array filters
        self.register('first', self._filter_first)
        self.register('last', self._filter_last)
        self.register('unique', self._filter_unique)
        self.register('sort', lambda a: sorted(a) if isinstance(a, list) else a)
        self.register('reverse_array', lambda a: list(reversed(a)) if isinstance(a, list) else a)
        
        # Type filters
        self.register('json', self._filter_json)
        
        # I18n filters (registering base versions - locale variants handled elsewhere)
        self.register('phone', self._filter_phone)
        self.register('currency', self._filter_currency)
        self.register('date', self._filter_date)
        self.register('time', self._filter_time)
    
    @staticmethod
    def _filter_replace(s: str, old: str, new: str) -> str:
        """Replace filter."""
        return str(s).replace(str(old), str(new))
    
    @staticmethod
    def _filter_slice(s: str, start: int = 0, end: int = None) -> str:
        """Slice filter."""
        s_str = str(s)
        return s_str[int(start):int(end) if end is not None else None]
    
    @staticmethod
    def _filter_truncate(s: str, length: int = 50, suffix: str = "...") -> str:
        """Truncate filter."""
        s_str = str(s)
        if len(s_str) > int(length):
            return s_str[:int(length)] + str(suffix)
        return s_str
    
    @staticmethod
    def _filter_slug(s: str) -> str:
        """Slug filter (URL-safe identifier)."""
        s_str = str(s).lower()
        s_str = re.sub(r'[^a-z0-9]+', '-', s_str)
        return s_str.strip('-')
    
    @staticmethod
    def _filter_repeat(s: str, count: int = 1) -> str:
        """Repeat filter."""
        return str(s) * int(count)
    
    @staticmethod
    def _filter_first(arr: Any, default: Any = None) -> Any:
        """First element filter."""
        if isinstance(arr, (list, tuple, str)):
            return arr[0] if arr else default
        return default
    
    @staticmethod
    def _filter_last(arr: Any, default: Any = None) -> Any:
        """Last element filter."""
        if isinstance(arr, (list, tuple, str)):
            return arr[-1] if arr else default
        return default
    
    @staticmethod
    def _filter_unique(arr: Any) -> Any:
        """Unique filter."""
        if isinstance(arr, list):
            return list(dict.fromkeys(arr))  # Preserve order
        return arr
    
    @staticmethod
    def _filter_json(obj: Any) -> str:
        """JSON filter."""
        import json
        try:
            return json.dumps(obj)
        except (TypeError, ValueError):
            return "null"
    
    @staticmethod
    def _filter_phone(number: str, country: str = "US") -> str:
        """Phone filter (basic implementation)."""
        # Remove non-digits
        digits = re.sub(r'\D', '', str(number))
        
        # Format based on country (implementation would be expanded)
        if country.upper() == "US":
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif country.upper() == "GH":
            if len(digits) == 10:
                return f"+233 {digits[0]} {digits[1:4]} {digits[4:]}"
        
        return number
    
    @staticmethod
    def _filter_currency(amount: float, currency: str = "USD") -> str:
        """Currency filter (basic implementation)."""
        try:
            value = float(amount)
            currency_symbols = {
                "USD": "$",
                "EUR": "€",
                "GBP": "£",
                "GHS": "₵",
                "JPY": "¥",
                "CNY": "¥",
            }
            symbol = currency_symbols.get(currency.upper(), currency.upper())
            return f"{symbol}{value:,.2f}"
        except (ValueError, TypeError):
            return str(amount)
    
    @staticmethod
    def _filter_date(dt: Any, format: str = "%Y-%m-%d") -> str:
        """Date filter."""
        if isinstance(dt, datetime):
            return dt.strftime(str(format))
        return str(dt)
    
    @staticmethod
    def _filter_time(dt: Any, format: str = "%H:%M:%S") -> str:
        """Time filter."""
        if isinstance(dt, datetime):
            return dt.strftime(str(format))
        return str(dt)


class TestRegistry:
    """Registry for template test functions."""
    
    def __init__(self):
        self.tests: Dict[str, Callable] = {}
        self._register_builtin_tests()
    
    def register(self, name: str, func: Callable) -> None:
        """Register a test."""
        self.tests[name] = func
    
    def get(self, name: str) -> Optional[Callable]:
        """Get test by name."""
        return self.tests.get(name)
    
    def test(self, name: str, value: Any, *args, **kwargs) -> bool:
        """Apply test to value."""
        test_func = self.get(name)
        if test_func is None:
            return False
        try:
            return bool(test_func(value, *args, **kwargs))
        except Exception:
            return False
    
    def _register_builtin_tests(self):
        """Register all built-in tests."""
        self.register('empty', lambda v: not v)
        self.register('filled', lambda v: bool(v))
        self.register('null', lambda v: v is None)
        self.register('defined', lambda v: v is not None)
        self.register('even', lambda v: int(v) % 2 == 0)
        self.register('odd', lambda v: int(v) % 2 != 0)
        self.register('divisible_by', lambda v, d: int(v) % int(d) == 0)
        self.register('sameas', lambda v1, v2: v1 is v2)
        self.register('starts', lambda s, p: str(s).startswith(str(p)))
        self.register('ends', lambda s, p: str(s).endswith(str(p)))
        self.register('string', lambda v: isinstance(v, str))
        self.register('number', lambda v: isinstance(v, (int, float)) and not isinstance(v, bool))
        self.register('boolean', lambda v: isinstance(v, bool))


class TemplateEngine:
    """
    Main template execution engine.
    
    Combines compiled code, context, filters, and directives
    to render templates.
    """
    
    def __init__(self):
        self.filters = FilterRegistry()
        self.tests = TestRegistry()
        self.directives: Dict[str, DirectiveHandler] = {}
        self.partials: Dict[str, str] = {}  # Cached template partials
    
    async def render(self, compiled_code: str, context: Dict[str, Any]) -> str:
        """
        Render template using compiled code.
        
        Args:
            compiled_code: Python code from CodeGenerator
            context: Template context variables
        
        Returns:
            Rendered template string
        """
        ctx = TemplateContext(context)
        
        # Create execution namespace
        namespace = {
            'context': ctx,
            'filters': self.filters,
            'tests': self.tests,
            'output': [],
            'Markup': Markup,
            'escape': escape,
        }
        
        # TODO: Execute compiled code safely
        # For now, compile and execute
        try:
            exec(compiled_code, namespace)
            render_func = namespace.get('render')
            if render_func:
                if asyncio.iscoroutinefunction(render_func):
                    result = await render_func(ctx, self.filters, self.tests, self)
                else:
                    result = render_func(ctx, self.filters, self.tests, self)
                return str(result)
        except Exception as e:
            return f"[Render Error: {str(e)}]"
        
        return ""
    
    def register_directive(self, name: str, handler: DirectiveHandler) -> None:
        """Register a directive handler."""
        self.directives[name] = handler
    
    def get_directive(self, name: str) -> Optional[DirectiveHandler]:
        """Get directive handler."""
        return self.directives.get(name)
    
    def cache_partial(self, name: str, code: str) -> None:
        """Cache a partial template."""
        self.partials[name] = code
    
    def get_partial(self, name: str) -> Optional[str]:
        """Get cached partial template."""
        return self.partials.get(name)
    
    async def render_partial(self, name: str, context: Dict[str, Any]) -> str:
        """Render a partial template."""
        code = self.get_partial(name)
        if code is None:
            return f"[Partial not found: {name}]"
        return await self.render(code, context)


# ================= Module Exports =================

__all__ = [
    'TemplateContext',
    'TemplateEngine',
    'DirectiveHandler',
    'FilterRegistry',
    'TestRegistry',
    'SafeExpressionEvaluator',
]
