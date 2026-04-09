from __future__ import annotations
"""
Eden — Request Correlation ID Middleware

Generates or propagates a unique correlation ID for every request/connection,
enabling unified logging across distributed worker systems.
"""


import uuid
from typing import Any, Optional, TYPE_CHECKING
from starlette.types import ASGIApp, Receive, Scope, Send

if TYPE_CHECKING:
    from eden.requests import Request

class CorrelationIdMiddleware:
    """
    Middleware that ensures every request has a unique correlation ID.
    
    The ID is extracted from the 'X-Request-ID' header if present,
    otherwise a new UUID is generated. 
    
    The ID is placed in:
    1. ASGI scope: scope["eden_request_id"]
    2. Eden Context: context_manager.set_request_id(id)
    3. Response Header: X-Request-ID
    """
    def __init__(
        self, 
        app: ASGIApp, 
        header_name: str = "X-Request-ID",
        validate_uuid: bool = False
    ) -> None:
        self.app = app
        self.header_name = header_name.lower().encode()
        self.validate_uuid = validate_uuid

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # 1. Extract from headers
        headers = dict(scope.get("headers", []))
        request_id: Optional[str] = None
        
        # Binary header search
        raw_header = headers.get(self.header_name)
        if raw_header:
            try:
                request_id = raw_header.decode()
            except UnicodeDecodeError:
                pass

        # 2. Generate if missing
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # 3. Store in scope for application use
        scope["eden_request_id"] = request_id

        # 4. Set in async context for logging correlation
        from eden.context import set_request_id
        # We use set_request_id and handle cleanup with reset_request_id
        token = set_request_id(request_id)

        async def send_with_id(message: Any) -> None:
            if message["type"] == "http.response.start":
                msg_headers = list(message.get("headers", []))
                # Add/overwrite X-Request-ID in response
                msg_headers.append((self.header_name, request_id.encode()))
                message["headers"] = msg_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            # Cleanup context token
            from eden.context import reset_request_id
            reset_request_id(token)
