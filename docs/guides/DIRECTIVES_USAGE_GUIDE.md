# Eden @Directives - Comprehensive Usage Guide 🚀

A practical, real-world guide to every Eden templating directive with examples.

---

## Quick Reference

| Category | Directives |
| :--- | :--- |
| **Control Flow** | `@if`, `@unless`, `@switch`/`@case`, `@for`/`@foreach`, `@empty` |
| **Authentication** | `@auth`, `@guest` |
| **Authorization** | `@can`, `@cannot` |
| **HTMX** | `@htmx`, `@non_htmx`, `@fragment` |
| **Templating** | `@extends`, `@include`, `@includeWhen`, `@includeUnless`, `@section`/`@block`, `@yield`, `@push`, `@stack` |
| **Forms** | `@csrf`, `@csrf_token`, `@checked`, `@selected`, `@disabled`, `@readonly`, `@old` |
| **Routing** | `@url`, `@route`, `@active_link` |
| **Assets** | `@css`, `@js`, `@vite` |
| **Data** | `@let`, `@json`, `@dump`, `@span` |
| **Components** | `@component`, `@slot` |
| **Messages** | `@error`, `@messages` |
| **Attributes** | `@method` |

---

## Control Flow Directives

### @if - Conditional Rendering

```html
<!-- Simple if -->
@if (user.is_verified) {
    <div class="badge">✓ Verified</div>
}

<!-- Complex expression -->
@if (user.role == 'admin' || user.is_moderator) {
    <div class="admin-panel">...</div>
}

<!-- Accessing object properties -->
@if (post.published_date) {
    <p>Published: {{ post.published_date }}</p>
}
```

### @unless - Inverted If

```html
<!-- Only shows if condition is FALSE -->
@unless (user.is_banned) {
    <button>Participate</button>
}

<!-- Equivalent to: @if (!user.is_banned) -->
```

### @for/@foreach - Looping

```html
<!-- Loop with item and index -->
@for (item in items) {
    {{ $loop.index }}: {{ item.name }}
}

<!-- Alternative syntax -->
@foreach (user in users) {
    <li>{{ user.name }}</li>
}

<!-- With filter or map -->
@for (item in items | select_active) {
    <p>{{ item }}</p>
}

<!-- Dictionary/object iteration -->
@for (key, value in dict.items) {
    {{ key }}: {{ value }}
}

<!-- Using $loop helpers -->
@for (item in items) {
    <div class="{{ $loop.even ? 'bg-gray-800' : 'bg-gray-900' }}">
        @if ($loop.first) {
            <strong>First item:</strong>
        }
        {{ item.name }}
        @if ($loop.last) {
            <em>That's all folks!</em>
        }
    </div>
}
```

#### Available $loop Properties

- `$loop.index` - Current iteration (1-based)
- `$loop.index0` - Current iteration (0-based)
- `$loop.first` - Is this first iteration?
- `$loop.last` - Is this last iteration?
- `$loop.even` - Is iteration even?
- `$loop.odd` - Is iteration odd?
- `$loop.length` - Total items
- `$loop.revindex` - Iterations from end

### @switch/@case - Multi-branch Logic

```html
@switch (user.status) {
    @case ('active') {
        <span class="badge badge-green">Active</span>
    }
    @case ('pending') {
        <span class="badge badge-yellow">Pending Review</span>
    }
    @case ('suspended') {
        <span class="badge badge-red">Suspended</span>
    }
}

<!-- Without @case (direct if) -->
@switch (payment_method) {
    @case ('card') { <i class="icon-card"></i> Card }
    @case ('paypal') { <i class="icon-paypal"></i> PayPal }
    @case ('bank') { <i class="icon-bank"></i> Bank Transfer }
}
```

### @empty - For Loop Empty State

```html
@for (item in search_results) {
    <div class="result">{{ item.title }}</div>
} @empty {
    <div class="empty-state">
        <p>No results found for "{{ query }}"</p>
    </div>
}
```

### @elsif / @else if - Chained Conditions

```html
@if (score >= 90) {
    <div class="grade">A</div>
} @else if (score >= 80) {
    <div class="grade">B</div>
} @else if (score >= 70) {
    <div class="grade">C</div>
} @else {
    <div class="grade">F</div>
}
```

> [!TIP]
> Both `@elsif` and `@else if` are supported, but `@else if` is preferred for readability.

---

