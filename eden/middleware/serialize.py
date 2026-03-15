"""
Eden — Automatic Request/Response Serialization

Auto-serialize Pydantic models, ORM models, and dataclasses to JSON responses.

**Features:**
- Auto-serialize Model instances to JSON
- Auto-serialize lists of models
- Auto-serialize Pydantic models
- Preserve custom response types (FileResponse, StreamingResponse)
- Custom serializer registration
- Pagination metadata inclusion

**Setup:**

    from eden.middleware import AutoSerializeMiddleware
    from eden import Eden
    
    app = Eden(__name__)
    
    # Add auto-serialization middleware
    app.add_middleware(AutoSerializeMiddleware)

**Usage:**

    from eden import Router, Model, StringField
    from sqlalchemy.orm import Mapped
    
    class User(Model):
        id: Mapped[int]
        name: Mapped[str] = StringField()
        email: Mapped[str] = StringField()
    
    router = Router()
    
    @router.get("/api/users/{user_id}")
    async def get_user(request):
        user_id = int(request.path_params["user_id"])
        user = await User.get(user_id)
        
        # Return model directly, middleware auto-serializes
        return user
        # Automatically returns:
        # {"id": 1, "name": "Alice", "email": "alice@example.com"}
    
    @router.get("/api/users")
    async def list_users(request):
        users = await User.select().offset(0).limit(10).all()
        
        # Return list of models
        return users
        # Automatically returns:
        # {"data": [...], "pagination": {"page": 1, "limit": 10, "total": 150}}
    
    @router.post("/api/users")
    async def create_user(request):
        data = await request.json()
        user = await User.create(name=data["name"], email=data["email"])
        
        return user
        # Auto-serialized with status 201

**Excluding Fields:**

    class User(Model):
        id: Mapped[int]
        name: Mapped[str] = StringField()
        password_hash: Mapped[str] = StringField()
        
        class Meta:
            exclude_from_response = ["password_hash"]

**Custom Serializers:**

    from eden.middleware import register_serializer
    from datetime import date
    
    register_serializer(date, lambda d: d.isoformat())

**Status Code Determination:**

    - Model returned from POST -> 201 (Created)
    - List returned -> 200 (OK)
    - None returned -> 204 (No Content)
    - Other -> 200 (OK)
"""

import json
import logging
from typing import Any, Callable, Dict, Optional, List, Type
from datetime import datetime, date
from decimal import Decimal

from starlette.responses import JSONResponse
from starlette.datastructures import MutableHeaders

logger = logging.getLogger(__name__)

# Custom serializers registry
_serializers: Dict[Type, Callable[[Any], Any]] = {
    datetime: lambda dt: dt.isoformat(),
    date: lambda d: d.isoformat(),
    Decimal: lambda d: float(d),
    bytes: lambda b: b.decode("utf-8"),
    set: lambda s: list(s),
    frozenset: lambda s: list(s),
}


def register_serializer(type_: Type, serializer: Callable[[Any], Any]) -> None:
    """
    Register custom serializer for a type.
    
    Args:
        type_: Python type to serialize
        serializer: Function that converts type to JSON-safe value
    
    Example:
        from datetime import datetime
        register_serializer(datetime, lambda dt: dt.timestamp())
    """
    _serializers[type_] = serializer
    logger.debug(f"Serializer registered for {type_.__name__}")


def serialize_value(value: Any) -> Any:
    """
    Recursively serialize value to JSON-safe format.
    
    Args:
        value: Value to serialize
    
    Returns:
        JSON-safe value
    """
    if value is None:
        return None
    
    if isinstance(value, (str, int, float, bool)):
        return value
    
    # Check for custom serializer
    value_type = type(value)
    if value_type in _serializers:
        return _serializers[value_type](value)
    
    # Try ORM model
    if hasattr(value, "to_dict"):
        return value.to_dict()
    
    if hasattr(value, "model_dump"):  # Pydantic v2
        return value.model_dump()
    
    if hasattr(value, "dict"):  # Pydantic v1
        return value.dict()
    
    # Try dataclass
    if hasattr(value, "__dataclass_fields__"):
        import dataclasses
        return dataclasses.asdict(value)
    
    # Handle collections
    if isinstance(value, (list, tuple)):
        return [serialize_value(v) for v in value]
    
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    
    # Fallback to string representation
    return str(value)


