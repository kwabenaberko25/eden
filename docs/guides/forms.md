# Forms & Validation 📝

Eden's form system is centered around a **Unified Schema** architecture. By combining **Pydantic v2** validation with Eden's UI metadata, you can define your data structure, validation rules, and HTML rendering logic in a single, declarative place.

---

## 🏗️ The Unified Schema

The `Schema` class is the heart of Eden's form system. It inherits from Pydantic's `BaseModel` but adds powerful form-specific capabilities like automatic request parsing and UI metadata inheritance.

### Basic Usage

> **Important**: For Schema classes, use `field()` (or the shorter `v()`) from `eden.forms`. This returns a native Pydantic `Field` configured with Eden's UI metadata.

```python
from eden import Schema, field, EmailStr, v  # All from the top-level eden package!

class SignupSchema(Schema):
    email: EmailStr = field(widget="email", label="Email Address")
    password: str = field(min_length=8, widget="password")
    phone: str = v( # 'v' is a shorter alias for 'field'
        pattern=r"^\+?[1-9]\d{1,14}$", 
        help_text="Enter a valid international phone number",
        placeholder="+1234567890"
    )
    bio: str | None = v(widget="textarea", placeholder="Tell us about yourself...")

# In your route
@app.get("/signup")
async def signup_get(request):
    # Create an empty form from the schema
    form = SignupSchema.as_form()
    return request.render("signup.html", form=form)
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

---

### 🧬 `field()` / `v()` vs `f()`

Eden provides specific helpers for the different layers of your application. While they share similar UI metadata arguments, they return different underlying objects:

| Helper | Source | Layer | Returns |
| :--- | :---| :--- | :--- |
| `field()` / `v()` | `from eden import field` | Schemas / Forms | Pydantic `Field` |
| `f()` | `from eden import f` | Database Models | SQLAlchemy `mapped_column` |

> [!TIP]
> **Why separate them?** While Eden's `Schema` can automatically extract metadata from your database `f()` columns, using `field()` or `v()` explicitly in your schemas is the recommended way to define UI-specific validation that doesn't necessarily map to your database constraints.

### 🧬 Model-Based Schemas

Eden allows you to derive schemas directly from your database models. This is the cornerstone of the **Single Source of Truth** philosophy: define your data once in the model, and reuse it everywhere without repeating validation logic.

#### The Declarative Way (`class Meta`)

Seasoned developers will find the `class Meta` pattern familiar but uniquely integrated with Eden's UI system. You can define a `Schema` subclass that mirrors a model while adding or overriding logic for specific use cases.

```python
from eden.forms import Schema, field  # Use eden.forms!
from apps.products.models import Product
from pydantic import model_validator

class ProductSchema(Schema):
    class Meta:
        model = Product
        # Explicitly define which fields to pull from the model
        include = ["title", "description", "price", "stock"]

    # 1. Adding UI-only fields (not in the DB)
    accept_terms: bool = v(label="I confirm the price is correct")

    # 2. Field Overrides
    # Add UI-specific constraints that differ from DB defaults
    price: float = field(label="Retail Price", min=1.0) 

    # 3. Complex Multi-field Validation
    @model_validator(mode="after")
    def check_business_logic(self) -> "ProductSchema":
        if self.price > 1000 and self.stock < 5:
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

## � Complex Validation Patterns

Beyond basic field constraints, Eden supports sophisticated multi-field validation using Pydantic's `@model_validator`. This is essential for business logic that spans multiple fields.

### Cross-Field Validation

**Scenario**: Password confirmation must match the new password, and both must differ from the current password.

```python
from pydantic import model_validator, field_validator
from eden.forms import Schema, field

class ChangePasswordSchema(Schema):
    current_password: str = field(widget="password", label="Current Password")
    new_password: str = field(
        widget="password", 
        label="New Password",
        min_length=12,
        pattern=r"^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])",
        description="Must contain uppercase, number, and special character"
    )
    confirm_password: str = field(widget="password", label="Confirm New Password")

    @model_validator(mode="after")
    def validate_passwords(self) -> "ChangePasswordSchema":
        # Error 1: New and confirm don't match
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match")
        
        # Error 2: New password same as current
        if self.new_password == self.current_password:
            raise ValueError("New password must be different from current password")
        
        return self

# Usage in route handler
@app.post("/security/change-password")
@app.validate(ChangePasswordSchema, template="security.html")
async def change_password(data: ChangePasswordSchema, request):
    user = request.user
    
    # Verify current password before accepting change
    if not user.verify_password(data.current_password):
        # This is a custom check, not in the schema
        raise ValueError("Current password is incorrect")
    
    user.password = data.new_password
    await user.save()
    
    return redirect("/dashboard", flash_message="Password changed successfully!")
```

### Dependent Field Validation

**Scenario**: A discount code validation depends on the purchase amount and order status.

```python
from datetime import datetime
from decimal import Decimal
from enum import Enum

class OrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"

class CheckoutSchema(Schema):
    subtotal: Decimal = field(gt=0, label="Subtotal")
    discount_code: str | None = field(default=None, label="Discount Code (optional)")
    order_status: OrderStatus = field(label="Order Status")
    agreed_to_terms: bool = field(label="I agree to the terms and conditions")

    @model_validator(mode="after")
    def validate_discount_and_terms(self) -> "CheckoutSchema":
        # Rule 1: Discount codes only valid on submitted orders over $100
        if self.discount_code:
            if self.order_status != OrderStatus.SUBMITTED:
                raise ValueError("Discount codes only apply to submitted orders")
            
            if self.subtotal < Decimal("100.00"):
                raise ValueError("Discount codes require minimum order of $100")
            
            # Rule 2: Must accept terms if using discount
            if not self.agreed_to_terms:
                raise ValueError("You must accept terms to use a discount code")
        
        # Rule 3: Terms required for submitted orders
        if self.order_status == OrderStatus.SUBMITTED and not self.agreed_to_terms:
            raise ValueError("You must accept terms before submitting your order")
        
        return self

# Template rendering with conditional sections
@app.get("/checkout")
async def checkout_get(request):
    form = CheckoutSchema.as_form()
    return request.render("checkout.html", form=form, user=request.user)
```