## Loop Helpers

### @even/@odd - Striped Rows

```html
@for (row in table_data) {
    <tr class="@even { bg-gray-800 } @odd { bg-gray-900 }">
        <td>{{ row.name }}</td>
        <td>{{ row.value }}</td>
    </tr>
}
```

### @first/@last - Special Row Handling

```html
<!-- Add header styling to first row -->
@for (item in items) {
    <div class="@first { font-bold border-b-2 }">
        {{ item.name }}
    </div>
}

<!-- Add separator after last row -->
@for (product in products) {
    <div>{{ product.name }}: ${{ product.price }}</div>
    @last { <hr> }
}
```

---

## Authentication Directives

### @auth - Protected Content

```html
<!-- Only visible to logged-in users -->
@auth {
    <div class="user-menu">
        <p>Welcome, {{ user.name }}!</p>
        <a href="@url('profile')">My Profile</a>
        <a href="@url('logout')">Logout</a>
    </div>
}

> [!TIP]
> Eden automatically injects the `user` object into the context from `request.state.user`. You can access it directly as `user` or via `request.user`.

<!-- Used in navigation -->
<nav>
    @auth {
        <a href="@url('dashboard')">Dashboard</a>
        <a href="@url('settings')">Settings</a>
    }
</nav>
```

### @guest - Unauthenticated Content

```html
<!-- Only visible to non-logged-in users -->
@guest {
    <div class="login-box">
        <a href="@url('auth:login')">Login</a>
        <a href="@url('auth:register')">Sign Up</a>
    </div>
}

<!-- Redirect message -->
@guest {
    <div class="alert">
        <a href="@url('auth:login')">Please log in</a> to continue.
    </div>
}
```

---

## Authorization Directives

### @can / @cannot - Permission-Based Rendering

Check `request.user.has_permission()` to conditionally show or hide content based on fine-grained permissions.

```html
<!-- Show only if user has permission -->
@can("delete_posts") {
    <button class="btn-danger">Delete Post</button>
}

<!-- Show only if user does NOT have permission -->
@cannot("view_admin") {
    <div class="alert alert-warning">
        You do not have access to the admin panel.
    </div>
}

<!-- Combine with @auth for role-based + permission-based UI -->
@auth("admin") {
    @can("manage_users") {
        <a href="@url('admin:users')" class="nav-link">User Management</a>
    }
}
```

> [!TIP]
> Use `@auth` for role-based checks and `@can`/`@cannot` for fine-grained permission checks. They can be nested for compound authorization logic.

---

## HTMX Integration

### @htmx - HTMX Request Only

```html
<!-- Only render fragment for HTMX requests -->
<div class="content">
    @htmx {
        @fragment("results") {
            @for (item in results) {
                <div>{{ item }}</div>
            }
        }
    }
    
    @non_htmx {
        <!-- Full page layout for regular requests -->
        <h1>Search Results</h1>
        @fragment("results") { ... }
        <footer>...</footer>
    }
}
```

### @fragment - HTMX Target

```html
<!-- Target with hx-target="#results" -->
<div id="results">
    @fragment("results") {
        <div class="item">Item 1</div>
        <div class="item">Item 2</div>
    }
</div>

<!-- Usage -->
<button hx-get="@url('search')" hx-target="#results">
    Search
</button>
```

---

## Routing Directives

### @url - Generate URLs

```html
<!-- Basic route -->
<a href="@url('home')">Home</a>

<!-- With parameters -->
<a href="@url('posts:show', id=post.id)">{{ post.title }}</a>

<!-- Multiple parameters -->
<a href="@url('api:get-user-comments', user_id=123, page=2)">
    Comments
</a>

<!-- Store in variable -->
@let edit_url = @url('posts:edit', id=post.id)
<a href="{{ edit_url }}" class="btn btn-blue">Edit</a>

<!-- Dynamic route name -->
@let route = 'posts:show'
<a href="@url(route, id=post.id)">View</a>
```

### @active_link - Highlight Active Navigation

The `@active_link` directive intelligently marks links as active based on the current URI. It supports exact route names, wildcard sections (`*`), and even an optional third parameter for "inactive" styling.

