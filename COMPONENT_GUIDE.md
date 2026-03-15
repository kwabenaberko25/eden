# Component System Guide

**Eden Components** provide a modern, reactive way to build interactive UI elements. Components manage both rendering and user interactions through a declarative Python interface integrated with HTMX.

---

## Quick Start

### 1. Create a Component

```python
from eden.components import Component, register, action

@register("counter")
class CounterComponent(Component):
    template_name = "counter.html"
    
    def __init__(self, count=0, step=1, **kwargs):
        self.count = count
        self.step = step
        super().__init__(**kwargs)
    
    @action
    async def increment(self, request):
        self.count += self.step
        return await self.render()
```

### 2. Create a Template

Create `templates/counter.html`:

```html
<div class="counter">
    <p>Count: {{ count }}</p>
    <button hx-post="{{ action_url('increment') }}" {{ component_attrs }}>
        +{{ step }}
    </button>
</div>
```

### 3. Use in Templates

```html
@component("counter", count=initial_value, step=1) {
    <div class="container">
        <!-- Counter renders here -->
    </div>
}
```

---

## Core Concepts

### Components Are Stateful Python Objects

Components combine state management with rendering. Unlike traditional templates, components are **Python classes** that encapsulate both logic and presentation.

```python
@register("user_card")
class UserCardComponent(Component):
    template_name = "user_card.html"
    
    def __init__(self, user_id, **kwargs):
        self.user_id = user_id
        self.user = None  # Will be fetched
        super().__init__(**kwargs)
    
    def get_context_data(self, **kwargs):
        # Add computed properties
        ctx = super().get_context_data(**kwargs)
        ctx["is_verified"] = self.user and self.user.verified
        return ctx
```

### State is Automatically Persisted

When a component renders with HTMX attributes, its current state is embedded in hidden form fields. When the user triggers an action, the state is automatically restored:

```python
# Template automatically gets {{ component_attrs }}
# This expands to: hx-vals='{"count": 5, "step": 1}'

# When user clicks button with hx-post, these values are sent
# Component is re-instantiated with: CounterComponent(count=5, step=1)
# Then the action method runs with full state restored
```

### Actions are HTMX Endpoints

Each `@action` method is automatically exposed as an HTMX endpoint that:
1. Re-instantiates the component with persisted state
2. Calls the action method
3. Returns the rendered result

```python
@action
async def increment(self, request):
    self.count += self.step  # State is restored from request
    return await self.render()  # Return updated HTML
```

---

## Component Lifecycle

```
1. Component instance created with initial state
   ↓
2. get_context_data() prepares template context
   ↓
3. Template renders with state + action URLs
   ↓
4. User triggers action (form submit, button click, etc)
   ↓
5. HTMX sends request with persisted state + action name
   ↓
6. Framework re-instantiates component with state
   ↓
7. Action method executes (can modify state)
   ↓
8. Updated component is re-rendered
   ↓
9. HTML response replaces DOM element
```

---

## Passing Data to Components

### Positional Arguments in Templates

```html
<!-- Pass literal values -->
@component("counter", count=0, step=1, title="My Counter") {
    ...
}

<!-- Pass variables -->
@component("counter", count=item.count, step=step_size) {
    ...
}
```

### Component Constructor

Data is passed to `__init__`:

```python
class GreetingComponent(Component):
    def __init__(self, name, greeting="Hello", **kwargs):
        self.name = name
        self.greeting = greeting
        super().__init__(**kwargs)

# Template:
# @component("greeting", name="Alice", greeting="Welcome") { }
# →  GreetingComponent(name="Alice", greeting="Welcome")
```

### From Request Data

State is restored from HTMX requests automatically:

```python
@action
async def add_item(self, request, text: str):
    # Request sent from template: hx-post="{{ action_url('add_item') }}"
    # With form field: <input name="text" />
    # Type hint (str) handles automatic coercion
    self.items.append({"text": text})
    return await self.render()
```

---

## Managing State

### Simple Types are Serialized

Components serialize simple types (str, int, bool, float, list, dict, None) in `hx-vals`:

