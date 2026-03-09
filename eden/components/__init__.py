"""
Eden — UI Component System

Provides a base ``Component`` class, a ``@register`` decorator,
and a Jinja2 ``ComponentExtension`` for ``{% component %}`` / ``{% slot %}``.

Built-in components are auto-discovered on first import.
"""

import contextvars
import os
from typing import Any, Dict, List, Optional, Type

from jinja2 import ChoiceLoader, FileSystemLoader, nodes
from jinja2.ext import Extension
from markupsafe import Markup

# ── Registry ──────────────────────────────────────────────────────────────────

_registry: dict[str, type["Component"]] = {}
_slots_stack: contextvars.ContextVar[list] = contextvars.ContextVar(
    "eden_slots_stack", default=[]
)

# Built-in template directory (ships with Eden)
_BUILTIN_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


class Component:
    """
    Base class for defining an Eden UI Component.

    Sub-classes must set ``template_name`` and optionally override
    ``get_context_data`` to enrich the template context.
    """
    template_name: str = ""

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return kwargs


def register(name: str):
    """Decorator to register a component class by name."""
    def decorator(cls: type[Component]) -> type[Component]:
        _registry[name] = cls
        return cls
    return decorator


def get_component(name: str) -> type[Component] | None:
    return _registry.get(name)


# ── Jinja2 Extension ─────────────────────────────────────────────────────────

class ComponentExtension(Extension):
    """
    Jinja2 Extension that handles ``{% component %}``, ``{% slot %}``.
    """
    tags = {"component", "slot"}

    def __init__(self, environment):
        super().__init__(environment)
        # Inject the built-in templates directory into the loader
        existing = environment.loader
        builtin_loader = FileSystemLoader(_BUILTIN_TEMPLATE_DIR)
        if existing is None:
            environment.loader = builtin_loader
        elif isinstance(existing, ChoiceLoader):
            existing.loaders.append(builtin_loader)
        else:
            environment.loader = ChoiceLoader([existing, builtin_loader])

    def parse(self, parser):
        stream = parser.stream
        tag = stream.current.value
        lineno = next(stream).lineno

        if tag == "component":
            args = [parser.parse_expression()]
            kwargs = []
            while stream.current.type != "block_end":
                if stream.current.type == "comma":
                    next(stream)
                if stream.current.type == "name":
                    key = stream.current.value
                    next(stream)
                    stream.expect("assign")
                    val = parser.parse_expression()
                    kwargs.append(nodes.Keyword(key, val))
                else:
                    break
            body = parser.parse_statements(
                ["name:endcomponent"], drop_needle=True
            )
            return nodes.CallBlock(
                self.call_method("_render_component", args, kwargs),
                [], [], body,
            ).set_lineno(lineno)

        elif tag == "slot":
            args = [parser.parse_expression()]
            body = parser.parse_statements(
                ["name:endslot"], drop_needle=True
            )
            return nodes.CallBlock(
                self.call_method("_render_slot", args),
                [], [], body,
            ).set_lineno(lineno)

    def _render_component(self, name, caller, **kwargs):
        stack = _slots_stack.get()
        if not stack:
            stack = []
            _slots_stack.set(stack)

        slots_dict: dict[str, str] = {}
        stack.append(slots_dict)

        # Execute the body — inner {% slot %} tags populate *slots_dict*
        default_content = caller()

        stack.pop()

        slots_dict["default"] = default_content

        comp_cls = get_component(name)
        if not comp_cls:
            return Markup(f"<!-- Component '{name}' not found -->")

        inst = comp_cls()
        ctx = inst.get_context_data(**kwargs)
        ctx["slots"] = slots_dict

        tmpl = self.environment.get_template(inst.template_name)
        return Markup(tmpl.render(ctx))

    def _render_slot(self, name, caller):
        stack = _slots_stack.get()
        if stack:
            stack[-1][name] = caller()
        return Markup("")


# ── Auto-discovery of built-in components ─────────────────────────────────────

def _discover_builtins():
    """Import all modules in eden.components.* to trigger @register decorators."""
    import importlib
    import pkgutil
    pkg_dir = os.path.dirname(__file__)
    for _importer, modname, _ispkg in pkgutil.iter_modules([pkg_dir]):
        if modname.startswith("_"):
            continue
        importlib.import_module(f"eden.components.{modname}")

_discover_builtins()


def render_component(name: str, **kwargs: Any) -> Markup:
    """
    Renders a component by name with the given context data.
    Ensures the component is registered and renders its associated template.
    """
    comp_cls = get_component(name)
    if not comp_cls:
        return Markup(f"<!-- Component '{name}' not found -->")

    inst = comp_cls()
    ctx = inst.get_context_data(**kwargs)
    
    # Simple render without complex slot context for manual calls
    from eden.app import Eden
    app = Eden.get_current()
    if not app:
        return Markup(f"<!-- Eden app context not found for component '{name}' -->")
        
    tmpl = app.templating.get_template(inst.template_name)
    return Markup(tmpl.render(ctx))
