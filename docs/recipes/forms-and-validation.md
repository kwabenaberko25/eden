# Recipe: The Model-to-Form Bridge (Productivity at Scale)

In traditional web frameworks, you often define your data structure in your Database and then again in your Form library. This results in **Dual-Maintenance Debt**.

In Eden, your **Model IS your Form**. We use our **SchemaInferenceEngine** to automatically derive Pydantic schemas and Starlette-ready forms from your SQLAlchemy models.

---

## 1. Quick Start: `Model.as_form()`

Need a form for a model? Just call `as_form()`.

```python
from eden.db import Model, StringField, IntField

class Task(Model):
    title: str = StringField(max_length=200, label="Task Name", help_text="Keep it short!")
    priority: int = IntField(default=1, choices=[(1, 'Low'), (2, 'Med'), (3, 'High')])

# 1. Initialize the form from incoming request data
form = Task.as_form(request.data)

# 2. Validate it
if await form.validate():
    # Save the data directly
    task = await Task.create(**form.data)
else:
    # return the form with errors to your template
    return render_template("task_form.html", form=form)
```

---

## 2. Refining Your Forms

You can customize which fields from the model are included or excluded from the generated form.

```python
# Create a form that only includes 'title', excluding everything else (like id, created_at)
form = Task.as_form(request.data, include=['title'])

# Alternatively, exclude sensitive fields
form = User.as_form(request.data, exclude=['is_superuser', 'hashed_password'])
```

---

## 3. Custom Metadata (The `field()` Helper)

Eden's database fields (like `StringField`, `IntField`, `FileField`) allow you to attach UI-specific metadata that the form system will automatically respect.

```python
from eden.db import StringField, PasswordField, EmailField

class Profile(Model):
    email: str = EmailField(placeholder="user@example.com")
    bio: str = StringField(widget="textarea", max_length=500)
    password: str = PasswordField(label="Enter a strong password")
```

### Supported Metadata

- `label`: Human-readable field name.
- `help_text`: Instructions for the user.
- `placeholder`: Input placeholder.
- `widget`: The UI component to use (e.g., `textarea`, `checkbox`, `select`).

---

## 4. Automatic Validation Integration

Since Eden forms are backed by **Pydantic**, you get high-fidelity validation errors that are easy to display in your UI.

```python
if not await form.validate():
    for field_name, error in form.errors.items():
        print(f"Field {field_name} failed: {error.message}")
```

### Form Features

- **HTMX Ready**: Designed to work seamlessly with asynchronous form submissions.
- **CSRF Protected**: Every form automatically includes a hidden CSRF token field.
- **File Uploads**: `FileField` integration with progress support.

---

## 5. Advanced Dynamic Schemas

For complex workflows, you may need a form that doesn't map 1:1 to a single model. Eden allows you to merge multiple models into a single form context.

```python
# Create a unified form from User and Profile models
form = Form.from_models([User, Profile], data=request.data)

if await form.validate():
    # Eden handles splitting data back to the correct models
    user_data, profile_data = form.split()
    await User.create(**user_data)
    await Profile.create(**profile_data)
```

---

## 🚀 HTMX Auto-Partial Rendering

Eden forms are designed for the modern web. By simply passing the `partial=True` flag to your template, Eden will only render the form fields that have validation errors, allowing for ultra-fast HTMX updates.

```html
<!-- task_form.html -->
<form hx-post="/tasks" hx-target="this" hx-swap="outerHTML">
    @form(form, partial=True)
</form>
```

---

**Next: [Storage & File Management](../guides/storage.md) →**

