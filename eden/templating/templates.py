
from __future__ import annotations
from typing import Any, Optional
from jinja2 import Environment
from markupsafe import Markup
from starlette.templating import Jinja2Templates as StarletteJinja2Templates
from .extensions import EdenDirectivesExtension
from .lexer import TokenType

# Default styles for the @dump directive
DEFAULT_DUMP_STYLE = (
    "eden-dump p-4 bg-gray-950 text-gray-300 rounded-lg overflow-auto "
    "text-xs font-mono border border-gray-800 my-4"
)

def render_fragment(
    env: Environment,
    template_name: str,
    fragment_name: str,
    context: dict[str, Any],
) -> str:
    """
    Render a single named fragment from a template.
    """
    block_fn_name = f"fragment_{fragment_name}"
    tmpl = env.get_template(template_name)

    if block_fn_name not in tmpl.blocks:
        raise KeyError(
            f"Fragment '{fragment_name}' not found in template '{template_name}'. "
            f"Make sure you defined @fragment(\"{fragment_name}\") {{ ... }} in the template."
        )

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
        if EdenDirectivesExtension not in kwargs["extensions"] and "eden.templating.EdenDirectivesExtension" not in kwargs["extensions"]:
            kwargs["extensions"].append(EdenDirectivesExtension)
        if "eden.components.ComponentExtension" not in kwargs["extensions"]:
            kwargs["extensions"].append("eden.components.ComponentExtension")

        super().__init__(directory=directory, **kwargs)

        # ── Register filters and globals ─────────────────────────────────────
        from . import filters
        
        self.env.filters["time_ago"] = filters.format_time_ago
        self.env.filters["money"] = filters.format_money
        self.env.filters["truncate"] = filters.truncate_filter
        self.env.filters["truncate_filter"] = filters.truncate_filter
        self.env.filters["slugify"] = filters.slugify_filter
        self.env.filters["slugify_filter"] = filters.slugify_filter
        self.env.filters["json"] = filters.json_encode
        self.env.filters["json_encode"] = filters.json_encode
        self.env.filters["default"] = filters.default_if_none
        self.env.filters["default_if_none"] = filters.default_if_none
        self.env.filters["pluralize"] = filters.pluralize_filter
        self.env.filters["pluralize_filter"] = filters.pluralize_filter
        self.env.filters["title"] = filters.title_case
        self.env.filters["date"] = filters.format_date
        self.env.filters["time"] = filters.format_time
        self.env.filters["number"] = filters.format_number
        self.env.filters["mask"] = filters.mask_filter
        self.env.filters["mask_filter"] = filters.mask_filter
        self.env.filters["file_size"] = filters.file_size_filter
        self.env.filters["file_size_filter"] = filters.file_size_filter
        self.env.filters["repeat"] = filters.repeat_filter
        self.env.filters["phone"] = filters.phone_filter
        self.env.filters["unique"] = filters.unique_filter
        self.env.filters["markdown"] = filters.markdown_filter
        self.env.filters["nl2br"] = filters.nl2br_filter
        
        # Form field styling filters
        self.env.filters["add_class"] = filters.add_class
        self.env.filters["remove_class"] = filters.remove_class
        self.env.filters["add_error_class"] = filters.add_error_class
        self.env.filters["attr"] = filters.attr
        self.env.filters["set_attr"] = filters.set_attr
        self.env.filters["append_attr"] = filters.append_attr
        self.env.filters["remove_attr"] = filters.remove_attr
        self.env.filters["add_error_attr"] = filters.add_error_attr
        self.env.filters["field_type"] = filters.field_type
        self.env.filters["widget_type"] = filters.widget_type
        
        self.env.globals["class_names"] = filters.class_names
        
        # ── Design System & HTMX filters ─────────────────────────────────────
        from eden.design import eden_color, eden_bg, eden_text, eden_border, eden_shadow, eden_font
        from eden.htmx import hx_vals, hx_headers
        
        self.env.filters["eden_color"] = eden_color
        self.env.filters["eden_bg"] = eden_bg
        self.env.filters["eden_text"] = eden_text
        self.env.filters["eden_border"] = eden_border
        self.env.filters["eden_shadow"] = eden_shadow
        self.env.filters["eden_font"] = eden_font
        self.env.filters["hx_vals"] = hx_vals
        self.env.filters["hx_headers"] = hx_headers
        
        # ── Imports for assets ───────────────────────────────────────────────
        from eden.assets import (
            ALPINE_VERSION,
            HTMX_VERSION,
            TAILWIND_VERSION,
            eden_head,
            eden_scripts,
        )
        self.env.globals["ALPINE_VERSION"] = ALPINE_VERSION
        self.env.globals["HTMX_VERSION"] = HTMX_VERSION
        self.env.globals["TAILWIND_VERSION"] = TAILWIND_VERSION
        
        # Low-case aliases for tests/convenience
        self.env.globals["alpine_version"] = ALPINE_VERSION
        self.env.globals["htmx_version"] = HTMX_VERSION
        self.env.globals["tailwind_version"] = TAILWIND_VERSION
        
        self.env.globals["eden_head"] = eden_head
        self.env.globals["eden_scripts"] = eden_scripts

    def _old_helper(self, name: str, default: Any = "") -> Any:
        """Helper for @old directive logic."""
        from eden.context import get_request
        request = get_request()
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

    def _csrf_helper(self) -> Markup:
        """Render a hidden CSRF token input field."""
        from eden.context import get_request
        request = get_request()
        token = ""
        if request and hasattr(request, "scope"):
            token = getattr(request.state, "csrf_token", "")
        return Markup(f'<input type="hidden" name="_token" value="{token}">')

    def _csrf_token_helper(self) -> str:
        """Render the raw CSRF token."""
        from eden.context import get_request
        request = get_request()
        if request and hasattr(request, "state"):
            return getattr(request.state, "csrf_token", "")
        return ""

    def _dump_helper(self, value: Any, label: str = "") -> Markup:
        """Premium @dump directive implementation."""
        import pprint
        formatted = pprint.pformat(value, indent=2)
        header = f'<div class="text-xs font-bold text-blue-400 mb-1">@dump: {label}</div>' if label else ""
        html = (
            f'<div class="{DEFAULT_DUMP_STYLE}">'
            f'{header}'
            f'<pre class="whitespace-pre-wrap"><code>{formatted}</code></pre>'
            f'</div>'
        )
        return Markup(html)

    def render(self, request: Any, template_name: str, context: dict[str, Any], **kwargs: Any) -> Any:
        """Convenience wrapper — preferred over ``TemplateResponse`` directly."""
        ctx = {"request": request, **context, **kwargs}
        return self.TemplateResponse(template_name, ctx)

def render_template(template_name: str, **context: Any) -> Any:
    """Render an HTML template using the current request context."""
    from eden.context import get_request
    request = get_request()
    if request is None:
        raise RuntimeError("render_template() must be called within a request context.")
    return request.app.render(template_name, **context)