```python
class CartComponent(Component):
    def __init__(self, items=None, total=0.0, **kwargs):
        self.items = items or []      # ✓ List serialized
        self.total = total             # ✓ Float serialized
        self.user = get_user()         # ✗ Complex object - excluded
        super().__init__(**kwargs)

# get_state() returns: {"items": [...], "total": 0.0}
# user is excluded from JSON
```

### Override get_state() for Custom Serialization

```python
class ArticleComponent(Component):
    def __init__(self, article=None, **kwargs):
        self.article = article
        self.article_id = article.id if article else None
        super().__init__(**kwargs)
    
    def get_state(self):
        # Exclude complex article object, keep ID
        state = super().get_state()
        state.pop("article", None)  # Remove non-serializable
        return state
```

### Computed Properties in Templates

Use `get_context_data()` to add computed fields that don't need to be persisted:

```python
class TodoListComponent(Component):
    def __init__(self, items=None, **kwargs):
        self.items = items or []
        super().__init__(**kwargs)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Computed on each render, not persisted in state
        ctx["pending"] = sum(1 for i in self.items if not i.get("done"))
        ctx["done"] = sum(1 for i in self.items if i.get("done"))
        return ctx

# Template can access {{ pending }} and {{ done }} without them in URL
```

---

## Action Methods

### Basic Actions

```python
@action
async def increment(self, request):
    """Called when button with hx-post="{{ action_url('increment') }}" is clicked."""
    self.count += 1
    return await self.render()
```

### Custom Action Slug

```python
@action("update")
async def save_changes(self, request):
    """Called via hx-post="{{ action_url('update') }}"."""
    # Slug can differ from method name
    return await self.render()
```

### Parameter Passing

Use type hints for automatic coercion:

```python
@action
async def set_count(self, request, value: int):
    """
    Called with: hx-post="{{ action_url('set_count') }}" 
    and form field: <input name="value" type="number" />
    
    value is coerced from string to int automatically.
    """
    self.count = value
    return await self.render()

@action
async def toggle_notification(self, request, enabled: bool):
    """Bool type hint converts 'true'/'false' strings to bool."""
    self.notifications_enabled = enabled
    return await self.render()
```

### Accessing Request Object

```python
@action
async def save_with_context(self, request):
    """Access request for headers, method, etc."""
    user = request.user  # From auth middleware
    logger.info(f"User {user} triggered action")
    return await self.render()
```

### Return Values

```python
@action
async def update(self, request):
    # Return HTML: rendered as response
    return await self.render()

@action
async def update(self, request):
    # Return another component: rendered and returned
    return AnotherComponent(data=self.data)

@action
async def update(self, request):
    # Return string/Markup: returned as HTML
    return Markup("<p>Updated!</p>")

@action
async def update(self, request):
    # Return dict: returned as JSON (for API usage)
    return {"status": "ok", "count": self.count}
```

---

## Template Integration

### Component Directive

```html
<!-- Basic usage -->
@component("counter") {
    <!-- Rendered content -->
}

<!-- With parameters -->
@component("counter", count=5, step=1) {
    <!-- Rendered with initial state -->
}

<!-- In a loop -->
@for (item in items) {
    @component("item_card", item=item, selected=item.id == selected_id) {
        <!-- Each item gets its own component -->
    }
}
```

### Accessing Component Methods

```html
<!-- Generate action URL -->
<button hx-post="{{ action_url('increment') }}">Increment</button>

<!-- Include state in request -->
<button hx-post="{{ action_url('update') }}" {{ component_attrs }}>
    Save
</button>

<!-- Pass additional parameters -->
<form hx-post="{{ action_url('add_item') }}" {{ component_attrs }}>
    <input name="text" />
    <button>Add</button>
</form>

<!-- Access component instance in template -->
<div class="{{ component.__class__.__name__ }}">
    <!-- Use any computed property from get_context_data() -->
    Pending: {{ pending_count }}
</div>
```

### Slots for Template Composition

```python
@register("card")
class CardComponent(Component):
    template_name = "card.html"
    
    def __init__(self, title, **kwargs):
        self.title = title
        super().__init__(**kwargs)
```

