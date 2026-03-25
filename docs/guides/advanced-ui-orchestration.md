# 🌿 Eden UI: Advanced Orchestration Master Class

This guide delves into the internal mechanics of the **Eden Orchestration Engine**. It is designed for senior developers who need to understand how Eden bridges the gap between Python server-side logic and high-fidelity browser interactions.

---

## 🎨 Part 1: The Widget Engine (Fluent Form Styling)

Eden doesn't just render HTML; it provides a **Fluent API** for manipulating form fields in real-time within your templates. This eliminates the need for dirty "Widget" classes in your Python code, keeping your UI logic where it belongs: in the view/template layer.

### ⛓️ Method Chaining

Every `FormField` returned by `form["field_name"]` supports chaining. These methods return a **clone** of the field, ensuring that one rendering doesn't pollute the next.

| Method | Description | Example |
| :--- | :--- | :--- |
| `.add_class(cls)` | Appends a CSS class. | `form["email"].add_class("border-red-500")` |
| `.attr(key, val)` | Sets or updates an attribute. | `form["search"].attr("placeholder", "Find...")` |
| `.append_attr(k, v)` | Appends value to existing attr (with space). | `form["btn"].append_attr("x-on:click", "open=true")` |
| `.render_composite()` | Renders Label + Input + Errors. | `{{ form["email"].render_composite() }}` |

### 🚀 Example: The "Live Validation" Input

In this elite pattern, we use chaining to inject HTMX validation directly into a standard Pydantic-backed form:

```html
<form method="POST">
    {{ form.render_csrf() | safe }}
    
    <div class="mb-4">
        {{ form["username"]
            .add_class("eden-input-glass")
            .attr("hx-post", "/auth/check-username")
            .attr("hx-trigger", "keyup changed delay:500ms")
            .attr("hx-target", "#username-status")
            .render_composite() | safe 
        }}
        <div id="username-status"></div>
    </div>
    
    <button type="submit" class="eden-btn-primary">Secure Join</button>
</form>
```

---

## 🧠 Part 2: The Action Engine (Stateful Components)

The most powerful feature of Eden is the **Stateful Python Component**. This allows you to build complex UI widgets (like a multi-step wizard or a dynamic data table) entirely in Python, while HTMX handles the atomic updates.

### 🏛️ Architecture of a Component

A component consists of three parts.

1. **Python Class**: Inherits from `eden.components.Component`.
1. **Template**: A `.html` file inside `templates/eden/`.
1. **State Management**: Automatic HMAC-signed serialization of class attributes.

### 🛡️ Secure State Persistence

When a component renders, Eden serializes its public attributes into a JSON object, signs it with your `SECRET_KEY`, and embeds it in the HTML via `hx-vals`.

When you trigger an **Action** (a method decorated with `@action`), HTMX sends this state back to the server. Eden:
1. **Verifies** the signature (preventing client-side tampering).
2. **Re-hydrates** the component instance.
3. **Executes** the requested method.

### 🚀 Implementation Example: The `ReactiveCounter`

**1. The Python Logic (`app/components.py`):**

```python
from eden.components import Component, action

class ReactiveCounter(Component):
    # Public attributes are automatically persisted in 'state'
    count: int = 0
    label: str = "Taps"

    @action
    async def increment(self, amount: int = 1):
        """Update state server-side."""
        self.count += amount
        # Returning self triggers a re-render of the component fragment
        return self

    def get_template_name(self):
        return "eden/counter.html"
```

**2. The Fragment Template (`templates/eden/counter.html`):**

```html
<div class="eden-card p-6 text-center" id="{{ component_id }}">
    <h3 class="text-xs uppercase tracking-widest text-white/50">{{ label }}</h3>
    <div class="text-5xl font-bold my-4 font-mono">{{ count }}</div>
    
    <div class="flex gap-2 justify-center">
        <button class="eden-btn-secondary" 
                hx-post="{{ action_url('increment', amount=-1) }}"
                {{ action_trigger() }}>
            -1
        </button>
        <button class="eden-btn-primary" 
                hx-post="{{ action_url('increment', amount=1) }}"
                {{ action_trigger() }}>
            +1
        </button>
    </div>
</div>
```

---

## 📦 Part 3: Advanced Asset Bundling

Eden components are designed to be **Self-Contained Modules**. You can bundle scoped CSS and Alpine.js logic directly within the component definition.

### 🛡️ Scoped Reactivity with `@reactive`

The `@reactive` directive in Jinja2 ensures that your component's JavaScript and CSS are only loaded once per page, even if multiple instances of the component exist.

```html
@reactive {
    <style>
        .custom-widget { 
            background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%); 
        }
    </style>
    
    <script>
        console.log("Component framework initialized.");
    </script>
}
```

### 🧠 The Global `AssetManager`

When `ComponentExtension` encounters a `@reactive` block, it extracts the contents and passes them to the `AssetManager`. During the final page render:

1. All extracted `<style>` tags are concatenated into a single `<style id="eden-component-styles">` block in the `<head>`.
2. All `<script>` blocks are moved to the end of the `<body>`.
3. Duplicates are automatically pruned based on content hash.

---

## 🏗️ Part 4: The "Component Dispatcher" Pattern

To enable component actions, you must register the **Global Action Route** in your application. This single endpoint handles re-hydration and dispatching for **all** components in your system.

```python
from eden.components import component_action_handler
from starlette.routing import Route

# Single route that powers every interactive component in the app
routes = [
    Route("/_eden/component/{component_name}/{action_name}", 
          component_action_handler, 
          methods=["POST"], 
          name="eden_component_action")
]
```

### 🤝 Integration with Multi-Tenancy

Because `component_action_handler` runs inside your application's middleware stack, it automatically inherits the `tenant_id` context. This ensures that a component re-hydrated in "Tenant A" cannot perform actions against "Tenant B's" data, even if the state signature is valid.

---

## 💎 Elite Best Practices

1. **Keep State Lean**: Only store what is necessary for UI representation. Use IDs, not full objects, to keep the `hx-vals` payload small.
2. **Prefer OOB Swaps**: If an action in one component needs to update a different part of the page (e.g., a "Notification Bell"), return an **Out-of-Band Swap** fragment.
3. **Type Hint Actions**: Eden uses Python type-hint inspection to automatically coerce `hx-vals` strings into `int`, `float`, or `bool` before calling your action method.

> [!IMPORTANT]
> Always use `{{ action_trigger() | safe }}` on your HTMX elements. This helper injects the necessary target and swap attributes to ensure the re-rendered fragment replaces the correct DOM node.
