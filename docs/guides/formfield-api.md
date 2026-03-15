# FormField API Reference & Customization

The `FormField` class provides fluent methods for rendering individual form fields with full control over HTML attributes, CSS classes, widget type, and error styling.

> **See main guide**: [Forms, Validation & Schemas](../tutorial/task6_forms.md)

---

## FormField Methods

### CSS Class Management

**Method**: `add_class(css_class: str) -> FormField`  
Add a CSS class to the field (fluent - returns new FormField).

```python
# Example: Add Bootstrap classes
form['email'].add_class('form-control').add_class('is-valid')
# Renders: <input class="form-control is-valid" ...>
```

**Method**: `remove_class(css_class: str) -> FormField`  
Remove a CSS class.

```python
form['password'].remove_class('hidden')
```

**Method**: `add_error_class(css_class: str) -> FormField`  
Conditionally add class only if field has validation error.

```python
# Only applies class if form['email'].error is set
form['email'].add_error_class('border-red-500')
```

### HTML Attribute Management

**Method**: `attr(key: str, value: str) -> FormField`  
Set an HTML attribute (fluent).

```python
form['username'].attr('data-type', 'alphanumeric')
form['age'].attr('min', '18').attr('max', '120')
# Renders: <input data-type="alphanumeric" min="18" max="120" ...>
```

**Method**: `set_attr(key: str, value: str) -> FormField`  
Alias for `attr()`.

```python
form['status'].set_attr('aria-label', 'User status')
```

**Method**: `append_attr(key: str, value: str) -> FormField`  
Append to an existing attribute (space-separated). Useful for class-like attributes.

```python
form['name'].append_attr('class', 'custom-input')
form['name'].append_attr('data-tags', 'important')
# Renders: <input class="custom-input" data-tags="important" ...>
```

**Method**: `remove_attr(key: str) -> FormField`  
Remove an HTML attribute.

```python
form['hidden_field'].remove_attr('required')
```

**Method**: `add_error_attr(key: str, value: str) -> FormField`  
Conditionally add attribute only if field has error.

```python
form['email'].add_error_attr('aria-invalid', 'true')
```

---

## Widget Rendering Methods

**Method**: `render(**kwargs) -> str`  
Render the field using its widget type. Auto-dispatches to correct widget method.

```python
# Auto-detects widget type and renders appropriately
html = form['email'].render()

# Pass extra HTML attributes
html = form['email'].render(placeholder='user@example.com', tabindex='1')
```

**Method**: `render_label() -> str`  
Render just the label HTML.

```python
html = form['email'].render_label()
# Output: <label for="id_email">Email</label>
```

### Input Widget

Default widget. Renders `<input>` tag.

```python
# Basic text input
form['name'].render()
# <input type="text" name="name" id="id_name" value="..." />

# Email field
form['email'].render()  # Uses widget="email"
# <input type="email" name="email" id="id_email" value="..." />

# Number field
form['age'].render()  # Uses widget="number"
# <input type="number" name="age" id="id_age" value="..." />
```

### Textarea Widget

Renders `<textarea>` tag.

```python
form['bio'].as_textarea()
# <textarea name="bio" id="id_bio">current content</textarea>

# With rows/cols
form['bio'].as_textarea(rows='5', cols='40')
```

### Select Widget

Renders `<select>` with options.

```python
choices = [
    ('us', 'United States'),
    ('ca', 'Canada'),
    ('mx', 'Mexico'),
]

form['country'].as_select(choices)
# <select name="country" id="id_country">
#   <option value="us">United States</option>
#   <option value="ca" selected>Canada</option>
#   <option value="mx">Mexico</option>
# </select>
```

### File Widget

Renders `<input type="file">`.

```python
# Basic file upload
form['avatar'].as_file()
# <input type="file" name="avatar" id="id_avatar" />

# Image files only
form['photo'].as_file(accept='image/*')

# Multiple files with filter
form['documents'].as_file(accept='.pdf,.docx', multiple=True)
# <input type="file" name="documents" id="id_documents" accept=".pdf,.docx" multiple />

# Specific MIME types
form['backup'].as_file(accept='application/zip')
```

### Hidden Widget

```python
form['csrf_token'].as_hidden()
# <input type="hidden" name="csrf_token" value="..." />
```

---

## Complete Examples

### Example 1: Email Field with Error Styling

```python
@app.get("/signup")
async def signup_form(request):
    schema = UserSchema()
    form = schema.as_form()
    return request.render("signup.html", {"form": form})

@app.post("/signup")
async def handle_signup(request):
    form = await BaseForm.from_request(UserSchema, request)
    
    if not form.is_valid():
        # Re-render with errors
        return request.render(
            "signup.html", 
            {"form": form},
            status=400
        )
    
    # In template:
    # {{ form['email'].add_error_class('border-red-500').render() }}
```

### Example 2: Complex Form with Multiple Widgets

