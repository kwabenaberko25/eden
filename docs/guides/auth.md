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
user.roles             # ['admin', 'user']
user.permissions       # ['can_edit', 'can_delete']
user.is_superuser      # True if superuser

```

### Social Accounts
Eden supports linking multiple social providers to a single user account.

---

## Role-Based Access Control (RBAC) 👑

Eden uses a simple yet powerful role-based system. Roles are strings, and you can restrict access to routes using decorators.

### Restricting Access

| Decorator | Argument | Description |
| :--- | :--- | :--- |
| `@login_required` | None | Requires any authenticated user. |
| `@roles_required` | `list[str]` | Requires at least one of these roles. |
| `@permissions_required` | `list[str]` | Requires ALL of these permissions. |
| `@require_permission` | `str` | Checks hierarchy (admin > manager). |

### Roles & Permissions

You can secure endpoints using roles and permissions.

```python
from eden.auth import roles_required

@app.get("/admin")
@roles_required(["admin"])
async def admin_dashboard(request):
    return render_template("admin.html")
```


---

## Social Login (OAuth)

Eden supports Google and GitHub OAuth out of the box.

### Configuration

Add your credentials to your `.env` file:

```text
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

### Automatic Configuration

The easiest way to use social login is to let Eden handle the routes.

```python
from eden.auth.oauth import OAuthManager

oauth = OAuthManager()
oauth.register_google(
    client_id=os.getenv("GOOGLE_ID"),
    client_secret=os.getenv("GOOGLE_SECRET")
)

# Mounts routes at /auth/oauth/google/login etc.
oauth.mount(app)
```

### Profile & Unlinking

Once mounted, Eden provides a `/profile` view where users can see linked accounts and unlink them. Note that unlinking the last remaining login method (if no password is set) is prevented for security.


---

## API Token Authentication 🔑

For stateless API access, Eden provides a secure, hashed API Key system.

### Generating a Key

```python
from eden import APIKey

# Generates a key object and the raw string (show this only once!)
api_key, raw_key = await APIKey.generate(
    session,
    user=request.user, 
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

## JWT Provider

For stateless API authentication, Eden ships with a `JWTProvider` (aliased from `JWTBackend`).

```python
from eden.auth.providers import JWTProvider

provider = JWTProvider(secret="top-secret", algorithm="HS256")

# Creating a token
token = provider.encode({"sub": user.id, "scope": "admin"}, expires_in=3600)

# Verifying a token
payload = provider.decode(token)
```

> **Note**: `encode()` accepts an optional `expires_in` parameter (in seconds).
> You can also use `create_access_token()` and `create_refresh_token()` for
> fine-grained control over token types.

**Next Steps**: [Templating Directives](templating.md)
