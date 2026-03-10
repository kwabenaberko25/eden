# Task 6: Forms, Validation & Unified Schemas 📝

**Goal**: Collect user input securely and validate it using Eden's powerful **Unified Schema Architecture**.

Eden combines the power of **Pydantic** validation with UI metadata generation, allowing you to define a schema *once* and use it for validation, error handling, and automatically rendering HTML forms.

---

## 📋 Step 6.1: Defining the Unified Schema

Instead of defining separate Pydantic models and HTML form objects, Eden provides a unified `Schema` class. You can define validation rules (like `min_length`) alongside UI metadata (like `label` and `placeholder`) in one place using the `f()` helper.

**File**: `app/schemas/user.py`

```python
from eden.forms import Schema
from eden.db.fields import f
from pydantic import EmailStr

class UserCreateSchema(Schema):
    name: str = f(
        min_length=2, 
        max_length=100, 
        label="Full Name", 
        placeholder="e.g. Jane Doe"
    )
    email: EmailStr = f(
        label="Email Address", 
        placeholder="jane@example.com",
        widget="email"
    )
    age: int = f(
        default=None, 
        ge=18, 
        le=120, 
        label="Age (18+)",
        help_text="You must be at least 18 years old to join."
    )
```

---

## 🧩 Step 6.2: Handling Submissions Declaratively

Eden provides an elegant `@app.validate` decorator. It automatically parses the form data, validates it against your `Schema`, and injects the validated object directly into your route handler. If validation fails, it automatically re-renders your template with error messages!

**File**: `app/routes/user.py`

```python
from eden.routing import Router
from app.schemas.user import UserCreateSchema
from app.models.user import User

user_router = Router()

@user_router.get("/join")
async def join_form(request):
    """Render the signup page with an empty schema."""
    form = UserCreateSchema.as_form()
    return request.app.render("signup.html", {"form": form})

@user_router.post("/join")
@user_router.validate(UserCreateSchema, template="signup.html")
async def process_join(request, credentials: UserCreateSchema):
    """
    Handle the signup submission.
    This function ONLY runs if validation passes!
    If it fails, 'signup.html' is automatically re-rendered with errors.
    """
    # Simply create the user from the validated schema
    await User.create_from(credentials)
    
    return request.app.redirect("/users/directory")
```

---

## 🎨 Step 6.3: Rendering Forms in Templates

Now that we have our `Schema` and route, let's render the form. Eden provides powerful template directives to make this incredibly easy and clean.

**File**: `templates/signup.html`

```html
@extends("layouts/base")

@section("title", "Join the Community")

@section("content")
<div class="max-w-md mx-auto bg-slate-800 p-8 rounded-2xl shadow-xl mt-10 border border-slate-700">
    <h1 class="text-3xl font-black mb-6">Create Account</h1>

    <!-- Display massive errors if you want to handle them globally -->
    @if (form.errors) {
        <div class="p-4 mb-6 bg-red-900/50 border border-red-500 rounded-lg text-red-200">
            Please correct the errors below.
        </div>
    }

    <form method="POST" action="/users/join" class="space-y-5">
        <!-- Always include CSRF protection! -->
        @csrf

        <!-- Method 1: The Magic @render_field Directive -->
        <!-- Automatically renders the label, input, and error messages -->
        <div class="field-wrapper">
            @render_field(form['name'], class="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all")
        </div>

        <div class="field-wrapper">
            @render_field(form['email'], class="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all")
        </div>

        <!-- Method 2: Manual field rendering for ultimate control -->
        <div>
            {{ form['age'].render_label(class="block text-sm font-medium text-slate-300 mb-1") }}
            
            {{ form['age'].render(class="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all") }}
            
            @if (form['age'].help_text) {
                <p class="text-xs text-slate-500 mt-1">{{ form['age'].help_text }}</p>
            }

            <!-- Use the @error directive to show field specific errors -->
            @error("age") {
                <p class="text-sm text-red-400 mt-1">{{ message }}</p>
            }
        </div>

        <button type="submit" class="w-full py-3 bg-blue-600 hover:bg-blue-500 hover:-translate-y-0.5 transition-all text-white font-bold rounded-lg shadow-lg shadow-blue-500/30">
            Join Now
        </button>
    </form>
</div>
@endsection
```

### ✨ Premium Features Demonstrated

1. **`@csrf`**: Automatically injects a hidden CSRF token to secure your form.
2. **`@render_field`**: Renders the complete group (label, input, errors) cleanly, attaching the CSS classes you define.
3. **`@error("field_name") { ... }`**: Contextually checks if a field has an error, and injects the error text into `{{ message }}` inside the block.
4. **`Model.create_from()`**: A secure method on Eden Models to automatically extract and create an instance using ONLY the fields explicitly defined on your Schema, preventing mass-assignment vulnerabilities.

---

### **Next Task**: [Securing the Application](./task7_security.md)
