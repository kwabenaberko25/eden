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


class EdenDirectivesExtension(Extension):
    """
    Jinja2 extension that pre-processes Eden's modern syntax (@if, @for, etc.)
    """
    def preprocess(self, source: str, name: str | None, filename: str | None = None) -> str:
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
        
        # yield and stack
        source = re.sub(r'@yield\s*\(\s*[\'"]?([^\'"\)]+?)[\'"]?\s*\)', r'{% block \1 %}{% endblock %}', source)
        source = re.sub(r'@stack\s*\(\s*[\'"]?([^\'"\)]+?)[\'"]?\s*\)', r'{% block \1 %}{% endblock %}', source)
        source = re.sub(r'@render\s*\(\s*[\'"]?([^\'"\)]+?)[\'"]?\s*\)', r'{% block \1 %}{% endblock %}', source)
        source = re.sub(r'@show\s*\(\s*[\'"]?([^\'"\)]+?)[\'"]?\s*\)', r'{{ super() }}', source)

        # Complex single-line replacements that might span lines if formatted weirdly
        def _simple_replacer(m):
            # Map of common simple replacements
            text = m.group(0)
            if text.startswith('@extends'):
                res = f'{{% extends {m.group(1)} %}}'
            elif text.startswith('@include'):
                res = f'{{% include {m.group(1)} %}}'
            elif text.startswith('@super'):
                res = '{{ super() }}'
            else:
                res = text
            return _preserve_lines(text, res)

        source = re.sub(r'@extends\s*\(\s*([\'"].+?[\'"])\s*\)', _simple_replacer, source)
        source = re.sub(r'@include\s*\(\s*([\'"].+?[\'"])\s*\)', _simple_replacer, source)
        source = re.sub(r'@super\s*\(\s*\)|@super(?![\w(])', _simple_replacer, source)

        # Inline attribute directives
        def _attr_replacer(m):
            attr_dir = m.group(1)
            cond = m.group(2)
            res = f'{{% if {cond} %}}{attr_dir}{{% endif %}}'
            return _preserve_lines(m.group(0), res)

        source = re.sub(r'@(checked|selected|disabled|readonly)\s*\((.+?)\)', _attr_replacer, source)

        # @render_field integration
        def _render_field_replacer(m):
            field_expr = m.group(1).strip()
            raw_attrs = m.group(2)
            if not raw_attrs:
                res = f'{{{{ {field_expr}.render_composite() }}}}'
            else:
                pairs = re.findall(r'(\w[\w-]*)\s*=\s*"([^"]*)"', raw_attrs)
                attr_args = []
                for key, val in pairs:
                    # In python kwargs, we use 'class_' or just pass as str if using **dict
                    # But in Jinja call, field.render_composite(class="foo") works fine.
                    attr_args.append(f'{key}="{val}"')
                
                res = f'{{{{ {field_expr}.render_composite({", ".join(attr_args)}) }}}}'
            return _preserve_lines(m.group(0), res)

        source = re.sub(r'@render_field\s*\(\s*(.+?)\s*(?:,\s*(.+?))?\s*\)', _render_field_replacer, source)

        # 2. Block transitions (@else, @elif, @empty)
        # We must capture the whitespace/newlines to preserve them
        def _transition_replacer(m):
            text = m.group(0)
            if '@else if' in text or '@elif' in text:
                cond = m.group(1)
                res = f'{{% elif {cond} %}}'
            elif '@else' in text or '@empty' in text:
                res = '{% else %}'
            return _preserve_lines(text, res)

        source = re.sub(r'\}\s*@else\s*if\s*\((.*?)\)\s*\{', _transition_replacer, source)
        source = re.sub(r'\}\s*@else\s*\{', _transition_replacer, source)
        source = re.sub(r'\}\s*@empty\s*\{', _transition_replacer, source)

        # 3. Recursive Block Directives
        directives = [
            ("if", r'@if\s*\((.*?)\)\s*\{', r'{% if \1 %}', "endif"),
            ("unless", r'@unless\s*\((.*?)\)\s*\{', r'{% if not (\1) %}', "endif"),
            ("for", r'@(?:for|foreach)\s*\((.*?)\)\s*\{', r'{% for \1 %}', "endfor"),
            ("switch", r'@switch\s*\((.*?)\)\s*\{', r'{% with __sw = \1 %}', "endwith"),
            ("case", r'@case\s*\((.*?)\)\s*\{', r'{% if __sw == \1 %}', "endif"),
            ("auth", r'@auth\s*\{', 
             r'{% if request.user and request.user.is_authenticated %}', "endif"),
            ("guest", r'@guest\s*\{', 
             r'{% if not request.user or not request.user.is_authenticated %}', "endif"),
            ("htmx", r'@htmx\s*\{', 
             r'{% if request.headers.get("HX-Request") == "true" %}', "endif"),
            ("non_htmx", r'@non_htmx\s*\{', 
             r'{% if request.headers.get("HX-Request") != "true" %}', "endif"),
            ("section", r'@(?:section|block)\s*\(\s*[\'"]?([^\'"\)]+?)[\'"]?\s*\)\s*\{', 
             r'{% block \1 %}', "endblock"),
            ("push", r'@push\s*\(\s*[\'"](.+?)[\'"]\s*\)\s*\{', 
             r'{% block \1 %}{{ super() }}', "endblock"),
            ("fragment", r'@fragment\s*\(\s*[\'"](.+?)[\'"]\s*\)\s*\{', 
             r'{% block fragment_\1 %}', "endblock"),
            ("slot", r'@slot\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)\s*\{', 
             r'{% slot "\1" %}', "endslot"),
            ("component", r'@component\s*\(\s*[\'"]([^\'"]+)[\'"]\s*(?:,\s*(.+?))?\s*\)\s*\{', 
             None, "endcomponent"),
        ]

        def find_balancing_brace(text, start_pos):
            depth = 1
            for i in range(start_pos, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        return i
            return -1

        # Innermost-first replacement ensures nested components and blocks are handled correctly
        while True:
            best_match = None
            best_end = float('inf')

            for name, pattern, open_tmpl, close_tag in directives:
                # Use re.DOTALL to ensure we match across newlines in the pattern itself
                for match in re.finditer(pattern, source, re.DOTALL):
                    start_brace = match.end() - 1
                    end_brace = find_balancing_brace(source, start_brace + 1)
                    if end_brace != -1 and end_brace < best_end:
                        best_end = end_brace
                        best_match = (match, start_brace, end_brace, name, open_tmpl, close_tag)

            if not best_match:
                break

            match, start_brace, end_brace, name, open_tmpl, close_tag = best_match

            # Build opening tag
            if name == "component":
                comp_name = match.group(1)
                comp_kwargs = match.group(2) if match.group(2) else ""
                open_tag = f'{{% component "{comp_name}"{", " + comp_kwargs if comp_kwargs else ""} %}}'
            elif name == "for":
                inner = match.group(1).strip()
                # Handle '$' prefixes and 'as' keyword
                inner = inner.replace('$', '')
                if ' as ' in inner:
                    parts = inner.split(' as ')
                    if len(parts) == 2:
                        inner = f"{parts[1].strip()} in {parts[0].strip()}"
                open_tag = f'{{% for {inner} %}}'
            else:
                open_tag = open_tmpl
                for idx, g in enumerate(match.groups()):
                    val = g.replace('$', '') if g else g
                    open_tag = open_tag.replace(f'\\{idx+1}', val if val is not None else "")

            # Line preservation for opening tag
            open_tag = _preserve_lines(match.group(0), open_tag)

            close_tag_str = f"{{% {close_tag} %}}" if close_tag else ""
            content = source[start_brace+1 : end_brace]

            # Replace the block.
            source = source[:match.start()] + open_tag + content + close_tag_str + source[end_brace+1:]

        # Handle @let
        def _let_replacer(m):
            res = f'{{% set {m.group(1)} = {m.group(2)} %}}'
            return _preserve_lines(m.group(0), res)

        source = re.sub(r'@let\s*(.*?)\s*=\s*(.*?)\s*$', _let_replacer, source, flags=re.MULTILINE)

        # ── @url() ────────────────────────────────────────────────────────────
        # Normalize namespace:action  →  namespace_action  in the route name.
        def _normalise_route(raw_name: str) -> str:
            """'core:dashboard' → 'core_dashboard', 'dashboard' stays."""
            return raw_name.replace(':', '_')

        # Pattern shared by all @url variants:
        #   @url('name')                     - bare
        #   @url('ns:action')                - namespace shorthand
        #   @url('name', key=val, ...)       - with kwargs
        #   @url(...) as alias               - variable assignment
        _url_re = re.compile(
            r'@url\s*\(\s*[\'"]([^\'"]+)[\'"]\s*(?:,\s*([^)]+?))?\s*\)'
            r'(?:\s+as\s+(\w+))?',
            re.DOTALL,
        )

        def _url_replacer(m):
            raw_name  = _normalise_route(m.group(1))
            kwargs    = m.group(2)  # may be None
            alias     = m.group(3)  # may be None
            call_args = f'"{raw_name}"' + (f', {kwargs.strip()}' if kwargs else '')
            if alias:
                res = f'{{% set {alias} = url_for({call_args}) %}}'
            else:
                res = f'{{{{ url_for({call_args}) }}}}'
            return _preserve_lines(m.group(0), res)

        source = _url_re.sub(_url_replacer, source)

        # ── @active_link('route_or_ns:action', 'css_class') ──────────────────
        # Emits the css_class string when request.url.path matches the route.
        # Works inline inside any HTML attribute value.
        _active_re = re.compile(
            r'@active_link\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)',
            re.DOTALL,
        )

        def _active_replacer(m):
            raw_name = _normalise_route(m.group(1))
            css_cls  = m.group(2)
            res = (
                f'{{{{ "{css_cls}" if is_active(request, "{raw_name}") else "" }}}}'
            )
            return _preserve_lines(m.group(0), res)

        source = _active_re.sub(_active_replacer, source)

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

            Supports a simple prefix-match so that '/tasks/create' is considered
            active when the route resolves to '/tasks'.

            Usage in templates::

                class="nav-link {{ 'active' if is_active(request, 'dashboard') else '' }}"
            """
            try:
                resolved = str(request.url_for(route_name, **kwargs)).rstrip("/") or "/"
                current  = request.url.path.rstrip("/") or "/"
                return current == resolved or current.startswith(resolved + "/")
            except Exception:
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

        # Add common helpers
        context["route"] = context.get("route") or self.env.globals.get("url_for")

        return super().TemplateResponse(
            name, context, status_code, headers, media_type, background
        )

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