```html
<!-- card.html template -->
<div class="card">
    <h3>{{ title }}</h3>
    <div class="card-body">
        {{ slots.default }}
    </div>
</div>
```

```html
<!-- Usage -->
@component("card", title="Profile") {
    <p>User information goes here</p>
}
```

---

## Real-World Examples

### Counter Component

```python
@register("counter")
class CounterComponent(Component):
    template_name = "counter.html"
    
    def __init__(self, count=0, step=1, **kwargs):
        self.count = count
        self.step = step
        super().__init__(**kwargs)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_decrement"] = self.count > 0
        return ctx
    
    @action
    async def increment(self, request):
        self.count += self.step
        return await self.render()
    
    @action
    async def decrement(self, request):
        self.count = max(0, self.count - self.step)
        return await self.render()
```

### Todo List Component

```python
@register("todo_list")
class TodoListComponent(Component):
    template_name = "todo_list.html"
    
    def __init__(self, items=None, next_id=1, **kwargs):
        self.items = items or []
        self.next_id = next_id
        super().__init__(**kwargs)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pending"] = sum(1 for i in self.items if not i.get("done"))
        ctx["done"] = sum(1 for i in self.items if i.get("done"))
        return ctx
    
    @action
    async def add_item(self, request, text: str):
        if text.strip():
            self.items.append({
                "id": self.next_id,
                "text": text.strip(),
                "done": False
            })
            self.next_id += 1
        return await self.render()
    
    @action
    async def toggle_item(self, request, item_id: int):
        for item in self.items:
            if item.get("id") == item_id:
                item["done"] = not item.get("done")
        return await self.render()
    
    @action
    async def delete_item(self, request, item_id: int):
        self.items = [i for i in self.items if i.get("id") != item_id]
        return await self.render()
```

### Form Component with Validation

```python
@register("contact_form")
class ContactFormComponent(Component):
    template_name = "contact_form.html"
    
    def __init__(self, name="", email="", message="", errors=None, submitted=False, **kwargs):
        self.name = name
        self.email = email
        self.message = message
        self.errors = errors or {}
        self.submitted = submitted
        super().__init__(**kwargs)
    
    @action
    async def submit(self, request, name: str, email: str, message: str):
        self.name = name
        self.email = email
        self.message = message
        self.errors = {}
        
        # Validate
        if not name.strip():
            self.errors["name"] = "Name is required"
        if not email or "@" not in email:
            self.errors["email"] = "Valid email is required"
        if len(message) < 10:
            self.errors["message"] = "Message must be at least 10 characters"
        
        if not self.errors:
            # Send email, etc.
            self.submitted = True
        
        return await self.render()
    
    @action
    async def reset(self, request):
        self.name = ""
        self.email = ""
        self.message = ""
        self.errors = {}
        self.submitted = False
        return await self.render()
```

---

## Best Practices

### 1. Keep Components Focused
Each component should have a single responsibility. Don't create monolithic mega-components.

```python
# ✓ Good: Focused components
@register("todo_item")
class TodoItemComponent(Component):
    def __init__(self, item, **kwargs):
        self.item = item
        super().__init__(**kwargs)

# Composed into a list:
@component("todo_list", items=items) {
    @for (item in items) {
        @component("todo_item", item=item) { }
    }
}

# ✗ Bad: Too much responsibility
@register("mega_todo_app")
class MegaTodoComponent(Component):
    # UI, database access, authentication, notifications, etc.
    pass
```

### 2. Validate State in Actions
Always sanitize and validate action parameters:

```python
@action
async def set_priority(self, request, priority: str):
    valid = ["low", "medium", "high"]
    if priority not in valid:
        return "Invalid priority"  # Or raise an exception
    self.priority = priority
    return await self.render()
```

### 3. Use Computed Fields in get_context_data
Don't persist derived data in state:

```python
# ✗ Bad: Computed value stored in state
def __init__(self, items=None, **kwargs):
    self.items = items or []
    self.total = sum(i["price"] for i in self.items)  # Changes with items!

# ✓ Good: Computed in context
def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx["total"] = sum(i["price"] for i in self.items)
    return ctx
```

