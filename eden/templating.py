"""
Eden — Modern Templating Engine
"""

import datetime
import json as _json
import re
from typing import Any

from jinja2 import Environment
from jinja2.ext import Extension
from markupsafe import Markup
from starlette.background import BackgroundTask
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates as StarletteJinja2Templates
from eden.responses import HtmlResponse
# Default styles for the @dump directive
DEFAULT_DUMP_STYLE = (
    "eden-dump p-4 bg-gray-950 text-gray-300 rounded-lg overflow-auto "
    "text-xs font-mono border border-gray-800 my-4"
)


class EdenDirectivesExtension(Extension):
    """
    Jinja2 extension that pre-processes Eden's modern syntax (@if, @for, etc.)
    Ensures that directives are not replaced within strings or comments.
    """
    def preprocess(self, source: str, name: str | None, filename: str | None = None) -> str:
        # 0. Protection: Extract strings and comments to avoid accidental replacement
        protected_blocks = []
        def _protect(match):
            placeholder = f"__EDEN_PROTECTED_{len(protected_blocks)}__"
            protected_blocks.append(match.group(0))
            return placeholder

        # Protect HTML comments
        source = re.sub(r'<!--.*?-->', _protect, source, flags=re.DOTALL)
        # Protect single and double quoted strings (carefully)
        source = re.sub(r'\'[^\']*\'|"[^"]*"', _protect, source)

        def _preserve_lines(match_str: str, replacement: str) -> str:
            """Ensure replacement has same number of newlines as match_str."""
            original_lines = match_str.count('\n')
            replacement_lines = replacement.count('\n')
            if original_lines > replacement_lines:
                return replacement + ('\n' * (original_lines - replacement_lines))
            return replacement

        # 1. Simple replacements (no block context)
        source = re.sub(r'@csrf', r'<input type="hidden" name="csrf_token" value="{{ request.session.eden_csrf_token }}" />', source)
        source = re.sub(r'@eden_head', r'{{ eden_head() }}', source)
        source = re.sub(r'@eden_scripts', r'{{ eden_scripts() }}', source)
        
        # yield and stack fundamentals
        source = re.sub(r'@yield\s*\(\s*[\'"]?([^\'"\)]+?)[\'"]?\s*\)', r'{% block \1 %}{% endblock %}', source)
        source = re.sub(r'@render\s*\(\s*[\'"]?([^\'"\)]+?)[\'"]?\s*\)', r'{% block \1 %}{% endblock %}', source)
        source = re.sub(r'@show\s*\(\s*[\'"]?([^\'"\)]+?)[\'"]?\s*\)', r'{{ super() }}', source)

        # Basic Layout Helpers
        source = re.sub(r'@extends\s*\(\s*([\'"].+?[\'"])\s*\)', r'{% extends \1 %}', source)
        source = re.sub(r'@include\s*\(\s*([\'"].+?[\'"])\s*\)', r'{% include \1 %}', source)
        source = re.sub(r'@super\s*\(\s*\)|@super(?![\w(])', r'{{ super() }}', source)

        # Form Helpers
        source = re.sub(r'@method\s*\(\s*[\'"](.+?)[\'"]\s*\)', r'<input type="hidden" name="_method" value="\1" />', source)
        
        # Asset helpers
        source = re.sub(r'@css\s*\(\s*[\'"](.+?)[\'"]\s*\)', r'<link rel="stylesheet" href="{{ url_for("static", path="\1") }}" />', source)
        source = re.sub(r'@js\s*\(\s*[\'"](.+?)[\'"]\s*\)', r'<script src="{{ url_for("static", path="\1") }}"></script>', source)
        source = re.sub(r'@vite\s*\(\s*((?:[^()]|\([^()]*\))*)\s*\)', r'{{ vite(\1) }}', source)

        # Value helpers
        source = re.sub(r'@old\s*\(\s*[\'"](.+?)[\'"]\s*(?:,\s*(.+?))?\s*\)', 
                        lambda m: f'{{{{ old("{m.group(1)}", {m.group(2) or "None"}) }}}}', source)
        source = re.sub(r'@span\s*\(((?:[^()]|\([^()]*\))*)\)', lambda m: f'{{{{ {m.group(1).replace("$", "")} }}}}' if m.group(1) else "", source)
        source = re.sub(r'@json\s*\(((?:[^()]|\([^()]*\))*)\)', r'{{ \1 | json_encode }}', source)
        source = re.sub(r'@dump\s*\(((?:[^()]|\([^()]*\))*)\)', fr'<div class="{DEFAULT_DUMP_STYLE}"><pre>{{{{ \1 | json_encode(indent=4) }}}}</pre></div>', source)
        source = re.sub(r'@status\s*\(\s*(\d+)\s*\)', r'{{ set_response_status(\1) }}', source)

        # Inline attribute directives
        source = re.sub(r'@(checked|selected|disabled|readonly)\s*\((.+?)\)', 
                        lambda m: f'{{% if {m.group(2)} %}}{m.group(1)}{{% endif %}}', source)

        # @props directive
        def _props_replacer(m):
            import ast
            raw_props = m.group(1).strip()
            try:
                props_dict = ast.literal_eval(raw_props)
                res_lines = []
                for k, v in props_dict.items():
                    jinja_val = _json.dumps(v)
                    res_lines.append(f'{{% set {k} = {k} if {k} is defined else {jinja_val} %}}')
                return "\n".join(res_lines)
            except Exception:
                return m.group(0)
        source = re.sub(r'@props\s*\(\s*(\{.*?\})\s*\)', _props_replacer, source, flags=re.DOTALL)

        # Recursive Block Directives
        # Format: (name, pattern, open_tag_tmpl or callback, close_tag_name)
        directives = [
            ("if", r'@if\s*\((.*?)\)\s*\{', r'{% if \1 %}', "endif"),
            ("unless", r'@unless\s*\((.*?)\)\s*\{', r'{% if not (\1) %}', "endif"),
            ("for", r'@(?:for|foreach)\s*\((.*?)\)\s*\{', None, "endfor"),
            ("switch", r'@switch\s*\((.*?)\)\s*\{', None, "endwith"),
            ("case", r'@case\s*\((.*?)\)\s*\{', r'__EDEN_CASE__(\1)__', "__EDEN_ENDCASE__"),
            ("default", r'@default\s*\{', r'__EDEN_DEFAULT__', "__EDEN_ENDDEFAULT__"),
            ("auth", r'@auth(?:\s*\((.*?)\))?\s*\{', None, "endif"),
            ("guest", r'@guest\s*\{', r'{% if not (request.user and request.user.is_authenticated) %}', "endif"),
            ("htmx", r'@htmx\s*\{', r'{% if request.headers.get("HX-Request") == "true" %}', "endif"),
            ("fragment", r'@fragment\s*\("(.*?)"\)\s*\{', r'{% block fragment_\1 %}', "endblock"),
            ("push", r'@push\s*\("(.*?)"\)\s*\{', r'{{ eden_push("\1", """', '""") }}'),
            ("verbatim", r'@verbatim\s*\{', r'{% raw %}', "endraw"),
            ("error", r'@error\s*\(\s*[\'"]?([^\'"\s\)]+?)[\'"]?\s*\)\s*\{', 
             r'{% if errors and errors.has("\1") %}{% set error = errors.first("\1") %}', "endif"),
        ]

        def find_balancing_brace(text, start_pos):
            depth = 1
            for i in range(start_pos, len(text)):
                if text[i] == '{': depth += 1
                elif text[i] == '}': 
                    depth -= 1
                    if depth == 0: return i
            return -1

        while True:
            best_match = None
            best_end = float('inf')

            for name, pattern, open_tmpl, close_tag in directives:
                for match in re.finditer(pattern, source, re.DOTALL):
                    start_brace = match.end() - 1
                    end_brace = find_balancing_brace(source, start_brace + 1)
                    if end_brace != -1 and end_brace < best_end:
                        best_end = end_brace
                        best_match = (match, start_brace, end_brace, name, open_tmpl, close_tag)

            if not best_match: break

            match, start_brace, end_brace, name, open_tmpl, close_tag = best_match
            body = source[start_brace+1 : end_brace]
            
            if name == "for":
                inner = match.group(1).replace('$', '')
                if ' as ' in inner:
                    parts = inner.split(' as ')
                    inner = f"{parts[1].strip()} in {parts[0].strip()}"
                open_tag = f'{{% for {inner} %}}'
            elif name == "switch":
                # Convert markers inside body to exclusive if/elif
                cases_replaced = 0
                def _case_cb(cm):
                    nonlocal cases_replaced
                    res = f"{{% {'if' if cases_replaced == 0 else 'elif'} __sw == {cm.group(1)} %}}"
                    cases_replaced += 1
                    return res
                body = re.sub(r'__EDEN_CASE__\((.*?)\)__', _case_cb, body)
                body = body.replace('__EDEN_ENDCASE__', '').replace('__EDEN_DEFAULT__', '{% else %}').replace('__EDEN_ENDDEFAULT__', '')
                if cases_replaced > 0: body += "{% endif %}"
                open_tag = f'{{% with __sw = {match.group(1)} %}}'
            elif name == "auth":
                raw_args = match.group(1)
                if raw_args:
                    roles_list = [r.strip().strip("'\"").replace('$', '') for r in raw_args.split(',')]
                    cond = f'request.user.role == "{roles_list[0]}"' if len(roles_list) == 1 else f'request.user.role in {roles_list}'
                    open_tag = f'{{% if request.user and request.user.is_authenticated and {cond} %}}'
                else:
                    open_tag = '{% if request.user and request.user.is_authenticated %}'
            else:
                open_tag = open_tmpl
                for idx, g in enumerate(match.groups()):
                    open_tag = open_tag.replace(f'\\{idx+1}', (g or "").replace('$', ''))

            # Apply replacement
            source = source[:match.start()] + open_tag + body + (f"{{% {close_tag} %}}" if close_tag else "") + source[end_brace+1:]

        # ── @url() & @active_link() ───────────────────────────────────────────
        def _url_normalise(raw): return raw.replace(':', '_')
        
        def _url_replacer(m):
            raw_name, kwargs, alias = m.group(1), m.group(2), m.group(3)
            if raw_name.startswith("component:"):
                args = f'"component:dispatch", action_slug="{raw_name.split(":")[1]}"' + (f", {kwargs.strip()}" if kwargs else "")
            else:
                args = f'"{_url_normalise(raw_name)}"' + (f", {kwargs.strip()}" if kwargs else "")
            res = f'{{% set {alias} = url_for({args}) %}}' if alias else f'{{{{ url_for({args}) }}}}'
            return res

        source = re.sub(r'@url\s*\(\s*[\'"]([^\'"]+)[\'"]\s*(?:,\s*([^)]+?))?\s*\)(?:\s+as\s+(\w+))?', _url_replacer, source)

        def _active_replacer(m):
            arg1, css = m.group(1).strip(), m.group(2)
            if (arg1.startswith("'") or arg1.startswith('"')):
                res = f'{{{{ "{css}" if is_active(request, "{_url_normalise(arg1[1:-1])}") else "" }}}}'
            else:
                res = f'{{{{ "{css}" if is_active(request, {arg1}) else "" }}}}'
            return res

        source = re.sub(r'@active_link\s*\(\s*(.+?)\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)', _active_replacer, source)

        # ── Security: Automate target="_blank" protection ─────────────────────
        def _enforce_noopener(m):
            tag = m.group(0)
            if 'rel=' not in tag.lower(): return tag[:-1] + ' rel="noopener noreferrer">'
            return tag
        source = re.sub(r'<a\s+[^>]*?target=[\'"]_blank[\'"][^>]*>', _enforce_noopener, source, flags=re.IGNORECASE)

        # 4. Restoration: Bring back protected strings and comments
        for i, original in enumerate(protected_blocks):
            source = source.replace(f"__EDEN_PROTECTED_{i}__", original)

        return source


