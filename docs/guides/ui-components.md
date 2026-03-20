# 🌿 Eden UI: High-Fidelity Component System

Eden provides a production-ready, Premium UI Library built with **Tailwind CSS**, **Alpine.js**, and our custom **@directive** engine. It’s designed to look like a $50,000 custom-built SaaS interface from day one.

---

## 💎 The Design Philosophy: "2026 Premium"

Every component in Eden follows our **High-Fidelity Signature**:
- **Glassmorphism**: Subtle `backdrop-blur-xl` and `border-white/10` for a depth-heavy, modern feel.
- **Accents**: We use **Lime-400** as our primary action color—it's high-contrast, energetic, and professional.
- **Micro-Interactions**: Smooth scale-in/out transitions and hover effects that make the app feel alive.

---

## 🛠️ The Core Directive: `@component`

You invoke components in your templates using the `@component` directive. This is cleaner than standard Jinja2 `include` or `macro` tags and allows for scoped block inheritance.

```html
@component("alert", type="success", dismissible=true) {
    Your profile has been updated successfully!
}
```

### Slots & Props
Most components support **Named Slots** for maximum flexibility:
```html
@component("modal", title="Create Project") {
    <!-- Default Slot (Body) -->
    <p>Ready to start something new?</p>

    @slot("footer") {
        <button class="eden-btn-secondary">Cancel</button>
        <button class="eden-btn-primary">Create</button>
    }
}
```

---

## 📚 Component Catalog

### 1. Modals & Overlays
The Modal is the heart of interactivity. It uses **Alpine.js** for smooth transitions and keyboard support (ESC to close). It also utilizes **x-teleport** to ensure it's rendered at the end of the body, avoiding z-index conflicts.

**Properties:**
- `id`: Unique identifier (referenced by events).
- `title`: Header text.
- `size`: `sm`, `md`, `lg`, `xl`, `full` (default: `md`).

**Example:**
```html
@component("modal", id="upload-modal", title="Upload Asset") {
    @slot("trigger") {
        <button class="eden-btn-primary">Upload File</button>
    }
    
    <div class="space-y-4">
        <label class="block text-sm font-medium">Select File</label>
        <input type="file" class="eden-input">
    </div>

    @slot("footer") {
        <button class="eden-btn-primary w-full">Start Upload</button>
    }
}
```

### 2. Tabs & Navigation
Tabs are perfect for breaking up complex dashboards. They use **x-transition** for smooth horizontal sliding effects.

**Properties:**
- `tabs`: List of `{"id": "...", "label": "..."}` objects.
- `active`: Index of the start tab (default: `0`).

**Example:**
```html
@component("tabs", active=0, tabs=[
    {"id": "overview", "label": "Overview"},
    {"id": "analytics", "label": "Analytics"},
    {"id": "settings", "label": "Settings"}
]) {
    @slot("tab_overview") {
        <p>Main dashboard content goes here...</p>
    }
}
```

### 3. Stat Cards
Used for displaying high-level metrics with visual progress indicators.

```html
<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
    @component("stat", label="Active Revenue", value="$12,840", trend="+12.5%", icon="payments", progress=75)
    @component("stat", label="New Customers", value="1,240", trend="+3.2%", icon="group", progress=40)
    @component("stat", label="Server Load", value="24%", trend="-0.5%", icon="speed", progress=24)
</div>
```

---

## 🏗️ Building a Complete Page from Scratch

Let's build a **Professional Dashboard** using only Eden components.

### 1. The Layout Base
We use the `app-layout` component to provide the sidebar and top navigation context.

```html
@component("app-layout", title="Cloud Console") {
    @slot("sidebar") {
        <div class="space-y-1">
            <a href="/" class="flex items-center gap-3 px-3 py-2 text-lime-400 bg-lime-400/10 rounded-lg">
                <span class="material-symbols-outlined text-xl">grid_view</span>
                <span class="font-medium">Dashboard</span>
            </a>
            <!-- Additional links -->
        </div>
    }

    <!-- Main Content -->
    <div class="space-y-8">
        @yield("content")
    </div>
}
```

