# Task 6: Forms, Validation & Unified Schemas 📝

**Goal**: Collect user input securely and validate it using Eden's powerful **Unified Schema Architecture**.

Eden combines the power of **Pydantic** validation with UI metadata generation, allowing you to define a schema *once* and use it for validation, error handling, and automatically rendering HTML forms.

---

## 📋 Step 6.1: Defining the Unified Schema

Instead of defining separate Pydantic models and HTML form objects, Eden provides a unified `Schema` class. You can define validation rules (like `min_length`) alongside UI metadata (like `label` and `placeholder`) in one place using the `field()` helper.

**File**: `app/schemas/user.py`

```python
from eden.forms import Schema, field, EmailStr

class UserCreateSchema(Schema):
    name: str = field(
        min_length=2, 
        max_length=100, 
        label="Full Name", 
        placeholder="e.g. Jane Doe",
        pattern=r"^[A-Za-z\s]+$"
    )
    email: EmailStr = field(
        label="Email Address", 
        placeholder="jane@example.com",
        widget="email"
    )
    age: int = field(
        default=None, 
        ge=18, 
        le=120, 
        label="Age (18+)",
        help_text="You must be at least 18 years old to join."
    )
```

> [!TIP]
> Use `field()` (or the shorter `v()`) for form schemas, and `f()` for database models. This prevents naming collisions and keeps your code clean.

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
    return request.render("signup.html", {"form": form})

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

For fine-grained field customization (CSS classes, HTML attributes, widget types), see the [FormField API Reference](../guides/formfield-api.md). It documents all rendering methods like `add_class()`, `as_textarea()`, `as_select()`, and `as_file()` for advanced field styling and behavior.

**File**: `templates/signup.html`

```html
@extends("layouts/base")

@section("title") { Join the Community }

@section("content") {
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
            @span(form['age'].render_label(class="block text-sm font-medium text-slate-300 mb-1"))
            
            @span(form['age'].render(class="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all"))
            
            @if (form['age'].help_text) {
                <p class="text-xs text-slate-500 mt-1">@span(form['age'].help_text)</p>
            }

            <!-- Use the @error directive to show field specific errors -->
            @error("age") {
                <p class="text-sm text-red-400 mt-1">@span(message)</p>
            }
        </div>

        <button type="submit" class="w-full py-3 bg-blue-600 hover:bg-blue-500 hover:-translate-y-0.5 transition-all text-white font-bold rounded-lg shadow-lg shadow-blue-500/30">
            Join Now
        </button>
    </form>
</div>
}
```

### ✨ Premium Features Demonstrated

1. **`@csrf`**: Automatically injects a hidden CSRF token to secure your form.
2. **`@render_field`**: Renders the complete group (label, input, errors) cleanly, attaching the CSS classes you define.
3. **`@error("field_name") { ... }`**: Contextually checks if a field has an error, and injects the error text into `@span(message)` inside the block.
4. **`Model.create_from()`**: A secure method on Eden Models to automatically extract and create an instance using ONLY the fields explicitly defined on your Schema, preventing mass-assignment vulnerabilities.

---

## Validation

## 🔐 Step 6.4: Complex Validation with Validators

For validation logic that spans multiple fields, use Pydantic's `@field_validator`:

```python
from pydantic import field_validator

class PasswordResetSchema(Schema):
    new_password: str = field(
        min_length=8,
        label="New Password",
        help_text="At least 8 characters required"
    )
    confirm_password: str = field(
        label="Confirm Password"
    )
    current_password: str = field(
        widget="password",
        label="Current Password"
    )
    
    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        """Ensure password confirmation matches."""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v
```

---

## 📋 Step 6.5: Dynamic Forms with Conditional Fields

Create forms that change based on user input:

```python
class PaymentSchema(Schema):
    payment_method: str = field(
        label="Payment Method",
        widget="select",
        choices=[
            ("card", "Credit Card"),
            ("bank", "Bank Transfer"),
            ("paypal", "PayPal")
        ]
    )
    # These fields only show if payment_method is 'card'
    card_number: str | None = field(default=None, label="Card Number")
    expiry: str | None = field(default=None, label="Expiry (MM/YY)")
    cvv: str | None = field(default=None, label="CVV")
```

In your template:
```html
<div class="form-group">
    @render_field(form['payment_method'])
</div>

<!-- Only show card fields if payment method is 'card' -->
<div id="card-fields" style="display:none;" class="form-group">
    @render_field(form['card_number'])
    @render_field(form['expiry'])
    @render_field(form['cvv'])
</div>

<script>
document.getElementById('payment-method').addEventListener('change', (e) => {
    document.getElementById('card-fields').style.display = 
        e.target.value === 'card' ? 'block' : 'none';
});
</script>
```

---

## File Uploads

## 📁 Step 6.6: File Upload Handling

Handle file uploads securely with validation:

```python
from eden.forms import Schema, FileField

class DocumentUploadSchema(Schema):
    title: str = field(label="Document Title", max_length=100)
    document: FileField = field(
        label="Upload PDF",
        accept=".pdf",
        max_size=5 * 1024 * 1024  # 5MB limit
    )
    is_public: bool = field(default=False, label="Make public")

# In your route:
@document_router.post("/upload")
@document_router.validate(DocumentUploadSchema, template="upload.html")
async def handle_upload(request, data: DocumentUploadSchema):
    """Upload and store a document."""
    file = data.document
    
    # Save to storage
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Create database record
    doc = await Document.create(
        title=data.title,
        file_path=file_path,
        is_public=data.is_public,
        user_id=request.user.id
    )
    
    return {"message": "Document uploaded successfully", "doc_id": doc.id}
```

---

## ✨ Step 6.7: Multi-Step Forms (Wizards)

Build complex forms that span multiple pages:

```python
# Step 1: Basic Info
class OnboardingStep1(Schema):
    first_name: str = field(label="First Name")
    last_name: str = field(label="Last Name")

# Step 2: Company Info
class OnboardingStep2(Schema):
    company_name: str = field(label="Company Name")
    industry: str = field(label="Industry")

# Routes
@onboarding_router.get("/step1")
async def step1_form(request):
    form = OnboardingStep1.as_form()
    return request.render("onboarding/step1.html", {"form": form})

@onboarding_router.post("/step1")
@onboarding_router.validate(OnboardingStep1, template="onboarding/step1.html")
async def step1_submit(request, data: OnboardingStep1):
    # Store in session temporarily
    request.session['onboarding_step1'] = data.dict()
    return request.app.redirect("/onboarding/step2")

@onboarding_router.get("/step2")
async def step2_form(request):
    form = OnboardingStep2.as_form()
    # Pre-populate from previous step if needed
    return request.render("onboarding/step2.html", {"form": form})

@onboarding_router.post("/step2")
@onboarding_router.validate(OnboardingStep2, template="onboarding/step2.html")
async def step2_submit(request, data: OnboardingStep2):
    # Combine with step 1 data
    step1_data = request.session.get('onboarding_step1', {})
    combined = {**step1_data, **data.dict()}
    
    # Create user with all data
    await User.create(**combined)
    request.session.clear()
    
    return request.app.redirect("/dashboard")
```

---

### **Next Task**: [Securing the Application](./task7_security.md)
