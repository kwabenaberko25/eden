"""
Eden — OpenAPI Documentation Generator

Auto-generates an OpenAPI 3.1 spec from the app's registered routes,
and serves a Swagger UI at /docs.
"""

from __future__ import annotations

import inspect
import re
from typing import Any, get_type_hints

from eden.responses import HtmlResponse, JsonResponse


# ── Type Mapping ─────────────────────────────────────────────────────────

_PY_TO_OPENAPI: dict[type, dict[str, str]] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    list: {"type": "array", "items": {"type": "string"}},
    dict: {"type": "object"},
}


def _python_type_to_schema(hint: Any) -> dict[str, str]:
    """Convert a Python type hint to an OpenAPI schema fragment."""
    origin = getattr(hint, "__origin__", None)
    if origin is list:
        args = getattr(hint, "__args__", (str,))
        inner = _python_type_to_schema(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": inner}
    return _PY_TO_OPENAPI.get(hint, {"type": "string"})


# ── Path Parameter Extraction ────────────────────────────────────────────

_PATH_PARAM_RE = re.compile(r"\{(\w+)(?::(\w+))?\}")


def _extract_path_params(path: str) -> list[dict[str, Any]]:
    """Extract OpenAPI parameter definitions from Eden path patterns."""
    params = []
    for match in _PATH_PARAM_RE.finditer(path):
        name = match.group(1)
        type_hint = match.group(2) or "string"
        schema = {"type": "integer"} if type_hint == "int" else {"type": "string"}
        params.append({
            "name": name,
            "in": "path",
            "required": True,
            "schema": schema,
        })
    return params


def _clean_path(path: str) -> str:
    """Convert Eden path syntax ({param:type}) to OpenAPI syntax ({param})."""
    return _PATH_PARAM_RE.sub(r"{\1}", path)


# ── Schema Helpers ───────────────────────────────────────────────────────

def _get_response_schema(endpoint: Any) -> dict[str, Any]:
    """Infer response schema from return type hints."""
    try:
        hints = get_type_hints(endpoint)
    except Exception:
        return {"200": {"description": "Successful response"}}

    return_type = hints.get("return")
    if return_type is None:
        return {"200": {"description": "Successful response"}}

    if return_type is dict or getattr(return_type, "__origin__", None) is dict:
        return {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {"type": "object"},
                    }
                },
            }
        }

    return {"200": {"description": "Successful response"}}


# ── Core Generator ───────────────────────────────────────────────────────

def generate_openapi_spec(
    app: Any,
    title: str | None = None,
    version: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """
    Generate an OpenAPI 3.1.0 specification from all registered Eden routes.

    Args:
        app: The Eden application instance.
        title: API title (defaults to app.title).
        version: API version (defaults to app.version).
        description: API description.

    Returns:
        A complete OpenAPI spec dictionary.
    """
    spec: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": title or getattr(app, "title", "Eden API"),
            "version": version or getattr(app, "version", "0.1.0"),
            "description": description or getattr(app, "description", ""),
        },
        "paths": {},
    }

    tags_set: set[str] = set()

    # Collect routes from the app's internal router
    router = getattr(app, "_router", None)
    if not router:
        return spec

    for route in router.routes:
        if not getattr(route, "include_in_schema", True):
            continue
            
        openapi_path = _clean_path(route.path)
        path_params = _extract_path_params(route.path)

        if openapi_path not in spec["paths"]:
            spec["paths"][openapi_path] = {}

        for method in route.methods:
            method_lower = method.lower()

            operation: dict[str, Any] = {
                "summary": route.summary or route.name,
                "operationId": f"{method_lower}_{route.name}",
                "responses": _get_response_schema(route.endpoint),
            }

            if route.description:
                operation["description"] = route.description.strip()

            if route.tags:
                operation["tags"] = route.tags
                tags_set.update(route.tags)

            if path_params:
                operation["parameters"] = path_params

            # Infer request body for mutation methods
            if method_lower in ("post", "put", "patch"):
                try:
                    sig = inspect.signature(route.endpoint)
                    hints = get_type_hints(route.endpoint)
                except Exception:
                    sig = None
                    hints = {}

                if sig:
                    body_fields = {}
                    for param_name, param in sig.parameters.items():
                        if param_name in ("self", "request", "cls"):
                            continue
                        # Skip path params
                        if any(p["name"] == param_name for p in path_params):
                            continue

                        hint = hints.get(param_name)
                        if hint:
                            body_fields[param_name] = _python_type_to_schema(hint)
                        else:
                            body_fields[param_name] = {"type": "string"}

                    if body_fields:
                        operation["requestBody"] = {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": body_fields,
                                    }
                                }
                            }
                        }

            spec["paths"][openapi_path][method_lower] = operation

    # Build tags list
    if tags_set:
        spec["tags"] = [{"name": tag} for tag in sorted(tags_set)]

    return spec


# ── Swagger UI HTML ──────────────────────────────────────────────────────

_SWAGGER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title} — API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <style>
        body {{ margin: 0; background: #0F172A; }}
        .swagger-ui .topbar {{ display: none; }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({{
            url: '{spec_url}',
            dom_id: '#swagger-ui',
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset,
            ],
            layout: 'BaseLayout',
            deepLinking: true,
        }});
    </script>
</body>
</html>"""


def mount_openapi(app: Any, spec_path: str = "/openapi.json", docs_path: str = "/docs") -> None:
    """
    Mount OpenAPI spec and Swagger UI routes onto an Eden app.

    Usage:
        from eden.openapi import mount_openapi
        mount_openapi(app)
        # Now visit /docs for Swagger UI
    """

    @app.get(spec_path, name="openapi_spec", tags=["docs"])
    async def openapi_spec():
        """Return the OpenAPI JSON spec."""
        spec = generate_openapi_spec(app)
        return JsonResponse(content=spec)

    @app.get(docs_path, name="swagger_ui", tags=["docs"])
    async def swagger_ui():
        """Swagger UI documentation page."""
        html = _SWAGGER_HTML.format(
            title=getattr(app, "title", "Eden API"),
            spec_url=spec_path,
        )
        return HtmlResponse(html)