def format_time_ago(value: datetime.datetime) -> str:
    """
    Format a datetime as a human-readable "time ago" string.
    """
    if not value:
        return ""

    now = datetime.datetime.now()
    if value.tzinfo:
        now = datetime.datetime.now(value.tzinfo)

    diff = now - value

    if diff.days > 365:
        return f"{diff.days // 365} years ago"
    if diff.days > 30:
        return f"{diff.days // 30} months ago"
    if diff.days > 0:
        return f"{diff.days} days ago"
    if diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    if diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    return "just now"

def format_money(value: int | float | None, currency: str = "$") -> str:
    """
    Format a value as currency.
    """
    if value is None:
        return ""
    return f"{currency}{value:,.2f}"

def class_names(base: str, conditions: dict[str, bool]) -> str:
    """
    Angular-style class names helper.
    """
    classes = [base]
    for cls, cond in conditions.items():
        if cond:
            classes.append(cls)
    return " ".join(classes)

# ─────────────────────────────────────────────────────────────────────────────
# Widget tweaks helpers (Jinja filters)
# ─────────────────────────────────────────────────────────────────────────────

def add_class(field: Any, css_class: str) -> Any:
    if hasattr(field, "add_class"):
        return field.add_class(css_class)
    return field

def remove_class(field: Any, css_class: str) -> Any:
    if hasattr(field, "remove_class"):
        return field.remove_class(css_class)
    return field

