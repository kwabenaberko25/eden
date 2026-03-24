# 🍳 Eden UI Recipes: Professional SaaS Patterns

Follow these verified, full-stack recipes to implement complex features using Eden's UI and Backend libraries.

---

## 🔍 Recipe 1: AI-Driven Command Palette

Integrated global search using the `command-bar` component and Eden's Vector Search backend.

### 1. The Frontend (Layout)
Place the command bar at the bottom of your main layout file.

```html
@component("command-bar", placeholder="Search projects or ask AI...")
```

### 2. The Search Fragment (HTMX)
In your `search_results.html` fragment, render the results dynamically.

```html
<div id="command-results-list" class="space-y-2">
    @for(result in results) {
        <div class="p-3 bg-white/5 rounded-lg hover:bg-lime-400/10 cursor-pointer transition-colors">
            <span class="block font-medium text-lime-400">{{ result.title }}</span>
            <span class="text-xs text-slate-400">{{ result.excerpt }}</span>
        </div>
    }
</div>
```

### 3. The Backend (Python)
```python
@app.route("/search/semantic")
async def semantic_search(request):
    query = request.args.get("q")
    # This calls Eden's integrated Vector Search
    results = await eden.ai.search(query, collection="docs", limit=5)
    return render_template("fragments/search_results.html", results=results)
```

---

## 💳 Recipe 2: Premium Subscription Stats

Displaying real-time MRR and payment health using Stat Cards.

### 1. The Component
```html
@component("stat", 
    label="Project Revenue", 
    value=format_currency(revenue), 
    trend=calculate_trend(revenue), 
    icon="payments", 
    color="lime")
```

### 2. The Auto-Refresh Logic
Use HTMX to refresh the stats every 60 seconds without a page reload.

```html
<div hx-get="/api/stats/revenue" 
     hx-trigger="every 60s" 
     hx-swap="outerHTML">
     <!-- The @component call above -->
</div>
```

---

## 📦 Recipe 3: Atomic Storage Uploads

A resilient file upload flow using the `atomic-dropzone` and Eden's Storage Backend.

### 1. The UI Component
```html
@component("atomic-dropzone", id="project-assets", accept="image/*")
```

### 2. The Python Transaction
```python
from eden.storage import AtomicStorageTransaction

@app.route("/api/upload", methods=["POST"])
async def handle_upload(request):
    async with AtomicStorageTransaction(request.tenant_id) as tx:
        for file in request.files.getlist("files"):
            # Save to S3 and generate metadata in one transaction
            asset = await tx.save_file(file, path="uploads/")
            await tx.audit_log(f"Uploaded asset: {asset.id}")
    
    return HTMXResponse(status=200, message="Upload Successful")
```

---

## 🛡️ Recipe 4: Secure Multi-Tenant Context

Ensuring UI elements only show data the user has access to, using `@tenant_isolated`.

### 1. The Backend Guard
```python
from eden.tenancy import tenant_isolated

@app.get("/api/tenant-data")
@tenant_isolated() # Automatically filters the session for the active tenant
async def get_data(request):
    data = await MyModel.objects.all() # Locked to the current tenant
    return render_template("fragments/data_view.html", data=data)
```

### 2. The UI Switcher
Implement the `tenant-selector` to allow smooth context switching.

```html
@component("tenant-selector", current=active_org.name, tenants=orgs)
```

---

## 💡 Best Practices

1. **Keep Fragments Small**: HTMX works best when you swap small, focused pieces of the DOM.
2. **Handle Errors Gracefully**: Always return a valid HTML fragment even if an error occurs (e.g., an error message component).
3. **Use @slot for Extensions**: Don't hack the component internals; use named slots to inject custom logic.
