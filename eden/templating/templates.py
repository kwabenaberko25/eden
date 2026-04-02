from __future__ import annotations
import logging
from typing import Any, Optional
from jinja2 import Undefined
from jinja2.sandbox import SandboxedEnvironment
from markupsafe import Markup
from starlette.templating import Jinja2Templates as StarletteJinja2Templates
from .extensions import EdenDirectivesExtension
from .lexer import TokenType

# Default styles for the @dump directive
DEFAULT_DUMP_STYLE = (
    "eden-dump p-4 bg-gray-950 text-gray-300 rounded-lg overflow-auto "
    "text-xs font-mono border border-gray-800 my-4"
)

_safe_undefined_logger = logging.getLogger("eden.templating.undefined")

# Module-level flag set by EdenTemplates.__init__ to propagate debug mode
# into EdenSafeUndefined without requiring access to the Jinja env.
_eden_debug_mode: bool = False


class EdenSafeUndefined(Undefined):
    """
    Custom Jinja2 Undefined that degrades gracefully instead of crashing.

    Behaviour is configurable based on the module-level ``_eden_debug_mode``:
    - **Production** (False): Returns an empty string, making missing
      variables invisible in rendered output while logging a warning.
    - **Debug** (True): Returns a visible placeholder like
      ``[UNDEFINED: variable_name]`` so developers can spot missing context
      variables during development.

    The flag is set by ``EdenTemplates.__init__`` at startup.

    Examples:
        >>> from jinja2.sandbox import SandboxedEnvironment
        >>> env = SandboxedEnvironment(undefined=EdenSafeUndefined)
        >>> env.from_string("Hello {{ user.name }}").render()
        'Hello '  # production mode — empty string, warning logged
    """

    def __str__(self) -> str:
        """Return empty string or debug placeholder instead of raising."""
        # Determine variable name for logging
        hint = self._undefined_hint
        name = self._undefined_name or "unknown"
        obj = self._undefined_obj

        if obj is not None:
            description = f"{type(obj).__name__}.{name}"
        elif hint:
            description = hint
        else:
            description = name

        _safe_undefined_logger.warning(
            "Template referenced undefined variable: '%s'",
            description,
        )

        # In debug mode, return a visible placeholder for developers
        if _eden_debug_mode:
            return f"[UNDEFINED: {description}]"

        return ""

    def __iter__(self):
        """Return empty iterator instead of raising."""
        _safe_undefined_logger.warning(
            "Template iterated over undefined variable: '%s'",
            self._undefined_name or "unknown",
        )
        return iter([])

    def __bool__(self) -> bool:
        """Undefined is always falsy."""
        return False

    def __len__(self) -> int:
        """Undefined has zero length."""
        return 0

    def __eq__(self, other: Any) -> bool:
        """Undefined equals only other Undefined instances or None."""
        return isinstance(other, Undefined) or other is None

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return id(type(self))

    def __getattr__(self, name: str) -> "EdenSafeUndefined":
        """Chained attribute access returns another safe undefined."""
        if name.startswith("_"):
            raise AttributeError(name)
        return EdenSafeUndefined(
            hint=self._undefined_hint,
            obj=self._undefined_obj,
            name=name,
            exc=self._undefined_exception,
        )

    def __getitem__(self, name: str) -> "EdenSafeUndefined":
        """Item access returns another safe undefined."""
        return self.__getattr__(str(name))

    def __call__(self, *args: Any, **kwargs: Any) -> "EdenSafeUndefined":
        """Calling an undefined returns another safe undefined."""
        _safe_undefined_logger.warning(
            "Template called undefined as function: '%s'",
            self._undefined_name or "unknown",
        )
        return EdenSafeUndefined(
            hint=self._undefined_hint,
            obj=self._undefined_obj,
            name=self._undefined_name,
            exc=self._undefined_exception,
        )