```html
<!-- checkout.html -->
<form method="POST" class="max-w-2xl">
    @csrf
    
    <div class="space-y-4">
        <!-- Subtotal field -->
        @render_field(form['subtotal'])
        
        <!-- Conditional: Only show discount if subtotal >= 100 -->
        {% if form['subtotal'].value >= 100 %}
            <fieldset class="border-l-4 border-green-500 pl-4">
                <legend>💰 Eligible for Discount</legend>
                @render_field(form['discount_code'])
            </fieldset>
        {% endif %}
        
        <!-- Order status -->
        @render_field(form['order_status'])
        
        <!-- Conditional: Terms only required for submitted orders -->
        {% if form['order_status'].value == 'submitted' %}
            <fieldset class="bg-red-50 p-4 border-red-200">
                <legend>⚠️ Required for Submission</legend>
                @render_field(form['agreed_to_terms'])
            </fieldset>
        {% endif %}
    </div>
    
    <button type="submit">Proceed</button>
</form>
```

### Pattern Validation & Enums

**Scenario**: Email validation, status enum enforcement, and URL pattern checking.

```python
from enum import Enum
from pydantic import field_validator, EmailStr

class UserRole(str, Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"

class UserProfileSchema(Schema):
    email: EmailStr = field(label="Email Address")
    role: UserRole = field(label="User Role")
    website: str | None = field(default=None, label="Personal Website")
    phone: str | None = field(
        default=None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        label="Phone (E.164 Format)"
    )
    
    @field_validator("website")
    @classmethod
    def validate_website_url(cls, v: str | None) -> str | None:
        if not v:
            return v
        
        # Basic URL validation
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Website must start with http:// or https://")
        
        if len(v) > 2048:
            raise ValueError("Website URL too long (max 2048 chars)")
        
        return v

# Usage - note role options show in form dropdown automatically
@app.post("/profile/update")
@app.validate(UserProfileSchema, template="profile_edit.html")
async def update_profile(data: UserProfileSchema, request):
    user = request.user
    user.email = data.email
    user.website = data.website
    user.phone = data.phone
    
    # Only admins can assign roles
    if request.user.is_admin:
        user.role = data.role
    
    await user.save()
    return redirect("/profile", flash="Profile updated!")
```

---

## 🧩 Form Composition & Reuse

