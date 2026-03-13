# Eden @Directives - Troubleshooting Guide 🔧

Comprehensive troubleshooting for Eden templating directives.

---

## Quick Diagnosis

**Is an @directive not working?**

1. Check the [Directive Syntax](#directive-syntax) table below
2. Verify [Route Names](templating.md#url-routing-and-navigation) if using @url or @active_link
3. Enable [Debug Logging](#enable-debug-logging)
4. Check the [Common Issues](#common-issues) section

---

## Directive Syntax

| Directive | Correct Syntax | ✓ Working | ✗ Wrong |
|-----------|---|---|---|
| @if | `@if (condition) { }` | `@if (age > 18) { }` | `@if condition { }` or `@if(age > 18){}`  |
| @for | `@for (item in items) { }` | `@for (x in list) { }` | `@for item in list { }` |
| @auth | `@auth { }` | `@auth { <p>Hi</p> }` | `@auth()` or `@auth` (no braces) |
| @csrf | `@csrf` | `<form> @csrf </form>` | `@csrf()` (don't add parens) |
| @url | `@url('route')` | `@url('posts:show')` | `@url(posts.show)` (quotes required) |
| @active_link | `@active_link('route', 'class')` | `@active_link('home', 'active')` | `@active_link('home')` (needs class) |
| @checked | `@checked(condition)` | `@checked(user.agrees)` | `@if (checked)` — use @checked instead! |
| @let | `@let var = value` | `@let total = 42` | `@let(var = 42)` (no parens) |
| @component | `@component('name') { }` | `@component('card') { }` | `@component card { }` |

---

## Common Issues

### Issue 1: @active_link not highlighting

**Symptom:** Navigation links never get the active class, even when on that route.

**Diagnosis Steps:**

1. **Verify the route name exists:**
   ```python
   # ✓ Correct: route has a name

   @app.get("/dashboard", name="dashboard")
   def dashboard():
       pass
   
   # ✗ Wrong: route has no name

   @app.get("/dashboard")
   def dashboard():
       pass
   ```

2. **Check exact route name match:**
   ```html
   <!-- ✓ Matches route name="dashboard" -->

   @active_link('dashboard', 'active')
   
   <!-- ✗ Doesn't match (typo) -->

   @active_link('dashbaord', 'active')
   
   <!-- ✗ Doesn't match (full path) -->

   @active_link('/dashboard', 'active')
   ```

3. **For namespaced routes, use `:` syntax:**
   ```python
   # Python route registration

   @app.get("/admin/users", name="admin:users")
   
   # Template - works!

   @active_link('admin:users', 'active')
   ```

4. **Enable debug logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

   ```

   Look for messages like:
   ```

   eden.templating - DEBUG - is_active: Error resolving route 'dashboard': ...

   ```

5. **Test path resolution in template:**
   ```html
   <!-- Debug output -->

   <div style="background: yellow; padding: 10px;">
     Current path: {{ request.url.path }} <br>
     Route URL: {{ request.url_for('dashboard') }} <br>
     Is active: {{ is_active(request, 'dashboard') }} <br>
   </div>
   ```

**Solutions:**

- Fix route name: Ensure route has `name="..."` parameter

- Fix route reference: Use exact name from route definition

- Check URL formation: Verify `request.url_for()` returns valid URL

- Trim paths: @active_link handles trailing slashes automatically

---

### Issue 2: @active_link with wildcard not matching

**Symptom:** `@active_link('admin:*', 'active')` doesn't highlight on admin pages.

**Root Cause:** Wildcard routes weren't supported in older versions. This is now fixed!

**Verify it's working:**

```html
<!-- Route structure:

    /admin/users (admin:users route)
    /admin/settings (admin:settings route)
    Current URL: /admin/users
-->

<!-- This should highlight ✓ -->

<a href="@url('admin:index')" class="@active_link('admin:*', 'active')">
    Admin
</a>

```

**Troubleshooting Wildcard:**

1. At least one route matching the prefix must exist:
   ```python
   # ✓ At least one admin route must exist

   @app.get("/admin/dashboard", name="admin:index")
   @app.get("/admin/users", name="admin:users")
   @app.get("/admin/settings", name="admin:settings")
   ```

2. The wildcard pattern must match the namespace:
   ```html
   <!-- Works if you have admin:* routes -->

   @active_link('admin:*', 'highlight')
   
   <!-- Doesn't work - no 'blog:*' routes -->

   @active_link('blog:*', 'highlight')
   ```

3. Debug wildcard matching:
   ```html
   <!-- Check what path is being matched -->

   Path: {{ request.url.path }}<br>
   Base URL for 'admin:*': {{ request.url_for('admin:index') }}<br>
   Active: {{ is_active(request, 'admin:*') }}
   ```

---

### Issue 3: @for loop not working

**Symptom:** Loop content doesn't render or throws error.

**Common Mistake 1: Wrong loop syntax**

```html
<!-- ✗ Wrong -->

@for item in items { }
@for (item in items) { }  <!-- Missing loop arrow -->

<!-- ✓ Correct -->

@for (item in items) { }

```

**Common Mistake 2: $loop not available**

```html
<!-- ✓ Correct - use $loop inside @for -->

@for (item in items) {
    {{ $loop.index }}: {{ item.name }}
}

<!-- ✗ Wrong - $loop only works inside @for -->

@for (item in items) { }
<p>{{ $loop.index }}</p>

```

**Common Mistake 3: Empty collection**

```html
<!-- Renders nothing if items is empty, use @empty -->

@for (item in items) {
    <li>{{ item }}</li>
} @empty {
    <li>No items</li>
}

```

**Debugging:**

```html
<!-- Check if collection has items -->

@if (items | length > 0) {
    @for (item in items) { ... }
} @else {
    Collection is empty
}

<!-- Check item structure -->

@for (item in items) {
    {{ @dump(item) }}
}

```

---

### Issue 4: @csrf token not appearing

**Symptom:** `@csrf` doesn't emit hidden input field.

**Check:**

```html
<!-- ✗ Wrong - needs to be in form -->

<div>@csrf</div>

<!-- ✓ Correct - in form -->

<form method="POST">
    @csrf
    <!-- other fields -->

</form>

<!-- ✓ Also correct - @csrf just renders the input -->

@csrf

```

**Verify CSRF is working:**

1. Check request session has CSRF token:
   ```python
   print(request.session.get('eden_csrf_token'))
   ```

2. Verify token in rendered HTML:
   ```html
   <!-- View source - should see: -->

   <input type="hidden" name="csrf_token" value="abc123...">
   ```

3. Check form validation:
   ```python
   # In route handler

   if not csrf_token_valid(request):
       raise CSRFTokenError("Token mismatch")
   ```

---

### Issue 5: @checked, @selected, @disabled not working

**Symptom:** These conditional attributes never render.

**Check condition returns boolean:**

```html
<!-- ✓ Correct - evaluates to True/False -->

<input @checked(user.agrees == True)>
<input @checked(user.role == 'admin')>
<select>
    <option @selected(item.id == selected_id)>
</select>

<!-- ✗ Wrong - doesn't evaluate to boolean -->

<input @checked(user)>             <!-- Is user truthy? -->

<input @selected(item.name)>       <!-- Is name truthy? -->

```

**Template debugging:**

```html
<!-- Check condition value -->

Condition: {{ user.role == 'admin' }} (should be True or False) <br>

<!-- Debug with dump -->

@dump(user)

```

**Verify in rendered HTML:**

```html
<!-- Do a "View Source" and look for: -->

<!-- ✓ When true -->

<input type="checkbox" checked>

<!-- ✓ When false -->

<input type="checkbox">

<!-- ✗ If seeing this, condition is wrong -->

<input type="checkbox">  <!-- with no @checked applied -->

```

---

### Issue 6: @auth/@guest not showing/hiding content

**Symptom:** Content shows when it shouldn't, or doesn't show when it should.

**Check user authentication status:**

```python

# In your route or template

print(f"User: {request.user}")
print(f"Authenticated: {request.user.is_authenticated if request.user else False}")

```

**Debug in template:**

```html
<!-- Check current auth state -->

User: {{ request.user }} <br>
Is Auth: {{ request.user.is_authenticated if request.user else 'None' }} <br>

<!-- Use conditional instead of @auth/@guest to debug -->

@if (request.user and request.user.is_authenticated) {
    <p>You are logged in!</p>
} @else {
    <p>You are NOT logged in</p>
}

```

**Common issue: Session not persisted**

```python

# ✗ Wrong - losing session

response = HTMLResponse(template.render(request=request))
return response

# ✓ Correct - preserve session

response = templates.TemplateResponse("template.html", context)
return response

```

---

### Issue 7: @for with dictionary/object

**Symptom:** Loop doesn't work with dict or objects, only lists.

**For dictionaries:**

```html
<!-- ✗ Wrong -->

@for (item in dict) { {{ item }} }

<!-- ✓ Correct - use .items() -->

@for (key, value in dict.items) {
    {{ key }}: {{ value }}
}

<!-- Alternative - use values() -->

@for (value in dict.values) {
    {{ value }}
}

```

**For objects:**

```html
<!-- ✗ Wrong -->

@for (prop in user) { }

<!-- ✓ Correct - convert to dict first -->

@for (key, value in user.__dict__.items) {
    {{ key }}: {{ value }}
}

<!-- Or use specific attributes -->

@for (post in user.posts) {
    {{ post.title }}
}

```

---

## Enable Debug Logging

### Setup Logging

```python
import logging

# Detailed logging for debugging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'

)

# Or just for Eden

logger = logging.getLogger("eden")
logger.setLevel(logging.DEBUG)

```

### Run with Debug

```bash

# Set debug environment

export EDEN_DEBUG=1
python your_app.py

# Or in Python

import os
os.environ['EDEN_DEBUG'] = '1'

```

### View Debug Output

Look for messages like:

```

eden.templating - DEBUG - is_active: Error resolving route 'xyz': No route named 'xyz'

eden.middleware - DEBUG - Request: GET /dashboard

eden.orm - DEBUG - Database query: SELECT * FROM users WHERE id = 1

```

---

## Directive Testing

### Test @active_link Manually

```python

# In Python interpreter

from eden.context import get_request

request = get_request()  # or mock it

result = request.url_for('dashboard')  # Should return URL

print(result)

```

### Test Directive Conversion

```python
from eden.templating import EdenDirectivesExtension

# Create extension

ext = EdenDirectivesExtension(env=None)

# Test preprocessing

html = '@active_link("dashboard", "active")'
result = ext.preprocess(html, None)
print(result)  # Should show converted Jinja2

```

---

## Validate Syntax

### Use a Validator

```bash

# Validate HTML with Eden directives

python -c "
from pathlib import Path
from eden.templating import EdenDirectivesExtension

content = Path('template.html').read_text()
ext = EdenDirectivesExtension()
try:
    result = ext.preprocess(content, None)
    print('✓ Valid')
except Exception as e:
    print(f'✗ Error: {e}')
"

```

---

## Performance Issues

### Slow Template Rendering

**Check for:**

1. **Expensive queries in templates:**
   ```html
   <!-- ✗ BAD - query per item -->

   @for (user in users) {
       {{ user.organization.name }}  <!-- Triggers DB query! -->

   }
   
   <!-- ✓ GOOD - pre-fetch related data -->

   @for (user in users) {
       {{ user.organization.name }}  <!-- org already loaded -->

   }
   ```

2. **Deep nesting:**
   ```html
   <!-- ✗ Many nested loops -->

   @for (a in list_a) {
       @for (b in list_b) {
           @for (c in list_c) {
               {{ c }}
           }
       }
   }
   ```

3. **Large collections:**
   ```html
   <!-- ✗ Rendering 10,000 items -->

   @for (item in huge_list) { {{ item }} }
   
   <!-- ✓ Paginate -->

   @for (item in paginated_list) { {{ item }} }
   <!-- [1] [2] [3] ... [100] -->

   ```

---

## Version Compatibility

### Check Eden Version

```bash
python -c "import eden; print(eden.__version__)"

```

### Wildcard Support

- **Wildcard @active_link added in:** March 2026

- If using older version, update:

  ```bash
  pip install --upgrade eden
  ```

---

## Still Not Working?

### 1. Clear Cache

```python

# Clear template cache

import jinja2
env.cache.clear()

# Or restart application

```

### 2. Verify Installation

```bash

# Check Eden is installed

python -c "import eden; print(eden.__file__)"

# Verify templating module

python -c "from eden.templating import EdenDirectivesExtension; print('✓')"

```

### 3. Check File Encoding

```python

# Some templates may have encoding issues

content = Path('template.html').read_text(encoding='utf-8')

```

### 4. Enable Traceback

```python

# Get full error details

import traceback

try:
    # template rendering

except Exception:
    traceback.print_exc()  # Full error with line numbers

```

### 5. Minimal Reproduction

Create smallest possible example:

```html
<!-- min.html -->

@if (True) { Works! }

```

```python

# min.py

from eden import Eden
app = Eden(__name__)

@app.get("/")
def home(request):
    return app.templates.TemplateResponse("min.html", {})

# Run and test

```

---

## Getting Help

1. **Check the docs:**
   - [Directives Guide](DIRECTIVES_USAGE_GUIDE.md)

   - [Templating Basics](templating.md)

2. **Search existing issues:**
   - GitHub issues

   - Eden documentation FAQ

3. **Debug information to provide:**
   ```python
   import eden
   import logging
   
   print(f"Python: {__import__('sys').version}")
   print(f"Eden: {eden.__version__}")
   print(f"Logging configured: {logging.getLogger('eden').level}")
   
   # Your template

   print(open('template.html').read())
   
   # Your route

   # (paste the handler that renders the template)

   ```

---

**Happy templating! 🚀**

If you still need help:

- Check the [Directives Usage Guide](DIRECTIVES_USAGE_GUIDE.md) for examples

- Review the [Templating Documentation](templating.md) for concepts

- Enable debug logging to see what's happening
