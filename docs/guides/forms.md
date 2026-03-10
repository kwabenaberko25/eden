# Forms & Validation 📝

Eden's form system is centered around a **Unified Schema** architecture. By combining **Pydantic v2** validation with Eden's UI metadata, you can define your data structure, validation rules, and HTML rendering logic in a single, declarative place.

---

## 🏗️ The Unified Schema

The `Schema` class is the heart of Eden's form system. It inherits from Pydantic's `BaseModel` but adds powerful form-specific capabilities like automatic request parsing and UI metadata inheritance.

### Basic Usage

```python
from eden import Schema, f
from pydantic import EmailStr

class SignupSchema(Schema):
    email: str = f(max_length=255, widget="email", label="Email Address")
    password: str = f(min_length=8, widget="password")
    bio: str | None = f(widget="textarea", placeholder="Tell us about yourself...")

# In your route
@app.get("/signup")
async def signup_get():
    # Create an empty form from the schema
    form = SignupSchema.as_form()
    return app.render("signup.html", form=form)
```

### Automatic Validation with `@app.validate`

The most ergonomic way to handle forms is using the `@app.validate` decorator. It automatically parses the request (JSON or Form data), validates it against the schema, and injects the result into your handler.

```python
@app.post("/signup")
@app.validate(SignupSchema, template="signup.html")
async def signup_post(credentials: SignupSchema):
    # This block ONLY runs if validation passes.
    # If it fails, Eden automatically re-renders 'signup.html' with errors.
    
    user = await User.create_from(credentials)
    return redirect("/dashboard")
```

### 🧬 Model-Based Schemas

Eden allows you to derive schemas directly from your database models. This is the cornerstone of the **Single Source of Truth** philosophy: define your data once in the model, and reuse it everywhere without repeating validation logic.

#### The Declarative Way (`class Meta`)

Seasoned developers will find the `class Meta` pattern familiar but uniquely integrated with Eden's UI system. You can define a `Schema` subclass that mirrors a model while adding or overriding logic for specific use cases.

```python
from eden import Schema, f
from apps.products.models import Product
from pydantic import model_validator

class ProductSchema(Schema):
    class Meta:
        model = Product
        # Explicitly define which fields to pull from the model
        include = ["title", "description", "price", "stock"]
        # Alternatively, use 'exclude' to pull everything except specific fields
        # exclude = ["internal_code", "supplier_cost"]

    # --- ADVANCED CUSTOMIZATION ---
    
    # 1. Adding UI-only fields (fields not in the DB)
    accept_terms: bool = f(label="I confirm the price is correct")

    # 2. Field Overrides
    # If the model has price: float = f(), you can add UI constraints here
    price: float = f(label="Retail Price", min=1.0) 

    # 3. Complex Multi-field Validation
    @model_validator(mode="after")
    def check_business_logic(self) -> "ProductSchema":
        if self.price > 1000 and self.stock < 5:
            # This error will be attached to form.__all__ or the relevant fields
            raise ValueError("High-value items must have at least 5 units in stock.")
        return self
```

> [!TIP]
> **Metadata Inheritance**: When you use `class Meta`, Eden automatically copies `label`, `widget`, and `placeholder` values from your model's `f()` helpers. You only need to redefine them in your schema if you want the form appearance to differ from the database default.

#### The Programmatic Way (`Model.to_schema()`)

For simple use cases like search filters or quick API consumers, creating a class is overkill. Use `to_schema()` to generate a functional schema on the fly that preserves all your model's field constraints and UI markers.

```python
# Create a quick schema for a search bar containing only relevant fields
SearchSchema = Product.to_schema(include=["title", "category"])

@app.get("/api/search")
@app.validate(SearchSchema)
async def search(credentials: SearchSchema):
    # 'credentials' is a validated object with only 'title' and 'category'
    return await Product.filter(title__icontains=credentials.title).all()
```

---

## 🗃️ Model-Linked Forms (`ModelForm`)

