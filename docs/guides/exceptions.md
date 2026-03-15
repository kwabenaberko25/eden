# Exception Handling 🚥

Eden makes it easy to capture errors and present them beautifully or handle them programmatically.

## Custom Error Handlers

You can register handlers for specific HTTP status codes or Python exceptions.

```python
from eden import JsonResponse, NotFound

@app.exception_handler(NotFound)
async def not_found(request, exc):
    return JsonResponse(
        {"error": "This place is a desert. No resource found here."}, 
        status_code=404
    )

@app.exception_handler(ValueError)
async def handle_value_error(request, exc):
    return JsonResponse(
        {"error": str(exc)}, 
        status_code=400
    )

---

## Template Error Pages 🎨

Eden automatically looks for custom error templates in your `templates/errors/` directory.

- `templates/errors/404.html`
- `templates/errors/500.html`
- `templates/errors/exception.html` (General fallback)

If these files exist, Eden will render them instead of the default text response when an error occurs in production.
```

---

## Premium Debug Page

In `debug=True` mode, Eden replaces the standard stack trace with a **Premium Debug UI**.

This page includes:
- **Fuzzy Suggestions**: Suggests corrections for common typos.
- **Environment Snapshots**: Shows current Python and framework state.
- **Request Metadata**: Inspect headers, cookies, and parameters.

---

## Built-in HTTP Exceptions

Eden leverages Starlette's `HTTPException` for easy error signaling inside routes.

```python
from eden import Forbidden

@app.get("/secret")
async def secret_area(request):
    if not request.user.is_authenticated:
        raise Forbidden("Not permitted.")
    return {"secret": "Eden 🌿"}
```

---

## Global Error Logging

For production, you should combine custom exception handlers with a logging service to capture and monitor application health.

```python
from eden import JsonResponse
import logging

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logging.error(f"Global Error: {exc}", exc_info=True)
    return JsonResponse(
        {"error": "An internal error occurred. Our gardeners are on it."},
        status_code=500
    )
```

---

**Next Steps**: [CLI Suite](cli.md)
