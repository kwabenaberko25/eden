# Requests & Responses

> **Optimized Data Flow with Automatic Serialization & Safety**

Eden provides a high-level API for handling HTTP requests and crafting responses. It builds upon Starlette but adds deep integration with **Pydantic v2** for automatic serialization and built-in security features like **Open Redirect Protection**.

---

## 1. Handling Requests

The `eden.Request` object provides helpers for common data extraction patterns.

### Body & Form Parsing

```python
@app.post("/submit")
async def handle_submit(request):
    # 1. Parse JSON body
    data = await request.json()
    
    # 2. Parse Form data (Multipart or URL-encoded)
    form = await request.form()
    
    # 3. Access files
    upload = form.get("avatar")
    if upload:
        content = await upload.read()
```

### Contextual Data

Eden automatically injects several useful objects into the request state via middleware:

- `request.user`: The currently authenticated user (or AnonymousUser).
- `request.tenant`: The current tenant context (in multi-tenancy apps).
- `request.session`: The encrypted session store.
- `request.state`: A general-purpose storage for request-lifetime data.

---

## 2. crafting Responses

Eden provides several response classes and functional shortcuts to return data efficiently.

### JSON Responses

Unlike standard frameworks, Eden's `JsonResponse` automatically handles **Pydantic models**.

```python
from eden import JsonResponse

@app.get("/api/user")
async def get_user(request):
    user = request.user
    # Automatically serialized to JSON using model_dump(mode="json")
    return JsonResponse(user)
```

### Functional Shortcuts

For cleaner code, use the functional shortcuts provided by the framework:

```python
from eden import json, html, redirect

@app.get("/shortcuts")
async def examples():
    # Return JSON
    if some_condition:
        return json({"status": "ok"}, status_code=201)
    
    # Return raw HTML (usually you'd use render_template)
    return html("<h1>Hello</h1>")
```

---

## 3. Redirects & Security

Redirecting users safely is a common requirement in SaaS. Eden provides a specialized `SafeRedirectResponse` to prevent **Open Redirect** vulnerabilities.

### Safe Redirects

A regular redirect can be exploited by attackers to send users to malicious external domains. `SafeRedirectResponse` restricts redirects to local paths unless external hosts are explicitly allowed.

```python
from eden import redirect

@app.get("/login")
async def login(request):
    # 'next' parameter could be malicious (e.g., https://evil.com)
    next_url = request.query_params.get("next", "/")
    
    # By setting safe=True, Eden validates that the URL is local (starts with /)
    # If it's an external URL, it safely defaults back to "/"
    return redirect(next_url, safe=True)
```

---

## 4. File Downloads

Stream files directly to the user with the `FileResponse`.

```python
from eden import FileResponse

@app.get("/download/{id}")
async def download_report(id: str):
    path = f"/tmp/report_{id}.pdf"
    return FileResponse(
        path, 
        filename="Annual_Report.pdf",
        media_type="application/pdf"
    )
```

---

## 5. Global Message System (Flash)

Flash messages are stored in the session and displayed to the user on the next request (e.g., after a redirect).

```python
@app.post("/profile")
async def update_profile(request):
    # logic ...
    
    # This message will be available in the next template render
    return redirect("/dashboard", flash_message="Profile updated successfully!")
```

### Displaying Messages

Use the `eden_messages()` helper in your templates.

```html
<!-- Base Template -->
<div class="toast-container">
    @for(msg in eden_messages()) {
        <div class="alert alert-{{ msg.level_tag }}">
            {{ msg.message }}
        </div>
    }
</div>
```

---

## Best Practices

- ✅ **Use Shortcuts**: Prefer `json()`, `html()`, and `redirect()` for readability.
- ✅ **Always Use Safe Redirects**: When redirecting based on user-provided parameters (like `?next=`), always use `safe=True`.
- ✅ **Return Models directly**: Pass Pydantic models to `JsonResponse` to leverage Eden's automatic serialization.
- ✅ **Stream Large Files**: For very large files, use `StreamingResponse` to keep memory usage low.
