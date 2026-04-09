# Eden Framework: Completed Features Guide

This guide covers the three features that have been fully implemented and made production-ready.

## Table of Contents

1. [Admin Panel](#admin-panel)
2. [Component System](#component-system)
3. [Rate Limiting & Validators](#rate-limiting--validators)

---

## Admin Panel

### Overview

The Admin Panel is now fully production-ready with complete export functionality, inline model support, and chart widgets.

### Key Features

#### 1. Export Functionality

Export records in multiple formats: CSV, JSON, and Excel (XLSX).

**CSV Export:**
```python
from eden.admin.widgets import ExportAction

export_csv = ExportAction(format="csv")

# Usage in ModelAdmin:
class UserAdmin(ModelAdmin):
    actions = [
        DeleteAction(),
        ExportAction(format="csv"),
        ExportAction(format="json"),
        ExportAction(format="xlsx"),
    ]
```

**Export API:**
```python
from eden.admin.export import to_csv, to_json, to_excel

# Export selected records
records = [user1, user2, user3]
csv_data = await to_csv(records, User)
json_data = await to_json(records, User, pretty=True)
excel_bytes = await to_excel(records, User)
```

**Features:**
- Automatic type serialization (datetime, Decimal, Enum)
- Field filtering (select which columns to export)
- Standardized filenames with timestamps
- Proper HTTP headers for downloads
- Support for large datasets

**Supported Formats:**
| Format | MIME Type | Use Case |
|--------|-----------|----------|
| CSV | text/csv | Spreadsheet import, data analysis |
| JSON | application/json | API consumption, data interchange |
| XLSX | application/vnd.openxmlformats... | Excel files, reports |

#### 2. Inline Models

Edit related objects directly from parent record.

**Define Inlines:**
```python
from eden.admin import ModelAdmin, InlineModelAdmin

class TicketMessageInline(InlineModelAdmin):
    model = TicketMessage
    extra = 1  # Number of blank rows for new records
    template = "tabular_inline"  # or "stacked_inline"

class SupportTicketAdmin(ModelAdmin):
    inlines = [TicketMessageInline]
```

**Features:**
- Automatic FK detection
- Load related objects for editing
- Add/edit/delete related records
- Field metadata preservation
- Validation error handling

**Example Workflow:**
```
1. User opens /admin/support_ticket/123/
2. Related TicketMessages are fetched and displayed in inline form
3. User can:
   - Edit existing messages
   - Add new messages (using blank extra rows)
   - Delete messages (check "DELETE" checkbox)
4. On save, all inline changes are persisted
```

#### 3. Complete Edit View

Full POST handling for both parent and inline record updates.

**In admin views:**
```python
# GET: Display form with parent fields and inlines
# POST: Save parent + process all inlines atomically

async def admin_edit_view(request, model, model_admin, record_id, admin_site):
    if request.method == "POST":
        # 1. Update parent record
        # 2. Process inline forms
        # 3. Log changes to AuditLog
        # 4. Redirect to list view
```

---

## Component System

### Overview

The Component System is now fully functional with complete action dispatching, state persistence, template discovery, and slot rendering.

### Key Features

#### 1. Component Actions

Define interactive methods on components that respond to HTMX requests.

**Define Component with Actions:**
```python
from eden.components import Component, register, action

@register("counter")
class CounterComponent(Component):
    template_name = "counter.html"
    
    def __init__(self, count=0, **kwargs):
        self.count = count
        super().__init__(**kwargs)
    
    @action
    async def increment(self, request):
        self.count += 1
        return await self.render()
    
    @action
    async def decrement(self, request):
        self.count -= 1
        return await self.render()
    
    @action("reset")  # Custom action name
    async def reset_count(self, request):
        self.count = 0
        return await self.render()
    
    # Action with parameters
    @action
    async def add(self, request, amount: int = 1):
        self.count += amount
        return await self.render()
```

**Use in Template:**
```html
<div class="counter">
    <p>Count: {{ count }}</p>
    <button hx-post="{{ action_url('increment') }}" {{ component_attrs }}>+1</button>
    <button hx-post="{{ action_url('decrement') }}" {{ component_attrs }}>-1</button>
    <button hx-post="{{ action_url('reset') }}" {{ component_attrs }}>Reset</button>
</div>
```

**How It Works:**
1. Button click → HTMX POST to `/_eden/component/counter/increment`
2. Dispatcher extracts state from hx-vals: `{count: 5}`
3. Verifies HMAC signature for security
4. Re-instantiates: `CounterComponent(count=5)`
5. Calls action: `await component.increment(request)`
6. Returns re-rendered HTML

#### 2. Type Coercion

Action parameters are automatically coerced from request data based on type hints.

**Automatic Coercion:**
```python
@action
async def update_item(self, request, name: str, quantity: int, active: bool):
    # Parameters automatically coerced from form data:
    # name: "Widget" (str)
    # quantity: 5 (int, from "5" string)
    # active: True (bool, from "on" checkbox)
    self.items[name] = quantity
    return await self.render()
```

**Supported Conversions:**
- `str → int, float, bool`
- JSON strings → `list, dict`
- `None` → empty values

#### 3. State Persistence

Component state automatically persists across HTMX requests via hx-vals.

**State Serialization:**
```python
component = MyComponent(count=5, title="My Widget", user_id=123)

# Component serializes state to JSON:
# {
#   "count": 5,
#   "title": "My Widget",
#   "user_id": 123
# }

# Embedded in template as hx-vals and HMAC-signed
# On next action, state is restored automatically
```

**Security:**
- HMAC-SHA256 signature prevents tampering
- Signature verified before action execution
- Only simple types (str, int, float, bool, list, dict) serialized
- Complex objects excluded automatically

#### 4. Slots

Define named content areas in components for composition.

**Define Component with Slots:**
```html
<!-- card.html -->
<div class="card">
  {% if slots.header %}
  <div class="card-header">
    {{ slots.header }}
  </div>
  {% endif %}
  
  <div class="card-body">
    {{ slots.default }}
  </div>
  
  {% if slots.footer %}
  <div class="card-footer">
    {{ slots.footer }}
  </div>
  {% endif %}
</div>
```

**Use with Slots:**
```html
@component("card", title="User Profile") {
  {% slot "header" %}
    <h2>{{ title }}</h2>
  {% endslot %}
  
  {% slot "default" %}
    <p>User details here...</p>
  {% endslot %}
  
  {% slot "footer" %}
    <button>Save</button>
  {% endslot %}
}
```

#### 5. Template Discovery

Configurable template loading with theme support and multiple directories.

**Initialize Loader:**
```python
from eden.components.loaders import ComponentTemplateLoader, CachedTemplateLoader

# Basic usage
loader = ComponentTemplateLoader(
    project_dirs=["templates/components", "templates"],
    builtin_dir="eden/components/templates",
    theme="dark"
)

# With caching (production)
cached_loader = CachedTemplateLoader(
    project_dirs=["templates/components"],
    theme="dark"
)

# Change theme at runtime
loader.set_theme("light")
```

**Search Order:**
1. `templates/components/themes/dark/` (theme-specific)
2. `templates/components/` (project)
3. `eden/components/templates/themes/dark/` (built-in theme)
4. `eden/components/templates/` (built-in)

**Get Component Template:**
```python
# Use convention (looks for eden/card.html)
template = await loader.get_component_template("card")

# Use explicit path
template = await loader.get_component_template(
    "card",
    "my_templates/custom_card.html"
)

# Check existence
exists = await loader.template_exists("card.html")

# List templates
templates = await loader.list_templates("eden/*.html")
```

---

## Rate Limiting & Validators

### Rate Limiting

**Already 100% complete.** Both MemoryRateLimitStore and RedisRateLimitStore have full implementations.

**Usage:**
```python
from eden.middleware import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, store=RedisRateLimitStore())

# Apply to routes
@app.post("/api/users")
@rate_limit("10/minute", key=lambda req: req.remote_addr)
async def create_user(request):
    ...
```

**Features:**
- Per-IP rate limiting
- Per-user rate limiting
- Custom key functions
- 429 Too Many Requests responses
- X-RateLimit headers

### Validators

**Already 100% complete.** All 16+ validators fully implemented.

**Available Validators:**
- `validate_email()` - Email with optional DNS check
- `validate_phone()` - E.164 format, country-specific
- `validate_url()` - URL scheme and TLD validation
- `validate_ip()` - IPv4/IPv6, private address filtering
- `validate_credit_card()` - Luhn algorithm + brand detection
- `validate_password()` - Strength scoring, configurable requirements
- `validate_postcode()` - Country-specific postal codes
- `validate_iban()` - MOD-97 checksum
- `validate_national_id()` - Country-specific ID formats
- And many more...

**Usage:**
```python
from eden.validation import validate_email, validate_password, validate_url

result = await validate_email("user@example.com")
if result.ok:
    print(result.value)

result = await validate_password("MyP@ssw0rd", min_length=12)
if result.ok:
    # Password is strong
    pass

result = await validate_url("https://example.com")
assert result.is_valid
```

---

## Summary

### What's Complete

| Feature | Status | Coverage |
|---------|--------|----------|
| **Admin Panel** | ✅ Complete | Export (CSV/JSON/XLSX), Inline models, Edit view with inlines |
| **Component System** | ✅ Complete | Action dispatching, Type coercion, State persistence, Slots, Template loaders |
| **Rate Limiting** | ✅ Complete | Memory & Redis stores, Middleware, Decorators |
| **Validators** | ✅ Complete | 16+ validators, Composite validation, Pydantic types |

### Production Ready

All completed features are:
- ✅ Fully implemented
- ✅ Thoroughly tested
- ✅ Documented with examples
- ✅ Ready for production use
- ✅ Following Eden Framework patterns

### Integration Points

**Admin Panel:**
```python
# In your app
from eden.admin import AdminSite, ModelAdmin
from eden.admin.widgets import ExportAction

admin_site = AdminSite()

class UserAdmin(ModelAdmin):
    actions = [ExportAction(format="csv")]

admin_site.register(User, UserAdmin)
app.routes.extend(admin_site.build_router().routes)
```

**Components:**
```python
# In your templates
@component("counter", count=0) {
    <p>{{ count }}</p>
    <button hx-post="{{ action_url('increment') }}" {{ component_attrs }}>+</button>
}
```

---

## Next Steps

For advanced usage and customization:
- See `eden/admin/export.py` for custom export formats
- See `eden/admin/inline.py` for custom inline handling
- See `eden/components/dispatcher.py` for custom action routing
- See `eden/components/loaders.py` for template loader customization

Questions or issues? Check the test suite in `tests/test_rough_edges_completion.py`.
