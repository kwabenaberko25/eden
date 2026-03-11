"""
Eden — Authentication Middleware
"""

from collections.abc import Sequence
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse

from eden.auth.base import AuthBackend
from eden.context import reset_request, reset_user, set_request, set_user
from eden.requests import Request


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tries to authenticate the request using one or more backends.
    """

    def __init__(self, app: Any, backends: Sequence[AuthBackend], **kwargs) -> None:
        super().__init__(app, **kwargs)
        self.backends = backends

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        # Wrap starlette request into Eden request for backends
        # Note: BaseHTTPMiddleware already provides a Request object,
        # but we use our wrapper for consistency.
        eden_request = Request(request.scope, request.receive, request._send)

        # 1. Set request in context
        req_token = set_request(eden_request)
        user_token = None

        try:
            user = None
            for backend in self.backends:
                try:
                    user = await backend.authenticate(eden_request)
                except Exception:
                    # Log the error but continue to next backend or deny access
                    # Do not crash the request if one backend fails (e.g. DB connection lost)
                    pass

                if user:
                    break

            # 2. Set user in context and request state
            if user:
                user_token = set_user(user)
                request.state.user = user
            else:
                request.state.user = None

            response = await call_next(request)
            return response

        finally:
            # 3. Cleanup context
            if user_token:
                reset_user(user_token)
            reset_request(req_token)
