"""
Eden — UI Component System

Provides a base ``Component`` class, a ``@register`` decorator,
and a Jinja2 ``ComponentExtension`` for ``{% component %}`` / ``{% slot %}``.

Built-in components are auto-discovered on first import.
"""

import contextvars
import hmac
import hashlib
import json
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

    Components are pure-Python classes that encapsulate both rendering logic and 
    interactivity. They manage their own reactive state and respond to user actions 
    via HTMX. When an action is triggered, Eden re-instantiates the component with 
    any request data and calls the corresponding action method.

    **Core Capabilities:**
    - Render templates with reactive state
    - Handle HTMX-triggered actions with automatic request/response cycles
    - Persist state across requests using hidden form fields
    - Automatic type coercion for action parameters

    **Lifecycle:**
    1. Component is instantiated with initial state (via __init__)
    2. get_context_data() is called to prepare template variables
    3. Template renders with access to state and action URLs
    4. User triggers HTMX action (form submission, click handler, etc.)
    5. Component is re-instantiated with request data + persisted state
    6. Action method runs and returns updated HTML/component

    **Example - Simple Counter:**
        @register("counter")
        class CounterComponent(Component):
            template_name = "counter.html"
            
            def __init__(self, count=0, **kwargs):
                self.count = count
                super().__init__(**kwargs)
            
            @action
            async def increment(self, request):
                self.count += 1
                return await self.render()
            
            @action
            async def decrement(self, request):
                self.count -= 1
                return await self.render()

    **Template Usage:**
        @component("counter", count=initial_value) {
            <div class="counter">
                <p>Count: {{ count }}</p>
                <button hx-post="{{ action_url('increment') }}" 
                        {{ component_attrs }}>
                    +1
                </button>
                <button hx-post="{{ action_url('decrement') }}" 
                        {{ component_attrs }}>
                    -1
                </button>
            </div>
        }

    **Key Attributes:**
    - template_name: Path to the component's Jinja2 template (required)
    - _component_name: Auto-set by @register decorator
    """
    template_name: str = ""
    _component_name: str = ""
    _reactive_state: List[str] = []  # Override in subclass to whitelist reactive properties

    def __init__(self, **kwargs: Any):
        """
        Initialize component with optional state.
        
        Args:
            **kwargs: Arbitrary key-value pairs that become component state.
                     These are preserved across HTMX requests via hx-vals.
        
        Example:
            component = CounterComponent(count=5, title="My Counter")
        """
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Prepare the context dictionary for template rendering.

        This method is called before rendering the template. By default, it includes 
        all instance attributes, plus framework helpers for triggering actions.

        **Returned Context Includes:**
        - All component state (instance attributes)
        - component: Reference to self
        - action_url: Method to generate action URLs: {{ action_url('method_name') }}
        - component_attrs: HTMX attributes for state persistence
        - Any additional kwargs passed (higher priority)

        Args:
            **kwargs: Additional context variables to include (override defaults).

        Returns:
            dict: Template context ready for Jinja2 rendering.

        Example:
            @register("widget")
            class WidgetComponent(Component):
                template_name = "widget.html"
                
                def __init__(self, title="Default", **kwargs):
                    self.title = title
                    super().__init__(**kwargs)
                
                def get_context_data(self, **kwargs):
                    ctx = super().get_context_data(**kwargs)
                    # Add computed properties
                    ctx['title_upper'] = self.title.upper()
                    return ctx

            # When rendered:
            # ctx = component.get_context_data()
            # ctx['title']       -> "My Widget"
            # ctx['title_upper'] -> "MY WIDGET"
            # ctx['action_url']  -> <function>
        """
        ctx = self.__dict__.copy()
        ctx.pop("_component_name", None)
        ctx.pop("_reactive_state", None)
        ctx["component"] = self
        ctx["action_url"] = self.action_url
        ctx["component_attrs"] = self.get_hx_attrs()
        ctx.update(kwargs)
        
        # Ensure common Eden globals are available in component context
        from eden.templating import filters
        ctx.setdefault("json_encode", filters.json_encode)
        ctx.setdefault("json", filters.json_encode)
        
        return ctx

    @property
    def request(self) -> Optional[Any]:
        """
        Accessor for the current HTTP request context.
        
        Returns:
            Request object from context, or None if no request is active.
        
        Usage:
            user_agent = self.request.headers.get('user-agent')
        """
        from eden.context import get_request
        return get_request()

    def get_state(self) -> dict[str, Any]:
        """
        Returns the serializable state of the component for persistence.

        Only includes attributes that are:
        - Simple types (str, int, bool, float, list, dict, None)
        - Not prefixed with underscore (framework internals)
        - Not in the exclusion list (request, component, slots, etc.)

        This state is encoded into HTMX requests (via hx-vals) so that when the 
        user triggers an action, the component can be re-instantiated with all 
        current state automatically restored.

        **Type Restrictions:**
        Complex objects (custom classes, functions, etc.) are excluded automatically 
        to ensure JSON serializability. If you need to persist complex state, 
        serialize it to a string/dict before storing.

        Returns:
            dict: Serializable key-value pairs representing component state.

        Example:
            class CartComponent(Component):
                def __init__(self, items=None, total=0.0, **kwargs):
                    self.items = items or []      # List is OK
                    self.total = total             # Float is OK
                    self.user = get_user()         # User object - EXCLUDED
                    self.user_id = 123             # Int is OK - will persist
                    super().__init__(**kwargs)
                
                def get_state(self):
                    state = super().get_state()
                    # state = {'items': [...], 'total': 0.0, 'user_id': 123}
                    return state
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

        Generates a JSON-encoded hx-vals attribute that embeds the component's 
        current state, plus a cryptographic signature to prevent tampering.
        """
        state = self.get_state()
        signature = self._get_state_signature(state)
        
        attrs = [
            f'hx-vals=\'{json.dumps(state)}\'',
            f'hx-headers=\'{{"X-Eden-State-Signature": "{signature}"}}\''
        ]
        return Markup(" ".join(attrs))

    def _get_state_signature(self, state: dict[str, Any]) -> str:
        """Generate an HMAC signature for the component state."""
        from eden.app import Eden

        secret = None
        app = Eden.get_current()
        if app and getattr(app, "secret_key", None):
            secret = app.secret_key
        else:
            request = self.request
            if request is not None:
                request_app = getattr(request, "app", None)
                if request_app is not None:
                    if hasattr(request_app, "eden") and getattr(request_app, "eden", None) is not None:
                        secret = getattr(request_app.eden, "secret_key", None)
                    elif getattr(request_app, "secret_key", None):
                        secret = request_app.secret_key

        if not secret:
            secret = "dev-secret-key"
        
        # Canonicalize state for signature consistency:
        # Convert all values to strings to handle variations between original 
        # Python types (int, bool) and incoming request data (always strings).
        canonical = {str(k): str(v) for k, v in state.items() if v is not None}
        state_json = json.dumps(canonical, sort_keys=True)
        
        return hmac.new(
            secret.encode(),
            state_json.encode(),
            hashlib.sha256
        ).hexdigest()

    def _verify_state_signature(self, state: dict[str, Any], signature: str) -> bool:
        """Verify the HMAC signature for the component state."""
        if not signature:
            return False
        expected = self._get_state_signature(state)
        return hmac.compare_digest(signature, expected)

    async def render(self, **kwargs: Any) -> Markup:
        """
        Render the component's template with current state.

        This is the main method for converting a component instance to HTML. 
        It calls get_context_data() to build the template context, then renders 
        the associated template.

        Args:
            **kwargs: Additional context variables to pass to get_context_data().

        Returns:
            Markup: Safe HTML-escaped rendered template.

        Example:
            component = CounterComponent(count=5)
            html = await component.render()
            # Returns: <div class="counter">Count: 5...</div>

            # Can also pass additional context:
            html = await component.render(show_reset=True)
        """
        from eden.components import render_component
        return render_component(self._component_name, **self.get_context_data(**kwargs))

    def action_url(self, action_name: str) -> str:
        """
        Generate the URL to trigger an action on this component.

        Returns a URL that, when POSTed to (via HTMX), will re-instantiate this 
        component with current state and call the specified action method.

        Args:
            action_name: Name of the action method to call (e.g., 'increment', 'save').

        Returns:
            str: Absolute URL path for the action.

        Example:
            # In component:
            url = self.action_url('increment')
            # url = '/_eden/component/counter/increment'

            # In template:
            <button hx-post="{{ action_url('increment') }}" {{ component_attrs }}>
                +1
            </button>
        """
        return f"/_eden/component/{self._component_name}/{action_name}"



