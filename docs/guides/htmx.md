# HTMX Integration 🎯

Eden treats HTMX as a first-class citizen. Rather than just returning strings, Eden provides a unified **Fragment-Based Workflow** that allows you to keep your frontend logic in your templates while giving the backend surgical control over the UI.

## Getting Started

Eden includes HTMX by default in its recommended setup. If you're building a custom layout, use the `@eden_head` directive:

```html
<head>
    @eden_head
</head>
```

Or manually:

```html
<script src="{{ htmx_version | eden_scripts }}"></script>
```

## The "Killer" Workflow: Auto-Fragment Detection

In most frameworks, you have to create separate "partial" templates for HTMX requests. In Eden, you just mark regions with `@fragment`.

### 1. Define fragments in your main template

```html
<!-- page.html -->
@extends("layouts/app")

@section("content")
    <h1>Dashboard</h1>

    <div id="stats-panel">
        @fragment("stats") {
            <div class="grid grid-cols-3 gap-4">
                <div class="stat">Users: {{ user_count }}</div>
                <div class="stat">Revenue: {{ revenue | money }}</div>
            </div>
        }
    </div>

    <button hx-get="@url('dashboard:refresh_stats')" hx-target="#stats-panel">
        Refresh Stats
    </button>
@endsection
```

### 2. Return the full template in your route

Eden detects the `HX-Target` header automatically. If the target matches a fragment name, **only that fragment is rendered**.

```python
@app.get("/refresh-stats", name="dashboard:refresh_stats")
async def refresh_stats(request):
    # No need to check for HTMX or load a partial
    # Eden sees HX-Target="stats" and renders ONLY the @fragment("stats") block
    return request.render("page.html", {
        "user_count": await User.count(),
        "revenue": 1250.50
    })
```

> [!TIP]
> This pattern keeps your project clean. No more `_partial.html` files polluting your directories. Just surgical updates from within your main templates.

## Fluent Response API: `HtmxResponse`

For advanced control, use `eden.htmx.HtmxResponse`. It provides a fluent, chainable API for setting HTMX headers.

```python
from eden.htmx import HtmxResponse

@app.post("/tasks/create")
async def create_task(request):
    task = await Task.create(**await request.form())
    
    return HtmxResponse("@fragment('task_row')", {"task": task}) \
        .trigger("taskCreated", {"id": task.id}) \
        .push_url("/tasks") \
        .retarget("#task-list") \
        .swap("beforeend")
```

### Chainable Methods

| Method | Header | Description |
| :--- | :--- | :--- |
| `.trigger(event, detail=None)` | `HX-Trigger` | Fire a client-side event. |
| `.trigger_after_settle(event, detail=None)` | `HX-Trigger-After-Settle` | Fire event after settle. |
| `.trigger_after_swap(event, detail=None)` | `HX-Trigger-After-Swap` | Fire event after swap. |
| `.hx_redirect(url)` | `HX-Redirect` | Force a client-side redirect. |
| `.refresh()` | `HX-Refresh` | Force a full page reload. |
| `.retarget(selector)` | `HX-Retarget` | Redirect the swap target to a different element. |
| `.swap(strategy)` | `HX-Reswap` | Override the `hx-swap` strategy. |
| `.push_url(url)` | `HX-Push-Url` | Update the browser's URL bar. |
| `.reselect(selector)` | `HX-Reselect` | Pick a specific element from the response HTML. |

## Request Introspection

Use the `is_htmx` helper to handle conditional logic in your backend logic.

```python
from eden.htmx import is_htmx, hx_target

@app.get("/profile")
async def profile(request):
    user = request.user
    if is_htmx(request) and hx_target(request) == "bio":
        return f"<p>{user.bio}</p>"
    
    return request.render("profile.html")
```

## Template Filters

Eden provides filters to safely pass Python data to HTMX attributes.

### `hx_vals` and `hx_headers`
Automatically serializes dictionaries to JSON for HTMX attributes.

```html
<button hx-post="/update" 
        hx-vals="{{ {'id': item.id, 'status': 'active'} | hx_vals }}">
    Update
</button>
```

## Advanced Patterns

### Inline Form Validation
Use `@fragment` to return validated fields without refreshing the whole form.

```html
<form hx-post="/signup">
    <div id="email-field">
        @fragment("email_input") {
            <input name="email" hx-post="/validate-email" hx-target="#email-field">
            @error("email") { <span class="text-red-500">{{ message }}</span> }
        }
    </div>
</form>
```

### Multi-Target Updates (Out-of-Band)
Return multiple snippets in one response for complex UI updates.

```python
@app.post("/cart/add")
async def add_to_cart(request):
    # logic ...
    return """
    <div id="cart-count" hx-swap-oob="true">5 items</div>
    <div id="notification">Item added!</div>
    """
```

## Best Practices

- ✅ **Use Fragments**: Lean on `@fragment` instead of separate partial files.
- ✅ **Named Routes**: Always use `@url()` for `hx-get` and `hx-post` paths.
- ✅ **Loading States**: Use the `htmx-request` class to show premium spinner components automatically.
- ✅ **OOB for Side Effects**: Use Out-of-Band swaps for updating global UI elements like cart counts or notification bells.
- ✅ **Fluent API**: Prefer `HtmxResponse` over manually setting headers.