```python
# In template
<form method="POST">
    @csrf
    
    <!-- Text input with custom classes -->
    <div class="mb-4">
        @span(form['name'].render_label())
        @span(form['name']
            .add_class('form-control')
            .attr('placeholder', 'Full name')
            .render()
        )
    </div>
    
    <!-- Email with error styling -->
    <div class="mb-4">
        @span(form['email'].render_label())
        @span(form['email']
            .add_class('form-control')
            .add_error_class('is-invalid')
            .attr('type', 'email')
            .render()
        )
        @if (form['email'].error) {
            <div class="invalid-feedback">@span(form['email'].error)</div>
        }
    </div>
    
    <!-- Textarea -->
    <div class="mb-4">
        @span(form['bio'].render_label())
        @span(form['bio']
            .add_class('form-control')
            .as_textarea(rows='4')
        )
    </div>
    
    <!-- Select dropdown -->
    <div class="mb-4">
        @span(form['country'].render_label())
        @span(form['country']
            .add_class('form-select')
            .as_select([
                ('us', 'USA'),
                ('ca', 'Canada'),
                ('mx', 'Mexico'),
            ])
        )
    </div>
    
    <!-- File upload -->
    <div class="mb-4">
        @span(form['avatar'].render_label())
        @span(form['avatar']
            .as_file(accept='image/*')
            .attr('class', 'form-control')
        )
    </div>
    
    <button type="submit" class="btn btn-primary">Sign Up</button>
</form>
```

### Example 3: Conditional Attributes

```python
# Dynamic rendering based on conditions
def render_field_smart(form, field_name, required=False, disabled=False):
    field = form[field_name]
    
    # Add required marker
    if required:
        field = field.add_class('required')
    
    # Add disabled state
    if disabled:
        field = field.attr('disabled', 'disabled')
    
    # Add error styling
    if field.error:
        field = field.add_error_class('error-field')
    
    return field.render()

# Usage in template
@span(render_field_smart(form, 'email', required=True))
@span(render_field_smart(form, 'newsletter', disabled=True))
```

---

## Fluent Chain Examples

All methods return a `FormField` instance, so you can chain them:

```python
# Original field
field = form['username']

# Chain multiple operations
html = field \
    .add_class('form-control') \
    .add_class('large') \
    .attr('placeholder', 'username') \
    .attr('minlength', '3') \
    .add_error_class('border-red-500') \
    .render()
```

In templates using template syntax:

```html
<!-- Chain in template rendering -->
@span(form['email']
    .add_class('input-large')
    .attr('autocomplete', 'email')
    .add_error_class('has-error')
    .render()
)

<!-- Or with method calls on separate lines for readability -->
@span(
    form['password']
        .add_class('input-password')
        .attr('autocomplete', 'current-password')
        .render()
)
```

---

## File Upload Details

### UploadedFile Class

When handling file uploads, files are wrapped in the `UploadedFile` class:

```python
from eden.forms import UploadedFile

# In request handler
form = await BaseForm.from_multipart(UserSchema, request)

if form.is_valid():
    # Access uploaded files
    avatar: UploadedFile = form.files.get('avatar')
    
    if avatar:
        # Properties
        print(avatar.filename)      # 'profile.png'
        print(avatar.content_type)  # 'image/png'
        print(avatar.size)          # 2048 (bytes)
        print(avatar.extension)     # '.png'
        print(avatar.data)          # bytes content
        
        # Save to storage
        from eden.storage import storage
        
        path = await storage.save(
            f"avatars/{avatar.filename}",
            avatar.data
        )
```

### Multiple File Upload

```python
form = await BaseForm.from_multipart(DocumentSchema, request)

if form.is_valid():
    # Multiple files stored in same field
    documents = form.files.getlist('files')
    
    for doc in documents:
        # Process each file
        await storage.save(f"uploads/{doc.filename}", doc.data)
```

### Accept Filters in HTML

```python
# Image files only
form['photo'].as_file(accept='image/*')
# Renders: accept="image/*"

# Specific extensions
form['resume'].as_file(accept='.pdf,.doc,.docx')

# By MIME type
form['backup'].as_file(accept='application/zip,application/x-gzip')

# All spreadsheets
form['data'].as_file(accept='.xls,.xlsx,.csv')
```

---

## API Quick Reference Table

| Method | Arguments | Returns | Use Case |
|--------|-----------|---------|----------|
| `add_class()` | `css_class: str` | `FormField` | Add CSS class |
| `remove_class()` | `css_class: str` | `FormField` | Remove CSS class |
| `add_error_class()` | `css_class: str` | `FormField` | Conditionally add error class |
| `attr()` | `key: str, value: str` | `FormField` | Set HTML attribute |
| `set_attr()` | `key: str, value: str` | `FormField` | Alias for attr() |
| `append_attr()` | `key: str, value: str` | `FormField` | Append to attribute |
| `remove_attr()` | `key: str` | `FormField` | Remove HTML attribute |
| `add_error_attr()` | `key: str, value: str` | `FormField` | Conditionally add attribute |
| `render()` | `**kwargs` | `str` | Render field HTML |
| `render_label()` | none | `str` | Render label only |
| `as_textarea()` | `**kwargs` | `str` | Render textarea |
| `as_select()` | `choices: List[tuple]` | `str` | Render select dropdown |
| `as_file()` | `accept: str, multiple: bool` | `str` | Render file input |
| `as_hidden()` | `**kwargs` | `str` | Render hidden input |

---

## See Also

- [Forms Guide](../tutorial/task6_forms.md) - Schema definition and validation
- [Validation](../tutorial/task6_forms.md#validation) - Error handling
- [Template Directives](templating.md) - @render_field, @error
- [File Upload Handler](../tutorial/task6_forms.md#file-uploads) - Complete example
