# Task 5: Implement Premium UI with Templating

**Goal**: Move beyond JSON and render stunning, high-performance HTML pages using Eden's directive-driven templating engine.

---

## 🏰 Step 5.1: The "Base" Layout Pattern

Stop repeating yourself. Define a global layout once and inherit from it in every page.

**File**: `templates/layouts/base.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>@yield("title") — Eden</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 p-12">
    <nav class="mb-10 flex gap-4">
        <a href="/" class="text-blue-400 font-bold">Lumina Dashboard</a>
    </nav>
    
    <main class="max-w-4xl mx-auto">
        @yield("content")
    </main>
</body>
</html>
```

### 🧠 Layout Directives

- **`@yield("name")`**: Defines a placeholder or "hole" in your layout where child templates inject content (e.g. `@yield("content")`).
- **`@stack("name")`**: Defines an aggregation point, perfect for collecting CSS or JS from multiple child pages.

---

## 📄 Step 5.2: Creating your first Page

Use Eden's clean inheritance syntax to build rich, data-driven pages.

**File**: `templates/user_list.html`

```html
@extends("layouts/base")

@section("title") { Community Members }

@section("content") {
    <h1 class="text-4xl font-black mb-6">Our Community</h1>

    <div class="grid gap-4">
        @for (user in members) {
            <div class="p-6 bg-slate-800 rounded-2xl border border-white/5 shadow-xl">
                <h3 class="font-bold text-xl">{{ user.name }}</h3>
                <p class="text-slate-400 text-sm">{{ user.email }}</p>
            </div>
        } @empty {
            <p class="text-slate-500 italic">Nobody has joined the community yet.</p>
        }
    </div>
}
```

### ✨ Premium Features

- **`@extends("layout")`**: Declares that this template inherits from a layout. It must be the first line.
- **`@section("name") { ... }`**: Fills a `@yield` placeholder defined in the parent layout.
- **`@push("name") { ... }`**: Appends content to a `@stack` defined in the parent layout (great for adding page-specific `<script>` tags).
- **`@for (...) { ... } @empty { ... }`**: A logical, readable loop that handles empty states natively.
- **`{{ variable }}`**: Standard Jinja2-style interpolation.

---

## 🎨 Step 5.3: Rendering the Template

Back in your router, use the simple `.render()` helper to send the page to the client.

**File**: `app/routes/user.py`

```python
@user_router.get("/directory")
async def show_directory(request):
    """Render the community member directory."""
    members = await User.all()
    
    # Render using the request.render helper
    return request.render("user_list.html", {"members": members})
```

> [!TIP]
> For the ultimate clean syntax, you can also use `from eden import render_template`. It uses the current request context automatically:
> ```python
> return render_template("user_list.html", members=members)
> ```

> [!NOTE]
> Eden automatically looks for templates in the `templates/` directory defined in your app configuration.

---

### **Next Task**: [Handling Forms & Validation](./task6_forms.md)