### 4. Security: Validate User Permissions
If component displays user-specific data, verify authorization:

```python
@action
async def delete_item(self, request, item_id: int):
    # Verify user owns this item
    item = await Item.find(item_id)
    if not item or item.user_id != request.user.id:
        return HtmlResponse("Unauthorized", status_code=403)
    
    await item.delete()
    self.items = [i for i in self.items if i.id != item_id]
    return await self.render()
```

### 5. Testing Components
Test state management and actions separately from rendering:

```python
@pytest.mark.asyncio
async def test_increment_action():
    comp = CounterComponent(count=5)
    assert comp.count == 5
    
    # Simulate action
    await comp.increment(request=Mock())
    
    assert comp.count == 6
```

---

## Troubleshooting

### State Not Persisting Across Requests
**Problem**: Component state resets when action is triggered.

**Solution**: Ensure `{{ component_attrs }}` is on the button/form element:

```html
<!-- ✗ Missing component_attrs -->
<button hx-post="{{ action_url('save') }}">Save</button>

<!-- ✓ Correct -->
<button hx-post="{{ action_url('save') }}" {{ component_attrs }}>Save</button>
```

### Complex State Not Serializing
**Problem**: Component state with custom objects isn't preserved.

**Solution**: Override `get_state()` to serialize only simple types:

```python
def get_state(self):
    state = super().get_state()
    state["user_id"] = self.user.id if self.user else None
    state.pop("user", None)  # Remove complex object
    return state
```

### Action Parameters Not Coerced
**Problem**: Action receives string instead of int/bool.

**Solution**: Ensure type hints are present:

```python
# ✗ No type hint - item_id is a string
@action
async def delete(self, request, item_id):
    # item_id == "123" (string)
    self.items = [i for i in self.items if i.id != item_id]

# ✓ With type hint - coerced to int
@action
async def delete(self, request, item_id: int):
    # item_id == 123 (int)
    self.items = [i for i in self.items if i.id != item_id]
```

---

## Advanced Topics

### Async Actions
Actions can be async (preferred) or sync:

```python
@action
async def fetch_data(self, request):
    # Async operations: database queries, API calls, etc.
    self.data = await fetch_external_api()
    return await self.render()

@action
def sync_operation(self, request):
    # Sync operations
    self.processed = process_data(self.data)
    return await self.render()
```

### Component Composition
Nest components for complex UIs:

```html
@component("dashboard") {
    @for (widget in widgets) {
        @component("widget", title=widget.title) {
            @component("chart", data=widget.data) { }
        }
    }
}
```

### Debugging
Enable debug info in component context:

```python
def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    if settings.DEBUG:
        ctx["debug"] = {
            "state": self.get_state(),
            "actions": [m for m in dir(self) if hasattr(getattr(self, m), '_is_eden_action')]
        }
    return ctx
```

---

## API Reference

### Component Class

```python
class Component:
    template_name: str  # Required: path to template
    _component_name: str  # Set by @register
    
    def __init__(self, **kwargs)
        # Initialize with arbitrary state
    
    def get_context_data(self, **kwargs) -> dict
        # Prepare template context (override to add computed fields)
    
    def get_state(self) -> dict
        # Get serializable state for HTMX (override for custom serialization)
    
    def get_hx_attrs(self) -> Markup
        # Get HTMX state embedding
    
    async def render(self, **kwargs) -> Markup
        # Render template with current state
    
    def action_url(self, action_name: str) -> str
        # Get URL for action endpoint
    
    @property
    def request() -> Optional[Request]
        # Access current HTTP request
```

### Decorators

```python
@register(name: str)
    # Register component by name (required)

@action(slug: str = None)
    # Mark method as HTMX-callable action (optional slug)
```

---

## See Also

- [HTMX Documentation](https://htmx.org) - Understand hx-post, hx-vals, etc.
- [Eden Templating Guide](./TEMPLATING_GUIDE.md) - Component directives and slots
- [Example Components](../eden/components/) - Built-in components