`ModelForm` is a high-level wrapper around the `Schema` system designed for standard CRUD (Create, Read, Update, Delete) operations. It manages the lifecycle of an ORM instance automatically, including populating initial data and saving changes to the database.

### Practical CRUD Implementation

```python
class TaskForm(ModelForm):
    class Meta:
        model = Task
        fields = ["title", "due_date", "priority"]

# --- FLOW 1: Creating a New Task ---
@app.post("/tasks/new")
async def create_task(request):
    form = await TaskForm.from_request(request)
    if form.is_valid():
        # Automatically instantiates and saves the Task record
        task = await form.save() 
        return redirect(f"/tasks/{task.id}")
        
    return app.render("task_form.html", form=form)

# --- FLOW 2: Updating an Existing Task ---
@app.post("/tasks/{id}/edit")
async def edit_task(request, id: int):
    # 1. Retrieve the instance
    task = await Task.get(id)
    
    # 2. Bind the instance data to the form (populates initial values)
    # If it's a POST request, it also merges incoming user data
    form = await TaskForm.from_request(request, instance=task)
    
    if form.is_valid():
        # Updates the retrieved 'task' instance and saves it
        await form.save() 
        return redirect("/tasks")
        
    return app.render("task_form.html", form=form)
```

---

## 🎨 Rendering Forms

Eden makes rendering beautiful forms easy with powerful template directives.

### In your Template (`signup.html`)

```html
<form method="POST" action="/users/join" class="space-y-4">
    @csrf

    <!-- Method 1: Render complete fields magically! -->
    <!-- This renders the label, the input, and any error message -->
    <div class="field-wrapper">
        @render_field(form['email'], class="w-full bg-slate-900 border-slate-700 rounded-lg")
    </div>

    <!-- Method 2: Manual field rendering for ultimate control -->
    <div class="field-group">
        {{ form['password'].render_label(class="block text-slate-300 font-medium") }}
        
        {{ form['password'].render(class="w-full bg-slate-900 border-slate-700 rounded-lg") }}
        
        <!-- Use the @error directive to show field specific errors cleanly -->
        @error("password") {
            <p class="text-sm text-red-400 mt-1">{{ message }}</p>
        }
    </div>
    
    <button type="submit" class="w-full py-3 bg-blue-600 rounded-lg">Join</button>
</form>
```

### FormField Customization

Every field in the form (`form["field_name"]`) is a `FormField` instance with several helpers:

| Helper | Description | Example |
| :--- | :--- | :--- |
| `.label` | The field's label. | `{{ form.name.label }}` |
| `.value` | The current value (bound data). | `{{ form.name.value }}` |
| `.error` | Validation error message. | `{{ form.name.error }}` |
| `.render(...)` | Renders the HTML input. | `{{ form.name.render(placeholder="...") }}` |
| `.as_textarea()` | Forces `<textarea>` rendering. | `{{ form.bio.as_textarea() }}` |
| `.as_select()` | Renders a `<select>` dropdown. | `{{ form.role.as_select(choices) }}` |

---

## 🧪 Advanced Validation

Since `Schema` is based on Pydantic, you can use all Pydantic features like complex types, custom validators, and nested schemas.

```python
from pydantic import model_validator

class ResetPasswordSchema(Schema):
    new_password: str = f(widget="password")
    confirm_password: str = f(widget="password")

    @model_validator(mode="after")
    def check_passwords_match(self) -> "ResetPasswordSchema":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self
```

---

## 📤 File Uploads

To handle file uploads, ensure your form has `enctype="multipart/form-data"` and use `FileField` or the `as_file()` widget hint.

```python
class ProfileSchema(Schema):
    avatar: Any = f(widget="file")

@app.post("/profile")
async def profile_update(request):
    # from_request automatically detects multipart data
    form = await ProfileSchema.from_request(request)
    
    if form.is_valid():
        file = form.files.get("avatar")
        if file:
            await storage.save(f"avatars/{file.filename}", file.data)
```

---

**Next Steps**: [Exploring the ORM](orm.md)