```html
<!-- Simple active highlight -->
<nav class="flex gap-4">
    <a href="@url('dashboard')" class="@active_link('dashboard', 'active')">
        Dashboard
    </a>
    <a href="@url('settings')" class="@active_link('settings', 'active')">
        Settings
    </a>
</nav>

<!-- WILDCARD: Highlight menu section for all sub-routes -->
<li class="@active_link('projects:*', 'bg-blue-700 font-bold')">
    <a href="@url('projects:index')">Projects</a>
</li>

<!-- PREMIUM: Toggling between Active and Inactive states (3 arguments) -->
<a href="@url('calendar')"
   class="nav-item @active_link('calendar', 'text-white bg-blue-600', 'text-gray-400 hover:text-white')">
    Calendar
</a>

<!-- Dynamic route name with wildcard -->
@let current_section = 'admin:*'
<a href="@url('admin:index')"
   class="@active_link(current_section, 'is-active')">
    Admin Console
</a>
```

#### Premium UI Example (Side Navigation)

This example leverages the 3-argument syntax to create a polished, state-aware navigation menu:

```html
<nav class="sidebar">
    <a href="@url('home')"
       class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 
              @active_link('home', 
                  'text-lime-400 font-bold border-r-2 border-lime-400 bg-lime-400/10', 
                  'text-gray-400 hover:text-purple-400 hover:bg-gray-800'
              )">
        <span class="material-symbols-outlined">dashboard</span>
        <span>Dashboard</span>
    </a>

    <a href="@url('teams:index')"
       class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 
              @active_link('teams:*', 
                  'text-lime-400 font-bold border-r-2 border-lime-400 bg-lime-400/10', 
                  'text-gray-400 hover:text-purple-400 hover:bg-gray-800'
              )">
        <span class="material-symbols-outlined">groups</span>
        <span>Teams</span>
    </a>
</nav>
```

#### Wildcard Matching Examples

```html
<!-- Current URL: /admin/users/list -->

<!-- ✓ Matches -->
<a href="..." class="@active_link('admin:*', 'active')">Admin</a>

<!-- ✓ Matches -->
<a href="..." class="@active_link('admin:users', 'active')">Users</a>

<!-- ✗ Doesn't match -->
<a href="..." class="@active_link('admin:settings', 'active')">Settings</a>

<!-- ✗ Doesn't match -->
<a href="..." class="@active_link('posts:*', 'active')">Posts</a>
```

---

## Form Directives

### @csrf - CSRF Protection

```html
<form method="POST" action="@url('posts:store')">
    @csrf
    <input type="text" name="title">
    <button type="submit">Create</button>
</form>
```

<!-- Renders as: -->

```html
<!-- <input type="hidden" name="_token" value="..."> -->
```

### @csrf_token - Raw CSRF Token

Outputs the raw CSRF token string — useful for JavaScript `fetch()` calls or AJAX headers.

```html
<!-- In a <meta> tag for JS access -->
<meta name="csrf-token" content="@csrf_token">

<!-- In JavaScript -->
<script>
    const token = document.querySelector('meta[name="csrf-token"]').content;
    fetch('/api/data', {
        method: 'POST',
        headers: { 'X-CSRF-Token': token }
    });
</script>
```

### @checked - Conditional Checked

```html
<!-- Checkbox -->
<input type="checkbox" name="agree" @checked(user.has_accepted_terms)>
I agree to the terms

<!-- Radio button -->
<input type="radio" name="status" value="active" @checked(user.status == 'active')>
Active

<!-- Based on model attribute -->
<input type="checkbox" name="newsletter" @checked(preferences.subscribe_newsletter)>
Subscribe to newsletter
```

### @selected - Conditional Selected

```html
<select name="country">
    <option @selected(user.country == 'US')>United States</option>
    <option @selected(user.country == 'CA')>Canada</option>
    <option @selected(user.country == 'MX')>Mexico</option>
</select>

<!-- Dynamic options -->
<select name="category">
    @for (category in categories) {
        <option value="{{ category.id }}" 
                @selected(selected_id == category.id)>
            {{ category.name }}
        </option>
    }
</select>
```

### @disabled - Conditional Disabled

```html
<!-- Disable button while loading -->
<button @disabled(form.is_submitting)>
    @if (form.is_submitting) { Processing... } @else { Save }
</button>

<!-- Disable based on permission -->
<input type="text" name="username" @disabled(!user.can_edit_username)>

<!-- Disable unavailable options -->
<button @disabled(stock.quantity == 0)>
    @if (stock.quantity == 0) { Out of Stock } @else { Add to Cart }
</button>
```