def register(name: str):
    """
    Decorator to register a component class by name in the global registry.

    This decorator makes a component available for use in templates via the 
    @component directive. It also automatically discovers and registers any 
    methods decorated with @action.

    Args:
        name: Unique identifier for the component (e.g., 'counter', 'user-card').
              Used in templates as @component("name", ...).

    Returns:
        Decorator function that registers the class and returns it unchanged.

    Example:
        @register("counter")
        class CounterComponent(Component):
            template_name = "counter.html"
            
            def __init__(self, count=0, **kwargs):
                self.count = count
                super().__init__(**kwargs)
            
            @action
            async def increment(self, request):
                self.count += 1
                return await self.render()

        # Now usable in templates:
        # @component("counter", count=initial) { ... }

    **Automatic Action Discovery:**
    When @register is applied, it scans the class for methods decorated with 
    @action and registers them globally for fast lookup. This allows the 
    dispatcher to route incoming requests to the correct action quickly.
    """
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

    Actions are component methods that respond to user interactions triggered from 
    templates via HTMX. When a user initiates an action (e.g., form submission, 
    button click), the framework:
    1. Re-instantiates the component with persisted state
    2. Calls the action method
    3. Returns the result (usually updated HTML)

    **Usage Variations:**

    Without arguments (uses method name as action slug):
        @action
        async def increment(self, request):
            self.count += 1
            return await self.render()

    With custom slug:
        @action("update")
        async def save_changes(self, request):
            # Updated from template: action_url('update')
            return await self.render()

    **Return Value Handling:**
    - str or Markup: Returned directly as HTML response
    - Component instance: Re-rendered and returned as HTML
    - dict: Returned as JSON response (for API usage)
    - Any other Response object: Returned unchanged

    **Action Parameters:**
    Actions can accept parameters that are automatically coerced from request data:

        @action
        async def add_item(self, request, name: str, quantity: int):
            # 'name' and 'quantity' are extracted from request form data
            # Type hints are used for automatic coercion
            self.items.append({'name': name, 'qty': quantity})
            return await self.render()

    **State Persistence:**
    The current component state is automatically included in HTMX requests via 
    hx-vals. When the component is re-instantiated, its state is restored before 
    the action method is called.

    Args:
        arg: Optional action slug (name for accessing from template).
            If omitted, method name is used.

    Returns:
        Decorated function with _is_eden_action and _action_slug attributes set.

    Example (Full Counter Component):
        @register("counter")
        class CounterComponent(Component):
            template_name = "counter.html"
            
            def __init__(self, count=0, **kwargs):
                self.count = count
                super().__init__(**kwargs)
            
            @action
            async def increment(self, request):
                self.count += 1
                return await self.render()
            
            @action
            async def decrement(self, request):
                self.count -= 1
                return await self.render()
            
            @action("reset")
            async def reset_count(self, request):
                self.count = 0
                return await self.render()
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
    state = {}
    if request.method == "POST":
        try:
            form_data = await request.form()
            state.update(dict(form_data))
        except Exception as e:
            from eden.logging import get_logger
            get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)
    state.update(dict(request.query_params))
    
    # Filter out common request params that aren't component state
    for internal in ["hx-request", "hx-target", "hx-current-url", "hx-trigger", "hx-trigger-name"]:
        state.pop(internal, None)
        state.pop(internal.upper().replace("-", "_"), None)

    try:
        inst = comp_cls(**state)
        
        # Verify state signature to prevent tampering
        signature = request.headers.get("X-Eden-State-Signature")
        if not inst._verify_state_signature(state, signature):
            return HtmlResponse("Invalid component state signature", status_code=403)
    except Exception as e:
        return HtmlResponse(f"Component Error: {e}", status_code=500)
    
    # Find and verify action
    action_method = getattr(inst, action_name, None)
    if not action_method or not getattr(action_method, "_is_eden_action", False):
        return HtmlResponse(f"Action '{action_name}' not found on component '{component_name}'", status_code=404)

    # Execute action with intelligent parameter injection
    import inspect
    sig = inspect.signature(action_method)
    params = {}
    if "request" in sig.parameters:
        params["request"] = request
    
    # Also pass values from state if they match parameter names (like in dispatcher)
    for name, param in sig.parameters.items():
        if name in state and name != "request":
            val = state[name]
            # Simple type casting
            if param.annotation is int:
                try: val = int(val)
                except (ValueError, TypeError): pass
            elif param.annotation is bool:
                val = str(val).lower() in ("true", "1", "yes", "on")
            params[name] = val

    if inspect.iscoroutinefunction(action_method):
        result = await action_method(**params)
    else:
        result = action_method(**params)

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
        except Exception as e:
            from eden.logging import get_logger
            get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)
    raw_state.update({k: v for k, v in request.query_params.items()})
    
    # Instantiate and call
    # We first instantiate to get the method and inspect its signature
    inst = comp_cls(**raw_state)
    
    # Verify state signature to prevent tampering
    signature = request.headers.get("X-Eden-State-Signature")
    if not inst._verify_state_signature(raw_state, signature):
        return HtmlResponse("Invalid component state signature", status_code=403)
    
    method = getattr(inst, method_name)
    
    # Cast types based on signature hints
    sig = inspect.signature(method)
    casted_params = {}
    has_kwargs = any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values())
    
    # Always pass request if it's in the signature
    if "request" in sig.parameters:
        casted_params["request"] = request

    for name, param in sig.parameters.items():
        if name == "request" or param.kind == param.VAR_KEYWORD:
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
    
    # If method has **kwargs, pass remaining raw_state
    if has_kwargs:
        for k, v in raw_state.items():
            if k not in casted_params:
                casted_params[k] = v
    
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
    router.get("/_eden/component/{component_name}/{action_name}", name="component_action_get")(component_action_handler)
    router.post("/_eden/component/{component_name}/{action_name}", name="component_action_post")(component_action_handler)
    # Simplified dispatcher
    router.get("/_components/{action_slug}", name="component_dispatch_get")(component_dispatcher)
    router.post("/_components/{action_slug}", name="component_dispatch_post")(component_dispatcher)
    return router


# ── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    # Core classes and functions
    "Component",
    "register",
    "action",
    
    # Registry and lookup
    "get_component",
    "_registry",
    "_action_registry",
    
    # Rendering
    "render_component",
    "get_component_router",
    
    # Jinja2 extension
    "ComponentExtension",
    
    # Handlers
    "component_action_handler",
    "component_dispatcher",
]


# Lazy import template loaders to avoid circular imports
def __getattr__(name):
    if name == "ComponentTemplateLoader":
        from eden.components.loaders import ComponentTemplateLoader
        return ComponentTemplateLoader
    elif name == "CachedTemplateLoader":
        from eden.components.loaders import CachedTemplateLoader
        return CachedTemplateLoader
    elif name == "BaseTemplateLoader":
        from eden.components.loaders import BaseTemplateLoader
        return BaseTemplateLoader
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