def add_error_class(field: Any, css_class: str) -> Any:
    if hasattr(field, "add_error_class"):
        return field.add_error_class(css_class)
    return field

def attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "attr"):
        return field.attr(name, str(value))
    return field

def set_attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "set_attr"):
        return field.set_attr(name, str(value))
    return field

def append_attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "append_attr"):
        return field.append_attr(name, str(value))
    return field

def remove_attr(field: Any, name: str) -> Any:
    if hasattr(field, "remove_attr"):
        return field.remove_attr(name)
    return field

def add_error_attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "add_error_attr"):
        return field.add_error_attr(name, str(value))
    return field

def field_type(field: Any) -> str:
    if hasattr(field, "field_type"):
        return field.field_type
    return ""

def widget_type(field: Any) -> str:  # pragma: nocover – simple proxy
    if hasattr(field, "widget_type"):
        return field.widget_type
    return ""

# ─────────────────────────────────────────────────────────────────────────────
# Utility filters
# ─────────────────────────────────────────────────────────────────────────────

def truncate_filter(value: Any, length: int = 50, end: str = "…") -> str:
    """Truncate a string to *length* characters, appending *end* if truncated."""
    s = str(value)
    if len(s) <= length:
        return s
    return s[:length].rstrip() + end


def slugify_filter(value: Any) -> str:
    """Convert text to a URL-friendly slug."""
    s = str(value).lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    return re.sub(r'[\s_]+', '-', s).strip('-')


