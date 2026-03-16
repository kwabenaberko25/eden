# JSON Functionality 💎

> **Unlock the power of flexible data structures with Eden's unified JSON support.**

JSON is a first-class citizen in Eden. From storage in PostgreSQL to rendering in templates and communicating via APIs, Eden provides a seamless, type-safe experience for working with structured data.

---

## 💾 JSON in the Database

Eden's ORM makes it easy to store and query JSON data. This is ideal for flexible schemas, audit logs, or complex settings.

### Defining JSON Fields

You can use the explicit `JSONField` or the `json=True` flag in the `f()` helper. By default, Eden uses PostgreSQL's `JSONB` for efficient indexing and searching.

```python
from eden.db import Model, f, JSONField

class Product(Model):
    __tablename__ = "products"
    
    name: Mapped[str] = f(max_length=255)
    
    # Using the explicit helper
    metadata: Mapped[dict] = JSONField(default={})
    
    # Or using the Zen helper
    attributes: Mapped[dict] = f(json=True, default={})
```

### Querying JSON Paths

Since Eden uses SQLAlchemy, you can perform powerful JSON path queries.

```python
# Find products where the 'color' inside 'attributes' is 'blue'
blue_products = await Product.filter(
    Product.attributes["color"].as_string() == "blue"
).all()

# Accessing nested keys
premium_items = await Product.filter(
    Product.metadata["tier"]["level"].as_integer() > 5
).all()
```

---

## 🎨 JSON in Templates

Passing data from Python to your frontend (especially for Alpine.js or HTMX) is a core workflow in Eden.

### The `@json` Directive

Use `@json()` to safely serialize Python objects into a format your frontend scripts can consume. It handles escaping automatically to prevent XSS.

```html
<div x-data="{ config: @json(app_config) }">
    <p x-text="config.api_url"></p>
</div>
```

### The `json_encode` Filter

For use inside expressions or when you need more control, use the `json_encode` filter.

```html
<script>
    const userPermissions = {{ permissions | json_encode }};
</script>
```

---

## 🛠️ JSON in the Admin Panel

Eden provides specialized widgets for editing JSON data with safety and style.

### The Code Editor (Monaco/Ace)

For developers and power users, the `CodeWidget` provides a professional editing experience with syntax highlighting and validation.

```python
from eden.admin import admin

@admin.register(Configuration)
class ConfigAdmin:
    formfield_overrides = {
        "payload": {"widget": admin.widgets.CodeWidget(language="json")}
    }
```

---

## 🚀 JSON in APIs & Responses

Eden's `JsonResponse` is optimized for modern Python, with built-in support for **Pydantic v2** models and automatic conversion of common types.

### Automatic Serialization

Eden's `JsonResponse` (and the `json()` shortcut) recursively serializes:
- **Pydantic Models**: Using `model_dump(mode="json")`.
- **Dates & Times**: Automatically converted to ISO strings.
- **UUIDs & Decimals**: Converted to strings.

```python
from eden import JsonResponse
from datetime import datetime

@app.get("/api/status")
async def get_status(request):
    data = {
        "status": "online",
        "last_ping": datetime.now(), # Eden handles this!
        "user_id": request.user.id     # UUIDs are also handled
    }
    return JsonResponse(data)
```

### Parsing Request JSON

```python
@app.post("/api/update")
async def update_data(request):
    # Asynchronously parse the request body
    data = await request.json()
    
    # Or let Eden validate it automatically
    # @app.validate(MySchema)
```

---

## 🧪 JSON Logging & Testing

### Structured Logging

Eden can output logs in JSON format for production environments, making them easy to digest by tools like ELK or Datadog.

```python
# settings.py / app.py
app.configure_logging(json_format=True)
```

### Testing JSON APIs

Eden's `TestClient` provides helpers to simplify JSON assertions.

```python
@pytest.mark.asyncio
async def test_api(client):
    # Shortcut to post JSON and get back a dict
    data = await client.post_json("/api/tasks", {"title": "New Task"})
    
    assert data["title"] == "New Task"
    
    # Assert JSON contains specific keys
    response = await client.get("/api/tasks")
    client.assert_json_contains(response, "title", "New Task")
```

---

## Best Practices

- ✅ **Use JSONB**: When using PostgreSQL, ensure you use `JSONField` for the best performance.
- ✅ **Schema Validation**: Always wrap JSON request data in a `Schema` class using `@app.validate` to ensure data integrity.
- ✅ **Safe Script Tags**: Use the `@json` directive instead of raw curly braces in templates to prevent XSS.
- ✅ **Standardize Dates**: Eden's `JsonResponse` uses ISO 8601 for dates, which is the industry standard for JSON APIs.
