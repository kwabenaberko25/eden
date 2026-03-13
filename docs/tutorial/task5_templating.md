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
                <h3 class="font-bold text-xl">@span(user.name)</h3>
                <p class="text-slate-400 text-sm">@span(user.email)</p>
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
- **`@span(variable)`**: Eden template variable interpolation (replaces Jinja2 `{{ variable }}`)

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

## 🎨 Step 5.4: Conditional Rendering & Advanced Directives

Make your templates dynamic and interactive:

```html
@extends("layouts/base")

@section("title") { User Dashboard }

@section("content") {
    <h1>Welcome, @span(user.name)!</h1>

    <!-- Conditional: Show premium features only if user is subscribed -->
    @if (user.is_premium) {
        <div class="premium-badge">✨ Premium Member</div>
        <p>You have access to advanced features!</p>
    } @else {
        <p>Upgrade to Premium to unlock more features.</p>
        <a href="/upgrade" class="btn btn-primary">Upgrade Now</a>
    }

    <!-- Switch/Case: Show different content based on user role -->
    @switch (user.role) {
        @case ("admin") {
            <button class="btn btn-danger">Delete All Users</button>
        }
        @case ("moderator") {
            <button class="btn btn-warning">Flag Inappropriate Content</button>
        }
        @default {
            <p>You are a regular user.</p>
        }
    }

    <!-- Loop with index and conditions -->
    <h2>Your Recent Posts</h2>
    @if (posts | length > 0) {
        <ul class="post-list">
            @for (post in posts) {
                <li class="post-item">
                    <span class="post-number">#@span($loop.index)</span>
                    <strong>@span(post.title)</strong>
                    <p>@span(post.content | truncate(100))</p>
                    
                    <!-- Show "Featured" badge only on the first post -->
                    @if ($loop.first) {
                        <span class="badge">Featured</span>
                    }
                    
                    <!-- Show edit button only on user's own posts -->
                    @if (post.user_id == current_user.id) {
                        <a href="/posts/@span(post.id)/edit" class="btn btn-sm">Edit</a>
                    }
                </li>
            }
        </ul>
    } @else {
        <p class="empty-state">You haven't written any posts yet.</p>
    }
}
```

---

## 🔗 Step 5.5: Template Inheritance & Blocks

Create specialized layouts for different sections of your app:

```html
<!-- templates/layouts/admin.html -->
@extends("layouts/base")

@section("content") {
    <div class="admin-container">
        <aside class="admin-sidebar">
            <nav>
                <a href="/admin">Dashboard</a>
                <a href="/admin/users">Users</a>
                <a href="/admin/settings">Settings</a>
            </nav>
        </aside>
        
        <main class="admin-main">
            @yield("admin_content")
        </main>
    </div>
}
```

Then in your admin page:
```html
@extends("layouts/admin")
@section("admin_content") {
    <h2>User Management</h2>
    <!-- admin-specific content here -->
}
```

---

## 💾 Step 5.6: Form Rendering in Templates

Combine schemas from Task 6 with your templates for seamless form handling:

```html
@extends("layouts/base")

@section("content") {
    <div class="form-container">
        <h2>Create New Post</h2>

        <form method="POST" action="/posts" class="form">
            @csrf

            <!-- Automatic field rendering with error handling -->
            <div class="form-group">
                @render_field(form['title'], 
                    class="form-input",
                    placeholder="Enter post title"
                )
                @error("title") {
                    <span class="error-message">@span(message)</span>
                }
            </div>

            <div class="form-group">
                @render_field(form['content'].as_textarea(),
                    class="form-textarea",
                    rows="8"
                )
                @error("content") {
                    <span class="error-message">@span(message)</span>
                }
            </div>

            <button type="submit" class="btn btn-primary">Create Post</button>
        </form>
    </div>
}
```

---

## 📱 Step 5.7: Responsive Design & CSS Integration

Use Tailwind CSS (included via CDN in base.html) for rapid styling:

```html
@extends("layouts/base")

@section("content") {
    <!-- Responsive grid: 1 column on mobile, 3 on desktop -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        @for (stat in dashboard_stats) {
            <div class="p-6 bg-blue-50 rounded-lg shadow-md hover:shadow-lg transition-shadow">
                <h3 class="text-lg font-bold">@span(stat.label)</h3>
                <p class="text-3xl font-black text-blue-600">@span(stat.value)</p>
            </div>
        }
    </div>

    <!-- Sticky navigation -->
    <nav class="sticky top-0 bg-white shadow-md p-4">
        <a href="/" class="text-blue-600 font-bold">Home</a>
        <a href="/about" class="ml-4">About</a>
        <a href="/contact" class="ml-4">Contact</a>
    </nav>
}
```

---

### **Next Task**: [Handling Forms & Validation](./task6_forms.md)