### @readonly - Conditional Read-Only

```html
<!-- Read-only after published -->
<textarea name="content" @readonly(post.is_published)>
    {{ post.content }}
</textarea>

<!-- Read-only for non-editors -->
<input type="email" name="email" @readonly(!user.can_edit_email)>

<!-- Disable editing for archived items -->
<input type="text" value="{{ item.name }}" @readonly(item.is_archived)>
```

---

## Template Inheritance

### @extends - Inherit Layout

```html
<!-- child.html -->
@extends("layouts/base")

@section("title") { Home Page }

@section("content") {
    <h1>Welcome</h1>
    <p>This content goes in the main area.</p>
}
```

### @section/@block - Define Block

```html
<!-- layouts/base.html -->
@section("title") { Default Title }

<!-- Can be overridden in child -->

<!-- Or use @block (alias) -->
@block("content") {
    <p>Default content</p>
}
```

### @yield - Render Block

```html
<!-- layouts/base.html -->
<title>@yield("title") - My App</title>

<main>
    @yield("content")
</main>

<!-- Child template fills in the blanks -->
```

### @push/@pop - Append to Block

```html
<!-- layouts/base.html -->
@yield("scripts")

<!-- child.html -->
@push("scripts") {
    <script>
        console.log('Page-specific script');
    </script>
}
```

### @include - Include Partial

```html
<!-- Include a component/partial -->
@include("components/header")

<!-- With variables -->
@include("components/card", title="My Card", content=item.description)

<!-- In a loop -->
@for (post in posts) {
    @include("components/post-card", post=post)
}
```

### @includeWhen - Conditional Include

Include a partial template only when a condition is true.

```html
<!-- Only include sidebar if user has permission -->
@includeWhen(user.is_premium, "partials/premium-badge")

<!-- Include admin tools only for admins -->
@includeWhen(request.user.is_superuser, "partials/admin-toolbar")
```

### @includeUnless - Inverted Conditional Include

Include a partial template only when a condition is false.

```html
<!-- Include maintenance banner unless system is healthy -->
@includeUnless(system.is_healthy, "partials/maintenance-banner")

<!-- Show onboarding unless user has completed setup -->
@includeUnless(user.onboarding_complete, "partials/onboarding-wizard")
```

---

## Data Helpers

### @let - Variable Assignment

```html
<!-- Simple assignment -->
@let total = items | sum('price')
<p>Total: ${{ total }}</p>

<!-- Complex expression -->
@let is_premium = user.subscription.tier == 'premium' && user.subscription.active
@if (is_premium) { <span>Premium Member</span> }

<!-- Nested data -->
@let admin_email = request.user.organization.admin.email
<p>Contact: {{ admin_email }}</p>

<!-- Multiple assignments -->
@let price = product.price
@let discount = product.discount_percent
@let final = price * (1 - discount/100)
<p>${{ final }}</p>
```

### @old - Form Re-fill

```html
<!-- Repopulate form after validation error -->
<input type="text" name="email" value="@old('email', user.email)">
<textarea name="message">@old('message')</textarea>

<!-- With default -->
<input type="text" name="username" value="@old('username', 'Guest')">
```

### @json - JSON Encoding

```html
<!-- Pass data to JavaScript -->
<script>
    const data = @json(items);
    console.log(data);
</script>

<!-- Encode complex data -->
{{ form_metadata | @json }}
```

### @dump - Debug Output

```html
<!-- Pretty-print debugging -->
@dump(user)
@dump(request.headers)
@dump(form.errors)

<!-- Styles beautifully as JSON with monospace font and dark bg -->
```

### @span - Safe Interpolation

The `@span` directive is a shorthand for `{{ }}` wrap, providing clean inline interpolation. It includes a built-in **Null-Coalescing Shorthand** using the `??` operator.

```html
<!-- Direct output -->
<p>Hello, @span(user.name)!</p>

<!-- Null-Coalescing Shorthand (??) -->
<!-- Renders 'Guest' if user.display_name is None/Null -->
<p>Welcome, @span(user.display_name ?? 'Guest')</p>

<!-- Complex fallback logic -->
<div class="status">
    @span(user.bio ?? 'No bio provided for this user.')
</div>

<!-- With design system filters -->
<h1 class="{{ 'bold' | eden_text }}">
    @span(post.title | title_case ?? 'Untitled Post')
</h1>
```

