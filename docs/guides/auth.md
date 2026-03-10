# Authentication & Security 🛡️

Eden provides a comprehensive, session-based and token-based authentication system designed for both traditional web apps and modern APIs.

## Core Models

### `User` & `BaseUser`

The foundation of identity in Eden. `BaseUser` provides the fields and methods for authentication, while `User` is the default implementation.

```python
from eden.auth import User

# Properties
user.is_authenticated  # True/False
user.email
user.role              # 'admin', 'editor', 'user'
```

### Social Accounts
Eden supports linking multiple social providers to a single user account.

---

## Role-Based Access Control (RBAC) 👑

Eden uses a simple yet powerful role-based system. Roles are strings, and you can restrict access to routes using decorators.

### Restricting Access

```python
from eden.auth import roles_required, permissions_required

@app.get("/admin")
@roles_required(["admin"])
async def admin_dashboard(request):
    return render_template("admin.html")

@app.post("/delete-entry")
@permissions_required(["can_delete"])
async def delete_entry(request):
    ...
```

---

## OAuth & Social Login 🌐

Eden currently supports **Google** and **GitHub** out of the box.

### Configuration

Add your credentials to your `.env` file:

```text
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

### The Login Flow
```python
@app.get("/login/google")
async def google_login(request):
    return await app.auth.redirect_to_provider("google", request)

@app.get("/auth/callback/google")
async def google_callback(request):
    user = await app.auth.handle_callback("google", request)
    return RedirectResponse("/")
```

---

## API Token Authentication 🔑

For stateless API access, Eden provides a secure, hashed API Key system.

### Generating a Key

```python
from eden import APIKey

# Generates a key object and the raw string (show this only once!)
key_obj, raw_key = await APIKey.generate(
    user_id=user.id, 
    name="Mobile App Token"
)
```

### Using the Key
Clients should send the key in the `Authorization` header:
`Authorization: Bearer ed_...`

---

## Security Middleware Suite 🧱

Eden protects your app automatically when you enable the security middleware.

```python
app.add_middleware("security")  # CSP, HSTS, X-Frame-Options
app.add_middleware("csrf")      # CSRF Protection
app.add_middleware("ratelimit") # Rate Limiting
```

### CSRF in Templates

Always include the `@csrf` directive in your forms:

```html
<form method="POST">
    @csrf
    <input type="text" name="data">
    <button type="submit">Send</button>
</form>
```

---

## Security & Data Validation Reference 🛠️

Eden provides a comprehensive suite of validators in `eden.validators`. These can be used standalone or as Pydantic types.

| Validator | Type Hint | Description |
| :--- | :--- | :--- |
| `validate_email` | `EdenEmail` | RFC 5322 structural check. |
| `validate_phone` | `EdenPhone` | E.164 and local format validation. |
| `validate_password` | `str` | Checks length, case, digits, and special chars. |
| `validate_slug` | `EdenSlug` | Lowercase alphanumeric with hyphens. |
| `validate_url` | `EdenURL` | Full URL structure and scheme check. |
| `validate_ip` | `str` | IPv4/IPv6 validation. |
| `validate_credit_card` | `str` | Luhn algorithm + brand detection. |
| `validate_gps` | `Coordinate` | Latitude/Longitude range checks. |
| `validate_file_type` | `dict` | MIME type and file size (MB) validation. |
| `validate_iban` | `str` | International Bank Account Number. |
| `validate_national_id` | `str` | GH (NIA), US (SSN), GB (NI) support. |

### Usage Example
```python
from eden.validators import validate_email, validate_password

def register_view(request):
    email_res = validate_email(request.form.get("email"))
    pass_res = validate_password(request.form.get("password"))

    if not email_res.ok:
        return {"error": email_res.error}
```

---

## Password Security & Hashing 🔒

Eden uses **Argon2** (via `argon2-cffi`) by default for industry-leading password security. All User models inherit `set_password` and `check_password` methods that handle salting and hashing automatically.

---

## Example: Custom JWT Provider 🛡️

If your application needs custom JWT tokens (e.g., for short-lived access), you can use the built-in `JWTProvider`.

```python
from eden.auth import JWTProvider

provider = JWTProvider(secret="top-secret", algorithm="HS256")

# Creating a token
token = provider.encode({"sub": user.id, "scope": "admin"}, expires_in=3600)

# Verifying a token
payload = provider.decode(token)
```

**Next Steps**: [Templating Directives](templating.md)