Rather than defining validation logic repeatedly, compose reusable form schemas. This follows the **DRY (Don't Repeat Yourself)** principle and makes maintenance easier.

### Schema Inheritance

**Scenario**: Define a base address schema, then reuse it for shipping, billing, and company address forms.

```python
from eden.forms import Schema, field

# ✓ Base schema with common address fields
class AddressSchema(Schema):
    street: str = field(min_length=5, label="Street Address")
    city: str = field(min_length=2, label="City")
    state: str = field(min_length=2, max_length=2, label="State (US)")
    zipcode: str = field(
        pattern=r"^\d{5}(-\d{4})?$",
        label="ZIP Code",
        help_text="Format: 12345 or 12345-6789"
    )
    country: str = field(default="US", label="Country")
    
    @model_validator(mode="after")
    def validate_zip_state_combo(self) -> "AddressSchema":
        # Simple validation: US zips only for US addresses
        if self.country == "US" and not self.zipcode.replace("-", "").isdigit():
            raise ValueError("US addresses require numeric ZIP codes")
        return self

# ✓ Shipping form extends address with delivery options
class ShippingFormSchema(Schema):
    address: AddressSchema = field(label="Shipping Address")
    shipping_method: str = field(label="Shipping Method")
    special_instructions: str | None = field(
        default=None,
        widget="textarea",
        label="Special Delivery Instructions"
    )
    
    @model_validator(mode="after")
    def validate_shipping(self) -> "ShippingFormSchema":
        # Rule: Express shipping not available in certain states
        if self.shipping_method == "express" and self.address.state in ["AK", "HI"]:
            raise ValueError("Express shipping unavailable for Alaska and Hawaii")
        return self

# ✓ Billing form reuses address too
class BillingFormSchema(Schema):
    billing_address: AddressSchema = field(label="Billing Address")
    same_as_shipping: bool = field(default=False, label="Same as shipping address?")
    
    @model_validator(mode="after")  
    def validate_billing(self) -> "BillingFormSchema":
        if not self.same_as_shipping:
            # Billing address must be filled out
            if not all([
                self.billing_address.street,
                self.billing_address.city,
                self.billing_address.state,
                self.billing_address.zipcode,
            ]):
                raise ValueError("Please complete your billing address")
        return self

# ✓ Usage: Reduce code duplication
@app.post("/checkout/shipping")
@app.validate(ShippingFormSchema, template="shipping.html")
async def set_shipping(data: ShippingFormSchema, request):
    session = request.session
    session["shipping"] = data.model_dump()
    return redirect("/checkout/billing")

@app.post("/checkout/billing")
@app.validate(BillingFormSchema, template="billing.html")
async def set_billing(data: BillingFormSchema, request):
    session = request.session
    session["billing"] = data.model_dump()
    return redirect("/checkout/review")
```

### Schema Composition with Mixins

**Scenario**: Many forms need timestamp and creator tracking. Use a mixin for common fields.

```python
from datetime import datetime
from eden.forms import Schema, field

# ✓ Mixin with common audit fields
class AuditMixin:
    created_by: int = field(label="Created By")
    created_at: datetime = field(default_factory=datetime.now, label="Created At")
    updated_by: int | None = field(default=None, label="Last Updated By")

# ✓ Comment form with audit fields
class CommentSchema(Schema, AuditMixin):
    post_id: int = field(lt=0, label="Post ID")
    content: str = field(min_length=1, max_length=5000, widget="textarea")
    is_deleted: bool = field(default=False, label="Mark as Deleted")
    
    @model_validator(mode="after")
    def validate_comment(self) -> "CommentSchema":
        if self.is_deleted and not self.updated_by:
            raise ValueError("Deletion must be tracked with updated_by")
        return self

# ✓ Article form with audit fields
class ArticleSchema(Schema, AuditMixin):
    title: str = field(min_length=5, max_length=200, label="Title")
    slug: str = field(
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        label="URL Slug",
        help_text="lowercase, hyphens only"
    )
    content: str = field(widget="textarea", label="Content")
    published: bool = field(default=False, label="Published?")

# ✓ Both forms now have audit field tracking automatically
@app.post("/articles/create")
@app.validate(ArticleSchema, template="article_form.html")
async def create_article(data: ArticleSchema, request):
    data.created_by = request.user.id
    data.updated_by = request.user.id
    
    article = Article(**data.model_dump())
    await article.save()
    return redirect(f"/articles/{article.slug}")
```

---

## 🎭 Dynamic Forms & Conditional Fields

Often, what fields appear in a form depends on user input or user type. Eden makes this pattern simple and performant.

### Conditional Fields Based on Selection

**Scenario**: Different billing options require different fields. Credit card needs card details, but bank transfer needs account info.

```python
from enum import Enum
from pydantic import field_validator, model_validator

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"

class PaymentFormSchema(Schema):
    amount: int = field(gt=0, label="Amount (cents)")
    payment_method: PaymentMethod = field(label="Payment Method")
    
    # Credit card fields (optional, but required if method is credit_card)
    card_number: str | None = field(
        default=None,
        pattern=r"^\d{13,19}$",
        label="Card Number"
    )
    card_expiry: str | None = field(
        default=None,
        pattern=r"^\d{2}/\d{2}$",
        label="Expiry (MM/YY)"
    )
    card_cvc: str | None = field(
        default=None,
        pattern=r"^\d{3,4}$",
        label="CVC"
    )
    
    # Bank transfer fields (optional, but required if method is bank_transfer)
    bank_account: str | None = field(
        default=None,
        pattern=r"^\d{8,17}$",
        label="Bank Account Number"
    )
    bank_routing: str | None = field(
        default=None,
        pattern=r"^\d{9}$",
        label="Routing Number"
    )
    
    # PayPal (no extra fields needed)
    
    @model_validator(mode="after")
    def validate_by_payment_method(self) -> "PaymentFormSchema":
        if self.payment_method == PaymentMethod.CREDIT_CARD:
            # All credit card fields required
            if not all([self.card_number, self.card_expiry, self.card_cvc]):
                raise ValueError("Credit card requires all card details")
            
            # CVC length depends on card type (Visa/Mastercard: 3, Amex: 4)
            if len(self.card_cvc) == 4 and not self.card_number.startswith("3"):
                raise ValueError("4-digit CVC only valid for American Express")
        
        elif self.payment_method == PaymentMethod.BANK_TRANSFER:
            # All bank fields required
            if not all([self.bank_account, self.bank_routing]):
                raise ValueError("Bank transfer requires account and routing numbers")
        
        elif self.payment_method == PaymentMethod.PAYPAL:
            # No additional validation needed
            pass
        
        return self

# Template with conditional field rendering
@app.get("/payment")
async def payment_form(request):
    form = PaymentFormSchema.as_form()
    return request.render("payment.html", form=form)

@app.post("/payment")
@app.validate(PaymentFormSchema, template="payment.html")
async def process_payment(data: PaymentFormSchema, request):
    if data.payment_method == PaymentMethod.CREDIT_CARD:
        # Process credit card
        await stripe.charge(data.card_number, data.amount)
    elif data.payment_method == PaymentMethod.BANK_TRANSFER:
        # Process bank transfer
        await bank_api.transfer(data.bank_account, data.amount)
    elif data.payment_method == PaymentMethod.PAYPAL:
        # Redirect to PayPal
        return redirect(await paypal_redirect_url(data.amount))
    
    return redirect("/payment/success")
```

```html
<!-- payment.html - Shows/hides fields based on selection -->
<form method="POST" class="max-w-lg">
    @csrf
    
    @render_field(form['amount'])
    @render_field(form['payment_method'])
    
    <!-- Credit card fields - shown only if payment_method == 'credit_card' -->
    <div id="credit-card-fields" class="hidden mt-4 p-4 border rounded">
        <h3 class="font-bold mb-3">Card Details</h3>
        @render_field(form['card_number'])
        @render_field(form['card_expiry'])
        @render_field(form['card_cvc'])
    </div>
    
    <!-- Bank transfer fields - shown only if payment_method == 'bank_transfer' -->
    <div id="bank-fields" class="hidden mt-4 p-4 border rounded">
        <h3 class="font-bold mb-3">Bank Account</h3>
        @render_field(form['bank_account'])
        @render_field(form['bank_routing'])
    </div>
    
    <button type="submit" class="mt-6">Process Payment</button>
</form>

<script>
    // Show/hide fields based on payment method selection
    const methodSelect = document.querySelector('[name="payment_method"]');
    const cardFields = document.getElementById('credit-card-fields');
    const bankFields = document.getElementById('bank-fields');
    
    function updateVisibility() {
        const method = methodSelect.value;
        cardFields.classList.toggle('hidden', method !== 'credit_card');
        bankFields.classList.toggle('hidden', method !== 'bank_transfer');
    }
    
    methodSelect.addEventListener('change', updateVisibility);
    updateVisibility(); // Initial state
</script>
```

### Permission-Based Form Fields

**Scenario**: Only admins see the "approved" checkbox. Managers see different discount limits.

```python
from enum import Enum

class UserType(str, Enum):
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"

class DiscountFormSchema(Schema):
    product_id: int = field(gt=0, label="Product ID")
    discount_percent: int = field(ge=0, le=100, label="Discount %")
    
    # Admin-only fields
    admin_override: bool | None = field(
        default=None,
        label="Override pricing rules? (Admin only)"
    )
    
    # Manager-only tracking
    manager_notes: str | None = field(
        default=None,
        widget="textarea",
        label="Manager Notes"
    )

# Dynamic form creation based on user role
def get_discount_form_for_user(user):
    """Create a form schema based on user's role"""
    
    fields_to_include = {
        "product_id": DiscountFormSchema.model_fields["product_id"],
        "discount_percent": DiscountFormSchema.model_fields["discount_percent"],
    }
    
    # Add role-specific fields
    if user.role == UserType.ADMIN:
        fields_to_include["admin_override"] = DiscountFormSchema.model_fields["admin_override"]
    
    if user.role in [UserType.MANAGER, UserType.ADMIN]:
        fields_to_include["manager_notes"] = DiscountFormSchema.model_fields["manager_notes"]
    
    # Create dynamic schema with only authorized fields
    return DiscountFormSchema.model_rebuild(
        __config__={"fields": fields_to_include}
    )

# Usage in route
@app.post("/discounts/create")
async def create_discount(request):
    user = request.user
    
    # Get form appropriate to user role
    form_class = get_discount_form_for_user(user)
    form = await form_class.from_request(request)
    
    if form.is_valid():
        discount = Discount(**form.model_dump(exclude_none=True))
        discount.created_by = user.id
        await discount.save()
        return redirect("/discounts")
    
    return request.render("discount_form.html", form=form)
```

---

## �🗃️ Model-Linked Forms (`ModelForm`)

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
        
    return request.render("task_form.html", form=form)

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
        
    return request.render("task_form.html", form=form)
```

---

## 📤 File Uploads - Comprehensive Patterns

File uploads require special handling: proper encoding, file validation, secure storage, and error recovery. Eden makes this ergonomic while maintaining security.

### Single File Upload with Validation

**Scenario**: User uploads a profile picture. Validate file type, size, and image dimensions.

```python
from eden.forms import Schema, field
from pydantic import field_validator
from PIL import Image
from io import BytesIO

class ProfileAvatarSchema(Schema):
    avatar: str = field(
        widget="file",
        label="Profile Picture",
        description="PNG, JPG, or WEBP (max 5MB, min 100x100px)"
    )
    
    @field_validator("avatar")
    @classmethod
    def validate_avatar_file(cls, v: str) -> str:
        # Note: In a real scenario, you'd get the actual file object from request.files
        # This is a simplified example showing validation logic
        return v

# In your route handler - actual file validation happens here
@app.post("/profile/avatar")
async def upload_avatar(request):
    form = await ProfileAvatarSchema.from_request(request)
    
    # Get the actual uploaded file
    if "avatar" not in request.files:
        raise ValueError("No avatar file provided")
    
    file = request.files["avatar"]
    
    # Validation 1: File size (5MB max)
    file_size_mb = len(file.data) / (1024 * 1024)
    if file_size_mb > 5:
        raise ValueError(f"File too large ({file_size_mb:.1f}MB). Max 5MB.")
    
    # Validation 2: File type check (by MIME type)
    allowed_mimes = ["image/png", "image/jpeg", "image/webp"]
    if file.content_type not in allowed_mimes:
        raise ValueError(f"Invalid file type. Allowed: {', '.join(allowed_mimes)}")
    
    # Validation 3: Image dimensions using PIL
    try:
        image = Image.open(BytesIO(file.data))
        width, height = image.size
        
        if width < 100 or height < 100:
            raise ValueError(f"Image too small ({width}x{height}). Min 100x100.")
        
        # Optional: Resize if too large
        if width > 1000 or height > 1000:
            image.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
    
    except Exception as e:
        raise ValueError(f"Invalid image file: {str(e)}")
    
    # Validation 4: File extension check (defense in depth)
    filename = file.filename.lower()
    if not any(filename.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
        raise ValueError("File must have image extension (.png, .jpg, .webp)")
    
    # Save file securely
    user = request.user
    safe_filename = f"avatars/{user.id}_avatar_{datetime.now().timestamp()}.png"
    await storage.save(safe_filename, file.data)
    
    # Update user profile
    user.avatar_url = safe_filename
    await user.save()
    
    return redirect("/profile", flash="Avatar updated!")
```

### Multiple File Upload

**Scenario**: User uploads multiple documents (receipts, invoices). Each needs validation and deduplicated naming.

```python
from typing import List

class DocumentUploadSchema(Schema):
    title: str = field(min_length=3, label="Document Set Title")
    documents: List[str] = field(
        widget="file",
        label="Upload Documents (PDF, DOC, DOCX)",
        description="Max 10 files, 10MB each"
    )
    category: str = field(label="Category")

@app.post("/documents/upload")
async def upload_documents(request):
    form = await DocumentUploadSchema.from_request(request)
    
    if "documents" not in request.files:
        raise ValueError("No documents provided")
    
    files = request.files.getlist("documents")
    
    # Validation 1: File count
    max_files = 10
    if len(files) > max_files:
        raise ValueError(f"Too many files. Max {max_files}.")
    
    if len(files) == 0:
        raise ValueError("At least one document required")
    
    user = request.user
    saved_files = []
    
    for idx, file in enumerate(files):
        # Validation 2: File size (10MB max per file)
        file_size_mb = len(file.data) / (1024 * 1024)
        if file_size_mb > 10:
            raise ValueError(
                f"File '{file.filename}' too large ({file_size_mb:.1f}MB). Max 10MB per file."
            )
        
        # Validation 3: Allowed MIME types
        allowed_mimes = [
            "application/pdf",
            "application/msword",  # .doc
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        ]
        if file.content_type not in allowed_mimes:
            raise ValueError(f"File type not allowed: {file.content_type}")
        
        # Validation 4: Check file extension
        filename = file.filename.lower()
        if not any(filename.endswith(ext) for ext in ['.pdf', '.doc', '.docx']):
            raise ValueError(f"Invalid extension: {filename}")
        
        # Validation 5: Deduplicate filenames
        # If two files have same name, add index to second one
        safe_name = file.filename
        if any(d["filename"] == safe_name for d in saved_files):
            name_parts = safe_name.rsplit(".", 1)
            safe_name = f"{name_parts[0]}_{idx}.{name_parts[1]}"
        
        # Save file
        filepath = f"documents/{user.id}/{form.category}/{safe_name}"
        await storage.save(filepath, file.data)
        
        saved_files.append({
            "filename": safe_name,
            "filepath": filepath,
            "size_mb": file_size_mb
        })
    
    # Store metadata
    doc_set = DocumentSet(
        user_id=user.id,
        title=form.title,
        category=form.category,
        file_count=len(saved_files),
        files=saved_files
    )
    await doc_set.save()
    
    return redirect("/documents", flash=f"Uploaded {len(saved_files)} files")
```

### CSV Import with Validation

**Scenario**: Admin user imports product data from CSV. Each row must be validated before inserting into database.

```python
import csv
from io import StringIO, TextIOWrapper

class CSVImportSchema(Schema):
    csv_file: str = field(
        widget="file",
        label="CSV File",
        description="Columns: name, sku, price, stock"
    )
    skip_duplicates: bool = field(default=True, label="Skip duplicate SKUs?")
    dry_run: bool = field(default=False, label="Preview only (don't import)?")

@app.post("/admin/import-products")
@app.validate(CSVImportSchema, template="admin_import.html")
async def import_products(data: CSVImportSchema, request):
    # Check permissions
    if not request.user.is_admin:
        raise PermissionError("Only admins can import products")
    
    # Get uploaded file
    if "csv_file" not in request.files:
        raise ValueError("No CSV file provided")
    
    file = request.files["csv_file"]
    
    # Validation 1: File type
    if not file.filename.lower().endswith('.csv'):
        raise ValueError("File must be a .csv file")
    
    # Validation 2: File size (5MB max)
    file_size_mb = len(file.data) / (1024 * 1024)
    if file_size_mb > 5:
        raise ValueError("CSV file too large (max 5MB)")
    
    # Parse CSV
    try:
        # Decode bytes to string, then parse
        csv_text = file.data.decode('utf-8')
        reader = csv.DictReader(StringIO(csv_text))
        
        if not reader.fieldnames:
            raise ValueError("CSV file is empty")
        
        # Validation 3: Check required columns exist
        required_columns = {"name", "sku", "price", "stock"}
        csv_columns = set(reader.fieldnames)
        missing = required_columns - csv_columns
        if missing:
            raise ValueError(f"Missing columns: {', '.join(missing)}")
        
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
            try:
                # Validation 4: Data type and range validation
                sku = str(row["sku"]).strip()
                
                if not sku or len(sku) > 50:
                    raise ValueError(f"Invalid SKU: {sku}")
                
                # Check for duplicate
                existing = await Product.filter(sku=sku).first()
                if existing and data.skip_duplicates:
                    skipped_count += 1
                    continue
                
                # Parse price
                try:
                    price = float(row["price"])
                    if price < 0:
                        raise ValueError("Price cannot be negative")
                except ValueError:
                    raise ValueError(f"Invalid price: {row['price']}")
                
                # Parse stock
                try:
                    stock = int(row["stock"])
                    if stock < 0:
                        raise ValueError("Stock cannot be negative")
                except ValueError:
                    raise ValueError(f"Invalid stock: {row['stock']}")
                
                # In dry_run mode, just validate without saving
                if not data.dry_run:
                    product = Product(
                        name=row["name"].strip(),
                        sku=sku,
                        price=price,
                        stock=stock,
                        imported_by=request.user.id
                    )
                    await product.save()
                
                imported_count += 1
            
            except ValueError as e:
                errors.append({
                    "row": row_num,
                    "error": str(e),
                    "data": row
                })
                if len(errors) >= 50:  # Stop after 50 errors
                    break
        
        # Return results
        mode = "dry-run" if data.dry_run else "imported"
        message = f"CSV {mode}: {imported_count} products"
        if skipped_count:
            message += f", {skipped_count} skipped"
        if errors:
            message += f", {len(errors)} errors"
        
        return request.render("import_results.html", {
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "errors": errors,
            "dry_run": data.dry_run,
            "message": message
        })
    
    except UnicodeDecodeError:
        raise ValueError("CSV file must be UTF-8 encoded")
    except csv.Error as e:
        raise ValueError(f"CSV parsing error: {str(e)}")

# Template for showing import results
@app.get("/admin/import-results")
async def import_results(request):
    return request.render("import_results.html")
```

### Audio/Media Upload with Streaming

**Scenario**: User uploads audio file. Store efficiently and provide streaming playback.

```python
import mimetypes
from pathlib import Path

class PodcastEpisodeSchema(Schema):
    title: str = field(min_length=5, label="Episode Title")
    audio_file: str = field(
        widget="file",
        label="Audio File (MP3, M4A, WAV)",
        description="Max 500MB"
    )
    description: str | None = field(
        default=None,
        widget="textarea",
        label="Episode Description"
    )

@app.post("/podcasts/upload-episode")
async def upload_episode(request):
    form = await PodcastEpisodeSchema.from_request(request)
    
    if "audio_file" not in request.files:
        raise ValueError("No audio file provided")
    
    file = request.files["audio_file"]
    
    # Validation 1: File size (500MB max for audio)
    file_size_mb = len(file.data) / (1024 * 1024)
    max_size_mb = 500
    if file_size_mb > max_size_mb:
        raise ValueError(f"File too large ({file_size_mb:.1f}MB). Max {max_size_mb}MB.")
    
    # Validation 2: Audio MIME types
    allowed_audio_types = ["audio/mpeg", "audio/mp4", "audio/wav", "audio/ogg"]
    if file.content_type not in allowed_audio_types:
        raise ValueError(
            f"Invalid audio format: {file.content_type}. "
            f"Allowed: {', '.join(allowed_audio_types)}"
        )
    
    # Validation 3: File extension
    filename = file.filename.lower()
    if not any(filename.endswith(ext) for ext in ['.mp3', '.m4a', '.wav', '.ogg']):
        raise ValueError("File must be MP3, M4A, WAV, or OGG")
    
    # Save to storage with channel-based organization
    user = request.user
    timestamp = datetime.now().isoformat()
    file_ext = Path(file.filename).suffix
    safe_filename = f"podcasts/{user.id}/{timestamp}{file_ext}"
    
    await storage.save(safe_filename, file.data)
    
    # Create episode record
    episode = PodcastEpisode(
        user_id=user.id,
        title=form.title,
        description=form.description,
        audio_path=safe_filename,
        audio_size_mb=file_size_mb,
        uploaded_at=datetime.now()
    )
    await episode.save()
    
    return redirect(f"/podcasts/{episode.id}", flash="Episode uploaded!")

# Streaming endpoint for audio playback
@app.get("/podcasts/{episode_id}/stream")
async def stream_episode(episode_id: int, request):
    episode = await PodcastEpisode.get(episode_id)
    
    # Check access permissions
    if episode.user_id != request.user.id and not request.user.is_admin:
        raise PermissionError("Cannot access this episode")
    
    # Stream file from storage
    file_data = await storage.get(episode.audio_path)
    
    return Response(
        content=file_data,
        media_type=episode.audio_content_type,
        headers={
            "Content-Disposition": f"inline; filename={episode.title}",
            "Accept-Ranges": "bytes"
        }
    )
```

---

## 🎨 Advanced Form Rendering

Eden makes rendering beautiful forms easy with powerful template directives. From simple single-step forms to complex multi-step wizards, you can build any form experience.

### Automatic Field Rendering

The simplest approach: Let Eden automatically render fields with labels, inputs, and errors based on their Python type.

```python
@app.get("/contact")
async def contact_form(request):
    form = ContactSchema.as_form()
    return request.render("contact.html", form=form)
```

```html
<!-- contact.html -->
<form method="POST" class="max-w-2xl space-y-4">
    @csrf
    
    <!-- Renders complete field: label + input + error message -->
    <!-- Eden auto-chooses input type based on Python type -->
    @render_field(form['email'], class="w-full px-4 py-2 border rounded")
    @render_field(form['message'], class="w-full px-4 py-2 border rounded min-h-32")
    @render_field(form['subscribe_newsletter'])  <!-- Auto-rendered as checkbox -->
    
    <button type="submit" class="px-6 py-2 bg-blue-600 text-white rounded">Send</button>
</form>
```

### Manual Field Control

For fine-grained control, build fields manually piece by piece.

```html
<form method="POST" class="max-w-2xl">
    @csrf
    
    <!-- Full manual control: Build label + input + errors yourself -->
    <div class="form-group mb-4">
        <!-- Render label -->
        {{ form['email'].render_label(class="block font-bold text-gray-700 mb-2") }}
        
        <!-- Render input with custom attributes -->
        {{ form['email'].render(
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500",
            placeholder="your@email.com",
            autocomplete="email"
        )}}
        
        <!-- Show validation error if present -->
        {% if form['email'].error %}
            <p class="text-sm text-red-600 mt-1">⚠️ {{ form['email'].error }}</p>
        {% endif %}
        
        <!-- Show field help text -->
        {% if form['email'].help_text %}
            <p class="text-xs text-gray-500 mt-1">💡 {{ form['email'].help_text }}</p>
        {% endif %}
    </div>
    
    <!-- Textarea rendering (override default text input) -->
    <div class="form-group mb-4">
        {{ form['message'].render_label(class="block font-bold text-gray-700 mb-2") }}
        {{ form['message'].as_textarea(
            class="w-full px-4 py-2 border rounded-lg",
            rows="6"
        )}}
        {% if form['message'].error %}
            <p class="text-sm text-red-600 mt-1">{{ form['message'].error }}</p>
        {% endif %}
    </div>
    
    <!-- Select dropdown -->
    <div class="form-group mb-4">
        {{ form['category'].render_label(class="block font-bold text-gray-700 mb-2") }}
        {{ form['category'].as_select(
            choices=[("general", "General Inquiry"), ("technical", "Technical Support")],
            class="w-full px-4 py-2 border rounded-lg"
        )}}
    </div>
    
    <button type="submit" class="px-6 py-3 bg-blue-600 text-white rounded-lg">Submit</button>
</form>
```

### Dynamic Field Rendering Based on State

**Scenario**: Show different fields or validation messages based on form or user state. This is essential for conditional UX.

```html
<form method="POST" id="checkout-form" class="max-w-3xl">
    @csrf
    
    <!-- Standard fields always shown -->
    @render_field(form['email'])
    
    <!-- Conditionally show shipping fields based on selected method -->
    {% if form.get('shipping_method') and form['shipping_method'].value == 'express' %}
        <div class="bg-blue-50 p-4 border-l-4 border-blue-500 rounded">
            <p class="font-bold text-blue-900">⚡ Express Shipping Selected</p>
            <p class="text-sm text-blue-700 mt-1">2-day delivery guarantee</p>
            @render_field(form['express_instructions'], widget="textarea")
        </div>
    {% elif form.get('shipping_method') and form['shipping_method'].value == 'standard' %}
        <div class="bg-gray-50 p-4 border-l-4 border-gray-300 rounded">
            <p class="font-bold text-gray-900">📦 Standard Shipping</p>
            <p class="text-sm text-gray-700 mt-1">5-7 business days</p>
        </div>
    {% endif %}
    
    <!-- Show payment section only if order total > 0 -->
    {% if form['total'].value > 0 %}
        <fieldset class="border-t pt-4 mt-6">
            <legend class="font-bold text-lg">Payment Details</legend>
            @render_field(form['payment_method'])
            
            <!-- Show payment method-specific fields -->
            {% if form['payment_method'].value == 'credit_card' %}
                <div class="bg-blue-50 p-3 rounded mt-3 mb-3 text-sm">
                    Card information is securely encrypted
                </div>
                @render_field(form['card_number'])
                <div class="grid grid-cols-2 gap-3">
                    @render_field(form['card_expiry'])
                    @render_field(form['card_cvc'])
                </div>
            {% elif form['payment_method'].value == 'paypal' %}
                <div class="bg-yellow-50 p-3 rounded mt-3 text-sm">
                    You will be redirected to PayPal to complete payment
                </div>
            {% endif %}
        </fieldset>
    {% else %}
        <p class="text-green-600 font-bold py-4">✓ This order qualifies for free shipping!</p>
    {% endif %}
    
    <button type="submit" class="mt-6 px-8 py-3 bg-blue-600 text-white rounded-lg">Complete Checkout</button>
</form>

<script>
    // Dynamically update form visibility when selections change
    document.querySelectorAll('select').forEach(select => {
        select.addEventListener('change', () => {
            // Force form re-render or toggle visibility classes
            document.getElementById('checkout-form').dispatchEvent(new Event('change'));
        });
    });
</script>
```

### Multi-Step Form Wizard

**Scenario**: Break a complex form into multiple steps with progress tracking, validation per step, and session persistence.

```python
class PersonalInfoStep(Schema):
    first_name: str = field(min_length=1, label="First Name")
    last_name: str = field(min_length=1, label="Last Name")
    email: EmailStr = field(label="Email")

class AddressStep(Schema):
    street: str = field(min_length=5, label="Street Address")
    city: str = field(min_length=2, label="City")
    state: str = field(min_length=2, max_length=2, label="State")
    zipcode: str = field(pattern=r"^\d{5}(-\d{4})?$", label="ZIP Code")

class PaymentStep(Schema):
    payment_method: str = field(label="Payment Method")
    card_number: str | None = field(default=None, label="Card Number")

class ReviewStep(Schema):
    agreed_to_terms: bool = field(label="I agree to terms and conditions")

# Multi-step form handlers
@app.get("/signup-wizard")
async def wizard_form_get(request):
    step = int(request.query_params.get("step", 1))
    
    step_schemas = {
        1: PersonalInfoStep,
        2: AddressStep,
        3: PaymentStep,
        4: ReviewStep,
    }
    
    current_schema = step_schemas.get(step)
    if not current_schema:
        raise ValueError("Invalid wizard step")
    
    # Populate with previously saved data
    form = current_schema.as_form()
    if step > 1:
        prev_data = request.session.get(f"wizard_step_{step}", {})
        for key, val in prev_data.items():
            if key in form.fields:
                form[key].value = val
    
    return request.render("wizard.html", form=form, step=step, total_steps=4)

@app.post("/signup-wizard")
async def wizard_form_post(request):
    step = int(request.form.get("current_step", 1))
    
    step_schemas = {
        1: PersonalInfoStep,
        2: AddressStep,
        3: PaymentStep,
        4: ReviewStep,
    }
    
    schema_class = step_schemas.get(step)
    if not schema_class:
        raise ValueError("Invalid wizard step")
    
    form = await schema_class.from_request(request)
    
    if not form.is_valid():
        # Re-render form with validation errors
        return request.render("wizard.html", form=form, step=step, total_steps=4)
    
    # Save step data to session
    request.session[f"wizard_step_{step}"] = form.model_dump()
    
    # Move to next step
    if step < 4:
        return redirect(f"/signup-wizard?step={step + 1}")
    else:
        # All steps complete - create user from all session data
        all_data = {}
        for i in range(1, 5):
            all_data.update(request.session.get(f"wizard_step_{i}", {}))
        
        # Save user to database
        user = User(**all_data)
        await user.save()
        
        # Clean up session
        for i in range(1, 5):
            request.session.pop(f"wizard_step_{i}", None)
        
        return redirect("/dashboard", flash="Welcome!")
```

```html
<!-- wizard.html -->
<div class="max-w-2xl mx-auto">
    <!-- Progress indicator -->
    <div class="mb-8">
        <div class="flex justify-between text-sm font-bold mb-3">
            {% for i in range(1, total_steps + 1) %}
                <span class="{% if i <= step %}text-blue-600{% elif i == step + 1 %}text-gray-700{% else %}text-gray-400{% endif %}">
                    Step {{ i }}
                </span>
            {% endfor %}
        </div>
        
        <!-- Progress bar -->
        <div class="w-full bg-gray-200 rounded-full h-2">
            <div class="bg-blue-600 h-2 rounded-full transition-all" style="width: {{ (step / total_steps * 100) }}%"></div>
        </div>
    </div>
    
    <!-- Current step form -->
    <form method="POST" class="space-y-6">
        @csrf
        <input type="hidden" name="current_step" value="{{ step }}">
        
        <!-- Render all fields for current step with proper styling -->
        {% for field_name, field in form.fields.items() %}
            @render_field(field, class="w-full px-4 py-2 border rounded-lg")
        {% endfor %}
        
        <!-- Navigation buttons -->
        <div class="flex justify-between pt-6 border-t">
            {% if step > 1 %}
                <a href="/signup-wizard?step={{ step - 1 }}" class="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
                    ← Back
                </a>
            {% else %}
                <div></div>
            {% endif %}
            
            <button type="submit" class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                {% if step < total_steps %}
                    Next →
                {% else %}
                    Complete Signup
                {% endif %}
            </button>
        </div>
        
        <!-- Step indicators -->
        <p class="text-center text-sm text-gray-500">
            Step {{ step }} of {{ total_steps }}
        </p>
    </form>
</div>
```

### Custom Widget Rendering

**Scenario**: Render specialized fields with custom widgets (rich text editor, date picker, color picker, autocomplete).

```python
from eden.forms import Schema, field
from datetime import datetime

class BlogPostSchema(Schema):
    title: str = field(min_length=5, label="Post Title")
    content: str = field(widget="richtext", label="Content")  # Custom widget
    featured_image: str = field(widget="file", label="Featured Image")
    publish_date: datetime = field(widget="datetime", label="Publish Date")
    tags: str = field(widget="autocomplete", label="Tags")
    color_theme: str = field(widget="color", label="Theme Color")

@app.get("/blog/new")
async def new_blog_post(request):
    form = BlogPostSchema.as_form()
    return request.render("blog_editor.html", form=form)
```

```html
<!-- blog_editor.html with custom widgets -->
<form method="POST" enctype="multipart/form-data" class="max-w-4xl">
    @csrf
    
    <!-- Standard text field -->
    @render_field(form['title'], class="w-full px-4 py-2 border rounded text-2xl font-bold")
    
    <!-- Custom: Rich text editor (TinyMCE, Quill, etc.) -->
    <div class="form-group">
        <label for="content" class="block font-bold mb-2">{{ form['content'].label }}</label>
        <div id="editor" class="border rounded min-h-96 p-3 bg-white"></div>
        <textarea name="content" id="content" class="hidden">{{ form['content'].value or '' }}</textarea>
        {% if form['content'].error %}
            <p class="text-sm text-red-600 mt-1">{{ form['content'].error }}</p>
        {% endif %}
    </div>
    
    <!-- Custom: Date/time picker -->
    <div class="form-group">
        <label for="publish_date" class="block font-bold mb-2">{{ form['publish_date'].label }}</label>
        <input 
            type="datetime-local" 
            name="publish_date" 
            id="publish_date"
            value="{% if form['publish_date'].value %}{{ form['publish_date'].value | isoformat }}{% endif %}"
            class="w-full px-4 py-2 border rounded"
        >
    </div>
    
    <!-- Custom: Color picker -->
    <div class="form-group">
        <label for="color_theme" class="block font-bold mb-2">{{ form['color_theme'].label }}</label>
        <div class="flex gap-2">
            <input 
                type="color" 
                name="color_theme" 
                id="color_theme"
                value="{{ form['color_theme'].value or '#3B82F6' }}"
                class="w-16 h-10 border rounded cursor-pointer"
            >
            <span class="px-4 py-2 bg-gray-100 rounded">{{ form['color_theme'].value or 'Default Blue' }}</span>
        </div>
    </div>
    
    <!-- Custom: File upload with preview -->
    <div class="form-group">
        <label for="featured_image" class="block font-bold mb-2">{{ form['featured_image'].label }}</label>
        <input 
            type="file" 
            name="featured_image" 
            id="featured_image"
            accept="image/*"
            class="w-full px-4 py-2 border rounded"
            onchange="previewImage(this)"
        >
        {% if form['featured_image'].value %}
            <div class="mt-4">
                <img 
                    id="imagePreview"
                    src="{{ form['featured_image'].value }}" 
                    alt="Preview" 
                    class="max-w-xs rounded shadow"
                >
            </div>
        {% else %}
            <img id="imagePreview" class="max-w-xs rounded shadow hidden mt-4">
        {% endif %}
    </div>
    
    <!-- Custom: Autocomplete/tags input -->
    <div class="form-group">
        <label for="tags" class="block font-bold mb-2">{{ form['tags'].label }}</label>
        <input 
            type="text" 
            name="tags" 
            id="tags"
            value="{{ form['tags'].value or '' }}"
            placeholder="Enter tags separated by commas"
            class="w-full px-4 py-2 border rounded"
            autocomplete="off"
            data-fetch-url="/api/tags/autocomplete"
        >
        <div id="tagsDropdown" class="hidden absolute bg-white border rounded shadow mt-1 z-10"></div>
    </div>
    
    <button type="submit" class="mt-8 px-8 py-3 bg-blue-600 text-white rounded-lg font-bold">Publish Post</button>
</form>

<!-- Initialize custom widgets -->
<script src="https://cdn.quilljs.com/1.3.6/quill.js"></script>
<script>
    // Initialize rich text editor
    const quill = new Quill('#editor', {
        theme: 'snow',
        modules: {
            toolbar: [
                [{ 'header': [1, 2, 3, false] }],
                ['bold', 'italic', 'underline', 'strike'],
                ['blockquote', 'code-block'],
                ['link', 'image'],
                [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                ['clean']
            ]
        }
    });
    
    // Sync hidden textarea with rich editor
    document.querySelector('form').addEventListener('submit', () => {
        document.getElementById('content').value = quill.root.innerHTML;
    });
    
    // Load existing content
    const content = `{{ form['content'].value | safe }}`;
    if (content) {
        quill.root.innerHTML = content;
    }
    
    // Image preview
    function previewImage(input) {
        const preview = document.getElementById('imagePreview');
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = (e) => {
                preview.src = e.target.result;
                preview.classList.remove('hidden');
            };
            reader.readAsDataURL(input.files[0]);
        }
    }
    
    // Tags autocomplete
    document.getElementById('tags').addEventListener('input', debounce(async (e) => {
        const query = e.target.value;
        if (query.length < 1) return;
        
        const url = e.target.dataset.fetchUrl + '?q=' + encodeURIComponent(query);
        const response = await fetch(url);
        const tags = await response.json();
        
        const dropdown = document.getElementById('tagsDropdown');
        dropdown.innerHTML = tags.map(tag => 
            `<div class="px-4 py-2 hover:bg-gray-100 cursor-pointer">${tag}</div>`
        ).join('');
        dropdown.classList.remove('hidden');
    }, 300));
    
    // Debounce helper
    function debounce(fn, delay) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn(...args), delay);
        };
    }
</script>
```

---

**Next Steps**: [Exploring the ORM](orm.md)
