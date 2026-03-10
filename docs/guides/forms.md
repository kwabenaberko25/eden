# Forms & Validation 📝

Eden's form system is powered by **Pydantic v2**, providing ultra-fast, type-safe validation and automatic HTML rendering.

## The `BaseForm`

Define your forms as classes. Eden handles the mapping from request data to these objects.

```python
from eden.forms import BaseForm, FormField
from eden.validators import String, Email

class ContactForm(BaseForm):
    name: str = FormField(label="Your Name", validators=[String(min_length=2)])
    email: str = FormField(label="Email Address", validators=[Email()])
    message: str = FormField(widget="textarea")
```

---

## Rendering Forms

You can render fields individually or the entire form at once.

### Automatic Rendering

```html
<form method="POST">
    @csrf
    {{ form.render() }}
    <button type="submit">Send</button>
</form>
```

### Manual Rendering (for custom layouts)

```html
<div>
    <label>{{ form.email.label }}</label>
    {{ form.email.render(class="input") }}
    @error("email") { <span class="error">{{ message }}</span> }
</div>
```

---

## Validation Logic

Handling form submissions in your route is a breeze.

```python
@app.post("/contact")
async def handle_contact(request):
    form = await ContactForm.from_request(request)
    
    if await form.validate():
        # data is now cast and clean
        send_email(form.email, form.message)
        return RedirectResponse("/success")
    
    return render_template("contact.html", {"form": form})
```

---

## The Validator Suite 🛡️

Eden includes a massive library of standalone validators for common data types.

| Category | Validators |
| :--- | :--- |
| **Common** | `Email`, `URL`, `IPAddress`, `Phone`, `Slug` |
| **Finance** | `CreditCard`, `IBAN`, `BIC`, `VAT` |
| **Identity** | `NationalID`, `Passport`, `Postcode` |
| **Security** | `Password` (strength checking), `JWT` |
| **Geo** | `GPS`, `Coordinate` |

---

## File Uploads 📤

Eden handles both small bytes and large file streams.

```python
from eden.forms import FileField

class UploadForm(BaseForm):
    avatar = FileField()

# In the route
form = await UploadForm.from_request(request)
if await form.validate():
    file_path = await form.avatar.save("uploads/")
```

## FormField Options 🎛️

The `FormField` allows you to define how data is validated and rendered.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `label` | `str` | Display label for the field. |
| `widget` | `str` | Type of input (`text`, `textarea`, `select`, `checkbox`, `radio`). |
| `validators` | `list` | List of `eden.validators`. |
| `default` | `Any` | Initial value for the field. |
| `choices` | `list` | Options for `select` or `radio` widgets. |
| `required` | `bool` | Whether the field is mandatory (default: `True`). |
| `help_text` | `str` | Additional context rendered below the field. |

---

## Form Directives Reference 🏷️

Eden provides specialized directives for form rendering inside templates.

| Directive | Description |
| :--- | :--- |
| `@csrf` | Emits a CSRF token hidden input. Mut be used in every POST form. |
| `@method(name)`| Spoofs HTTP methods for browsers (e.g., `@method('PUT')`). |
| `@error(name)` | Opens a block if the field `name` has validation errors. |
| `@old(name)` | Retrieves value from the previous request for that field. |
| `@render_field(f)`| Renders the full field (label + input + errors). |

### Example: Component-Based Rendering

```html
<form action="/login" method="POST">
    @csrf
    @for(field in form.fields) {
        <div class="mb-4">
            @render_field(field)
        </div>
    }
    <button type="submit">Login</button>
</form>
```

---

## Real-World Example: Multi-Step Wizard 🧙‍♂️

For complex registration flows, you can split forms across multiple routes and use the session for state management.

```python
@app.get("/register/step-1")
async def step_1(request):
    form = await AccountForm.from_request(request)
    return render_template("step1.html", {"form": form})

@app.post("/register/step-1")
async def handle_step_1(request):
    form = await AccountForm.from_request(request)
    if await form.validate():
        request.session["reg_data"] = form.data
        return RedirectResponse("/register/step-2")
    return render_template("step1.html", {"form": form})
```

### In-Memory Validation

You can also validate raw dictionaries against form structures.

```python
data = {"email": "invalid"}
form = ContactForm(data=data)
is_valid = await form.validate() # False
```

**Next Steps**: [Multi-Tenancy](tenancy.md)
