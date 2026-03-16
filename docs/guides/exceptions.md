# Exception Handling 🚨

Eden provides a robust system for capturing and responding to errors, from automatic validation failures to custom business logic exceptions.

## Built-in Exception Handling

Eden automatically catches common errors and converts them into safe, aesthetic HTTP responses.

### The Debug Error Page
In development mode (`debug=True`), Eden displays a "Premium" high-fidelity error page. It includes:
- **Glassmorphic Design**: A clean, modern aesthetic with obsidian themes and backdrop blurs.
- **Code Explorer**: 
    - **Syntax Highlighting**: Powered by Pygments for clear code reading.
    - **Line-Level Accuracy**: Even for complex template errors, Eden performs traceback recovery to find the exact line.
    - **Predictive Diagnostics**: Automatically suggests fixes for common typos (e.g., "Did you mean: user?").
- **Intelligent Context Analysis**: 
    - **Variable State**: Inspect the exact state of your template variables at the moment of failure.
    - **Request Context**: Inspect headers, cookies, and query parameters.
- **Environment Details**: See the current state of your system.

---

## Custom Exception Handlers

You can define how Eden should handle specific exception types globally using the `@app.exception_handler` decorator.

```python
from eden import Response, logger

class CustomLogicError(Exception):
    pass

@app.exception_handler(CustomLogicError)
async def handle_logic_error(request, exc):
    logger.warning(f"Domain logic failure: {exc}")
    return Response(
        {"error": str(exc), "code": "logic_failure"},
        status_code=400
    )
```

### Common HTTP Exceptions
It's often useful to override default handlers for common status codes like 404 or 500.

```python
from eden.exceptions import HTTPException

@app.exception_handler(404)
async def not_found(request, exc):
    return render_template("errors/404.html"), 404

@app.exception_handler(500)
async def server_error(request, exc):
    # Log the full traceback to your observability tool
    logger.critical("Fatal application error", exc_info=True)
    return render_template("errors/500.html"), 500
```

---

## The `@app.validate` Error Flow

When using the built-in validation system, Eden handles errors for you.

```python
@app.post("/register")
@app.validate(UserSchema, template="register.html")
async def register(request, data: UserSchema):
    # If validation fails, Eden automatically:
    # 1. Renders 'register.html'
    # 2. Injects the 'form' object with error messages
    # 3. Sets the status code to 422 (Unprocessable Entity)
    pass
```

---

## Raising Exceptions in Logic

You can raise exceptions anywhere in your code to stop execution and return an error response.

```python
from eden.exceptions import HTTPException

async def get_user_profile(user_id):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_private and not can_access(user):
        raise HTTPException(status_code=403, detail="This profile is private")
        
    return user
```

---

## Error Reporting Integration

For production, you should combine Eden's handlers with external error tracking.

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # 1. Capture for Sentry/Bugsnag
    capture_exception(exc)
    
    # 2. Return a generic safe response to the user
    return render_template("errors/generic.html"), 500
```

---

**Next Steps**: [Logging & Telemetry](logging.md)