### 2. High-Fidelity Dashboard Content
Inside your page, combine the layout with interactive components.

```html
@section("content") {
    <div class="flex items-end justify-between mb-8">
        <div>
            <h1 class="text-3xl font-bold tracking-tight">Project Overview</h1>
            <p class="text-slate-400">Real-time performance across all nodes.</p>
        </div>
        
        <!-- Action Button with Modal -->
        @component("modal", id="config-modal", title="Node Configuration") {
            @slot("trigger") {
                <button class="eden-btn-primary flex items-center gap-2">
                    <span class="material-symbols-outlined text-lg">settings</span>
                    Configure Fleet
                </button>
            }
            
            <div class="space-y-4">
                <p class="text-slate-400">Select the deployment targets for the next cycle.</p>
                <div class="grid grid-cols-2 gap-3">
                    <button class="p-4 border border-lime-500/30 bg-lime-500/5 rounded-xl text-left">
                        <span class="block font-bold">US-East</span>
                        <span class="text-sm text-slate-500">12 Nodes</span>
                    </button>
                    <!-- More targets -->
                </div>
            </div>
        }
    </div>

    <!-- Metrics Row -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        @component("stat", label="Total Revenue", value="$124,500", trend="+14%", icon="payments", progress=75)
        @component("stat", label="Active Users", value="12,402", trend="+5%", icon="group", progress=40)
        @component("stat", label="Server Load", value="24%", trend="-2%", icon="speed", progress=24)
    </div>

    <!-- Main View: Tabs + Data -->
    <div class="eden-card overflow-hidden">
        @component("tabs", tabs=[
            {"id": "activity", "label": "Recent Activity"},
            {"id": "topology", "label": "Network Topology"}
        ]) {
            @slot("tab_activity") {
                @component("data-table", items=recent_events, columns=[
                    {"key": "user", "label": "User"},
                    {"key": "action", "label": "Action"},
                    {"key": "time", "label": "Time"}
                ])
            }
        }
    </div>
}
```

---

## 🚀 Advanced Interactivity & State

### 🎨 Mastering Alpine.js in Eden
To avoid conflicts between the Eden Templating Engine and Alpine.js, we follow these **Premium Rules**:

1.  **Use Full Attributes**: Avoid `@click` or `:class`. Use `x-on:click` and `x-bind:class`. This prevents the Eden lexer from confusing them with framework directives.
2.  **External Events**: Trigger Eden components from anywhere using custom events.
    ```html
    <!-- Trigger the 'config-modal' from a separate button -->
    <button x-on:click="$dispatch('eden:modal-open', { id: 'config-modal' })">
        Remote Toggle
    </button>
    ```

### 🏛️ Smart Fragment Resolution (HTMX)
Eden components automatically support partial updates. When you make an HTMX request with a `HX-Target` matching a component ID, Eden only renders that specific fragment.

```html
<!-- Only the 'activity-list' fragment will be re-rendered and swapped -->
<button hx-get="/activity/refresh" 
        hx-target="#activity-list" 
        hx-trigger="click">
    Refresh Logs
</button>
```

---

## 💎 Utility Reference

### Button Classes
- `eden-btn-primary`: Vibrant Lime highlight.
- `eden-btn-secondary`: Subtle slate ghost button.
- `eden-btn-danger`: Alert/Exit actions.

### Input Classes
- `eden-input`: Standard text/password field with focus glow.
- `eden-select`: Styled dropdown.
- `eden-checkbox`: Premium custom checkbox.

---

## 🛠️ Customizing the CSS
Eden uses CSS Variables for easy white-labeling. Update these in your global stylesheet:

```css
:root {
  --eden-primary: theme('colors.lime.400');
  --eden-bg: #0F172A;
  --eden-accent: #38BDF8; /* Light blue accent */
}
```
