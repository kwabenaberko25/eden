"""
Eden Component System — Action Dispatcher

Provides the ASGI middleware for routing component actions (/_eden/component/{name}/{action}).

**Key Responsibilities:**
- Extract component state from request (hx-vals or JSON body)
- Verify HMAC state signature for security
- Deserialize and type-coerce action parameters
- Re-instantiate component with persisted state
- Call action method with dependency injection
- Return rendered HTML/JSON response

**Usage:**

    from eden.components.dispatcher import ComponentActionDispatcher
    
    app.add_middleware(ComponentActionDispatcher)

**How It Works:**

1. Request arrives at POST /_eden/component/counter/increment
2. Middleware extracts state from hx-vals: {"count": 5}
3. Verifies HMAC signature (X-Eden-State-Signature header)
4. Looks up CounterComponent in registry
5. Re-instantiates: component = CounterComponent(count=5)
6. Calls action: result = await component.increment(request)
7. Returns result as HTML response with HTMX directives
"""

import json
import logging
from typing import Any, Dict, List, Optional, get_type_hints, get_origin, get_args
from functools import wraps
import inspect

from eden.requests import Request
from eden.responses import HtmlResponse, JsonResponse, Response
from eden.exceptions import BadRequest, NotFound, Unauthorized

logger = logging.getLogger(__name__)


