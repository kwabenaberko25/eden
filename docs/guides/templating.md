# Eden Templating Engine Documentation 🎨

> **Modern, Powerful, Express-Inspired Syntax for Web Templates**

Eden's templating engine is a modern templating system designed to make templates readable, maintainable, and powerful. It replaces verbose Jinja2 tags with a clean, brace-based `@directive` syntax inspired by JavaScript frameworks. It is fully line-preserving and optimized for developer experience.

**Quick Facts:**
- **40+ Directives** covering control flow, forms, routing, authentication, and components
- **38+ Filters** for string manipulation, formatting, arrays, and i18n
- **Full HTML Integration** with server-side components and HTMX support
- **Express-Inspired** syntax that feels familiar to JavaScript developers
- **Type-Safe URLs** with the `@url()` directive—never hardcode routes again
- **Automatic CSRF Protection** with the `@csrf` directive

## Table of Contents

1. [Rendering Templates in Routes](#rendering-templates-in-routes)
2. [Syntax Basics](#syntax-basics)
3. [Control Flow Directives](#control-flow-directives)
4. [All Filters Reference](#all-filters-reference)
5. [Form Directives](#form-directives)
6. [Authentication & Authorization](#authentication--authorization)
7. [Routing & Navigation](#routing--navigation)
8. [Template Inheritance & Layout](#template-inheritance--layout)
9. [Components & Fragments](#components--fragments)
10. [Loop Helpers](#loop-helpers)
11. [Advanced Features](#advanced-features)
12. [Best Practices & Patterns](#best-practices--patterns)

---

## Rendering Templates in Routes

### Using `request.render()` (Recommended)

Every Eden `Request` object has a built-in `.render()` method. This is the idiomatic way to render templates in your route handlers.

```python
@app.get("/dashboard")
async def dashboard(request):
    """Render dashboard template with context."""
    user = await User.get(id=request.user.id)
    posts = await Post.filter(user_id=user.id).all()
    
    return request.render(
        "dashboard.html",
        user=user,
        posts=posts,
        title="My Dashboard"
    )
```

**Template file** (`templates/dashboard.html`):
```html
@extends("layouts/base")

@section("title") { {{ title }} }

@section("content") {
    <h1>Welcome, {{ user.name }}!</h1>
    <p>You have {{ posts | length }} posts.</p>
    
    @for (post in posts) {
        <article>
            <h2>{{ post.title }}</h2>
            <p>{{ post.content | truncate(150) }}</p>
        </article>
    }
}
```

### Using `app.render()` (Global Access)

For convenience in non-request contexts, use the app-level render method:

```python
from eden import Eden

app = Eden(title="My App")

@app.get("/home")
async def home():
    """Using app.render() when you don't have request context."""
    return app.render("home.html", title="Welcome Home")
```

### Using `render_template()` Helper (Context-Aware)

For the cleanest syntax, import and use the `render_template` helper. It automatically discovers the current request context using Python context variables:

```python
from eden import render_template

@app.get("/")
async def home():
    """render_template automatically uses request context."""
    return render_template("home.html", title="Welcome Home")

@app.post("/submit")
async def submit_form(request):
    # Still works in async context
    return render_template("confirmation.html", message="Success!")
```

**Advantages of `render_template()`:**
- No need to explicitly pass `request` 
- Automatic context detection
- Cleaner, more expressive code
- Works in async contexts

### Passing Context Data

All rendering methods accept context variables as keyword arguments or a dictionary:

```python
# Method 1: Keyword arguments
return request.render("template.html", user=user, posts=posts)

# Method 2: Dictionary
context = {"user": user, "posts": posts, "theme": "dark"}
return request.render("template.html", context)

# Method 3: Mixed approach
return request.render(
    "template.html",
    {"user": user},
    posts=posts
)
```

### Fragment Rendering (HTMX Support)

Render only a specific part of a template without the layout:

```python
@app.get("/users/list")
async def list_users_fragment(request):
    users = await User.all()
    
    # Renders ONLY the fragment="users-table", not the entire layout
    return request.render(
        "users.html",
        users=users,
        fragment="users-table"
    )
```

**Template file:**
```html
@extends("layouts/base")

@fragment("users-table") {
    <table>
        <thead>
            <tr><th>Name</th><th>Email</th></tr>
        </thead>
        <tbody>
            @for (user in users) {
                <tr>
                    <td>{{ user.name }}</td>
                    <td>{{ user.email }}</td>
                </tr>
            }
        </tbody>
    </table>
}
```

---

## Syntax Basics

### The `@` Syntax

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
| | `@checked(cond)` | `cond`: Boolean | Sets `checked` attr if true. |
| | `@selected(cond)` | `cond`: Boolean | Sets `selected` attr if true. |
| | `@disabled(cond)` | `cond`: Boolean | Sets `disabled` attr if true. |
| | `@readonly(cond)` | `cond`: Boolean | Sets `readonly` attr if true. |
| **Logic** | `@let var = val` | `var`, `val` | Inline variable assignment. |
| | `@url(name)` | `name`, `**kwargs` | Generates a URL. Supports `component:` prefix. |
| | `@active_link(name, cls)` | `name`, `cls` | Emits `cls` if route is active (supports wildcards). |
| **Loop Helpers** | `@even` | None | Content for even loop rows. |
| | `@odd` | None | Content for odd loop rows. |
| | `@first` | None | Content for the first loop row. |
| | `@last` | None | Content for the last loop row. |

---

## All Filters Reference 🎯

Eden provides 38+ built-in filters for formatting, transforming, and displaying data in templates. Filters are applied using the pipe operator `|`.

### String Filters

#### Case Conversion Filters

```html
<!-- Uppercase -->
{{ "hello world" | upper }}
<!-- Output: HELLO WORLD -->

<!-- Lowercase -->
{{ "HELLO WORLD" | lower }}
<!-- Output: hello world -->

<!-- Title Case (capitalize each word) -->
{{ "hello world" | title }}
<!-- Output: Hello World -->

<!-- Capitalize (only first letter) -->
{{ "hello" | capitalize }}
<!-- Output: Hello -->
```

#### String Manipulation Filters

```html
<!-- Reverse string -->
{{ "eden" | reverse }}
<!-- Output: nede -->

<!-- Trim whitespace -->
{{ "  hello world  " | trim }}
<!-- Output: hello world -->

<!-- Trim left (leading whitespace) -->
{{ "  hello" | ltrim }}
<!-- Output: hello -->

<!-- Trim right (trailing whitespace) -->
{{ "hello  " | rtrim }}
<!-- Output: hello -->

<!-- Replace text -->
{{ "hello world" | replace("world", "Eden") }}
<!-- Output: hello Eden -->

<!-- Slice (substring) -->
{{ "hello world" | slice(0, 5) }}
<!-- Output: hello -->
<!-- With negative indices -->
{{ "hello world" | slice(-5) }}
<!-- Output: world -->

<!-- Get string length -->
{{ "hello" | length }}
<!-- Output: 5 -->

<!-- Truncate with ellipsis -->
{{ "This is a very long text" | truncate(15) }}
<!-- Output: This is a very... -->
<!-- Custom suffix -->
{{ "This is a very long text" | truncate(15, "…") }}
<!-- Output: This is a very… -->

<!-- Convert to URL-safe slug -->
{{ "Hello World! 🌍" | slug }}
<!-- Output: hello-world-%f0%9f%8c%8d -->

<!-- Repeat string -->
{{ "ab" | repeat(3) }}
<!-- Output: ababab -->
```

### Numeric Filters

```html
<!-- Absolute value -->
{{ -42 | abs }}
<!-- Output: 42 -->

<!-- Round to decimal places -->
{{ 3.14159 | round }}
<!-- Output: 3 -->
{{ 3.14159 | round(2) }}
<!-- Output: 3.14 -->

<!-- Ceiling (round up) -->
{{ 3.2 | ceil }}
<!-- Output: 4 -->

<!-- Floor (round down) -->
{{ 3.7 | floor }}
<!-- Output: 3 -->
```

### Array & Collection Filters

```html
<!-- Get first element -->
{{ items | first }}
<!-- Works with: lists, tuples, strings -->

<!-- Get first with default -->
{{ empty_list | first("No items") }}

<!-- Get last element -->
{{ items | last }}

<!-- Get unique elements (removes duplicates) -->
{{ [1, 2, 2, 3, 3, 3] | unique }}
<!-- Output: [1, 2, 3] -->

<!-- Sort array -->
{{ numbers | sort }}
<!-- Output: sorted in ascending order -->

<!-- Reverse array -->
{{ items | reverse_array }}

<!-- Number of items -->
{{ items | length }}
```

### Format Filters

**Currency:**
```html
<!-- Default USD -->
{{ 99.99 | currency }}
<!-- Output: $99.99 -->

<!-- British pounds -->
{{ 50 | currency("GBP") }}
<!-- Output: £50.00 -->

<!-- Euro -->
{{ 75.5 | currency("EUR") }}
<!-- Output: €75.50 -->

<!-- Ghanaian cedis -->
{{ 100 | currency("GHS") }}
<!-- Output: ₵100.00 -->

<!-- Supported currencies: USD, EUR, GBP, GHS, JPY, CNY -->
```

**Phone Numbers:**
```html
<!-- US phone format -->
{{ "2025551234" | phone }}
<!-- Output: (202) 555-1234 -->

<!-- Ghana phone format -->
{{ "0912345678" | phone("GH") }}
<!-- Output: +233 0 912 345678 -->
```

**Date & Time:**
```html
<!-- Format date -->
{{ user.created_at | date }}
<!-- Output: 2024-03-13 (default format) -->

<!-- Custom date format -->
{{ user.created_at | date("%B %d, %Y") }}
<!-- Output: March 13, 2024 -->

<!-- Time format -->
{{ event.start_time | time }}
<!-- Output: 14:30:00 -->

<!-- Custom time format -->
{{ event.start_time | time("%I:%M %p") }}
<!-- Output: 02:30 PM -->
```

### Data Type & JSON Filters

```html
<!-- Convert to JSON (safe for JavaScript) -->
<script>
  const userData = @json(user);
  console.log(userData);
</script>

<!-- Direct JSON output -->
{{ data | json }}
<!-- Output: {"key": "value", ...} -->
```

### Filter Chaining

Filters can be chained together for powerful transformations:

```html
<!-- Chain 1: Clean and format text -->
{{ user.email | lower | slice(0, 5) | upper }}

<!-- Chain 2: Format numbers -->
{{ price * quantity | round(2) | currency }}

<!-- Chain 3: Advanced data manipulation -->
{{ products 
   | sort 
   | unique 
   | reverse_array 
   | json }}
```

### Creating Custom Filters

While Eden comes with many built-in filters, you can register custom filters:

```python
from eden import Eden

app = Eden()

# Simple custom filter
def pluralize(count, word):
    return f"{count} {word}{'s' if count != 1 else ''}"

app.templates.filters.register('pluralize', pluralize)
```

Usage in templates:

```html
<!-- You have 5 items -->
You have {{ count | pluralize("item") }}
```

---

## Control Flow Directives (Detailed) 🎯

Now let's look more deeply at each control flow directive with comprehensive examples.

### @if - Conditional Rendering

```html
<!-- Simple if -->
@if (user.is_verified) {
    <div class="badge badge-green">✓ Verified</div>
}

<!-- If-else -->
@if (user.is_admin) {
    <span>Administrator</span>
} @else {
    <span>Regular User</span>
}

<!-- If-else if-else chain -->
@if (status == "active") {
    <span class="badge badge-green">Active</span>
} @else if (status == "pending") {
    <span class="badge badge-yellow">Pending</span>
} @else if (status == "suspended") {
    <span class="badge badge-red">Suspended</span>
} @else {
    <span class="badge badge-gray">Unknown</span>
}

<!-- Nested conditions -->
@if (user) {
    @if (user.profile) {
        <p>{{ user.profile.bio }}</p>
    }
}

<!-- Complex boolean expressions -->
@if (user.age >= 18 && user.is_verified && !user.is_banned) {
    <form action="/adult-content">
        <!-- content -->
    </form>
}

<!-- Negation -->
@if (!user.is_banned) {
    <button>Post comment</button>
}

<!-- Checking for existence/null -->
@if (user.phone) {
    <p>Phone: {{ user.phone }}</p>
}
```

### @unless - Inverted Conditional

`@unless` is equivalent to `@if (!condition)`. Use it when you want to emphasize the negation:

```html
<!-- If NOT verified -->
@unless (user.is_verified) {
    <div class="warning">
        Please verify your account before posting.
    </div>
}

<!-- Equivalent to: -->
@if (!user.is_verified) {
    <div class="warning">
        Please verify your account before posting.
    </div>
}

<!-- Multiple negations -->
@unless (user.is_banned || user.is_suspended) {
    <button class="primary">Post</button>
}
```

### @for / @foreach - Looping

```html
<!-- Basic loop -->
@for (item in items) {
    <li>{{ item }}</li>
}

<!-- Loop with index access -->
@for (index, item in items) {
    <tr>
        <td>{{ index + 1 }}</td>
        <td>{{ item.name }}</td>
    </tr>
}

<!-- Loop over dictionary keys and values -->
@for (key, value in user.metadata) {
    <dt>{{ key }}</dt>
    <dd>{{ value }}</dd>
}

<!-- Alternative syntax (@foreach) -->
@foreach (product in products) {
    <div class="product-card">
        {{ product.name }} - ${{ product.price }}
    </div>
}

<!-- Nested loops -->
@for (category in categories) {
    <h3>{{ category.name }}</h3>
    <ul>
        @for (product in category.products) {
            <li>{{ product.name }}</li>
        }
    </ul>
}

<!-- Loop with fallback for empty lists -->
@for (comment in post.comments) {
    <div class="comment">{{ comment.text }}</div>
} @empty {
    <p>No comments yet. Be the first!</p>
}
```

### Loop Metadata: The `$loop` Variable

Inside any `@for` loop, you have access to a special `$loop` object with useful metadata:

```html
@for (item in items) {
    <div class="item {{ $loop.even ? 'bg-gray-100' : 'bg-white' }}">
        <!-- Basic counters -->
        <span class="badge">{{ $loop.index }}</span>
        <!-- 1-based index -->
        
        <strong>{{ item.name }}</strong>
        
        <!-- Conditions -->
        @if ($loop.first) {
            <span class="label-new">First Item</span>
        }
        
        @if ($loop.last) {
            <span class="label-last">Last Item</span>
        }
        
        <!-- Display total -->
        <small>({{ $loop.iteration }} of {{ $loop.length }})</small>
    </div>
}
```

**Complete `$loop` API:**

| Property | Description | Example |
| :--- | :--- | :--- |
| `$loop.index` | 1-based iteration number | 1st iteration = 1 |
| `$loop.index0` | 0-based iteration number | 1st iteration = 0 |
| `$loop.revindex` | Distance from end (1-based) | Last item = 1 |
| `$loop.revindex0` | Distance from end (0-based) | Last item = 0 |
| `$loop.first` | Is this the first iteration? | Boolean |
| `$loop.last` | Is this the last iteration? | Boolean |
| `$loop.even` | Is iteration number even? | Boolean |
| `$loop.odd` | Is iteration number odd? | Boolean |
| `$loop.length` | Total items in sequence | Integer |
| `$loop.iteration` | Same as `index` | Alias |

### @switch / @case - Multi-branch Logic

```html
<!-- Basic switch -->
@switch (user.role) {
    @case ('admin') {
        <span class="role-admin">Administrator</span>
    }
    @case ('editor') {
        <span class="role-editor">Editor</span>
    }
    @case ('viewer') {
        <span class="role-viewer">Viewer</span>
    }
}

<!-- Switch with fallback (@else/@default) -->
@switch (status) {
    @case ('pending') {
        <span class="badge badge-yellow">Pending</span>
    }
    @case ('approved') {
        <span class="badge badge-green">Approved</span>
    }
    @else {
        <span class="badge badge-gray">Unknown</span>
    }
}

<!-- Switch with multiple matching cases -->
@switch (http_code) {
    @case (200) { <span class="success">OK</span> }
    @case (201) { <span class="success">Created</span> }
    @case (204) { <span class="success">No Content</span> }
    @case (400) { <span class="error">Bad Request</span> }
    @case (404) { <span class="error">Not Found</span> }
    @else { <span class="unknown">Unknown Code</span> }
}
```

### Loop Helpers: @even, @odd, @first, @last

These directives work inside `@for` loops to render content conditionally:

```html
<!-- Striped table with @even / @odd -->
@for (row in table_data) {
    <tr class="@even { bg-gray-100 } @odd { bg-white }">
        <td>{{ row.name }}</td>
        <td>{{ row.value }}</td>
    </tr>
}

<!-- Add class to first row -->
@for (item in items) {
    <div class="@first { font-bold border-b-2 }">
        {{ item.name }}
    </div>
}

<!-- Add separator after last row -->
@for (product in products) {
    <p>{{ product.name }}: ${{ product.price }}</p>
    @last { <hr class="my-4"> }
}

<!-- Combine multiple helpers -->
@for (score in scores) {
    <div class="@first { text-lg font-bold } @last { mb-4 }">
        {{ score }}
    </div>
}
```

---

## Form Directives 📋

### @csrf - CSRF Protection

Automatically emit a hidden CSRF token input for all forms:

```html
<form method="POST" action="/submit">
    @csrf
    <!-- Renders: <input type="hidden" name="_token" value="..."> -->
    
    <input type="email" name="email" required>
    <button type="submit">Submit</button>
</form>
```

**Note:** CSRF protection is middleware-configured and automatic for POST/PUT/PATCH/DELETE requests.

### @checked - Checkbox & Radio Button States

Apply the `checked` attribute conditionally:

```html
<!-- Simple checkbox -->
<label>
    <input type="checkbox" name="subscribe" @checked(user.subscribe_newsletter)>
    Subscribe to newsletter
</label>

<!-- Multiple checkboxes (select multiple values) -->
@for (tag in available_tags) {
    <label>
        <input 
            type="checkbox" 
            name="tags" 
            value="{{ tag.id }}"
            @checked(tag.id in user.tag_ids)
        >
        {{ tag.name }}
    </label>
}

<!-- Radio buttons -->
@for (option in payment_options) {
    <label>
        <input 
            type="radio" 
            name="payment_method" 
            value="{{ option.id }}"
            @checked(user.preferred_payment_id == option.id)
        >
        {{ option.label }}
    </label>
}

<!-- Toggling based on condition -->
<label>
    <input 
        type="checkbox" 
        name="agree_to_terms"
        @checked(!user.has_agreed_once)
    >
    I agree to the terms
</label>
```

### @selected - Select Option States

Set the `selected` attribute on `<option>` elements:

```html
<!-- Simple select -->
<select name="role">
    <option @selected(user.role == 'admin')>Administrator</option>
    <option @selected(user.role == 'user')>User</option>
    <option @selected(user.role == 'guest')>Guest</option>
</select>

<!-- Loop-based select (dynamic options) -->
<select name="category">
    <option value="">Select a category...</option>
    @for (cat in categories) {
        <option 
            value="{{ cat.id }}"
            @selected(selected_category_id == cat.id)
        >
            {{ cat.name }}
        </option>
    }
</select>

<!-- Multi-select -->
<select name="permissions" multiple>
    @for (perm in all_permissions) {
        <option 
            value="{{ perm.id }}"
            @selected(perm.id in user.permission_ids)
        >
            {{ perm.name }}
        </option>
    }
</select>
```

### @disabled - Disable Form Elements

Disable inputs, buttons, and selects conditionally:

```html
<!-- Disable during submission -->
<button type="submit" @disabled(form.is_submitting)>
    @if (form.is_submitting) { Processing... } @else { Submit }
</button>

<!-- Conditional field disabling -->
<input 
    type="text" 
    name="company" 
    @disabled(user.is_freelancer)
    placeholder="Company name (disabled for freelancers)"
>

<!-- Disable select based on other field -->
<div class="form-group">
    <label>Account Type</label>
    <select name="account_type">
        <option value="personal">Personal</option>
        <option value="business">Business</option>
    </select>
</div>

<div class="form-group">
    <label>Business License</label>
    <input 
        type="text"
        name="license"
        @disabled(account_type != 'business')
        placeholder="Required for business accounts"
    >
</div>

<!-- Disable readonly fields -->
<textarea 
    name="generated_id" 
    @disabled(true)
    placeholder="Auto-generated, cannot edit"
>{{ auto_id }}</textarea>
```

### @readonly - Make Fields Read-Only

Mark fields as read-only once data is submitted:

```html
<!-- Readonly after submission -->
<input 
    type="email"
    name="email"
    value="{{ user.email }}"
    @readonly(user.email_verified)
>

<!-- Showing that a field cannot be modified -->
<div class="form-group">
    <label>Account Number</label>
    <input 
        type="text"
        value="{{ account.number }}"
        @readonly(true)
        class="bg-gray-100 cursor-not-allowed"
    >
</div>

<!-- Conditional readonly based on business logic -->
<textarea 
    name="notes"
    @readonly(task.is_completed || !user.can_edit)
>{{ task.notes }}</textarea>
```

---

## Authentication & Authorization 🔐

### @auth - Authenticated Users Only

```html
<!-- Simple auth check -->
@auth {
    <p>Welcome, {{ request.user.name }}!</p>
    <a href="@url('logout')">Logout</a>
}

<!-- With fallback -->
@auth {
    <div class="user-menu">
        <img src="{{ request.user.avatar }}" class="avatar">
        <span>{{ request.user.name }}</span>
    </div>
} @else {
    <a href="@url('login')">Log In</a>
    <a href="@url('register')">Sign Up</a>
}
```

### @guest - Unauthenticated Users Only

```html
<!-- Only show to non-logged-in users -->
@guest {
    <div class="banner">
        <p>Create an account to unlock premium features!</p>
        <a href="@url('register')" class="btn btn-primary">Get Started</a>
    </div>
}

<!-- Restrict authenticated users from certain pages -->
@guest {
    <form method="POST" action="@url('login')">
        @csrf
        <input type="email" name="email" required>
        <input type="password" name="password" required>
        <button type="submit">Log In</button>
    </form>
} @else {
    <p>You are already logged in. <a href="@url('dashboard')">Go to dashboard</a></p>
}
```

### Role & Permission Checks

```html
<!-- Check user role -->
@if (request.user.role == 'admin') {
    <a href="@url('admin:dashboard')">Admin Panel</a>
}

<!-- Check permission -->
@if (request.user.can('delete_posts')) {
    <button class="btn-danger" onclick="deletePost()">Delete</button>
}

<!-- Check multiple permissions -->
@if (request.user.can_all(['edit_post', 'delete_comments'])) {
    <!-- Full moderation controls -->
}

<!-- Check user ownership -->
@if (post.author_id == request.user.id || request.user.is_admin) {
    <a href="@url('posts:edit', id=post.id)">Edit Post</a>
}

<!-- Complex auth logic -->
@if (request.user && request.user.subscription_active && !request.user.subscription_paused) {
    <button class="premium-action">Download Report</button>
}
```

---

## HTMX & Real-Time Features 💫

### @htmx / @non_htmx - Request Type Detection

```html
<!-- Only render for HTMX requests -->
@htmx {
    <!-- This content only sent for AJAX/HTMX updates -->
    @fragment("results") {
        @for (item in items) {
            <tr>
                <td>{{ item.name }}</td>
                <td>{{ item.value }}</td>
                <td>
                    <button hx-delete="@url('items:delete', id=item.id)">Delete</button>
                </td>
            </tr>
        }
    }
}

<!-- Full page for non-HTMX requests -->
@non_htmx {
    <h1>Search Results</h1>
    <table>
        <thead><tr><th>Name</th><th>Value</th><th>Action</th></tr></thead>
        <tbody>
            @htmx {
                @fragment("results") { ... }
            }
        </tbody>
    </table>
</div>
```

### @fragment - Define HTMX-Targetable Sections

```html
<!-- Define a fragment for HTMX to target -->
@fragment("comments-list") {
    @for (comment in post.comments) {
        <div class="comment" id="comment-{{ comment.id }}">
            <strong>{{ comment.author }}</strong>
            <p>{{ comment.text }}</p>
            <span class="text-sm text-gray-500">{{ comment.created_at | time }}</span>
        </div>
    } @empty {
        <p>No comments yet.</p>
    }
}

<!-- Another fragment -->
@fragment("comment-form") {
    <form hx-post="@url('comments:create')" hx-target="#comments-list" hx-swap="beforeend">
        @csrf
        <textarea name="text" required></textarea>
        <button type="submit">Post Comment</button>
    </form>
}
```

---

## Conditional Attribute Directives 📋

Conditionally apply HTML attributes to form elements with clean, readable syntax.

### Attribute Directives

#### `@checked(condition)`
Applies the `checked` attribute when condition is true (for checkboxes and radio buttons).

```html
<input type="checkbox" name="subscribe" @checked(user.subscribe_newsletter)>
<!-- Renders as: -->
<!-- <input type="checkbox" name="subscribe" {% if user.subscribe_newsletter %}checked{% endif %}> -->
```

#### `@selected(condition)`
Applies the `selected` attribute when condition is true (for select options).

```html
<select name="role">
    <option @selected(user.role == 'admin')>Administrator</option>
    <option @selected(user.role == 'user')>User</option>
    <option @selected(user.role == 'guest')>Guest</option>
</select>
```

#### `@disabled(condition)`
Applies the `disabled` attribute when condition is true (disables form elements).

```html
<button @disabled(form.is_submitting)>
    @if(form.is_submitting) { Processing... } @else { Submit }
</button>
```

#### `@readonly(condition)`
Applies the `readonly` attribute when condition is true (makes inputs read-only).

```html
<textarea name="notes" @readonly(post.is_published)>
    {{ post.notes }}
</textarea>
```

---

## URL Routing & Navigation 🔗

### @url() - Route to URL

Generate URLs for your routes without hardcoding paths.

```html
<!-- Simple route -->
<a href="@url('dashboard')">Dashboard</a>

<!-- Route with parameters -->
<a href="@url('students:show', id=student.id)">View Student</a>

<!-- Store in variable -->
@let dashboard_url = @url('dashboard')
<a href="{{ dashboard_url }}">Go Home</a>
```

**Route Name Format:**
- Simple routes: `'dashboard'`
- Namespaced routes: `'admin:users'` (becomes `admin_users` internally)
- Component routes: `'component:action-slug'` (uses special dispatcher)

### @active_link() - Highlight Active Navigation

Conditionally add CSS classes to active links in your navigation.

```html
<!-- Simple usage -->
<a href="@url('dashboard')" class="nav-link @active_link('dashboard', 'is-active')">
    Dashboard
</a>

<!-- With custom class names -->
<a href="@url('students:index')" 
   class="px-4 py-2 @active_link('students:index', 'bg-blue-600 text-white')">
    Students
</a>
```

#### Wildcard Matching (NEW!)

Match multiple routes with wildcard syntax:

```html
<!-- Highlights when on ANY admin page (admin:users, admin:settings, etc.) -->
<a href="@url('admin:index')" 
   class="@active_link('admin:*', 'font-bold text-white')">
    Admin Panel
</a>

<!-- Matches all student routes -->
<li class="@active_link('students:*', 'border-l-4 border-blue-500')">
    Students
</li>
```

**How Wildcards Work:**
- Pattern: `'namespace:*'`
- Matches any route starting with that namespace
- Does path-based prefix matching
- Falls back gracefully if base route not found

**Troubleshooting:**
If `@active_link` doesn't highlight:
1. Verify the route name matches exactly: `@url('dashboard')` ↔ `@active_link('dashboard', ...)`
2. Check that the route is registered in your routes file with a `name` parameter
3. Enable debug logging to see route resolution errors:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

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

### 🔗 Dynamic URLs (`@url`)

The `@url` directive is the most powerful way to handle link generation in Eden. It's refactor-safe and supports multiple patterns.

- **Named Routes**: `@url('route_name', param=val)`
- **Namespaced Routes**: `@url('ns:route_name')` 
- **Components**: `@url('component:action-slug')` — *New!*

```html
<!-- Regular Link -->
<a href="@url('users:profile', id=user.id)">Profile</a>

<!-- HTMX Component Call -->
<button hx-post="@url('component:like-post', id=post.id)">
  Like
</button>
```

### 🧩 Components (`@component`)

Render self-contained logic units directly in your templates.

```html
@component("user-card", user=user, theme="dark")
```

[Learn more about Server-Side Components](components.md)

### Reusable Components (Legacy/Pure-UI)

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

## 🎨 Real-World Templates: Admin Dashboard

Building admin interfaces is a core use case. Let's create a production-ready dashboard with tables, sorting, filtering, and pagination.

### Complete Product Admin Dashboard

**Template Structure**:
```html
<!-- templates/admin/products.html -->
@extends("layouts/admin")

@section("title") { Product Management }

@section("content") {
    <div class="p-6">
        <!-- Header with actions -->
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-3xl font-bold">Products</h1>
            <a href="@url('admin:products:create')" class="btn btn-primary">
                ➕ Add Product
            </a>
        </div>
        
        <!-- Search & FilterBar -->
        <form method="GET" class="mb-6 p-4 bg-gray-50 rounded-lg">
            <div class="grid grid-cols-3 gap-4">
                <!-- Search input -->
                <input 
                    type="text" 
                    name="search" 
                    placeholder="Search by name or SKU..."
                    value="@old('search', request.query_params.get('search', ''))"
                    class="px-4 py-2 border rounded"
                >
                
                <!-- Category filter -->
                <select name="category" class="px-4 py-2 border rounded">
                    <option value="">All Categories</option>
                    @for (cat in categories) {
                        <option value="{{ cat.id }}" 
                                @if(request.query_params.get('category') == cat.id|string) { selected })>
                            {{ cat.name }}
                        </option>
                    }
                </select>
                
                <!-- Status filter -->
                <select name="status" class="px-4 py-2 border rounded">
                    <option value="">All Status</option>
                    <option value="active" @if(request.query_params.get('status') == 'active') { selected }>Active</option>
                    <option value="inactive" @if(request.query_params.get('status') == 'inactive') { selected }>Inactive</option>
                </select>
            </div>
            
            <div class="mt-3 flex gap-2">
                <button type="submit" class="btn btn-sm btn-primary">🔍 Search</button>
                <a href="@url('admin:products')" class="btn btn-sm btn-secondary">Clear</a>
            </div>
        </form>
        
        <!-- Results info -->
        <div class="mb-4 text-sm text-gray-600">
            Showing {{ products.offset + 1 }} to {{ [products.offset + products.limit, products.total]|min }} 
            of {{ products.total }} products
        </div>
        
        <!-- Data table with sorting -->
        <div class="overflow-x-auto rounded-lg border border-gray-200">
            <table class="w-full text-sm">
                <thead class="bg-gray-100 border-b">
                    <tr>
                        <th class="px-6 py-3 text-left font-semibold">
                            <a href="@url('admin:products', sort='name', dir=request.query_params.get('dir') == 'asc' ? 'desc' : 'asc')">
                                Name @if(request.query_params.get('sort') == 'name') { 
                                    {{ request.query_params.get('dir') == 'asc' ? '▲' : '▼' }} 
                                }
                            </a>
                        </th>
                        <th class="px-6 py-3 text-left font-semibold">
                            <a href="@url('admin:products', sort='sku')">
                                SKU @if(request.query_params.get('sort') == 'sku') { 
                                    {{ request.query_params.get('dir') == 'asc' ? '▲' : '▼' }} 
                                }
                            </a>
                        </th>
                        <th class="px-6 py-3 text-right font-semibold">
                            <a href="@url('admin:products', sort='price')">
                                Price @if(request.query_params.get('sort') == 'price') { 
                                    {{ request.query_params.get('dir') == 'asc' ? '▲' : '▼' }} 
                                }
                            </a>
                        </th>
                        <th class="px-6 py-3 text-right font-semibold">
                            <a href="@url('admin:products', sort='stock')">
                                Stock @if(request.query_params.get('sort') == 'stock') { 
                                    {{ request.query_params.get('dir') == 'asc' ? '▲' : '▼' }} 
                                }
                            </a>
                        </th>
                        <th class="px-6 py-3 text-center font-semibold">Status</th>
                        <th class="px-6 py-3 text-center font-semibold">Actions</th>
                    </tr>
                </thead>
                <tbody class="divide-y">
                    @for (product in products.items) {
                        <tr class="hover:bg-gray-50 transition">
                            <td class="px-6 py-4">
                                <a href="@url('admin:products:detail', id=product.id)" class="text-blue-600 hover:underline">
                                    {{ product.name }}
                                </a>
                            </td>
                            <td class="px-6 py-4 text-gray-600">{{ product.sku }}</td>
                            <td class="px-6 py-4 text-right font-mono">${{ product.price|currency }}</td>
                            <td class="px-6 py-4 text-right">
                                <span class="@if(product.stock < 10) { text-red-600 font-bold } else { text-green-600 }">
                                    {{ product.stock }}
                                </span>
                            </td>
                            <td class="px-6 py-4 text-center">
                                @if(product.is_active) {
                                    <span class="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-semibold">Active</span>
                                } @else {
                                    <span class="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs font-semibold">Inactive</span>
                                }
                            </td>
                            <td class="px-6 py-4 text-center space-x-2">
                                <a href="@url('admin:products:edit', id=product.id)" class="text-blue-600 hover:underline text-sm">Edit</a>
                                <a href="@url('admin:products:delete', id=product.id)" 
                                   onclick="return confirm('Delete?')"
                                   class="text-red-600 hover:underline text-sm">Delete</a>
                            </td>
                        </tr>
                    } @empty {
                        <tr>
                            <td colspan="6" class="px-6 py-8 text-center text-gray-500">
                                No products found. <a href="@url('admin:products:create')" class="text-blue-600">Create one?</a>
                            </td>
                        </tr>
                    }
                </tbody>
            </table>
        </div>
        
        <!-- Pagination controls -->
        @include("components/pagination", {
            "current_page": products.page,
            "total_pages": products.total_pages,
            "has_prev": products.has_prev,
            "has_next": products.has_next,
            "prev_url": products.prev_url,
            "next_url": products.next_url,
            "base_url": request.url.path
        })
    </div>
}
```

### Response Handler for Dashboard

```python
from eden import Router
from math import ceil

@app.get("/admin/products")
async def admin_products_list(request):
    # Query parameters for filtering and sorting
    search = request.query_params.get("search", "")
    category_id = request.query_params.get("category")
    status = request.query_params.get("status")
    sort_by = request.query_params.get("sort", "name")
    sort_dir = request.query_params.get("dir", "asc")
    page = int(request.query_params.get("page", 1))
    per_page = 20
    
    # Build query
    query = Product.all()
    
    # Apply filters
    if search:
        query = query.filter(
            Q(name__icontains=search) | Q(sku__icontains=search)
        )
    
    if category_id:
        query = query.filter(category_id=category_id)
    
    if status == "active":
        query = query.filter(is_active=True)
    elif status == "inactive":
        query = query.filter(is_active=False)
    
    # Get total count before limiting
    total = await query.count()
    
    # Apply sorting
    sort_field = f"-{sort_by}" if sort_dir == "desc" else sort_by
    query = query.order_by(sort_field)
    
    # Apply pagination
    offset = (page - 1) * per_page
    products = await query.limit(per_page).offset(offset).all()
    
    # Calculate pagination info
    total_pages = ceil(total / per_page)
    
    # Get categories for filter dropdown
    categories = await Category.all()
    
    return request.render("admin/products.html", {
        "products": {
            "items": products,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "offset": offset,
            "limit": per_page,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_url": f"?page={page-1}&search={search}&category={category_id}&status={status}",
            "next_url": f"?page={page+1}&search={search}&category={category_id}&status={status}",
        },
        "categories": categories,
    })
```

---

## 📄 Pagination & Navigation

Pagination is essential for listing large datasets. Here's a reusable pagination component.

### Pagination Component Template

```html
<!-- templates/components/pagination.html -->
<div class="mt-8 flex items-center justify-between">
    <!-- Previous button -->
    @if(has_prev) {
        <a href="{{ prev_url }}" class="btn btn-sm btn-secondary">← Previous</a>
    } @else {
        <button disabled class="btn btn-sm btn-secondary opacity-50 cursor-not-allowed">← Previous</button>
    }
    
    <!-- Page numbers -->
    <div class="flex gap-1">
        @for (page_num in range(max(1, current_page - 2), min(total_pages + 1, current_page + 3))) {
            @if(page_num == current_page) {
                <span class="px-3 py-2 bg-blue-600 text-white rounded font-bold">{{ page_num }}</span>
            } @else {
                <a href="{{ base_url }}?page={{ page_num }}" class="px-3 py-2 border rounded hover:bg-gray-100">
                    {{ page_num }}
                </a>
            }
        }
    </div>
    
    <!-- Next button -->
    @if(has_next) {
        <a href="{{ next_url }}" class="btn btn-sm btn-primary">Next →</a>
    } @else {
        <button disabled class="btn btn-sm btn-primary opacity-50 cursor-not-allowed">Next →</button>
    }
</div>

<!-- Page info -->
<div class="mt-4 text-center text-sm text-gray-500">
    Page {{ current_page }} of {{ total_pages }}
</div>
```

### Cursor-Based Pagination (for large datasets)

For very large datasets, cursor-based pagination is more efficient:

```html
<!-- Cursor-based pagination -->
<div class="mt-8 flex gap-4">
    @if(has_prev) {
        <a href="?cursor={{ prev_cursor }}" class="btn btn-secondary">← Previous</a>
    }
    
    @if(has_next) {
        <a href="?cursor={{ next_cursor }}" class="btn btn-primary">Next →</a>
    }
</div>
```

```python
@app.get("/items")
async def items_with_cursor(request):
    cursor = request.query_params.get("cursor")
    limit = 25
    
    # Build query
    query = Item.all().order_by("-created_at")
    
    # If cursor provided, start from there
    if cursor:
        cursor_time = datetime.fromisoformat(cursor)
        query = query.filter(created_at__lt=cursor_time)
    
    # Fetch one extra to determine if there's a next page
    items = await query.limit(limit + 1).all()
    
    has_next = len(items) > limit
    if has_next:
        items = items[:limit]
    
    # Calculate next cursor (last item's timestamp)
    next_cursor = items[-1].created_at.isoformat() if items and has_next else None
    
    # Previous cursor (first item's timestamp)
    prev_cursor = items[0].created_at.isoformat() if items else None
    
    return request.render("items.html", {
        "items": items,
        "has_next": has_next,
        "has_prev": bool(cursor),
        "next_cursor": next_cursor,
        "prev_cursor": prev_cursor,
    })
```

---

## 🔍 Search & Filter Integration

Combining search, filters, and sorting creates a powerful data exploration experience.

### Advanced Search with Multiple Filters

```html
<!-- templates/search_results.html -->
@extends("layouts/base")

@section("content") {
    <div class="max-w-4xl mx-auto">
        <h1 class="text-3xl font-bold mb-6">Search Users</h1>
        
        <!-- Advanced search form -->
        <form method="GET" class="mb-8 p-6 bg-gray-50 rounded-xl">
            <div class="grid grid-cols-2 gap-4 mb-4">
                <!-- Text search -->
                <div>
                    <label class="block font-bold mb-2">Name or Email</label>
                    <input 
                        type="text" 
                        name="q" 
                        placeholder="Search..."
                        value="@old('q', request.query_params.get('q', ''))"
                        class="w-full px-4 py-2 border rounded-lg"
                    >
                </div>
                
                <!-- Role filter -->
                <div>
                    <label class="block font-bold mb-2">Role</label>
                    <select name="role" class="w-full px-4 py-2 border rounded-lg">
                        <option value="">Any Role</option>
                        <option value="admin" @if(request.query_params.get('role') == 'admin') { selected }>Admin</option>
                        <option value="manager" @if(request.query_params.get('role') == 'manager') { selected }>Manager</option>
                        <option value="user" @if(request.query_params.get('role') == 'user') { selected }>User</option>
                    </select>
                </div>
                
                <!-- Date range -->
                <div>
                    <label class="block font-bold mb-2">From Date</label>
                    <input 
                        type="date" 
                        name="from_date"
                        value="@old('from_date', request.query_params.get('from_date', ''))"
                        class="w-full px-4 py-2 border rounded-lg"
                    >
                </div>
                
                <div>
                    <label class="block font-bold mb-2">To Date</label>
                    <input 
                        type="date" 
                        name="to_date"
                        value="@old('to_date', request.query_params.get('to_date', ''))"
                        class="w-full px-4 py-2 border rounded-lg"
                    >
                </div>
            </div>
            
            <!-- Advanced options -->
            <details class="mb-4 p-3 bg-white rounded border">
                <summary class="cursor-pointer font-bold">More Options</summary>
                <div class="mt-3 space-y-3">
                    <label class="flex items-center">
                        <input type="checkbox" name="verified_only" 
                               @if(request.query_params.get('verified_only') == 'on') { checked }>
                        <span class="ml-2">Verified Only</span>
                    </label>
                    <label class="flex items-center">
                        <input type="checkbox" name="active_only"
                               @if(request.query_params.get('active_only') == 'on') { checked }>
                        <span class="ml-2">Active Only</span>
                    </label>
                </div>
            </details>
            
            <div class="flex gap-2">
                <button type="submit" class="btn btn-primary">🔍 Search</button>
                <a href="@url('users:search')" class="btn btn-secondary">Clear</a>
            </div>
        </form>
        
        <!-- Results -->
        @if(results.count > 0) {
            <div class="mb-4 text-sm text-gray-600">
                Found {{ results.count }} results
            </div>
            
            <div class="space-y-3">
                @for (user in results.items) {
                    <div class="p-4 border rounded-lg hover:bg-gray-50 transition">
                        <div class="flex justify-between items-start">
                            <div>
                                <h3 class="font-bold text-lg">{{ user.full_name }}</h3>
                                <p class="text-gray-600 text-sm">{{ user.email }}</p>
                                <p class="text-gray-500 text-xs mt-1">
                                    Joined {{ user.created_at|date }} • Role: <span class="font-semibold">{{ user.role }}</span>
                                </p>
                            </div>
                            <div class="text-right">
                                <a href="@url('admin:users:detail', id=user.id)" class="btn btn-sm btn-primary">View</a>
                            </div>
                        </div>
                    </div>
                }
            </div>
            
            <!-- Pagination -->
            @include("components/pagination", pagination_data)
        } @else {
            <div class="p-8 text-center text-gray-500">
                No results found. Try adjusting your search criteria.
            </div>
        }
    </div>
}
```

---

## ⚡ HTMX Dynamic Updates

HTMX allows you to build dynamic interfaces without writing JavaScript. Eden has first-class HTMX support.

### Real-Time Task List with HTMX

```html
<!-- templates/tasks.html -->
<div id="task-list">
    <h2 class="text-2xl font-bold mb-4">Tasks</h2>
    
    <!-- Add task form with HTMX -->
    <form hx-post="@url('tasks:create')" 
          hx-target="#task-list" 
          hx-swap="afterbegin"
          class="mb-6 flex gap-2">
        @csrf
        <input 
            type="text" 
            name="title" 
            placeholder="New task..."
            class="flex-1 px-4 py-2 border rounded"
            required
        >
        <button type="submit" class="btn btn-primary">Add</button>
    </form>
    
    <!-- Tasks list with HTMX updates -->
    @fragment("task-items") {
        @for (task in tasks) {
            <div class="p-4 border rounded-lg flex items-center justify-between group">
                <div class="flex items-center gap-3">
                    <!-- Toggle completion with HTMX -->
                    <input 
                        type="checkbox"
                        @if(task.is_completed) { checked }
                        hx-post="@url('tasks:toggle', id=task.id)"
                        hx-trigger="change"
                        hx-swap="outerHTML"
                        class="cursor-pointer"
                    >
                    <span class="@if(task.is_completed) { line-through text-gray-400 }">
                        {{ task.title }}
                    </span>
                </div>
                
                <!-- Delete with confirmation -->
                <button 
                    hx-delete="@url('tasks:delete', id=task.id)"
                    hx-confirm="Are you sure?"
                    hx-target="closest div"
                    hx-swap="outerHTML swap:1s"
                    class="btn btn-sm btn-danger opacity-0 group-hover:opacity-100 transition"
                >
                    Delete
                </button>
            </div>
        }
    }
</div>
```

### Response Handlers for HTMX

```python
@app.post("/tasks/{task_id}/toggle")
async def toggle_task(request, task_id: int):
    task = await Task.get(task_id)
    task.is_completed = not task.is_completed
    await task.save()
    
    # Return just the updated task item (HTMX will swap it)
    return request.render("tasks.html", {"tasks": [task]}, fragment="task-items")

@app.post("/tasks")
async def create_task(request):
    data = await request.form()
    task = Task(title=data["title"], user_id=request.user.id)
    await task.save()
    
    # Return updated task list (HTMX will prepend it)
    tasks = await Task.filter(user_id=request.user.id).all()
    return request.render("tasks.html", {"tasks": tasks}, fragment="task-items")

@app.delete("/tasks/{task_id}")
async def delete_task(request, task_id: int):
    task = await Task.get(task_id)
    await task.delete()
    return ""  # Empty response for HTMX to remove element
```

### Real-Time Form Validation with HTMX

```html
<form>
    <div class="form-group">
        <label>Email</label>
        <input 
            type="email"
            name="email"
            hx-post="@url('api:validate_email')"
            hx-trigger="change"
            hx-target="next .feedback"
            class="w-full px-4 py-2 border rounded"
        >
        <div class="feedback text-sm mt-1"></div>
    </div>
</form>
```

```python
@app.post("/api/validate-email")
async def validate_email(request):
    email = (await request.form()).get("email")
    
    # Check if email exists
    exists = await User.filter(email=email).exists()
    
    if exists:
        return "<p class='text-red-600'>Email already registered</p>"
    else:
        return "<p class='text-green-600'>✓ Email available</p>"
```

---

## 🧩 Template Component Patterns

Building reusable template components is key to maintainable templates.

### Card Component with Slots

```html
<!-- templates/components/card.html -->
<div class="p-6 border rounded-lg shadow @yield('classes', 'bg-white')">
    <!-- Header slot -->
    @if(!empty($slots['header']))
        <div class="border-b pb-3 mb-4">
            @include('components/slots/header')
        </div>
    }
    
    <!-- Default content -->
    @yield('content')
    
    <!-- Footer slot -->
    @if(!empty($slots['footer']))
        <div class="border-t pt-3 mt-4 flex justify-between">
            @include('components/slots/footer')
        </div>
    }
</div>
```

Usage in templates:

```html
@component("card", {class: "bg-blue-50"}) {
    @slot("header") {
        <h3 class="font-bold">User Profile</h3>
    }
    
    <p>{{ user.full_name }}</p>
    <p class="text-sm text-gray-600">{{ user.email }}</p>
    
    @slot("footer") {
        <button class="btn btn-sm btn-secondary">Edit</button>
        <button class="btn btn-sm btn-danger">Delete</button>
    }
}
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

---

## 🛠️ Common Directive Patterns

Mastering these patterns will significantly speed up your development.

### 1. The Active Navigation Pattern
Combine `@url` and `@active_link` for premium navigation bars.

```html
<nav class="flex gap-4">
    <a href="@url('dashboard')" class="nav-link @active_link('dashboard', 'is-active')">
        Dashboard
    </a>
    <a href="@url('students:index')" class="nav-link @active_link('students:*', 'is-active')">
        Students
    </a>
</nav>
```

### 2. The Conditional Fragment Pattern
Use `@htmx` to only render parts of a page when called via AJX/HTMX.

```html
<div class="content">
    @htmx {
        <!-- Only sent for HTMX partial updates -->
        @fragment("results") { ... }
    }
    @non_htmx {
        <!-- The full page layout for direct visits -->
        <h1>Search Results</h1>
        @fragment("results") { ... }
    }
</div>
```

### 3. The "Pure Logic" Component
Components aren't just for UI. Use them to encapsulate complex permissions or data fetching logic that needs to be reused across templates.

```html
@component("auth-gate", role="admin") {
    <button class="delete-btn">Secret Delete Action</button>
}
```

**Next Steps**: [Forms & Validation](forms.md)
