# Modern Templating Architecture 📝

Eden replaces the verbose Jinja2 tags with a clean, brace-based `@directive` syntax. It is designed to be expressive, readable, and fully line-preserving.

## The `@` Syntax

Unlike traditional templates that use `{% ... %}`, Eden uses `@` followed by the directive name and optional parentheses for arguments.

---

## Control Flow 🎢

### Loops

```html
@for (item in items) {
    <li>{{ item }}</li>
    @even { <span class="badge">Even Row</span> }
    @odd { <span class="badge">Odd Row</span> }
} @empty {
    <p>Nothing to show.</p>
}
```

### Loop Helpers

Beyond the `$loop` object, Eden provides clean directives for conditional rendering within loops:

| Directive | Description |
| :--- | :--- |
| `@even { ... }` | Renders only on even iterations. |
| `@odd { ... }` | Renders only on odd iterations. |
| `@first { ... }` | Renders only on the first iteration. |
| `@last { ... }` | Renders only on the last iteration. |

#### The `$loop` Object

Inside a `@for` loop, you have access to the `$loop` object (a wrapper around Jinja2's `loop` context) to get metadata about the current iteration.

| Property | Description |
| :--- | :--- |
| `$loop.index` | The current iteration (1-indexed). |
| `$loop.index0` | The current iteration (0-indexed). |
| `$loop.revindex` | Number of iterations from the end (1-indexed). |
| `$loop.revindex0` | Number of iterations from the end (0-indexed). |
| `$loop.first` | True if this is the first iteration. |
| `$loop.last` | True if this is the last iteration. |
| `$loop.length` | Total number of items in the sequence. |
| `$loop.iteration` | Same as `index`. |
| `$loop.even` | True if the current iteration is even. |
| `$loop.odd` | True if the current iteration is odd. |

Example usage:
```html
@for (user in users) {
    <div class="{{ $loop.even ? 'bg-gray-800' : 'bg-gray-900' }}">
        {{ user.name }} @if($loop.first) { (Admin) }
    </div>
}
```

#### Directive Parameters & Syntax

| Category | Directive | Parameters | Description |
| :--- | :--- | :--- | :--- |
| **Control** | `@if(cond)` | `cond`: Boolean expr | Standard if-block. |
| | `@unless(cond)` | `cond`: Boolean expr | Inverse if (if not). |
| | `@for(i in list)` | `i in list` | Loop. Access `$loop` properties. |
| | `@empty` | None | Content to show if loop is empty. |
| | `@switch(val)` | `val`: Any | Open a switch block. |
| | `@case(val)` | `val`: Any | Match a switch case. |
| **Auth** | `@auth` | None | Only for logged-in users. |
| | `@guest` | None | Only for non-logged-in users. |
| **HTMX** | `@htmx` | None | Only for HTMX requests. |
| | `@non_htmx` | None | Only for standard (non-HTMX) requests. |
| | `@fragment(id)` | `id`: String | Defines a targetable partial. |
| **Forms** | `@csrf` | None | Emits hidden CSRF input. |
| **Logic** | `@let var = val` | `var`, `val` | Inline variable assignment. |
| | `@url(name)` | `name`: String | Generates a URL for a route. |
| | `@active_link(name, cls)` | `name`, `cls` | Emits `cls` if route is active. |
| **Logic** | `@even` | None | Content for even loop rows. |
| | `@odd` | None | Content for odd loop rows. |
| | `@first` | None | Content for the first loop row. |
| | `@last` | None | Content for the last loop row. |

---

## Layouts & Inheritance 🧱

Eden's layout system allows you to build a reusable shell for your application and inject specific content for each page.

### 1. The `@extends` & `@yield` Pattern

The `@extends` directive tells Eden that this template inherits from another one. The `@yield` directive defines a placeholder in the layout that can be filled by children.

#### **Layout Template** (`layouts/base.html`)
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <title>@yield("title") — Eden App</title>
    @yield("styles")
</head>
<body class="bg-slate-900 text-white">
    <nav>...</nav>

    <main class="container mx-auto p-8">
        <!-- Main content placeholder -->
        @yield("content")
    </main>

    <!-- Global scripts placeholder -->
    @yield("scripts")
</body>
</html>
```

#### **Child Template** (`home.html`)
```html
@extends("layouts/base")

@section("title") { Welcome Home }

@section("content") {
    <h1 class="text-4xl font-bold">Premium Dashboard</h1>
    <p class="text-slate-400">Welcome to your new async workspace.</p>
}

@section("scripts") {
    <script>console.log("Welcome home!");</script>
}
```

---

### 2. Stacks & Pushing 🏗️

While `@section` replaces the content in a `@yield` placeholder, sometimes you want to *collect* content from multiple components or child templates (like adding CSS from different UI parts). For this, use `@stack` and `@push`.

*   **`@stack("name")`**: Defines a location in your layout to aggregate content.
*   **`@push("name") { ... }`**: Appends content to the corresponding stack.

**In Layout (`base.html`):**
```html
<head>
    <!-- Collect all pushed styles here -->
    @stack("styles")
</head>
```

**In Component or Page (`profile.html`):**
```html
@push("styles") {
    <style>.profile-card { border: 1px solid teal; }</style>
}
```

---

### 3. Advanced Block Controls

| Directive | Type | Usage | Description |
| :--- | :--- | :--- | :--- |
| `@yield(name)` | Layout | `@yield("content")` | Defines a hole for child content. |
| `@stack(name)` | Layout | `@stack("js")` | Defines an aggregation point. |
| `@section(name)` | Child | `@section("content") { ... }` | Replaces the yield in the parent. |
| `@push(name)` | Child | `@push("js") { ... }` | Appends content to the stack. |
| `@super` | Child | `@super` | Access content from the parent's block. |

### Reusable Components

Components allow you to encapsulate both logic and UI. Unlike inheritance, components are for smaller, repeatable pieces of UI.

```html
@component("ui/card", title="Profile", elevation="xl") {
    @slot("header") {
        <img src="/avatar.png" class="rounded-full">
    }
    <p>User bio goes here...</p>
}
```

---

## Forms & Security 🛡️

Secure your forms with zero effort.

```html
<form method="POST" action="/profile">
    @csrf
    @method("PUT")  <!-- Spoof PUT/PATCH/DELETE methods -->
    
    <div class="space-y-6">
        <!-- Method 1: The Magic @render_field directive -->
        <div class="field-wrapper">
            @render_field(form['email'], class="w-full rounded bg-slate-800 border-slate-700")
        </div>

        <!-- Method 2: Manual field construction using @old and @error -->
        <div class="manual-field-group">
            <label>Email</label>
            <input type="text" name="email" value="@old('email')" 
                   class="w-full rounded bg-slate-800 border-slate-700">
            
            @error("email") {
                <span class="text-xs text-emerald-500">{{ message }}</span>
            }
        </div>
    </div>
    
    <button type="submit">Update</button>
</form>

## HTMX & Fragment Rendering ⚡

Eden provides first-class support for **HTMX** with the `@fragment` directive. This allows you to define pieces of a page that can be rendered independently.

```html
<!-- index.html -->
<div>
    <h1>Welcome</h1>
    
    @fragment("user-list") {
        <ul id="users">
            @for (user in users) {
                 <li>{{ user.name }}</li>
            }
        </ul>
    }
</div>
```

In your Python route, you can render **just the fragment** without the surrounding layout:

```python
@app.get("/users")
async def list_users(request):
    users = await User.all()
    # Renders ONLY the <ul>, not the <h1> or layout!
    return request.render("index.html", users=users, fragment="user-list")
```

### The `request.render` Method

Every Eden `Request` object has a built-in `.render()` method. This is the idiomatic way to render templates when you have a request object in your handler.

```python
@app.get("/dashboard")
async def dashboard(request):
    return request.render("dashboard.html", user=request.user)
```

### The `render_template` Global Helper

For the ultimate clean syntax, you can use the `render_template` global helper (imported from `eden`). It automatically discovers the current request context using Python context variables, so you don't even need to pass the `request` object.

```python
from eden import render_template

@app.get("/")
async def home():
    return render_template("home.html", title="Welcome Home")
```


---

## Assets & Vite 📦

Manage your CSS and JS bundles easily.

```html
@css("style.css")
@js("app.js")

@vite(["resources/css/app.css", "resources/js/app.js"])
```

---

## Logic & Variables 🧠

```html
@let price = 99.99
@set discount = 0.1

<p>Discounted: {{ price * (1 - discount) }}</p>

<!-- Outputs safe JSON for Alpine.js or scripts -->
<div x-data='@json(user_data)'> ... </div>

<!-- Debugging: Pretty prints an object in a <pre> tag -->
@dump(request)
```

---

Eden includes Jinja2 filters that map directly to the **Elite** design tokens and functional helpers.

### General Purpose Filters

| Filter | Description | Example |
| :--- | :--- | :--- |
| `date` | Locale-aware date. | `{{ task.due_at\|date }}` |
| `time` | Locale-aware time. | `{{ task.due_at\|time }}` |
| `number` | Thousand separators. | `{{ 1500000\|number }}` |
| `currency` | Localized symbol. | `{{ 50\|currency }}` |
| `json_encode` | Safe JSON encoding. | `x-data="{{ data\|json_encode }}"` |
| `mask` | Mask sensitive data. | `{{ "cobby@eden.dev"\|mask }}` |
| `file_size` | Human file size. | `{{ 1048576\|file_size }}` |

### Design System Filters

| Filter | Usage | Effect |
| :--- | :--- | :--- |
| `eden_bg` | `{{ "primary"\|eden_bg }}` | Background color token. |
| `eden_text` | `{{ "white"\|eden_text }}` | Text color token. |
| `eden_shadow` | `{{ "lg"\|eden_shadow }}` | Elevation tokens. |
| `eden_font` | `{{ "heading"\|eden_font }}` | Typography tokens. |

---

---

## Elite Component: Data Table 📊

Build a powerful, reusable data table with sorting and premium styling.

```html
<!-- templates/components/data_table.html -->
<div class="overflow-x-auto rounded-xl border border-gray-700 bg-gray-900/50 backdrop-blur-md">
    <table class="w-full text-left">
        <thead class="bg-gray-800/50 text-sm font-semibold uppercase text-gray-400">
            <tr>
                @for (col in columns) {
                    <th class="px-6 py-4">{{ col.label }}</th>
                }
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-800">
            @for (row in data) {
                <tr class="hover:bg-gray-800/30 transition-colors">
                    @for (col in columns) {
                        <td class="px-6 py-4">{{ row[col.key] }}</td>
                    }
                </tr>
            }
        </tbody>
    </table>
</div>
```

**Next Steps**: [Forms & Validation](forms.md)