def json_encode(value: Any) -> str:
    """Serialize value to JSON (safe for ``x-data`` attributes)."""
    return Markup(_json.dumps(value))


def default_if_none(value: Any, default: Any = "") -> Any:
    """Return *default* when *value* is ``None``."""
    return default if value is None else value


def pluralize_filter(count: Any, singular: str = "", plural: str = "s") -> str:
    """Return *singular* or *plural* suffix based on *count*."""
    try:
        n = int(count)
    except (TypeError, ValueError):
        n = 0
    return singular if n == 1 else plural


def title_case(value: Any) -> str:
    """Convert text to Title Case."""
    return str(value).title()


def mask_filter(value: Any) -> str:
    """Mask a string, showing first and last character (e.g. emails → ``u***@e.com``)."""
    s = str(value)
    if "@" in s:
        local, domain = s.split("@", 1)
        masked_local = local[0] + "***" if local else "***"
        return f"{masked_local}@{domain}"
    if len(s) <= 2:
        return "*" * len(s)
    return s[0] + "*" * (len(s) - 2) + s[-1]


def file_size_filter(value: Any) -> str:
    """Format a byte count as a human-readable file size."""
    try:
        size = float(value)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


# ─────────────────────────────────────────────────────────────────────────────
# Fragment extraction helper
# ─────────────────────────────────────────────────────────────────────────────