> [!NOTE]
> The `??` operator inside `@span` is automatically transformed into Jinja2's `| default` filter during pre-processing, ensuring high performance while maintaining a clean developer experience.

---

## Asset Helpers

### @css - CSS Link

```html
<!-- Add CSS stylesheet -->
<head>
    @css("style.css")
    @css("theme.css")
    @css("admin.css")
</head>

<!-- Renders as: -->
<!-- <link rel="stylesheet" href="{{ url_for('static', path='style.css') }}"> -->
```

### @js - JavaScript Link

```html
<!-- Add JS script -->
<body>
    ...
    @js("app.js")
    @js("admin.js")
</body>

<!-- Renders as: -->
<!-- <script src="{{ url_for('static', path='app.js') }}"></script> -->
```

### @vite - Vite Assets

```html
<!-- For Vite bundler -->
<head>
    @vite(["resources/css/app.css", "resources/js/app.js"])
</head>

<!-- Multiple entry points -->
@vite([
    "resources/css/admin.css",
    "resources/js/admin.js",
    "resources/css/print.css"
])
```

---

## Component Directives

### @component - Render Component

```html
<!-- Simple component -->
@component("card") {
    <p>Card content</p>
}

<!-- With props -->
@component("button", label="Click me", variant="primary", size="lg") {
    Icon inside
}

<!-- Nested components -->
@component("layout", title="Dashboard") {
    @component("sidebar") {
        <nav>...</nav>
    }
    @component("content") {
        <main>...</main>
    }
}
```

### @slot - Named Component Slots

```html
<!-- components/modal.html -->
<div class="modal">
    <div class="modal-header">
        @slot("header") {
            <h2>Default Title</h2>
        }
    </div>
    <div class="modal-body">
        @slot("body") {
            Body content goes here
        }
    </div>
    <div class="modal-footer">
        @slot("footer") {
            <button>Close</button>
        }
    </div>
</div>

<!-- Usage -->
@component("modal") {
    @slot("header") { User Profile }
    @slot("body") { 
        <form>...</form>
    }
    @slot("footer") {
        <button>Save</button>
        <button>Cancel</button>
    }
}
```

---

## Message Directives

### @error - Form Errors

```html
<!-- Display field errors -->
@error('email') {
    <span class="error">{{ message }}</span>
}

<!-- With styling -->
<div>
    <input type="email" name="email">
    @error('email') {
        <div class="text-red-500 text-sm mt-1">
            <i class="icon-warning"></i> {{ message }}
        </div>
    }
</div>

<!-- Multiple errors -->
@for (error in form.errors.email) {
    <div class="alert alert-danger">{{ error }}</div>
}
```

### @messages - Flash Messages

```html
<!-- Display flash messages -->
<div class="alerts">
    @messages {
        <div class="alert alert-{{ message.category }}">
            {{ message.text }}
            @if (message.dismissible) {
                <button type="button" class="close" data-dismiss="alert">×</button>
            }
        </div>
    }
</div>

<!-- In your handler -->
# Python
request.messages.success("Profile updated!")
request.messages.error("Something went wrong")
request.messages.info("Please read this")
```

---

## Special Directives

### @method - HTTP Method Spoofing

```html
<!-- Spoof PUT/DELETE in forms -->
<form method="POST">
    @method('PUT')
    @csrf
    <input type="text" name="name">
    <button>Update</button>
</form>

<!-- For delete confirmation -->
<form method="POST" action="@url('posts:destroy', id=post.id)">
    @method('DELETE')
    @csrf
    <button type="submit" class="btn btn-danger">
        Permanently Delete
    </button>
</form>
```

---

## Real-World Examples

### Navigation with Active Links

```html
<nav class="navbar">
    <a href="@url('home')" class="@active_link('home', 'active')">
        Home
    </a>
    
    <div class="nav-section @active_link('blog:*', 'expanded')">
        <a href="@url('blog:index')" class="@active_link('blog:*', 'section-active')">
            Blog
        </a>
        <ul class="submenu">
            <li>
                <a href="@url('blog:categories')" class="@active_link('blog:categories', 'active')">
                    Categories
                </a>
            </li>
            <li>
                <a href="@url('blog:archives')" class="@active_link('blog:archives', 'active')">
                    Archives
                </a>
            </li>
        </ul>
    </div>
    
    @auth {
        <div class="nav-section">
            <a href="@url('dashboard')" class="@active_link('dashboard', 'active')">
                Dashboard
            </a>
        </div>
    }
    
    @guest {
        <a href="@url('auth:login')" class="btn-login">
            Login
        </a>
    }
</nav>
```

