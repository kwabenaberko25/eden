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
_action_registry: dict[str, tuple[type["Component"], str]] = {}
_slots_stack: contextvars.ContextVar[list] = contextvars.ContextVar(
    "eden_slots_stack", default=[]
)

# Built-in template directory (ships with Eden)
_BUILTIN_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


class Component:
    """
    Base class for defining an Eden UI Component.

    Components are pure-Python classes that handle their own rendering and actions.
    When an action is triggered via HTMX, Eden re-instantiates the component,
    populated with any request data, and calls the action method.
    """
    template_name: str = ""
    _component_name: str = ""

    def __init__(self, **kwargs: Any):
        # Allow passing state via __init__
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Prepare the context for template rendering.
        By default, includes all instance attributes.
        """
        ctx = self.__dict__.copy()
        ctx.pop("_component_name", None)
        ctx["component"] = self
        ctx["action_url"] = self.action_url
        ctx["component_attrs"] = self.get_hx_attrs
        ctx.update(kwargs)
        return ctx


    @property
    def request(self) -> Optional[Any]:
        """Accessor for the current request."""
        from eden.context import get_request
        return get_request()

    def get_state(self) -> dict[str, Any]:
        """
        Returns the serializable state of the component.
        Excludes everything by default unless it's a simple type (str, int, bool, float, list, dict).
        Also excludes internal framework attributes.
        """
        exclude = {"request", "component", "slots", "action_url", "component_attrs"}
        state = {}
        for k, v in self.__dict__.items():
            if k.startswith("_") or k in exclude:
                continue
            # Only include basic serializable types
            if isinstance(v, (str, int, bool, float, list, dict, type(None))):
                state[k] = v
        return state


    def get_hx_attrs(self) -> Markup:
        """
        Returns the HTMX attributes required for state persistence.
        """
        import json
        state = self.get_state()
        return Markup(f'hx-vals=\'{json.dumps(state)}\'')


    async def render(self, **kwargs: Any) -> Markup:
        """Render the component using its template."""
        from eden.components import render_component
        return render_component(self._component_name, **self.get_context_data(**kwargs))

    def action_url(self, action_name: str) -> str:
        """Return the URL to trigger an action on this component."""
        return f"/_eden/component/{self._component_name}/{action_name}"



def register(name: str):
    """Decorator to register a component class by name."""
    def decorator(cls: type[Component]) -> type[Component]:
        cls._component_name = name
        _registry[name] = cls
        
        # Also register any methods marked with @action and a slug
        import inspect
        for m_name, m_obj in inspect.getmembers(cls, predicate=inspect.isfunction):
            if hasattr(m_obj, "_action_slug"):
                _action_registry[m_obj._action_slug] = (cls, m_name)
                
        return cls
    return decorator


def action(arg=None):
    """
    Decorator to mark a component method as an HTMX-callable action.
    Can be used as @action or @action("slug").
    """
    if callable(arg): # Used as @action (no parentheses)
        func = arg
        func._is_eden_action = True
        func._action_slug = func.__name__ # Default slug to method name
        return func
    
    # Used as @action("slug")
    def decorator(func):
        func._is_eden_action = True
        func._action_slug = arg
        return func
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

        inst = comp_cls(**kwargs)
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
    from eden.app import Eden
    app = Eden.get_current()
    if not app:
        return Markup(f"<!-- Eden app context not found for component '{name}' -->")

    comp_cls = get_component(name)
    if not comp_cls:
        return Markup(f"<!-- Component '{name}' not found -->")

    inst = comp_cls(**kwargs)
    ctx = inst.get_context_data()
    
    tmpl = app.templates.get_template(inst.template_name)
    return Markup(tmpl.render(ctx))



# ── Component Router & Dispatch ───────────────────────────────────────────

async def component_action_handler(
    request: Any, 
    component_name: str, 
    action_name: str
) -> Any:
    """Central dispatcher for component-based HTMX actions."""
    from eden.responses import HtmlResponse
    
    comp_cls = get_component(component_name)
    if not comp_cls:
        return HtmlResponse(f"Component '{component_name}' not found", status_code=404)

    # Instantiate component with request data (state persistence)
    # Priority: POST form data > Query params
    state = {}
    if request.method == "POST":
        try:
            form_data = await request.form()
            state.update(form_data)
        except Exception:
            pass
    state.update(request.query_params)
    
    # Filter out common request params that aren't component state
    for internal in ["hx-request", "hx-target", "hx-current-url", "hx-trigger", "hx-trigger-name"]:
        state.pop(internal, None)
        state.pop(internal.upper().replace("-", "_"), None)

    inst = comp_cls(**state)
    
    # Find and verify action
    action_method = getattr(inst, action_name, None)
    if not action_method or not getattr(action_method, "_is_eden_action", False):
        return HtmlResponse(f"Action '{action_name}' not found on component '{component_name}'", status_code=404)

    # Execute action
    # Actions can return a full response, a Markup string, or another component inst.
    import inspect
    if inspect.iscoroutinefunction(action_method):
        result = await action_method(request)
    else:
        result = action_method(request)

    if isinstance(result, (str, Markup)):
        return HtmlResponse(str(result))
    if isinstance(result, Component):
        return HtmlResponse(str(await result.render()))
    
    return result

async def component_dispatcher(request: Any) -> Any:
    """Simplified dispatcher that maps a single action_slug to a component method."""
    from eden.responses import HtmlResponse
    import inspect
    
    action_slug = request.path_params.get("action_slug")
    match = _action_registry.get(action_slug)
    if not match:
        return HtmlResponse(f"Component action '{action_slug}' not found", status_code=404)
    
    comp_cls, method_name = match
    
    # Extract raw params
    raw_state = {}
    if request.method == "POST":
        try:
            form_data = await request.form()
            raw_state.update({k: v for k, v in form_data.items()})
        except Exception:
            pass
    raw_state.update({k: v for k, v in request.query_params.items()})
    
    # Instantiate and call
    # We first instantiate to get the method and inspect its signature
    inst = comp_cls(**raw_state)
    method = getattr(inst, method_name)
    
    # Cast types based on signature hints
    sig = inspect.signature(method)
    casted_params = {}
    
    # Always pass request if it's in the signature
    if "request" in sig.parameters:
        casted_params["request"] = request

    for name, param in sig.parameters.items():
        if name == "request":
            continue
            
        if name in raw_state:
            val = raw_state[name]
            # Try to cast if annotation is present
            if param.annotation is int:
                try: val = int(val)
                except (ValueError, TypeError): pass
            elif param.annotation is bool:
                val = str(val).lower() in ("true", "1", "yes", "on")
            elif param.annotation is float:
                try: val = float(val)
                except (ValueError, TypeError): pass
                
            casted_params[name] = val
    
    # Filter out internal params from state if they don't match signature
    # (they are already in 'inst' but we only pass relevant ones to method)
    
    try:
        if inspect.iscoroutinefunction(method):
            result = await method(**casted_params)
        else:
            result = method(**casted_params)
    except TypeError as e:
        # Fallback for methods that don't take specific params or take **kwargs
        if inspect.iscoroutinefunction(method):
            result = await method(request) if "request" in sig.parameters else await method()
        else:
            result = method(request) if "request" in sig.parameters else method()
        
    if isinstance(result, (str, Markup)):
        return HtmlResponse(str(result))
    if isinstance(result, Component):
        return HtmlResponse(str(await result.render()))
        
    return result

def get_component_router() -> Any:
    """Return a router configured with component action endpoints."""
    from eden.routing import Router
    router = Router()
    router.get("/_eden/component/{component_name}/{action_name}")(component_action_handler)
    router.post("/_eden/component/{component_name}/{action_name}")(component_action_handler)
    # Simplified dispatcher
    router.get("/_components/{action_slug}")(component_dispatcher)
    router.post("/_components/{action_slug}")(component_dispatcher)
    return router

