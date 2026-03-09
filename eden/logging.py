"""
Eden — Structured Logging

Provides structured logging with request correlation IDs,
configurable JSON or human-readable output, and a request
logging middleware for automatic access log generation.
"""

from __future__ import annotations

import logging
import sys
import time
import uuid

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# ── Logger Setup ─────────────────────────────────────────────────────────


class EdenFormatter(logging.Formatter):
    """
    Structured formatter that outputs colored, human-readable logs
    in development and JSON in production.
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
    }
    RESET = "\033[0m"

    def __init__(self, json_format: bool = False) -> None:
        super().__init__()
        self.json_format = json_format

    def format(self, record: logging.LogRecord) -> str:
        if self.json_format:
            import json

            log_data = {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            # Add extra fields
            for key in ("request_id", "method", "path", "status_code", "duration_ms", "client_ip"):
                val = getattr(record, key, None)
                if val is not None:
                    log_data[key] = val
            if record.exc_info and record.exc_info[1]:
                log_data["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_data)

        # Human-readable format
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET
        ts = self.formatTime(record, "%H:%M:%S")
        msg = record.getMessage()

        # Append request context if available
        request_id = getattr(record, "request_id", None)
        extra = ""
        if request_id:
            extra = f" [{request_id[:8]}]"

        return f"{color}{ts} {record.levelname:<8}{reset}{extra} {record.name} — {msg}"


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
) -> None:
    """
    Configure Eden's logging system.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: If True, output structured JSON logs for production.

    Usage:
        from eden.logging import setup_logging
        setup_logging(level="DEBUG", json_format=False)
    """
    root_logger = logging.getLogger("eden")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(EdenFormatter(json_format=json_format))
    root_logger.addHandler(handler)

    # Prevent propagation to root logger to avoid duplicates
    root_logger.propagate = False


def get_logger(name: str = "eden") -> logging.Logger:
    """
    Get an Eden logger instance.

    Usage:
        from eden.logging import get_logger
        logger = get_logger("eden.routes")
        logger.info("Processing request")
    """
    return logging.getLogger(f"eden.{name}" if not name.startswith("eden") else name)


# ── Request Logging Middleware ───────────────────────────────────────────


class RequestLoggingMiddleware:
    """
    Logs every HTTP request with method, path, status code, duration,
    and a unique request correlation ID.

    The correlation ID is injected as the ``X-Request-ID`` response header
    and is available    in the request scope as ``scope["eden_request_id"]``.

    Usage:
        app.add_middleware("logging")
        app.add_middleware("logging", log_level="DEBUG")
    """

    def __init__(
        self,
        app: ASGIApp,
        log_level: str = "INFO",
        exclude_paths: list[str] | None = None,
    ) -> None:
        self.app = app
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger = get_logger("requests")
        self.exclude_paths = set(exclude_paths or ["/health", "/ready", "/favicon.ico"])

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)
        path = request.url.path

        # Skip excluded paths
        if path in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        # Generate or extract correlation ID
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:16])
        scope["eden_request_id"] = request_id

        start_time = time.perf_counter()
        status_code = 500  # default in case of error

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            client = scope.get("client")
            client_ip = client[0] if client else "-"
            method = request.method

            # Format: GET /api/users → 200 (12.34ms) [abc12345]
            self.logger.log(
                self.log_level,
                "%s %s → %d (%.2fms)",
                method,
                path,
                status_code,
                duration_ms,
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                },
            )