### User List with Actions

```html
<div class="users-table">
    @if (users) {
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                @for (user in users) {
                    <tr class="@even { bg-gray-50 } @odd { bg-white } @first { border-t-2 }">
                        <td>{{ user.name }}</td>
                        <td>{{ user.email }}</td>
                        <td>
                            @if (user.is_active) {
                                <span class="badge badge-green">Active</span>
                            } @else {
                                <span class="badge badge-gray">Inactive</span>
                            }
                        </td>
                        <td>
                            <a href="@url('users:show', id=user.id)" class="btn btn-sm">View</a>
                            @auth {
                                @if (request.user.can_edit) {
                                    <a href="@url('users:edit', id=user.id)" class="btn btn-sm btn-blue">Edit</a>
                                }
                            }
                        </td>
                    </tr>
                }
            </tbody>
        </table>
    } @empty {
        <div class="empty-state">
            <p>No users found.</p>
        </div>
    }
</div>
```

### Dynamic Form

```html
<form method="POST" action="@url('posts:update', id=post.id)">
    @method('PUT')
    @csrf
    
    <div class="form-group">
        <label for="title">Title</label>
        <input type="text" id="title" name="title" value="@old('title', post.title)" required>
        @error('title') {
            <span class="error">{{ message }}</span>
        }
    </div>
    
    <div class="form-group">
        <label for="content">Content</label>
        <textarea id="content" name="content" @readonly(post.is_published)>
            @old('content', post.content)
        </textarea>
        @if (post.is_published) {
            <small>This post is published and cannot be edited.</small>
        }
    </div>
    
    <div class="form-group">
        <label for="category">Category</label>
        <select id="category" name="category_id" @disabled(!user.can_change_category)>
            @for (cat in categories) {
                <option value="{{ cat.id }}" @selected(cat.id == post.category.id)>
                    {{ cat.name }}
                </option>
            }
        </select>
    </div>
    
    <div class="form-group">
        <label>
            <input type="checkbox" name="featured" @checked(post.is_featured)>
            Feature this post
        </label>
    </div>
    
    <button type="submit" @disabled(form.is_submitting)>
        @if (form.is_submitting) { Saving... } @else { Save Changes }
    </button>
</form>
```

---

---

## Premium Design Integration

Eden templates are designed to work seamlessly with our core design system tokens.

### Typography & Colors

```html
<h1 class="{{ 'bold' | eden_text }} {{ 'primary' | eden_text_color }}">
    @span(title)
</h1>
<div class="{{ 'glass' | eden_surface }} {{ 'xl' | eden_shadow }} p-6">
    @yield("content")
</div>
```

### Micro-Animations

```html
@for(item in gallery) {
    <div class="transition-all duration-300 transform hover:scale-[1.02]">
        @include("partials/image-card", item=item)
    </div>
}
```

---

### Unimplemented & Experimental

> [!WARNING]
> The following directives are present in Eden's roadmap but are **not yet implemented** in the current engine. Using them will currently result in a parsing error or no output.

| Directive | Description | Planned Use Case |
| :--- | :--- | :--- |
| **@inject** | Service injection | `@inject('metrics', 'App\Services\Metrics')` |
| **@php** | Raw PHP block | (Legacy support, use `@let` for logic) |

---

## Troubleshooting

> [!NOTE]
> Most template issues stem from incorrect indentation or unclosed brace blocks.

### Issue: `@active_link` not highlighting

- [ ] Check route name matches exactly in the controller.
- [ ] Verify the route is registered with a `name` parameter in `routes.py`.
- [ ] Ensure the Request object is passed correctly (happens automatically with `render`).

### Issue: `@checked` or `@selected` not appearing

- [ ] Ensure the expression inside parentheses returns a strictly `True` or `False` value.
- [ ] Check if another directive is conflicting with the attribute output.

### Issue: `$loop` variable is undefined

- [ ] Verify you are referencing `$loop` strictly inside a `@for` or `@foreach` block.
- [ ] Check for typos (it must be `$loop`, not `loop`).

---

> [!TIP]
> Use `@dump(variable)` to inspect data shapes directly in your browser during development.

### Happy templating with Eden! 🚀
