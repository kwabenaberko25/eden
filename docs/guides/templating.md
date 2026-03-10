# Modern Templating Architecture 📝

Eden replaces the verbose Jinja2 tags with a clean, brace-based `@directive` syntax. It is designed to be expressive, readable, and fully line-preserving.

## The `@` Syntax

Unlike traditional templates that use `{% ... %}`, Eden uses `@` followed by the directive name and optional parentheses for arguments.

```html
@if (user.is_authenticated) {
    <p>Hello, {{ user.name }}!</p>
}
```

---

## Control Flow 🎢

### Loops

```html
@for (item in items) {
    <li>{{ item }}</li>
} @empty {
    <p>Nothing to show.</p>
}
```

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
| | `@method(verb)` | `verb`: HTTP Method | Spoof `PUT`, `PATCH`, `DELETE`. |
| | `@old(key)` | `key`: Field name | Returns previous input value. |
| | `@error(key)` | `key`: Field name | Block for validation errors. |
| **Assets** | `@css(path)` | `path`: String | Inject stylesheet. |
| | `@js(path)` | `path`: String | Inject script. |
| | `@vite(list)` | `list`: List[str] | Vite manifest bundle loader. |
| **Logic** | `@let var = val` | `var`, `val` | Inline variable assignment. |
| | `@json(data)` | `data`: Any | Outputs safe JSON string. |
| | `@dump(obj)` | `obj`: Any | Pretty-prints object for debugging. |


```html
@while (count > 0) {
    <span>{{ count }}</span>
}
```

---

## Layouts & Components 🧱

### Inheritance

```html
@extends("layouts/base")

@section("content") {
    <h1>Product Page</h1>
}
```

### Reusable Components
Components allow you to encapsulate both logic and UI.

```html
@component("ui/card", title="Profile", elevation="xl") {
    @slot("header") {
        <img src="/avatar.png">
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
    
    <div class="space-y-4">
        <label>Email</label>
        <input type="text" name="email" value="@old('email')" 
               class="w-full rounded bg-slate-800 border-slate-700">
        
        @error("email") {
            <span class="text-xs text-emerald-500">{{ message }}</span>
        }
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
async def list_users():
    users = await User.all()
    # Renders ONLY the <ul>, not the <h1> or layout!
    return render_template("index.html", users=users, fragment="user-list")
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
| `time_ago` | Human-readable time. | `{{ task.created_at\|time_ago }}` |
| `money` | Currency formatting. | `{{ 1500\|money }}` |
| `slugify` | URL slug generator. | `{{ "My Title"\|slugify }}` |
| `truncate(n)` | Truncate to $n$ chars. | `{{ bio\|truncate(20) }}` |
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
