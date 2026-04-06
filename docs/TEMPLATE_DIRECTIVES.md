# Eden Templating Directives Reference

Complete guide to all 65+ directives available in Eden's Blade-inspired template syntax.

**Table of Contents:**
- [Quick Start](#quick-start)
- [Control Flow](#control-flow)
- [Loops](#loops)
- [Layouts & Components](#layouts--components)
- [Forms & Validation](#forms--validation)
- [Authentication & Authorization](#authentication--authorization)
- [Utilities & Helpers](#utilities--helpers)
- [Advanced Features](#advanced-features)
- [Performance & Best Practices](#performance--best-practices)

---

## Quick Start

Eden templates use `@directive(args)` syntax instead of `{{ ... }}`:

```html
<!-- Conditional rendering -->
@if(user.is_authenticated)
  Welcome, {{ user.name }}!
@endif

<!-- Loops -->
@for(item in items)
  <li>{{ item.name }}</li>
@endfor

<!-- Template inheritance -->
@extends('layout.html')
@section('content')
  Content here
@endsection

<!-- Components -->
@component('button', text='Click me')
  <i class="icon"></i>
@endcomponent
```

---

## Control Flow

### @if / @elif / @elseif / @else_if / @else

Conditional rendering. Use with any expression.

```html
<!-- Basic if -->
@if(age >= 18)
  You are an adult
@endif

<!-- if-else -->
@if(status == 'pending')
  Pending approval
@else
  Approved
@endif

<!-- Multiple conditions -->
@if(user.is_admin)
  Admin panel
@elseif(user.is_moderator)
  Moderator tools
@else
  User view
@endif
```

**Aliases:**
- `@elseif`, `@elif`, `@else_if` — all equivalent

---

### @unless

Inverted if (renders when condition is FALSE).

```html
@unless(user.is_banned)
  <p>Welcome!</p>
@endunless

<!-- Equivalent to: -->
@if(not user.is_banned)
  <p>Welcome!</p>
@endif
```

---

### @switch / @case / @default

Pattern matching.

```html
@switch(user.role)
  @case('admin')
    Admin controls
  @case('moderator')
    Moderation tools
  @default
    Standard user view
@endswitch
```

---

## Loops

### @for / @foreach

Iterate over a collection. Supports `loop` context variable.

```html
<!-- Basic loop -->
@for(item in items)
  <div>{{ item.name }}</div>
@endfor

<!-- With loop context -->
@for(item in items)
  <li class="item-{{ loop.index }}">
    {{ item.name }}
    @if(loop.first)
      <em>(First item)</em>
    @endif
  </li>
@endfor

<!-- Alias: foreach -->
@foreach(user in users)
  {{ user.name }}
@endforeach
```

**Loop Context Variables:**
- `loop.index` — 1-indexed iteration number
- `loop.index0` — 0-indexed iteration number
- `loop.first` — True on first iteration
- `loop.last` — True on last iteration
- `loop.length` — Total items in collection
- `loop.previtem` — Previous item (or undefined)
- `loop.nextitem` — Next item (or undefined)
- `loop.changed(value)` — True if value changed from previous iteration

**Loop Iteration Safety:**
- Maximum 10,000 iterations per loop (prevents infinite loops in production)
- Exceeding limit logs warning and breaks loop

---

### @empty

Fallback content when loop is empty (Blade-style).

```html
@for(item in items)
  <div>{{ item.name }}</div>
@empty
  <p>No items found</p>
@endfor
```

---

### @while

Loop while condition is true. Implemented as `for` with break.

```html
@while(count > 0)
  <p>{{ count }}</p>
  @let count = count - 1
@endwhile
```

**Safety:**
- Maximum 10,000 iterations
- Useful for countdown or polling patterns

---

### @recursive

Render hierarchical (tree) structures recursively.

```html
@recursive(menu in menus)
  <li>
    {{ menu.name }}
    @if(menu.children)
      <ul>
        @child(menu.children)
      </ul>
    @endif
  </li>
@endrecursive
```

**Within @recursive:**
- Use `@child(items)` to recurse to next level
- Use `loop` for current level context
- Maximum 10,000 total iterations across all levels

---

### Loop Control

#### @break

Exit loop immediately.

```html
@for(item in items)
  @if(item.id == target_id)
    Found it! Breaking...
    @break
  @endif
@endfor

<!-- Conditional break -->
@for(i in range(100))
  @if(i == 50)
    @break
  @endif
@endfor
```

---

#### @continue

Skip to next iteration.

```html
@for(item in items)
  @if(item.hidden)
    @continue
  @endif
  <div>{{ item.name }}</div>
@endfor

<!-- Conditional continue -->
@for(i in range(10))
  @if(i % 2 == 0)
    @continue
  @endif
  <span>Odd: {{ i }}</span>
@endfor
```

---

### Loop Context Conditionals

#### @even / @odd / @first / @last

Render content based on loop position.

```html
@for(item in items)
  <tr class="@if(loop.even) even @else odd @endif">
    <td>{{ item.name }}</td>
  </tr>
@endfor

<!-- Simplified -->
@for(item in items)
  <tr class="@even even @endevenborder @odd odd @endodd">
    <td>{{ item.name }}</td>
  </tr>
@endfor

<!-- First/last items -->
@for(item in items)
  @first
    <h2>First: {{ item.name }}</h2>
  @endfirst
  
  @last
    <h2>Last: {{ item.name }}</h2>
  @endlast
@endfor
```

---

## Layouts & Components

### @extends

Inherit from parent template.

```html
@extends('base.html')

<!-- Parent layout (base.html) defines blocks that children can override -->
```

---

### @section / @block

Define named blocks for content injection.

```html
<!-- In layout.html -->
@section('header')
  <header>Default header</header>
@endsection

<!-- In child template -->
@extends('layout.html')
@section('header')
  <header>Custom header</header>
@endsection
```

**Alias:** `@block` (same as `@section`)

---

### @yield

Define a placeholder block.

```html
<!-- In layout.html -->
<div class="content">
  @yield('content')
</div>

<!-- In child template -->
@section('content')
  <p>Page content</p>
@endsection
```

---

### @include

Include a partial template.

```html
@include('partials/header.html')

<!-- With context passing -->
@include('components/card.html', {
  'title': 'My Card',
  'content': 'Card content'
})
```

---

### @includeWhen / @includeUnless

Conditional includes.

```html
<!-- Include only if authenticated -->
@includeWhen(request.user.is_authenticated, 'partials/user-menu.html')

<!-- Include unless user is admin -->
@includeUnless(request.user.is_admin, 'partials/user-welcome.html')
```

---

### @fragment

Define a named fragment for HTMX partial rendering.

```html
@fragment('user-list')
  <ul id="user-list">
    @for(user in users)
      <li>{{ user.name }}</li>
    @endfor
  </ul>
@endfragment
```

**Smart Fragment Rendering:** When HTMX targets a fragment ID, only that block is rendered, not the entire page. Greatly improves performance for dynamic updates.

---

### @component / @slot

Define reusable components with named slots.

```html
<!-- components/badge.html -->
@component('badge')
  @slot('content')
    Default badge text
  @endslot
  
  @slot('icon')
    📌
  @endslot
@endcomponent

<!-- Usage -->
@component('badge')
  <span>Premium Member</span>
@endcomponent
```

---

### @props

Declare component properties (metadata).

```html
<!-- components/form-field.html -->
@props(['name', 'label', 'type' => 'text', 'required' => false])

<div class="form-group">
  <label for="{{ name }}">{{ label }}</label>
  <input 
    type="{{ type }}" 
    name="{{ name }}" 
    id="{{ name }}"
    @if(required) required @endif
  />
</div>
```

---

### @push / @pushOnce / @prepend / @stack

Accumulate content in stacks (useful for scripts, styles).

```html
<!-- In layout.html -->
<head>
  @stack('styles')
</head>
<body>
  <!-- ... -->
  @stack('scripts')
</body>

<!-- In child template -->
@push('scripts')
  <script src="/js/page-specific.js"></script>
@endpush

<!-- Only push once per request, even if included multiple times -->
@pushOnce('scripts')
  <script>console.log("Once");</script>
@endpushonce

<!-- Prepend to stack (goes first) -->
@prepend('scripts')
  <script>console.log("First");</script>
@endprepend
```

---

## Forms & Validation

### @form

Render a form tag with automatic CSRF protection.

```html
@form(method='POST', action='/users')
  <!-- CSRF token automatically injected for POST forms -->
  
  <input type="text" name="username" />
  <button type="submit">Create</button>
@endform
```

---

### @csrf / @csrf_token

CSRF token helpers.

```html
<!-- Full hidden input -->
@csrf

<!-- Just the token value -->
<input type="hidden" name="_token" value="@csrf_token" />
```

---

### @field / @input / @button

Form component integration.

```html
<!-- Using form component system -->
@field('email', type='email', label='Email Address')

@input('password', 'Password')

@button('submit', 'Create Account')
```

---

### @render_field

Render a form field with validation errors.

```html
@render_field(form.username)

<!-- Renders field widget + error messages if invalid -->
```

---

### @error

Display validation errors.

```html
@error('email')
  <span class="text-red-500">{{ error }}</span>
@enderror
```

---

### @old

Restore previously submitted form values (for repopulation on validation error).

```html
<input 
  type="text" 
  name="email" 
  value="@old('email', '')" 
/>

<!-- Default value if not found -->
<textarea name="bio">@old('bio', 'Tell us about yourself...')</textarea>
```

---

### @method

Hidden method override for HTTP verb tunneling.

```html
<!-- Render hidden _method input for PUT/DELETE over POST -->
@method('PUT')
<!-- Renders: <input type="hidden" name="_method" value="PUT"> -->
```

---

## Authentication & Authorization

### @auth

Render content only if user is authenticated.

```html
@auth
  <p>Welcome, {{ request.user.name }}!</p>
@endauth

<!-- Check specific role -->
@auth('admin')
  Admin controls visible
@endauth

<!-- Check multiple roles -->
@auth('admin', 'moderator')
  Staff controls
@endauth
```

---

### @guest

Render content only if user is NOT authenticated.

```html
@guest
  <p><a href="/login">Login</a></p>
@endguest
```

---

### @can / @cannot / @permission

Permission-based rendering.

```html
@can('edit_post')
  <a href="/posts/{{ post.id }}/edit">Edit</a>
@endcan

@cannot('delete_post')
  <p>You don't have permission to delete</p>
@endcannot

<!-- Alias: @permission -->
@permission('publish_post')
  <button>Publish</button>
@endpermission
```

---

### @role

Check user role.

```html
@role('admin')
  Administrator view
@endrole

@role('admin', 'moderator')
  Staff view
@endrole
```

---

### @admin

Admin-only content (convenience shorthand for `@role('admin')`).

```html
@admin
  <a href="/admin">Admin Panel</a>
  <button>Admin Settings</button>
@endadmin

<!-- Equivalent to: -->
@role('admin')
  <a href="/admin">Admin Panel</a>
  <button>Admin Settings</button>
@endrole
```

Perfect for protecting admin-only UI elements and links.

---

## Utilities & Helpers

### @if / @span / @let

Simple expressions and variable assignment.

```html
<!-- Span: output expression -->
@span(user.email)
<!-- Renders: {{ user.email }} -->

<!-- Let: assign variable -->
@let full_name = user.first_name + ' ' + user.last_name
<p>{{ full_name }}</p>

<!-- Null coalescing shorthand -->
@span(user.middle_name ?? 'N/A')
```

---

### @json

Encode value as JSON.

```html
<script>
  const userData = @json(request.user);
</script>
```

---

### @dump

Pretty-print a value for debugging.

```html
@dump(user)
<!-- Renders styled <pre> block with formatted output -->

<!-- With label -->
@dump(request.session, 'Session Data')
```

---

### @url / @route

Generate URLs.

```html
<!-- Generate URL for route -->
<a href="@url('post.show', {'id': post.id})">
  Read post
</a>

<!-- Alias: @route -->
<a href="@route('home')">Home</a>
```

---

### @active_link

Add CSS class if route matches.

```html
<a 
  href="/posts"
  class="nav-link @active_link('posts.index', 'active', 'inactive')"
>
  Posts
</a>

<!-- Renders: class="nav-link active" if on posts.index route -->
```

---

### @class

Conditional CSS class binding.

```html
<div class="@class({
  'alert': True,
  'alert-success': is_success,
  'alert-danger': is_error,
  'hidden': not visible
})">
  Message
</div>
```

---

### @checked / @selected / @disabled / @readonly

Form field conditionals.

```html
<input 
  type="checkbox" 
  name="agree"
  @checked(user.has_agreed)
/>

<select name="status">
  <option value="active" @selected(user.status == 'active')>
    Active
  </option>
</select>

<input 
  type="text"
  @disabled(not is_editable)
  @readonly(is_readonly)
/>
```

---

### @verbatim

Prevent directive parsing (useful for nested templating).

```html
@verbatim
  This @if(condition) will not be parsed
  It's treated as literal text
@endverbatim
```

---

### @status

Set HTTP response status code.

```html
@status(404)

<h1>Page Not Found</h1>
```

---

### @messages / @error

Message/flash display.

```html
@messages
  <div class="alert alert-{{ message.level }}">
    {{ message.text }}
  </div>
@endmessages
```

---

## Advanced Features

### @reactive

Auto-sync block content via WebSocket when data changes.

```html
@reactive(post)
  <div>
    <h2>{{ post.title }}</h2>
    <p>{{ post.content }}</p>
  </div>
@endreactive

<!-- Refreshes automatically when post is updated -->
```

**Behind the scenes:**
- Sets up HTMX polling on change events
- Uses fragment rendering for efficient updates
- Requires proper WebSocket channel setup

---

### @inject

Inject services from app context into template.

```html
@inject(cache, 'cache')
@inject(mail, 'mail')
@inject(env, 'env')

@if(cache)
  <p>Cache is available: {{ cache }}</p>
@endif
```

**Resolution order:**
1. App instance attributes (`app.cache`, `app.mail`, etc.)
2. App config attributes (`app.config.database_url`, etc.)
3. App state attributes (`app.state.custom_value`)

---

### @php

Execute arbitrary logic (PHP-like, converted to Jinja2).

```html
@php
  sum = 0
  for i in range(10):
    sum += i
@endphp

<p>Sum: {{ sum }}</p>
```

**Note:** Basic Python-like syntax only. Complex logic should be in controllers instead.

---

### @htmx / @non_htmx

Render content based on request type.

```html
<!-- Only show if HTMX request -->
@htmx
  <p>Partial content</p>
@endhtmx

<!-- Show for regular requests -->
@non_htmx
  <div>Full page content</div>
@endnon_htmx
```

Useful for serving both full pages and fragments depending on client.

---

### @asset Directives

#### @css / @js

Link stylesheets and scripts.

```html
@css('https://cdn.example.com/style.css')

@js('https://cdn.example.com/script.js')
```

---

#### @vite

Vite asset bundling.

```html
@vite('resources/js/app.js', 'resources/css/app.css')
```

---

#### @eden_head / @eden_scripts / @eden_toasts

Eden framework integrations.

```html
<head>
  @eden_head
  <!-- Renders <title>, meta tags, etc. -->
</head>

<body>
  <!-- ... content ... -->
  
  @eden_scripts
  <!-- Loads Eden's JS runtime -->
  
  @eden_toasts
  <!-- Renders toast notifications -->
</body>
```

---

## Performance & Best Practices

### Loop Safety

- **Max iterations:** 10,000 per loop
- **Exceeding limit:** Logs warning, breaks loop
- Use `@break` to exit early in long iterations
- Consider pagination for large datasets

```html
<!-- Good: Paginated instead of all items -->
@for(item in paginated_items)
  <div>{{ item.name }}</div>
@endfor

<!-- Avoid: All items in one loop -->
@for(item in all_items)
  <div>{{ item.name }}</div>
@endfor
```

---

### Fragment Rendering

Use `@fragment` for HTMX-based updates instead of full page re-renders:

```html
<!-- Wrap dynamic content in fragment -->
@fragment('posts-list')
  @for(post in posts)
    @include('partials/post-item.html')
  @endfor
@endfragment

<!-- JavaScript triggers smart update -->
htmx.ajax('GET', '/posts', {target: '#posts-list'})
```

This renders only the fragment, not the entire page.

---

### Caching Injected Services

Use `@inject` to access cached/singleton services:

```html
@inject(cache, 'cache')

<!-- Cache is resolved once and reused for the request -->
@if(cache.get('featured_posts'))
  <div>{{ cache.get('featured_posts') }}</div>
@endif
```

---

### Security Considerations

#### Automatic Protections

Eden's templating engine includes automatic security hardening:

- ✅ **HTML Escaping** - All user-controlled output automatically escaped
- ✅ **Template Injection Prevention** - Role/permission names treated as data, not code  
- ✅ **Attribute Quoting** - CSS/JS URLs properly quoted to prevent injection
- ✅ **External Link Hardening** - Automatic `rel="noopener noreferrer"` on `target="_blank"` links
- ✅ **Input Validation** - All directive arguments validated with helpful error messages

---

#### @php Directive

⚠️ Use sparingly. Logic should live in controllers:

```html
<!-- Avoid complex logic in templates -->
@php
  result = expensive_calculation(data)
@endphp

<!-- Better: Pass pre-calculated data from controller -->
{{ calculated_result }}
```

---

#### CSRF Protection

Always use `@csrf` or `@csrf_token` in forms:

```html
@form(method='POST', action='/data')
  @csrf
  <!-- Or: <input type="hidden" value="@csrf_token"> -->
  
  <input type="text" name="data" />
  <button type="submit">Submit</button>
@endform
```

---

#### User Content Rendering

Always trust Eden's automatic escaping:

```html
<!-- ✅ SAFE: User input is automatically HTML-escaped -->
<p>{{ user_supplied_text }}</p>

<!-- ✅ SAFE: @dump also escapes output -->
@dump(user_data)

<!-- ✅ SAFE: External links are hardened -->
<a href="{{ user.website }}" target="_blank">Visit</a>
<!-- Automatically adds: rel="noopener noreferrer" -->
```

---

#### @verbatim

Use to prevent HTML/JS injection in nested templates:

```html
@verbatim
  Client-side template: {{ variable }}
  Won't be processed by Eden
@endverbatim
```

For comprehensive security guidance, see [Security Best Practices](./security.md#template-security).

---

### Built-in Filters

Eden provides 20+ filters for common operations:

```html
<!-- Time formatting -->
{{ post.created_at | time_ago }}  <!-- "2 hours ago" -->

<!-- Money formatting -->
{{ price | money }}  <!-- "$19.99" -->

<!-- Text truncation -->
{{ description | truncate(100) }}  <!-- First 100 chars + "..." -->

<!-- Markdown rendering -->
{{ content | markdown | safe }}

<!-- Line breaks to HTML -->
{{ bio | nl2br }}

<!-- Slugify -->
{{ title | slugify }}  <!-- "my-article-title" -->

<!-- And more in eden.templating.filters -->
```

---

## Troubleshooting

### Undefined Variables

**In Debug Mode:**
```html
<!-- Shows: [UNDEFINED: user.name] -->
```

**In Production:**
```html
<!-- Silently renders as empty string (logged as warning) -->
```

Toggle debug mode in app config or use `EdenTemplates(debug=True)`.

---

### Loop Limit Exceeded

```
<!-- EDEN: Loop iteration limit (10000) exceeded -->
```

**Solution:**
- Use pagination: `@for(item in page.items)`
- Exit early: `@break` when needed
- Pre-filter collection in controller

---

### Missing Fragments

HTMX target not rendering:

```html
<!-- Must have fragment_ prefix in block name -->
@fragment('user-list')  <!-- Creates: block fragment_user-list -->
  Content
@endfragment
```

When using HTMX: `hx-target="#user-list"` maps to `fragment_user-list` block.

---

## Quick Reference Table

| Directive | Purpose | Syntax |
|-----------|---------|--------|
| `@if` | Conditional | `@if(condition) ... @endif` |
| `@for` | Loop | `@for(item in items) ... @endfor` |
| `@while` | While loop | `@while(condition) ... @endwhile` |
| `@auth` | Auth check | `@auth ... @endauth` |
| `@admin` | Admin only | `@admin ... @endadmin` |
| `@role` | Role check | `@role('admin') ... @endrole` |
| `@can` | Permission | `@can('action') ... @endcan` |
| `@inject` | Service DI | `@inject(var, 'service')` |
| `@extends` | Inheritance | `@extends('parent.html')` |
| `@section` | Named block | `@section('name') ... @endsection` |
| `@include` | Partial | `@include('partial.html')` |
| `@component` | Component | `@component('name') ... @endcomponent` |
| `@fragment` | HTMX fragment | `@fragment('id') ... @endfragment` |
| `@csrf` | CSRF token | `@csrf` |
| `@class` | CSS classes | `@class({'active': condition})` |
| `@reactive` | WebSocket sync | `@reactive(obj) ... @endreactive` |

---

## Additional Resources

- [Eden Dependency Injection Guide](./di_guide.py)
- [Template Security](./security.md)
- [HTMX Integration Guide](./htmx.md)
- [Component Patterns](./components.md)
