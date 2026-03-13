# Eden Templating Engine - Complete Reference Guide

> **Modern, Powerful, Express-Inspired Syntax for Web Templates**

This is the definitive guide to the Eden templating engine—a modern templating system designed to make templates readable, maintainable, and powerful. It builds on Jinja2 but introduces a cleaner, Express-inspired syntax using `@directives`.

---

## Table of Contents

1. [Philosophy & Why Eden Syntax](#philosophy--why-eden-syntax)
2. [Syntax Basics](#syntax-basics)
3. [Control Flow Directives](#control-flow-directives)
4. [Templating & Inheritance](#templating--inheritance)
5. [Form Handling](#form-handling)
6. [Filters (38+)](#filters)
7. [Loop Helpers](#loop-helpers)
8. [Components](#components)
9. [Authentication & Authorization](#authentication--authorization)
10. [HTMX Integration](#htmx-integration)
11. [Real-World Examples](#real-world-examples)
12. [Best Practices](#best-practices)

---

## Philosophy & Why Eden Syntax

### Why Not Standard Jinja2?

**Standard Jinja2:**
```html
{% if user.is_admin %}
    {% for item in items %}
        {{ item.name }}
    {% endfor %}
{% endif %}
```

**Eden:**
```html
@if (user.is_admin) {
    @for (item in items) {
        {{ item.name }}
    }
}
```

### The Why: Eden Advantages

| Aspect | Jinja2 | Eden |
|--------|--------|------|
| **Familiarity** | Django/Python devs | JavaScript/Express devs |
| **Readability** | Block tags hard to track | Braces show nesting |
| **Consistency** | Mixed syntax styles | Uniform `@directive` pattern |
| **IDE Support** | Limited brace matching | Full brace/paren support |
| **Expresiveness** | Verbose | More concise |
| **Learning Curve** | Separate syntax from code | Natural for JS developers |

### Philosophy

Eden templates are designed for **web developers who write JavaScript**, making the transition between frontend and backend logic seamless.

---

## Syntax Basics

### Variables & Expressions

```html
<!-- Simple variable -->
{{ user.name }}

<!-- Expression evaluation -->
{{ price * quantity }}
{{ user.is_admin ? 'Admin' : 'User' }}

<!-- Filter chaining -->
{{ user.email | lowercase | slice(0, 3) }}
```

### Comments

Eden comments are preprocessed (never sent to browser):

```html
@* This comment won't appear in the rendered HTML *@
@* Multi-line comments work too
   You can write as much as you want here
*@

<!-- This is HTML comment - WILL be sent to browser -->
```

### Reserved Variables

Every template has access to:

```html
{{ request }}               @* Starlette Request object *@
{{ render }}                @* Template rendering function *@
{{ url_for }}               @* URL generation helper *@
{{ csrf_token }}            @* CSRF protection token *@
{{ loop }}                  @* Loop metadata (in @for/@foreach) *@
```

---

## Control Flow Directives

### @if - Conditional Logic

Renders block only if condition evaluates to truthy.

```html
<!-- Basic usage -->
@if (user.is_authenticated) {
    <p>Welcome, {{ user.name }}!</p>
}

<!-- Multiple conditions -->
@if (user.role == 'admin') {
    <a href="/admin">Admin Panel</a>
} @else if (user.role == 'moderator') {
    <a href="/moderation">Moderation</a>
} @else {
    <p>Standard user</p>
}

<!-- Negation -->
@if (!user.is_banned) {
    <button>Post comment</button>
}

<!-- Complex expressions -->
@if (user.credits > 100 && user.is_verified) {
    <button class="premium-action">Upgrade</button>
}
```

**Why use @if instead of Jinja's {% if %}?**
- Braces make nesting visually clear
- Parentheses around conditions are familiar to developers
- Looks like JavaScript: `if (condition) { ... }`

---

### @unless - Inverted Conditional

Renders if condition is **False**.

```html
<!-- Show if user is NOT banned -->
@unless (user.is_banned) {
    <form method="post">
        @csrf
        <textarea name="comment"></textarea>
    </form>
}

<!-- Equivalent to: @if (!user.is_banned) { ... } -->
```

**When to use:** Clearer intent when you want to show content for the "normal" case and hide for an exception.

---

### @for / @foreach - Looping

Iterate over collections.

```html
<!-- Basic foreach -->
@foreach (product in products) {
    <div class="product">
        <h3>{{ product.name }}</h3>
        <p>${{ product.price }}</p>
    </div>
}

<!-- With index: use $loop.index -->
@for (item in items) {
    <tr>
        <td>{{ $loop.index }}</td>
        <td>{{ item.name }}</td>
    </tr>
}

<!-- Destructuring (key-value pairs) -->
@for (key, value in user.metadata) {
    <p><strong>{{ key }}:</strong> {{ value }}</p>
}

<!-- Using filtered collection -->
@foreach (product in products | active_only) {
    <li>{{ product.name }}</li>
}

<!-- Chaining conditions inside loop -->
@for (order in user.orders) {
    @if (order.status == 'pending') {
        <div class="alert">Order #{{ order.id }} pending</div>
    }
}
```

**$loop Variables:**
```html
@for (item in items) {
    {{ $loop.index }}      @* 1-based position (1, 2, 3...) *@
    {{ $loop.index0 }}     @* 0-based position (0, 1, 2...) *@
    {{ $loop.first }}      @* True on first iteration *@
    {{ $loop.last }}       @* True on last iteration *@
    {{ $loop.even }}       @* True if index is even *@
    {{ $loop.odd }}        @* True if index is odd *@
    {{ $loop.length }}     @* Total items in loop *@
}
```

**Real Example: Product List with Alternating Rows**
```html
<table>
    @for (product in products) {
        <tr class="{{ $loop.even ? 'bg-gray-50' : 'bg-white' }}">
            <td class="text-center">{{ $loop.index }}</td>
            <td>{{ product.name }}</td>
            <td>${{ product.price | money }}</td>
            <td>
                @if ($loop.first) {
                    <span class="badge">New</span>
                }
                @if ($loop.last) {
                    <span class="badge">Latest</span>
                }
            </td>
        </tr>
    }
</table>
```

---

### @switch / @case - Multi-way Branching

For cleaner code than multiple `@if / @else if` chains.

```html
<!-- Status indicator -->
@switch (order.status) {
    @case ('pending') {
        <span class="badge-yellow">⏳ Pending</span>
    }
    @case ('shipped') {
        <span class="badge-blue">📦 Shipped</span>
    }
    @case ('delivered') {
        <span class="badge-green">✓ Delivered</span>
    }
    @case ('cancelled') {
        <span class="badge-red">✗ Cancelled</span>
    }
}

<!-- User role switcher -->
@switch (user.role) {
    @case ('admin') {
        <nav>@include('admin_nav.html')</nav>
    }
    @case ('moderator') {
        <nav>@include('moderator_nav.html')</nav>
    }
    @case ('user') {
        <nav>@include('user_nav.html')</nav>
    }
}
```

**Why switch?** Cleaner than 5+ `@else if` statements, shows intent clearly.

---

## Templating & Inheritance

### @extends - Template Inheritance

```html
@* layouts/base.html *@
<!DOCTYPE html>
<html>
<head>
    <title>@block('title') { My Site }</title>
</head>
<body>
    <header>@block('header') { ... }</header>
    <main>@block('content') { ... }</main>
    <footer>@block('footer') { ... }</footer>
</body>
</html>

@* pages/home.html *@
@extends('layouts/base.html')

@block('title') { Home Page }

@block('content') {
    <h1>Welcome</h1>
    <p>This content replaces the base template's content block</p>
}
```

**Why inheritance?** Avoid repeating HTML structure across 100s of pages.

---

### @block - Define Replaceable Sections

Blocks are named sections that child templates can override:

```html
@* Base layout *@
<!DOCTYPE html>
<html>
<head>
    <title>@block('title') { Default Title }</title>
    <style>
        @block('styles') {
            /* Default styles */
        }
    </style>
</head>
<body>
    @block('content') {
        <p>Default content goes here</p>
    }
    @block('scripts') {
        <script src="/vendor/jquery.js"></script>
    }
</body>
</html>

@* Child template *@
@extends('base.html')

@block('title') { Product Listing }

@block('styles') {
    <style>
        .product-grid { display: grid; }
    </style>
}

@block('content') {
    <div class="product-grid">
        @for (product in products) {
            <div class="product-card">
                <h3>{{ product.name }}</h3>
            </div>
        }
    </div>
}
```

---

### @include - Include Other Templates

Import template snippets without inheritance:

```html
<!-- Simple include -->
<div class="sidebar">
    @include('components/sidebar.html')
</div>

<!-- Pass variables to included template -->
@include('components/alert.html', {
    type: 'success',
    message: 'Changes saved!'
})

<!-- Include in loops -->
@for (comment in post.comments) {
    @include('components/comment.html', {
        comment: comment,
        post: post
    })
}
```

---

### @yield - Define Output Points

Insert block content from parent:

```html
@yield('scripts')  @* Output content from 'scripts' block *@
```

---

### @push - Append to Blocks

Append content to a block rather than replacing it:

```html
@* Base layout *@
<head>
    @block('scripts') {
        <script src="/base.js"></script>
    }
</head>

@* Child template *@
@extends('base.html')

@push('scripts') {
    <script src="/page-specific.js"></script>
}

@* Result: both scripts load *@
```

---

## Form Handling

### @csrf - CSRF Token Protection

Always include in POST/PUT/DELETE forms:

```html
<form method="post" action="/save-post">
    @csrf
    <textarea name="content"></textarea>
    <button>Save</button>
</form>

@* Renders as: *@
<!-- <input type="hidden" name="csrf_token" value="..." /> -->
```

**Why automatic?** Laravel-inspired—you should never have to remember this.

---

### @checked / @selected / @disabled / @readonly

Conditional attribute directives:

```html
<!-- Checkbox -->
<input type="checkbox" name="agree" @checked(user.has_agreed) />

<!-- Radio/Select -->
<select name="role">
    <option @selected(user.role == 'admin')>Admin</option>
    <option @selected(user.role == 'user')>User</option>
</select>

<!-- Disabled state -->
<button @disabled(!form.is_valid)>Submit</button>

<!-- Read-only -->
<input type="email" value="{{ user.email }}" @readonly(user.verified) />
```

**Generated HTML:**
```html
<input type="checkbox" name="agree" checked="checked" />
<option selected="selected">Admin</option>
<button disabled="disabled">Submit</button>
<input type="email" readonly="readonly" />
```

---

### @old - Repopulate Form Fields

For form validation errors, returns the previously submitted value:

```html
<input type="text" name="username" 
       value="{{ @old('username', user.username) }}" />

<textarea name="bio">{{ @old('bio') }}</textarea>

<!-- Select with old value -->
<select name="country">
    <option @selected(@old('country') == 'US')>United States</option>
    <option @selected(@old('country') == 'CA')>Canada</option>
</select>
```

---

### @method - Form Method Override

HTML forms only support GET/POST, use this for PUT/PATCH/DELETE:

```html
<form method="post" action="/users/{{ user.id }}">
    @csrf
    @method('PATCH')
    <input type="text" name="name" value="{{ user.name }}" />
    <button>Update</button>
</form>

@* Renders as: *@
<!-- <input type="hidden" name="_method" value="PATCH" /> -->
```

---

## Filters

Filters transform data. Use with `|` operator and chain them:

```html
{{ value | filter }}
{{ value | filter1 | filter2 | filter3 }}
{{ value | filter('param1', 'param2') }}
```

### String Filters

```html
<!-- Case transformation -->
{{ "hello world" | uppercase }}           @* HELLO WORLD *@
{{ "HELLO WORLD" | lowercase }}           @* hello world *@
{{ "hello world" | capitalize }}          @* Hello world *@
{{ "hello world" | title }}               @* Hello World *@

<!-- Trimming -->
{{ "  hello  " | trim }}                  @* hello *@
{{ "  hello" | ltrim }}                   @* hello *@
{{ "hello  " | rtrim }}                   @* hello *@

<!-- Replacement -->
{{ "hello world" | replace('world', 'Eden') }}   @* hello Eden *@

<!-- Slicing -->
{{ "hello" | slice(0, 3) }}               @* hel *@
{{ text | truncate(30) }}                 @* Truncate to 30 chars with "…" *@

<!-- String analysis -->
{{ "hello" | length }}                    @* 5 *@
{{ "hello" | reverse }}                   @* olleh *@
{{ "hello world" | contains('world') }}   @* True *@

<!-- Slugification -->
{{ "Hello World!" | slugify }}            @* hello-world *@
```

### List/Array Filters

```html
<!-- Sorting & Ordering -->
{{ items | sort }}                        @* Sort ascending *@
{{ items | sort('name') }}                @* Sort by field *@
{{ items | reverse }}                     @* Reverse order *@

<!-- Selection -->
{{ items | join(', ') }}                  @* "item1, item2, item3" *@
{{ items | first }}                       @* First element *@
{{ items | last }}                        @* Last element *@
{{ items | slice(1, 3) }}                 @* Get items 1-2 *@

<!-- Filtering -->
{{ users | select('is_active') }}         @* Active users only *@
{{ users | reject('is_deleted') }}        @* Non-deleted users *@

<!-- Length -->
{{ items | length }}                      @* 42 *@

<!-- Unique -->
{{ [1, 2, 2, 3] | unique }}               @* [1, 2, 3] *@
```

### Numeric Filters

```html
<!-- Rounding -->
{{ 3.14159 | round(2) }}                  @* 3.14 *@
{{ 3.6 | round }}                         @* 4 *@
{{ 3.6 | floor }}                         @* 3 *@
{{ 3.2 | ceil }}                          @* 4 *@

<!-- Arithmetic -->
{{ items | sum }}                         @* Sum all items *@
{{ price | abs }}                         @* Absolute value *@

<!-- Percentage -->
{{ 0.857 | percent }}                     @* 85.7% *@
```

### Conversion Filters

```html
<!-- Type conversion -->
{{ value | int }}                         @* Convert to integer *@
{{ value | float }}                       @* Convert to float *@
{{ value | string }}                      @* Convert to string *@
{{ value | boolean }}                     @* Convert to boolean *@
{{ value | json_encode }}                 @* JSON string *@
```

### Formatting Filters

```html
<!-- Money/Currency - locale-aware -->
{{ 1234.56 | money }}                     @* $1,234.56 (default) *@
{{ 1234.56 | money('€') }}                @* €1,234.56 *@
{{ 1234.56 | money('¥', 'ja_JP') }}       @* ¥1,234 (Japanese) *@

<!-- Time -->
{{ post.created_at | time_ago }}          @* "2 hours ago" *@
{{ post.created_at | date('M d, Y') }}    @* "Mar 13, 2026" *@

<!-- Phone Numbers - international format -->
{{ "5551234567" | phone('US') }}          @* (555) 123-4567 *@
{{ "5551234567" | phone('E.164') }}       @* +15551234567 *@
```

### Special Filters

```html
<!-- Default/fallback -->
{{ user.bio | default('No bio provided') }}

<!-- Conditional application -->
{{ value | if(condition) }}               @* Return value only if condition true *@

<!-- Pluralization -->
{{ item_count | pluralize('item', 'items') }}
@* "1 item" or "5 items" *@

<!-- Safe HTML (prevents escaping) -->
{{ html_content | safe }}                 @* Don't escape HTML *@

<!-- Markdown (if configured) -->
{{ markdown_text | markdown }}

<!-- mask (hide sensitive data) -->
{{ "1234-5678-9012-3456" | mask }}        @* "••••-••••-••••-3456" *@
```

### Filter Examples: Real World Usage

```html
<!-- User profile -->
<div class="user-profile">
    <h2>{{ user.name | title }}</h2>
    <p>{{ user.bio | truncate(100) }}</p>
    <p>{{ user.email | lowercase }}</p>
    <p>Member since {{ user.created_at | date('M Y') }}</p>
</div>

<!-- Product listing -->
<div class="price">
    @if (product.discount > 0) {
        <span class="original">${{ product.price | money }}</span>
        <span class="sale">${{ product.sale_price | money('$') }}</span>
    } @else {
        <span>${{ product.price | money }}</span>
    }
</div>

<!-- Comments with timestamp -->
@for (comment in post.comments | sort('created_at') | reverse) {
    <div class="comment">
        <p>{{ comment.text | truncate(200) }}</p>
        <small>{{ comment.created_at | time_ago }}</small>
    </div>
}

<!-- Multi-filter chaining -->
{{ user.email | lowercase | slice(0, 3) }}    @* First 3 chars *@
{{ name | trim | capitalize | slugify }}       @* Clean and slugify *@
```

---

## Loop Helpers

The `$loop` object inside @for/@foreach gives loop context:

```html
@for (item in items) {
    <!-- Position -->
    Position: {{ $loop.index }} of {{ $loop.length }}
    
    <!-- Boolean checks -->
    @if ($loop.first) {
        <h2>First Item</h2>
    }
    
    @if ($loop.last) {
        <p>No more items</p>
    }
    
    @if ($loop.even) {
        <tr class="bg-gray-100">
    } @else {
        <tr>
    }
    
    <!-- Useful for styling -->
    <div class="item-{{ $loop.index0 % 3 }}">
        {{ item.name }}
    </div>
}
```

---

## Components

Reusable template components with slots:

```html
@* components/card.html *@
<div class="card">
    <h3>@slot('title')</h3>
    <div class="card-body">
        @slot('body')
    </div>
</div>

@* Usage in another template *@
@component('card', {
    title: 'Welcome',
    body: 'This is card content'
})

@* Or with block syntax *@
@component('card') {
    @slot('title') { My Title }
    @slot('body') {
        <p>Rich content here</p>
    }
}
```

---

## Authentication & Authorization

### @auth - Check Authentication

Show content only if user is logged in:

```html
@auth {
    <p>Welcome, {{ request.user.name }}!</p>
    <a href="/profile">My Profile</a>
    <a href="/logout">Logout</a>
}
```

---

### @guest - Check Non-Authentication

Show content for unauthenticated users:

```html
@guest {
    <p>Sign in to continue</p>
    <a href="/login">Login</a>
    <a href="/register">Register</a>
}
```

---

### Role-Based Access

```html
<!-- Admin only -->
@if (request.user && request.user.role == 'admin') {
    <a href="/admin">Admin Dashboard</a>
}

<!-- Moderator+ -->
@if (request.user && request.user.role in ['admin', 'moderator']) {
    <button>Delete comment</button>
}

<!-- Practical pattern -->
@auth {
    @if (request.user.is_admin) {
        <nav>@include('admin_nav.html')</nav>
    } @else {
        <nav>@include('user_nav.html')</nav>
    }
} @guest {
    <nav>@include('public_nav.html')</nav>
}
```

---

## HTMX Integration

### @htmx - HTMX Request Detection

Render different content for HTMX requests vs regular page loads:

```html
@htmx {
    @* This renders only for HTMX requests *@
    <div class="toast">Updated!</div>
}

@non_htmx {
    @* This renders for normal page loads *@
    <div class="full-page-layout">
        <!-- Full HTML page -->
    </div>
}
```

**Real Example: Progressive Enhancement**
```html
@non_htmx {
    <!DOCTYPE html>
    <html>
    <head>
        <title>Task Manager</title>
        <script src="https://unpkg.com/htmx.org"></script>
    </head>
    <body>
        <h1>Tasks</h1>
        <div id="task-list" 
             hx-get="/tasks/list"
             hx-trigger="load"
             hx-swap="innerHTML">
            Loading...
        </div>
    </body>
    </html>
}

@htmx {
    @* HTMX request - return just the list *@
    @for (task in tasks) {
        <div class="task">
            <h3>{{ task.title }}</h3>
            <p>{{ task.description }}</p>
            <button hx-post="/tasks/{{ task.id }}/complete"
                    hx-swap="swapOut">
                Complete
            </button>
        </div>
    }
}
```

---

### @fragment - HTMX Fragment Naming

Name fragments for HTMX OOB (out-of-band) swaps:

```html
<div id="alerts">
    @fragment('alert-box') {
        <div class="alert">New message!</div>
    }
</div>

<!-- HTMX can target: hx-swap="beforeend:#alert-box" -->
```

---

## Real-World Examples

### Example 1: Blog Post with Comments

```html
@extends('layouts/blog.html')

@block('title') { {{ post.title }} }

@block('content') {
    <article>
        <h1>{{ post.title }}</h1>
        <p class="meta">
            By {{ post.author.name | capitalize }}
            on {{ post.created_at | date('M d, Y') }}
        </p>
        
        <div class="content">
            {{ post.body | safe }}
        </div>
        
        @if (post.tags | length > 0) {
            <ul class="tags">
                @for (tag in post.tags | sort) {
                    <li><a href="/tags/{{ tag | slugify }}">{{ tag }}</a></li>
                }
            </ul>
        }
    </article>
    
    <section class="comments">
        <h2>Comments ({{ post.comments | length }})</h2>
        
        @if (post.comments | length > 0) {
            @for (comment in post.comments | sort('created_at') | reverse) {
                <div class="comment">
                    <h4>{{ comment.author }}</h4>
                    <p>{{ comment.text }}</p>
                    <small>{{ comment.created_at | time_ago }}</small>
                    
                    @auth {
                        @if (request.user.id == post.author.id || request.user.is_admin) {
                            <button hx-delete="/comments/{{ comment.id }}">Delete</button>
                        }
                    }
                </div>
            }
        } @else {
            <p>No comments yet. Be the first!</p>
        }
        
        @auth {
            <form hx-post="/posts/{{ post.id }}/comments" hx-swap="beforeend">
                @csrf
                <textarea name="text" placeholder="Your comment..."></textarea>
                <button>Post Comment</button>
            </form>
        } @guest {
            <p><a href="/login">Log in</a> to comment</p>
        }
    </section>
}
```

---

### Example 2: E-Commerce Product Grid

```html
@extends('layouts/main.html')

@block('content') {
    <div class="filters">
        <h3>Filters</h3>
        <form hx-get="/products" hx-target="#products">
            <select name="category">
                <option value="">All Categories</option>
                @for (category in categories) {
                    <option @selected(request.query.category == category.id) 
                            value="{{ category.id }}">
                        {{ category.name }}
                    </option>
                }
            </select>
            
            <input type="range" name="price_max" min="0" max="10000" 
                   hx-trigger="change" />
            
            <button type="submit">Filter</button>
        </form>
    </div>
    
    <div id="products" class="product-grid">
        @if (products | length > 0) {
            @for (product in products) {
                <div class="product-card">
                    <img src="{{ product.image_url }}" alt="{{ product.name }}" />
                    
                    <h3>{{ product.name | truncate(30) }}</h3>
                    
                    <div class="rating">
                        {{ product.rating | round(1) }} / 5
                        ({{ product.reviews | length }} reviews)
                    </div>
                    
                    <div class="pricing">
                        @if (product.discount > 0) {
                            <span class="original">${{ product.price | money }}</span>
                            <span class="sale">${{ product.sale_price | money }}</span>
                            <span class="badge">-{{ product.discount }}%</span>
                        } @else {
                            <strong>${{ product.price | money }}</strong>
                        }
                    </div>
                    
                    @if (product.in_stock) {
                        <form hx-post="/cart/add" hx-swap="toast">
                            @csrf
                            <input type="hidden" name="product_id" value="{{ product.id }}" />
                            <input type="number" name="quantity" value="1" min="1" />
                            <button>Add to Cart</button>
                        </form>
                    } @else {
                        <button disabled>Out of Stock</button>
                    }
                    
                    <a href="/products/{{ product.slug }}">View Details</a>
                </div>
            }
        } @else {
            <p class="no-results">No products found. Try adjusting filters.</p>
        }
    </div>
}
```

---

### Example 3: Admin Dashboard

```html
@extends('layouts/admin.html')

@block('title') { Dashboard }

@block('content') {
    @unless (request.user && request.user.is_admin) {
        <div class="alert-red">Unauthorized</div>
    }
    
    <div class="dashboard-grid">
        <!-- Statistics -->
        <div class="stat-card">
            <h4>Total Users</h4>
            <p class="stat-value">{{ users | length | format_number }}</p>
            <span class="trend">↑ 12% this month</span>
        </div>
        
        <div class="stat-card">
            <h4>Revenue</h4>
            <p class="stat-value">{{ revenue | money }}</p>
            <span class="trend">↑ 23% this month</span>
        </div>
        
        <!-- Recent Activities -->
        <div class="panel">
            <h3>Recent Activities</h3>
            @if (activities | length > 0) {
                <ul>
                    @for (activity in activities | sort('timestamp') | reverse | slice(0, 10)) {
                        <li>
                            <strong>{{ activity.user.name | capitalize }}</strong>
                            {{ activity.action }}
                            <time>{{ activity.timestamp | time_ago }}</time>
                        </li>
                    }
                </ul>
            } @else {
                <p>No recent activities</p>
            }
        </div>
        
        <!-- User Management -->
        <div class="panel">
            <h3>Users</h3>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    @for (user in users | sort('created_at') | reverse | slice(0, 20)) {
                        <tr class="{{ $loop.even ? 'bg-gray-50' : '' }}">
                            <td>{{ $loop.index }}</td>
                            <td>{{ user.name | capitalize }}</td>
                            <td>{{ user.email | lowercase }}</td>
                            <td>
                                <span class="badge badge-{{ user.role }}">
                                    {{ user.role | title }}
                                </span>
                            </td>
                            <td>
                                @if (user.is_active) {
                                    <span class="status-active">● Active</span>
                                } @else {
                                    <span class="status-inactive">● Inactive</span>
                                }
                            </td>
                            <td>
                                <a href="/admin/users/{{ user.id }}">Edit</a>
                                <button hx-delete="/admin/users/{{ user.id }}" 
                                        hx-confirm="Delete {{ user.name }}?">
                                    Delete
                                </button>
                            </td>
                        </tr>
                    }
                </tbody>
            </table>
        </div>
    </div>
}
```

---

## Best Practices

### 1. Use Meaningful Block Names

```html
@* Good *@
@block('page_title')
@block('featured_products')
@block('user_navigation')

@* Avoid *@
@block('content1')
@block('section_a')
@block('part2')
```

---

### 2. Separate Logic from Templates

```html
@* Bad: Complex logic in template *@
@if (user.account_age > 365 && user.purchases > 10 && user.rating > 4.5) {
    <div>Premium member</div>
}

@* Good: Use filters or prepare data before rendering *@
@if (user.is_premium_member) {
    <div>Premium member</div>
}
```

---

### 3. Use Filters Instead of Parentheses

```html
@* Less clear *@
{{ truncate(product.name, 30) }}

@* Better *@
{{ product.name | truncate(30) }}
```

---

### 4. Comment Complex Expressions

```html
@* Filter for products that are:
   1. In stock
   2. Not on backorder
   3. In user's preferred categories *@
@for (product in products | available | in_preferred_categories) {
    ...
}
```

---

### 5. Use @unless for Negation Only When Clear

```html
@* Good: Simple negation *@
@unless (user.is_banned) {
    <form>...</form>
}

@* Better if complex: Use @if with ! *@
@if (!user.is_banned && user.is_verified) {
    <form>...</form>
}
```

---

### 6. Keep Components Small

```html
@* Good: One concern per component *@
@include('components/product_card.html')
@include('components/price_badge.html')
@include('components/rating_stars.html')

@* Avoid: Doing everything in one large component *@
@include('components/product_with_everything.html')
```

---

### 7. Use Consistent Indentation

```html
@* Good: Clear nesting *@
@for (item in items) {
    @if (item.visible) {
        <div>{{ item.name }}</div>
    }
}

@* Avoid: Inconsistent *@
@for (item in items) {
@if (item.visible) {
<div>{{ item.name }}</div>
}
}
```

---

### 8. Security: Always Escape User Content

```html
@* Bad: User input goes straight in *@
<p>{{ comment.text }}</p>

@* Good: Escaped by default (unless marked as safe) *@
<p>{{ comment.text }}</p>

@* Allowed only for trusted content *@
<div>{{ post.body | safe }}</div>
```

---

### 9. Performance: Avoid Expensive Operations

```html
@* Bad: Query inside template loop *@
@for (user in users) {
    <p>{{ user.name }} has {{ user.get_posts().length }} posts</p>
}

@* Good: Prepare data before rendering *@
@for (user in users_with_post_counts) {
    <p>{{ user.name }} has {{ user.post_count }} posts</p>
}
```

---

### 10. Use @csrf on Every Form

```html
<form method="post">
    @csrf
    <!-- Always include CSRF token -->
</form>
```

---

## Summary

The Eden templating engine combines the power of Jinja2 with an Express-inspired, JavaScript-familiar syntax. Key takeaways:

| Feature | Purpose |
|---------|---------|
| **@directives** | Control flow and templating logic |
| **{{ }}** | Variable interpolation and expressions |
| **\| filters** | Transform and format data |
| **@block/@extends** | Template inheritance and DRY principles |
| **$loop** | Access iteration context |
| **@csrf** | CSRF protection (always use) |
| **@checked/@selected/@disabled** | Smart form attributes |
| **@auth/@guest** | Authentication-based rendering |
| **@htmx/@fragment** | Modern interactive UI patterns |

**Master these concepts and you'll write maintainable, powerful, secure web templates.**

---

## Reference Quick Links

- **Full Filters Reference:** Use 38+ built-in filters for data transformation
- **Complete Directives Guide:** All 40+ @directives with examples
- **Component System:** Build reusable template components
- **Troubleshooting:** Common issues and solutions
- **Test Coverage:** 180+ passing tests validate all features

Happy templating! 🚀