def render_fragment(
    env: Environment,
    template_name: str,
    fragment_name: str,
    context: dict[str, Any],
) -> str:
    """
    Render a single named fragment from a template.

    Fragments are defined with ``@fragment("name") { ... }`` in the template.
    Internally they become Jinja2 ``{% block fragment_<name> %}`` blocks.

    Usage::

        html = render_fragment(env, "page.html", "inbox", {"messages": msgs})

    Returns the rendered HTML string for only that fragment.
    """
    block_fn_name = f"fragment_{fragment_name}"
    tmpl = env.get_template(template_name)

    if block_fn_name not in tmpl.blocks:
        raise KeyError(
            f"Fragment '{fragment_name}' not found in template '{template_name}'. "
            f"Make sure you defined @fragment(\"{fragment_name}\") {{ ... }} in the template."
        )

    # Build a real Jinja2 context and call the block render function directly.
    # template.blocks[name] is a callable that yields rendered string chunks.
    ctx = tmpl.new_context(context.copy())
    block_gen = tmpl.blocks[block_fn_name](ctx)
    return Markup("".join(block_gen))


class EdenTemplates(StarletteJinja2Templates):
    """
    Jinja2 templates with Eden logic.
    """

    def template_response(self, *args, **kwargs) -> Any:
        return self.TemplateResponse(*args, **kwargs)

    def __init__(self, directory: str | list[str], **kwargs: Any):
        if "extensions" not in kwargs:
            kwargs["extensions"] = []
        if "eden.templating.EdenDirectivesExtension" not in kwargs["extensions"]:
            kwargs["extensions"].append(EdenDirectivesExtension)
        if "eden.components.ComponentExtension" not in kwargs["extensions"]:
            kwargs["extensions"].append("eden.components.ComponentExtension")

        super().__init__(directory=directory, **kwargs)

        # ── Imports for filters / globals ────────────────────────────────────
        from eden.assets import (
            ALPINE_VERSION,
            HTMX_VERSION,
            TAILWIND_VERSION,
        )
        from eden.assets import (
            eden_head as _eden_head,
        )
        from eden.assets import (
            eden_scripts as _eden_scripts,
        )
        from eden.design import (
            eden_bg,
            eden_border,
            eden_color,
            eden_font,
            eden_shadow,
            eden_text,
        )
        from eden.htmx import hx_headers, hx_vals

        # Add default filters
        self.env.filters.update({
            # Built-in helpers
            "time_ago": format_time_ago,
            "money": format_money,
            "class_names": class_names,
            # Widget tweaks
            "add_class": add_class,
            "remove_class": remove_class,
            "add_error_class": add_error_class,
            "attr": attr,
            "set_attr": set_attr,
            "append_attr": append_attr,
            "remove_attr": remove_attr,
            "add_error_attr": add_error_attr,
            "field_type": field_type,
            "widget_type": widget_type,
            # Utility filters
            "truncate": truncate_filter,
            "slugify": slugify_filter,
            "json_encode": json_encode,
            "default_if_none": default_if_none,
            "pluralize": pluralize_filter,
            "title_case": title_case,
            "mask": mask_filter,
            "file_size": file_size_filter,
            # Design system
            "eden_color": eden_color,
            "eden_bg": eden_bg,
            "eden_text": eden_text,
            "eden_border": eden_border,
            "eden_shadow": eden_shadow,
            "eden_font": eden_font,
            # HTMX
            "hx_vals": hx_vals,
            "hx_headers": hx_headers,
        })

        # ── is_active() helper ────────────────────────────────────────────────
        def is_active(request: Any, route_name: str, **kwargs: Any) -> bool:
            """
            Return True when *request.url.path* matches the URL for *route_name*.

            Supports:
            - Exact route matching: 'dashboard'
            - Namespace routes: 'auth:login' (converted to 'auth_login')
            - Wildcard routes: 'students:*' (matches matches prefix of any resolved route starting with the namespace)
            - Prefix matching: If the current path starts with the resolved route path.

            Usage in templates::
                class="nav-link {{ 'active' if is_active(request, 'dashboard') else '' }}"
            """
            import logging
            logger = logging.getLogger("eden.templating")
            
            # Normalize path: /foo/ -> /foo
            current = request.url.path.rstrip("/") or "/"
            
            try:
                # 1. Handle wildcard routes (e.g., 'students:*' or 'admin:*')
                if route_name.endswith('*'):
                    # Convert 'students:*' -> 'students'
                    prefix = route_name[:-1].rstrip(':_').replace(':', '_')
                    
                    # Instead of guessing suffixes, we look for ANY route that starts with this prefix
                    # We'll use the first one we find to determine the base URL path.
                    from starlette.routing import Mount, Route
                    
                    base_path = None
                    
                    # We need to find the base path for this namespace
                    # A robust way is to check the app's route list
                    app = request.app
                    for route in app.routes:
                        # Check if route is a Mount or a Route with a name starting with our prefix
                        if hasattr(route, "name") and route.name and route.name.startswith(prefix):
                            try:
                                # Resolve this specific route to get its path
                                resolved = str(request.url_for(route.name, **kwargs)).rstrip("/") or "/"
                                # The base path is the common part. For a namespace, 
                                # it's usually everything up to the first param or the end of the namespace part.
                                # Heuristic: if route name is 'students_index', and path is '/students', 
                                # then '/students' is our base.
                                base_path = resolved
                                break
                            except Exception:
                                continue
                    
                    if base_path:
                        return current == base_path or current.startswith(base_path + "/")
                    
                    logger.debug(f"is_active: Could not resolve any route for wildcard '{route_name}'")
                    return False
                
                # 2. Normal (non-wildcard) route matching
                resolved = str(request.url_for(route_name, **kwargs)).rstrip("/") or "/"
                
                # Match if exact or if current is a sub-path (e.g. /tasks/1 is active for /tasks)
                return current == resolved or current.startswith(resolved + "/")
                
            except Exception as e:
                # Log the error for easier debugging
                logger.debug(f"is_active: Error resolving route '{route_name}': {e}")
                return False

        # Add default globals
        self.env.globals.update({
            "now": datetime.datetime.now,
            "is_active": is_active,
            "eden_head": _eden_head,
            "eden_scripts": _eden_scripts,
            "alpine_version": ALPINE_VERSION,
            "htmx_version": HTMX_VERSION,
            "tailwind_version": TAILWIND_VERSION,
            "old": self._old_helper,
            "vite": self._vite_helper,
        })

        # ── Messaging helper ──────────────────────────────────────────────────
        def eden_messages() -> list:
            """Retrieve and clear messages from the current request."""
            from eden.context import get_request
            request = get_request()
            if request:
                return list(request.messages)
            return []

        # ── Stack helpers ───────────────────────────────────────────────────
        stacks = {}
        def eden_push(name: str, content: str):
            if name not in stacks:
                stacks[name] = []
            stacks[name].append(content)
            return ""

        def eden_stack(name: str):
            res = "\n".join(stacks.get(name, []))
            # Optional: clear after use? usually not for stacks
            return res

        self.env.globals.update({
            "eden_messages": eden_messages,
            "eden_push": eden_push,
            "eden_stack": eden_stack,
        })

    def TemplateResponse(
        self,
        name: str,
        context: dict[str, Any],
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> Any:
        """
        Returns a response that renders a template.

        HTMX Auto-Fragment Detection
        ────────────────────────────
        If the request carries the ``HX-Request`` header, Eden looks for the
        ``HX-Target`` header (or an explicit ``hx-fragment`` context key) and
        automatically renders only that named fragment instead of the full page.

        Template authors don't need to write separate views — just mark regions::

            @fragment("inbox") {
              <ul>...</ul>
            }
        """
        # Ensure 'request' is in context for Starlette
        if "request" not in context:
            from eden.context import get_request
            context["request"] = get_request()

        request = context.get("request")

        # ── Context Injection (Tenant & User) ─────────────────────────────────
        if "current_tenant" not in context:
            from eden.tenancy.context import get_current_tenant
            from eden.tenancy.models import AnonymousTenant
            context["current_tenant"] = get_current_tenant() or AnonymousTenant()
            
        if "user" not in context:
            from eden.context import get_user
            context["user"] = get_user()

        # ── HTMX fragment auto-detection ──────────────────────────────────────
        if request is not None:
            # Check if this is an HTMX request
            is_htmx = getattr(request, "headers", {}).get("HX-Request") == "true"

            # Explicit override: caller can pass fragment="inbox" in context
            fragment_name = context.pop("fragment", None)

            # Or derive from HX-Target header (strip leading # if present)
            if not fragment_name and is_htmx:
                hx_target = getattr(request, "headers", {}).get("HX-Target", "")
                if hx_target:
                    fragment_name = hx_target.lstrip("#")

            if fragment_name:
                try:
                    html = render_fragment(self.env, name, fragment_name, context)
                    response_headers = dict(headers or {})
                    return HtmlResponse(
                        content=str(html),
                        status_code=status_code,
                        headers=response_headers,
                    )
                except (KeyError, ValueError):
                    # Fallback to full template if fragment not found
                    pass
        # ─────────────────────────────────────────────────────────────────────

        # ── Status Code Control ───────────────────────────────────────────────
        status_box = {"code": status_code}
        def set_response_status(code: int):
            status_box["code"] = code
            return ""
        
        context["set_response_status"] = set_response_status
        # ─────────────────────────────────────────────────────────────────────

        # Add common helpers
        context["route"] = context.get("route") or self.env.globals.get("url_for")

        response = super().TemplateResponse(
            name, context, status_code, headers, media_type, background
        )
        # Apply the status code if it was changed during rendering
        if status_box["code"] != status_code:
            response.status_code = status_box["code"]
        return response

    def _old_helper(self, name: str, default: Any = "") -> Any:
        """Helper for @old directive to retrieve previous form data."""
        from eden.context import get_request
        request = get_request()
        # 1. Check form in context (passed by app.validate)
        # We need to access the active context. Jinja globals don't have it easily.
        # But we can try to get it from a thread-local or the request itself.
        # For now, let's assume 'form' might be in the current rendering context.
        # However, TemplateResponse doesn't store the context it's currently rendering.
        # A better way is to use a contextfilter but we are in a global.
        
        # Fallback: check session if available
        if request and hasattr(request, "session"):
            old_data = request.session.get("_old_input", {})
            return old_data.get(name, default)
        
        return default

    def _vite_helper(self, inputs: str | list[str]) -> Markup:
        """Placeholder for Vite asset loading."""
        if isinstance(inputs, str):
            inputs = [inputs]
        
        tags = []
        for inp in inputs:
            if inp.endswith(".css"):
                tags.append(f'<link rel="stylesheet" href="/{inp}">')
            else:
                tags.append(f'<script type="module" src="/{inp}"></script>')
        return Markup("\n".join(tags))

    def render(self, request: Any, template_name: str, context: dict[str, Any], **kwargs: Any) -> Any:
        """
        Convenience wrapper — preferred over ``TemplateResponse`` directly.

        Usage in a view::

            return templates.render(request, "inbox.html", {"messages": msgs})

        HTMX requests are handled automatically.
        """
        ctx = {"request": request, **context, **kwargs}
        return self.TemplateResponse(template_name, ctx)


def render_template(template_name: str, **context: Any) -> Any:
    """
    Render an HTML template using the current request context.

    This is a shortcut for ``request.app.render(template_name, **context)``.
    It automatically handles HTMX fragment rendering and injects standard
    context variables (request, user, tenant).

    Usage:
        return render_template("home.html", title="Home Page")
    """
    from eden.context import get_request
    request = get_request()
    if request is None:
        raise RuntimeError("render_template() must be called within a request context.")

    return request.app.render(template_name, **context)

