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
        self.register('slugify', self._filter_slug)  # Alias
        self.register('repeat', self._filter_repeat)
        
        # String formatting & utilities
        self.register('title_case', lambda s: ' '.join(word.capitalize() for word in str(s).split()))
        self.register('mask', self._filter_mask)
        self.register('default_if_none', self._filter_default_if_none)
        self.register('pluralize', self._filter_pluralize)
        
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
        self.register('json_encode', self._filter_json)  # Alias
        
        # I18n filters
        self.register('phone', self._filter_phone)
        self.register('currency', self._filter_currency)
        self.register('money', self._filter_currency)  # Alias
        self.register('date', self._filter_date)
        self.register('time', self._filter_time)
        self.register('time_ago', self._filter_time_ago)
        self.register('file_size', self._filter_file_size)
        
        # Design system filters
        self.register('eden_bg', self._filter_eden_bg)
        self.register('eden_shadow', self._filter_eden_shadow)
        self.register('eden_text', self._filter_eden_text)
        
        # Form field filters
        self.register('add_class', self._filter_add_class)
        self.register('attr', self._filter_attr)
        self.register('append_attr', self._filter_append_attr)
        self.register('remove_attr', self._filter_remove_attr)
        self.register('field_type', self._filter_field_type)
    
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
    
    @staticmethod
    def _filter_mask(s: str, mask_char: str = "*") -> str:
        """Mask sensitive strings (email, phone)."""
        s_str = str(s)
        if '@' in s_str:
            parts = s_str.split('@')
            if len(parts[0]) > 2:
                return parts[0][0] + mask_char * (len(parts[0]) - 2) + parts[0][-1] + '@' + parts[1]
        if len(s_str) > 3:
            return mask_char * (len(s_str) - 3) + s_str[-3:]
        return mask_char * len(s_str)
    
    @staticmethod
    def _filter_pluralize(text: str, count: int = 1, plural: str = "s") -> str:
        """Add suffix based on count."""
        try:
            if int(count) != 1:
                return str(text) + str(plural)
            return str(text)
        except (ValueError, TypeError):
            return str(text)
    
    @staticmethod
    def _filter_default_if_none(value: Any, default: Any = "N/A") -> Any:
        """Fallback if None."""
        return default if value is None else value
    
    @staticmethod
    def _filter_file_size(bytes_val: int) -> str:
        """Format bytes to KB/MB/GB."""
        try:
            size = float(bytes_val)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} PB"
        except (ValueError, TypeError):
            return str(bytes_val)
    
    @staticmethod
    def _filter_time_ago(dt: Any, precision: str = 'minute') -> str:
        """Human-readable time distance."""
        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt)
            if not isinstance(dt, datetime):
                return str(dt)
            diff = datetime.now() - dt
            seconds = diff.total_seconds()
            if seconds < 60:
                return "just now"
            elif seconds < 3600:
                mins = int(seconds // 60)
                return f"{mins} minute{'s' if mins > 1 else ''} ago"
            elif seconds < 86400:
                hrs = int(seconds // 3600)
                return f"{hrs} hour{'s' if hrs > 1 else ''} ago"
            elif seconds < 604800:
                days = int(seconds // 86400)
                return f"{days} day{'s' if days > 1 else ''} ago"
            else:
                weeks = int(seconds // 604800)
                return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        except:
            return str(dt)
    
    @staticmethod
    def _filter_eden_bg(color: str) -> str:
        """Eden design system background colors."""
        eden_colors = {
            'primary': 'bg-blue-600', 'secondary': 'bg-slate-600',
            'success': 'bg-emerald-600', 'danger': 'bg-red-600',
            'warning': 'bg-amber-600', 'info': 'bg-cyan-600',
            'dark': 'bg-slate-900', 'light': 'bg-slate-100',
        }
        return eden_colors.get(str(color).lower(), str(color))
    
    @staticmethod
    def _filter_eden_shadow(size: str) -> str:
        """Eden design system shadows."""
        eden_shadows = {'sm': 'shadow-sm', 'md': 'shadow-md', 'lg': 'shadow-lg',
                       'xl': 'shadow-xl', '2xl': 'shadow-2xl', 'none': 'shadow-none'}
        return eden_shadows.get(str(size).lower(), f'shadow-{size}')
    
    @staticmethod
    def _filter_eden_text(tone: str) -> str:
        """Eden design system text colors."""
        eden_tones = {
            'slate-900': 'text-slate-900', 'slate-600': 'text-slate-600',
            'primary': 'text-blue-600', 'secondary': 'text-slate-600',
            'success': 'text-emerald-600', 'danger': 'text-red-600',
            'warning': 'text-amber-600', 'info': 'text-cyan-600',
            'muted': 'text-slate-500', 'light': 'text-slate-100',
        }
        return eden_tones.get(str(tone).lower(), str(tone))
    
    @staticmethod
    def _filter_add_class(obj: Any, class_name: str) -> dict:
        """Add CSS class to field object."""
        if isinstance(obj, dict):
            obj = obj.copy()
            if 'classes' in obj:
                obj['classes'] = f"{obj['classes']} {class_name}"
            else:
                obj['classes'] = class_name
            return obj
        return obj
    
    @staticmethod
    def _filter_attr(obj: Any, attr_name: str, value: Any) -> dict:
        """Set attribute on field object."""
        if isinstance(obj, dict):
            obj = obj.copy()
            if 'attributes' not in obj:
                obj['attributes'] = {}
            obj['attributes'][attr_name] = value
            return obj
        return obj
    
    @staticmethod
    def _filter_append_attr(obj: Any, attr_name: str, value: Any) -> dict:
        """Append to attribute on field object."""
        if isinstance(obj, dict):
            obj = obj.copy()
            if 'attributes' not in obj:
                obj['attributes'] = {}
            if attr_name in obj['attributes']:
                obj['attributes'][attr_name] = f"{obj['attributes'][attr_name]} {value}"
            else:
                obj['attributes'][attr_name] = value
            return obj
        return obj
    
    @staticmethod
    def _filter_remove_attr(obj: Any, attr_name: str) -> dict:
        """Remove attribute from field object."""
        if isinstance(obj, dict):
            obj = obj.copy()
            if 'attributes' in obj:
                obj['attributes'] = {k: v for k, v in obj['attributes'].items() if k != attr_name}
            return obj
        return obj
    
    @staticmethod
    def _filter_field_type(obj: Any) -> str:
        """Get field type."""
        if isinstance(obj, dict):
            return obj.get('type', 'text')
        return 'text'


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
        
        # Create restricted execution namespace with only safe builtins
        # This prevents execution of dangerous functions like open(), __import__, etc.
        restricted_builtins = {
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sum': sum,
            'min': min,
            'max': max,
            'any': any,
            'all': all,
            'sorted': sorted,
            'reversed': reversed,
        }
        
        namespace = {
            '__builtins__': restricted_builtins,
            'context': ctx,
            'filters': self.filters,
            'tests': self.tests,
            'output': [],
            'Markup': Markup,
            'escape': escape,
        }
        
        # Execute compiled code in restricted namespace
        # This prevents injection of arbitrary Python code
        try:
            exec(compiled_code, namespace)
            render_func = namespace.get('render')
            if render_func:
                if asyncio.iscoroutinefunction(render_func):
                    result = await render_func(ctx, self.filters, self.tests, self)
                else:
                    result = render_func(ctx, self.filters, self.tests, self)
                return str(result)
        except SyntaxError as e:
            return f"[Syntax Error in compiled template: {str(e)}]"
        except RuntimeError as e:
            return f"[Runtime Error: {str(e)}]"
        except Exception as e:
            import traceback
            return f"[Execution Error: {str(e)}\n{traceback.format_exc()}]"
    
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