def get_sync_channel(obj: Any) -> str:
    """
    Helper to resolve a sync channel from an object or class.
    Bridges to the shared get_reactive_channels logic.
    """
    if obj is None:
        return ""

    from eden.db.reactive import get_reactive_channels

    channels = get_reactive_channels(obj)

    if not channels:
        return str(obj)

    # Priority: user-specific > instance-specific > collection-specific
    user_channels = [c for c in channels if ":user:" in c]
    if user_channels:
        return user_channels[-1]

    return channels[-1]


def render_fragment(
    env: Environment,
    template_name: str,
    fragment_name: str,
    context: dict[str, Any],
) -> str:
    """
    Render a single named fragment from a template.
    """
    import logging

    log = logging.getLogger("eden.templating")

    block_fn_name = f"fragment_{fragment_name}"
    tmpl = env.get_template(template_name)

    if block_fn_name not in tmpl.blocks:
        available = [
            b.replace("fragment_", "") for b in tmpl.blocks.keys() if b.startswith("fragment_")
        ]
        raise KeyError(
            f"Fragment '{fragment_name}' not found in template '{template_name}'. "
            f"Available fragments: {available}"
        )

    ctx = tmpl.new_context(context.copy())
    block_gen = tmpl.blocks[block_fn_name](ctx)
    return Markup("".join(block_gen))