class ComponentActionDispatcher:
    """
    ASGI middleware for routing and executing component actions.
    
    Intercepts POST requests to /_eden/component/{component_name}/{action_name}
    and orchestrates the full component action lifecycle.
    """
    
    def __init__(self, app, scope=None, receive=None, send=None):
        """
        Initialize dispatcher. Can work as ASGI middleware or direct callable.
        
        Args:
            app: The next ASGI app in the stack (or the full app if middleware mode)
            scope, receive, send: ASGI connection params (middleware mode)
        """
        self.app = app
        self.scope = scope
        self.receive = receive
        self.send = send
    
    async def __call__(self, scope, receive, send):
        """ASGI interface - middleware mode."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check if this is a component action request
        path = scope.get("path", "")
        if not path.startswith("/_eden/component/"):
            await self.app(scope, receive, send)
            return
        
        if scope["method"] != "POST":
            await self.app(scope, receive, send)
            return
        
        # Parse path: /_eden/component/{component_name}/{action_name}
        parts = path.strip("/").split("/")
        if len(parts) < 4:
            # Not a valid component action path
            await self.app(scope, receive, send)
            return
        
        component_name = parts[2]
        action_name = parts[3]
        
        # Create a Request object to pass to handler
        request = Request(scope, receive)
        
        try:
            response = await self.dispatch_action(
                request, component_name, action_name
            )
            await response(scope, receive, send)
        except Exception as e:
            logger.exception(f"Component action dispatch error: {e}")
            error_response = JsonResponse(
                {"error": str(e)},
                status_code=500
            )
            await error_response(scope, receive, send)
    
    async def dispatch_action(
        self,
        request: Request,
        component_name: str,
        action_name: str,
    ) -> Response:
        """
        Dispatch a component action request.
        
        Args:
            request: The HTTP request
            component_name: Name of the component (e.g., "counter")
            action_name: Name of the action method (e.g., "increment")
        
        Returns:
            Response with rendered component or error
        
        Raises:
            NotFound: If component or action not found
            BadRequest: If state signature invalid
            Unauthorized: If action requires permission not granted
        """
        from eden.components import _registry
        
        # 1. Validate component exists
        if component_name not in _registry:
            logger.warning(f"Component not found: {component_name}")
            raise NotFound(detail=f"Component '{component_name}' not found")
        
        ComponentClass = _registry[component_name]
        
        # 2. Extract and deserialize state
        state = await self._extract_state(request)
        
        # 3. Verify state signature
        await self._verify_state_signature(request, state)
        
        # 4. Instantiate component with state
        component = ComponentClass(**state)
        
        # 5. Get action method
        if not hasattr(component, action_name):
            logger.warning(
                f"Action not found on {component_name}: {action_name}"
            )
            raise NotFound(detail=f"Action '{action_name}' not found")
        
        action_method = getattr(component, action_name)
        
        # Verify it's an action (has _is_eden_action marker from @action decorator)
        if not getattr(action_method, "_is_eden_action", False):
            logger.warning(
                f"Method is not an action: {component_name}.{action_name}"
            )
            raise BadRequest(detail=f"'{action_name}' is not an action")
        
        # 6. Extract and coerce action parameters
        params = await self._extract_action_params(request, action_method)
        
        # 7. Call action method with dependency injection
        try:
            # Build injection kwargs
            inject_kwargs = {"request": request}
            
            # Call with injected request + coerced params
            result = await action_method(**inject_kwargs, **params)
            
            # 8. Format response
            return await self._format_response(result, request)
        
        except Exception as e:
            logger.error(
                f"Action execution failed: {component_name}.{action_name}: {e}",
                exc_info=True
            )
            raise
    
    async def _extract_state(self, request: Request) -> Dict[str, Any]:
        """
        Extract component state from request.
        
        Tries multiple sources in order:
        1. hx-vals header (HTMX form data)
        2. JSON body
        3. Query parameters
        
        Returns:
            Dictionary of state values
        """
        # Try HTMX hx-vals first
        headers_dict = dict(request.headers)
        hx_vals_header = headers_dict.get("hx-vals", "")
        if hx_vals_header:
            try:
                return json.loads(hx_vals_header)
            except json.JSONDecodeError:
                logger.warning("Failed to parse hx-vals header")
        
        # Try JSON body
        try:
            body = await request.json()
            if isinstance(body, dict):
                return body
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Try form data
        try:
            form = await request.form()
            return dict(form)
        except Exception:
            pass
        
        # No state found - return empty dict
        logger.debug("No component state found in request")
        return {}
    
    async def _verify_state_signature(
        self,
        request: Request,
        state: Dict[str, Any],
    ) -> None:
        """
        Verify the HMAC signature for component state.
        
        Compares signature from request header with locally computed signature.
        
        Args:
            request: The HTTP request
            state: The component state dictionary
        
        Raises:
            Unauthorized: If signature is invalid or missing
        """
        headers_dict = dict(request.headers)
        signature = headers_dict.get("X-Eden-State-Signature", "")
        
        if not signature:
            logger.warning("Missing state signature header")
            # In development, allow unsigned requests
            app = getattr(request, "app", None)
            if app and not getattr(app, "debug", False):
                raise Unauthorized(detail="State signature required")
        
        # Create a temporary component to compute expected signature
        # (we need the Component class for this)
        from eden.components import Component
        
        temp_component = Component(**state)
        expected_signature = temp_component._get_state_signature(state)
        
        # Verify signature matches
        import hmac
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Invalid state signature")
            raise Unauthorized(detail="Invalid state signature")
    
    async def _extract_action_params(
        self,
        request: Request,
        action_method: Any,
    ) -> Dict[str, Any]:
        """
        Extract and type-coerce parameters for the action method.
        
        Inspects action method signature and coerces request parameters to match.
        
        Args:
            request: The HTTP request
            action_method: The action method to call
        
        Returns:
            Dictionary of coerced parameters
        """
        # Get method signature
        sig = inspect.signature(action_method)
        params = {}
        
        # Extract request body/form
        request_data = {}
        try:
            # Try JSON first
            json_data = await request.json()
            if isinstance(json_data, dict):
                request_data.update(json_data)
        except (json.JSONDecodeError, ValueError):
            # Try form data
            try:
                form_data = await request.form()
                request_data.update(dict(form_data))
            except Exception:
                pass
        
        # Get type hints for the method
        type_hints = get_type_hints(action_method)
        
        # Coerce each parameter
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "request"):
                # Skip special parameters
                continue
            
            if param_name not in request_data:
                # No value provided - use default if available
                if param.default is not inspect.Parameter.empty:
                    params[param_name] = param.default
                elif param.annotation is not inspect.Parameter.empty:
                    # Try to infer empty value for type
                    params[param_name] = self._get_empty_value(param.annotation)
                continue
            
            value = request_data[param_name]
            target_type = type_hints.get(param_name, param.annotation)
            
            # Coerce value to target type
            try:
                coerced_value = self._coerce_value(value, target_type)
                params[param_name] = coerced_value
            except Exception as e:
                logger.warning(
                    f"Failed to coerce parameter {param_name} to {target_type}: {e}"
                )
                # Keep original value
                params[param_name] = value
        
        return params
    
    def _coerce_value(self, value: Any, target_type: Any) -> Any:
        """
        Coerce a value to a target type.
        
        Handles common type conversions:
        - str → int, float, bool
        - list/dict ← JSON strings
        - Optional[T] → T or None
        
        Args:
            value: The value to coerce
            target_type: The type to coerce to
        
        Returns:
            Coerced value
        """
        if value is None:
            return None
        
        # Handle Optional[T]
        origin = get_origin(target_type)
        if origin is type(Optional):
            args = get_args(target_type)
            if args:
                target_type = args[0]
        
        # If already the right type, return as-is
        if isinstance(value, target_type):
            return value
        
        # String conversions
        if isinstance(value, str):
            if target_type is int:
                return int(value)
            elif target_type is float:
                return float(value)
            elif target_type is bool:
                return value.lower() in ("true", "1", "yes", "on")
            elif target_type is list:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return [value]
            elif target_type is dict:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return {"value": value}
        
        # List/dict from JSON string
        elif isinstance(value, str):
            if target_type in (list, dict):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
        
        # Fallback: return original value
        return value
    
    def _get_empty_value(self, target_type: Any) -> Any:
        """
        Get a default "empty" value for a type.
        
        Args:
            target_type: The type
        
        Returns:
            An appropriate empty/default value
        """
        if target_type is int:
            return 0
        elif target_type is float:
            return 0.0
        elif target_type is bool:
            return False
        elif target_type is str:
            return ""
        elif target_type in (list, List):
            return []
        elif target_type in (dict, Dict):
            return {}
        return None
    
    async def _format_response(
        self,
        result: Any,
        request: Request,
    ) -> Response:
        """
        Format action result as HTTP response.
        
        Handles:
        - Markup/HTML strings → HtmlResponse
        - Dicts/objects with .dict() → JsonResponse
        - Response objects → returned as-is
        
        Args:
            result: The action result
            request: The HTTP request
        
        Returns:
            HTTP Response ready to send
        """
        from markupsafe import Markup
        
        # If it's a Response already, return it
        if isinstance(result, Response):
            return result
        
        # If it's Markup or str, return as HTML
        if isinstance(result, (Markup, str)):
            return HtmlResponse(result)
        
        # If it's a dict, return as JSON
        if isinstance(result, dict):
            return JsonResponse(result)
        
        # If it has a dict method, return as JSON
        if hasattr(result, "dict"):
            try:
                return JsonResponse(result.dict())
            except Exception:
                pass
        
        # Fallback: convert to string and return as HTML
        return HtmlResponse(str(result))