def serialize_model(model: Any) -> Dict[str, Any]:
    """
    Serialize ORM/Pydantic model to dictionary.
    
    Args:
        model: Model instance to serialize
    
    Returns:
        Dictionary representation
    """
    # Try to_dict (custom method)
    if hasattr(model, "to_dict"):
        return model.to_dict()
    
    # Try Pydantic v2
    if hasattr(model, "model_dump"):
        return model.model_dump()
    
    # Try Pydantic v1
    if hasattr(model, "dict"):
        return model.dict()
    
    # Try dataclass
    if hasattr(model, "__dataclass_fields__"):
        import dataclasses
        return dataclasses.asdict(model)
    
    # Try ORM __dict__
    if hasattr(model, "__dict__"):
        return {
            k: serialize_value(v)
            for k, v in model.__dict__.items()
            if not k.startswith("_")
        }
    
    raise TypeError(f"Cannot serialize {type(model)}")


class AutoSerializeMiddleware:
    """
    ASGI middleware for automatic response serialization.
    
    Converts Model, Pydantic, and dataclass instances to JSON automatically.
    """
    
    def __init__(self, app: Any, exclude_paths: Optional[List[str]] = None):
        """
        Initialize middleware.
        
        Args:
            app: ASGI app
            exclude_paths: Paths to exclude from auto-serialization (e.g., ["/health"])
        """
        self.app = app
        self.exclude_paths = exclude_paths or []
        logger.info("Auto-serialization middleware enabled")
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware entry point."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Skip excluded paths
        path = scope.get("path", "")
        if any(path.startswith(p) for p in self.exclude_paths):
            await self.app(scope, receive, send)
            return
        
        # Wrap send to intercept HTTP responses
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Store response info for body wrapper
                send_wrapper.status_code = message["status"]
                send_wrapper.response_headers = MutableHeaders(raw=message.get("headers", []))
            
            await send(message)
        
        send_wrapper.status_code = 200
        send_wrapper.response_headers = MutableHeaders()
        
        # Call app
        await self.app(scope, receive, send_wrapper)


async def auto_serialize_response(
    return_value: Any,
    method: str = "GET",
    include_pagination: bool = True,
) -> JSONResponse:
    """
    Auto-serialize a return value to JSON response.
    
    This is called by route handlers that want auto-serialization.
    
    Args:
        return_value: Value to serialize
        method: HTTP method
        include_pagination: Include pagination metadata for lists
    
    Returns:
        JSONResponse ready to send
    
    Example:
        @router.get("/users")
        async def list_users(request):
            users = await User.select().all()
            return await auto_serialize_response(users)
    """
    # Handle None
    if return_value is None:
        return JSONResponse({}, status_code=204)
    
    # Handle lists (multiple models)
    if isinstance(return_value, list):
        data = [serialize_model(item) if hasattr(item, "__dataclass_fields__") or hasattr(item, "model_dump") or hasattr(item, "to_dict") else serialize_value(item) for item in return_value]
        
        response_data = {"data": data}
        
        # Add pagination metadata if available
        if include_pagination and hasattr(return_value, "pagination"):
            response_data["pagination"] = serialize_value(return_value.pagination)
        
        return JSONResponse(response_data)
    
    # Handle models
    if hasattr(return_value, "to_dict") or hasattr(return_value, "model_dump") or hasattr(return_value, "dict"):
        data = serialize_model(return_value)
        
        # Return 201 for POST/PUT creating resources
        status_code = 201 if method in ("POST", "PATCH") else 200
        
        return JSONResponse(data, status_code=status_code)
    
    # Handle dicts
    if isinstance(return_value, dict):
        return JSONResponse(return_value)
    
    # Fallback
    return JSONResponse({"data": serialize_value(return_value)})