class EdenTemplates(StarletteJinja2Templates):
    """
    Jinja2 templates with Eden logic.
    """

    def TemplateResponse(
        self,
        request: Any,
        name: str,
        context: Optional[dict] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Custom TemplateResponse that implements Smart Fragment Resolution.
        If the request is an HTMX request with a target ID that matches a
        fragment in the template, only that fragment will be rendered.
        """
        context = context or {}
        if "request" not in context:
            context["request"] = request

        # Auto-inject user from request state if present for developer convenience
        if "user" not in context and hasattr(request.state, "user"):
            context["user"] = request.state.user

        # Initialize reactive channel set for server-side verification
        if not hasattr(request.state, "eden_channels"):
            request.state.eden_channels = set()

        from eden.htmx import is_htmx, hx_target, HtmxResponse

        if is_htmx(request):
            # 1. Look for explicit fragment override in context
            target_fragment = context.get("__fragment__")

            # 2. Look for HX-Target if no explicit fragment
            if not target_fragment:
                target_fragment = hx_target(request)

            if target_fragment:
                if target_fragment.startswith("#"):
                    target_fragment = target_fragment[1:]
                # Normalize hyphens to underscores for Jinja2 block names
                target_fragment = target_fragment.replace("-", "_")

            if target_fragment:
                try:
                    # Attempt to render requested fragment
                    content = render_fragment(self.env, name, target_fragment, context)
                    return HtmxResponse(content, *args, **kwargs)
                except KeyError as e:
                    # Fragment not found, fall back to full page render
                    import logging

                    log = logging.getLogger("eden.templating")
                    log.debug(
                        f"Fragment '{target_fragment}' not found, falling back to full render: {e}"
                    )
                    pass

        # Fallback to standard full template response
        return super().TemplateResponse(request, name, context, *args, **kwargs)

    # Legacy/Compatibility alias
    template_response = TemplateResponse

    def __init__(self, directory: str | list[str], **kwargs: Any):
        # Propagate debug mode to the module-level flag so EdenSafeUndefined
        # can return visible placeholders during development.
        global _eden_debug_mode
        _eden_debug_mode = kwargs.pop("debug", False)

        if "extensions" not in kwargs:
            kwargs["extensions"] = []

        # Core Eden Extensions
        required_exts = [
            EdenDirectivesExtension,
            "jinja2.ext.loopcontrols",
            "jinja2.ext.do",
        ]

        # Attempt to add the component extension — degrade gracefully if unavailable
        try:
            from eden.components import ComponentExtension  # noqa: F401

            required_exts.append("eden.components.ComponentExtension")
        except ImportError:
            import logging

            logging.getLogger("eden.templating").warning(
                "eden.components.ComponentExtension unavailable. "
                "Template engine will work without component support."
            )

        for ext in required_exts:
            if ext not in kwargs["extensions"] and str(ext) not in [
                str(e) for e in kwargs["extensions"]
            ]:
                kwargs["extensions"].append(ext)

        # To avoid Starlette deprecation warnings, we create the environment explicitly
        from jinja2 import FileSystemLoader

        loader = FileSystemLoader(directory)

        # Inject EdenSafeUndefined for graceful missing-variable handling.
        # The 'undefined' kwarg is only set if the caller hasn't overridden it.
        kwargs.setdefault("undefined", EdenSafeUndefined)

        # Wrap Environment creation so a single broken extension doesn't prevent
        # the entire template engine from loading.
        # SECURITY: SandboxedEnvironment blocks access to dangerous Python
        # internals (__subclasses__, __globals__, os.system, etc.).
        try:
            env = SandboxedEnvironment(loader=loader, **kwargs)
        except Exception as ext_err:
            log = logging.getLogger("eden.templating")
            log.warning(
                f"Jinja2 SandboxedEnvironment creation failed with extensions: {ext_err}. "
                f"Retrying with only core extensions."
            )
            # Retry with minimal extensions
            kwargs["extensions"] = [
                EdenDirectivesExtension,
                "jinja2.ext.loopcontrols",
                "jinja2.ext.do",
            ]
            env = SandboxedEnvironment(loader=loader, **kwargs)

        super().__init__(env=env)

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

        # ── Register globals ─────────────────────────────────────────────────
        self.env.globals["json"] = filters.json_encode
        self.env.globals["json_encode"] = filters.json_encode

        # Standard context globals
        from eden import components

        self.env.globals["render_component"] = components.render_component
        self.env.filters["set_attr"] = filters.set_attr
        self.env.filters["append_attr"] = filters.append_attr
        self.env.filters["remove_attr"] = filters.remove_attr
        self.env.filters["add_error_attr"] = filters.add_error_attr
        self.env.filters["field_type"] = filters.field_type
        self.env.filters["widget_type"] = filters.widget_type

        self.env.globals["class_names"] = filters.class_names

        # ── Design System & HTMX filters ─────────────────────────────────────
        try:
            from eden.design import (
                eden_color,
                eden_bg,
                eden_text,
                eden_border,
                eden_shadow,
                eden_font,
            )
            from eden.htmx import hx_vals, hx_headers

            self.env.filters["eden_color"] = eden_color
            self.env.filters["eden_bg"] = eden_bg
            self.env.filters["eden_text"] = eden_text
            self.env.filters["eden_border"] = eden_border
            self.env.filters["eden_shadow"] = eden_shadow
            self.env.filters["eden_font"] = eden_font
            self.env.filters["hx_vals"] = hx_vals
            self.env.filters["hx_headers"] = hx_headers
        except ImportError as e:
            import logging

            logging.getLogger("eden.templating").warning(
                f"Design/HTMX filters unavailable: {e}. "
                f"Template engine will work without design system filters."
            )

        # ── Imports for assets ───────────────────────────────────────────────
        try:
            from eden.assets import (
                ALPINE_VERSION,
                HTMX_VERSION,
                TAILWIND_VERSION,
                eden_head,
                eden_scripts,
                eden_toasts,
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
            self.env.globals["eden_toasts"] = eden_toasts
        except ImportError as e:
            import logging

            logging.getLogger("eden.templating").warning(
                f"Asset helpers unavailable: {e}. "
                f"Template engine will work without asset versions/helpers."
            )

        # Register helpers as globals for directive availability
        self.env.globals["csrf_token"] = self._csrf_token_helper
        self.env.globals["old"] = self._old_helper
        self.env.globals["vite"] = self._vite_helper
        self.env.globals["eden_dump"] = self._dump_helper

        try:
            from eden.context import is_active

            self.env.globals["is_active"] = is_active
            self.env.globals["hasattr"] = hasattr
        except ImportError:
            pass

        # Ensure eden_messages is available as a global function
        try:
            from eden.messages import get_messages

            self.env.globals["eden_messages"] = get_messages
        except ImportError:
            pass

        # Core Stacking & DI Helpers
        self.env.globals["eden_push"] = self._push_helper
        self.env.globals["eden_stack"] = self._stack_helper
        self.env.globals["eden_dependency"] = self._dependency_helper
        self.env.globals["set_response_status"] = self._status_helper
        self.env.globals["get_sync_channel"] = get_sync_channel

        # Inject debug flag for EdenSafeUndefined to detect environment mode.
        # When True, undefined variables render as [UNDEFINED: var_name],
        # When False, undefined variables render as empty strings.
        self.env.globals["__eden_debug__"] = getattr(self, "_debug", False)

        # Maximum iterations for template loops (DoS prevention).
        # Injected as a global so compiled loop guards can reference it.
        self.env.globals["__eden_max_loop_iterations__"] = 10_000

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
        header = (
            f'<div class="text-xs font-bold text-blue-400 mb-1">@dump: {label}</div>'
            if label
            else ""
        )
        html = (
            f'<div class="{DEFAULT_DUMP_STYLE}">'
            f"{header}"
            f'<pre class="whitespace-pre-wrap"><code>{formatted}</code></pre>'
            f"</div>"
        )
        return Markup(html)

    def _push_helper(
        self, name: str, content: str, once: bool = False, prepend: bool = False
    ) -> str:
        """Helper for @push, @pushOnce, and @prepend directives."""
        from eden.context import get_request

        request = get_request()
        if request:
            if not hasattr(request.state, "eden_stacks"):
                request.state.eden_stacks = {}
            if not hasattr(request.state, "eden_seen_pushes"):
                request.state.eden_seen_pushes = set()

            if once and name in request.state.eden_seen_pushes:
                return ""

            if name not in request.state.eden_stacks:
                request.state.eden_stacks[name] = []

            if prepend:
                request.state.eden_stacks[name].insert(0, content)
            else:
                request.state.eden_stacks[name].append(content)

            if once:
                request.state.eden_seen_pushes.add(name)
        return ""

    def _stack_helper(self, name: str) -> Markup:
        """Helper for @stack directive."""
        from eden.context import get_request

        request = get_request()
        if request and hasattr(request.state, "eden_stacks"):
            stack = request.state.eden_stacks.get(name, [])
            return Markup("\n".join(stack))
        return Markup("")

    def _dependency_helper(self, alias: str) -> Any:
        """Helper for @inject directive."""
        from eden.context import get_app

        app = get_app()
        # In the future, this should use a proper DI container
        # For now, we check app and app.config
        if hasattr(app, alias):
            return getattr(app, alias)
        if hasattr(app, "config") and hasattr(app.config, alias):
            return getattr(app.config, alias)
        return None

    def _status_helper(self, code: int) -> str:
        """Helper for @status directive."""
        from eden.context import get_request

        request = get_request()
        if request:
            request.state._status_code = code
        return ""

    def render(
        self, request: Any, template_name: str, context: dict[str, Any], **kwargs: Any
    ) -> Any:
        """Convenience wrapper — preferred over ``TemplateResponse`` directly."""
        import time
        from eden.telemetry import record_template_render

        start = time.perf_counter()
        ctx = {"request": request, **context, **kwargs}
        response = self.TemplateResponse(request, template_name, ctx)

        duration = (time.perf_counter() - start) * 1000
        record_template_render(duration)

        return response


def render_template(template_name: str, **context: Any) -> Any:
    """Render an HTML template using the current request context."""
    from eden.context import get_request

    request = get_request()
    if request is None:
        raise RuntimeError("render_template() must be called within a request context.")
    if hasattr(request, "render"):
        return request.render(template_name, **context)

    # Fallback to app.render (which we proxy in Eden.build)
    if hasattr(request.app, "render"):
        return request.app.render(template_name, **context)

    # Final fallback to accessing Eden directly if available
    if hasattr(request.app, "eden"):
        return request.app.eden.render(template_name, **context)

    raise AttributeError(
        f"Could not find a 'render' method on request or app. App is {type(request.app)}"
    )
