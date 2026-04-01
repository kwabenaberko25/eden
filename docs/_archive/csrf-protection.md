# CSRF Protection & Session-Less Handling 🛡️

Cross-Site Request Forgery (CSRF) attacks trick users into submitting unintended requests. Eden's CSRF middleware protects form submissions, but requires special handling when sessions aren't available. This guide covers both standard and session-less CSRF protection.

---

## CSRF Overview

### The Attack

```
1. Attacker hosts evil.com
2. With evil.js:
   <img src="https://yourapp.com/users/123/delete" />

3. User logged into yourapp.com visits evil.com
4. Browser automatically sends auth cookies
5. Your app deletes user 123! 😱
```

### The Defense

CSRF tokens prevent this by requiring proof the request came from your site:

```html
<form method="POST" action="/users/update">
    <!-- Token proves this came from your form -->
    <input type="hidden" name="csrf_token" value="xyz123" />
    
    <!-- Evil site can't get the token -->
    <input type="text" name="username" />
    <button>Save</button>
</form>
```

---

## Standard CSRF Protection

### How It Works

```
1. User loads form
   GET /users/edit
   → Server generates random token, stores in session
   → HTML includes <input name="csrf_token" value="token123">

2. User submits form
   POST /users/update
   → Browser includes csrftoken cookie (and form field)
   → Server verifies token matches session
   → If no match → REJECT

Why it works:
- Evil site can't read the token (same-origin policy)
- Evil site can't set cookies (SameSite=Lax)
- So it can't complete a valid request
```

### Enable CSRF Middleware

```python
from eden import Eden

app = Eden(__name__)

# Add middleware (requires SessionMiddleware)
app.add_middleware("session")  # Must come first
app.add_middleware("csrf")     # CSRF requires session
```

### Add Token to Forms

**In templates:**

```html
@extends("layouts/base")

@section("content") {
<form method="POST" action="/users/update">
    <!-- Automatically included -->
    @csrf
    
    <input type="text" name="username" />
    <button>Save</button>
</form>
}
```

**Manually:**

```html
<form method="POST" action="/users/update">
    <input type="hidden" 
           name="csrf_token" 
           value="{{ csrf_token }}" />
    
    <input type="text" name="username" />
    <button>Save</button>
</form>
```

### AJAX/HTMX Requests

Eden automatically injects the token for AJAX requests:

```javascript
// HTMX automatically handles it
<form hx-post="/users/update" hx-target="#result">
    <input type="text" name="username" />
    <button>Save</button>
</form>

// JavaScript fetch - token in header
const token = document.cookie.split('; ')
    .find(row => row.startsWith('csrftoken='))
    .split('=')[1];

await fetch('/users/update', {
    method: 'POST',
    headers: {
        'X-CSRF-Token': token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({username: 'new-name'})
});
```

---

## Session-Less Pages (The Problem)

### When Sessions Aren't Available

Some pages don't use sessions (e.g., completely public pages, SPAs, mobile apps):

```python
# This page doesn't authenticate
@app.get("/news/article/{id}")
async def show_article(id: int, request):
    article = await Article.get(id)
    return request.render("article.html", {"article": article})

# User not authenticated, no session = no CSRF token in session
# Calling get_csrf_token(request) generates a token anyway
# But it won't validate on POST because... where's it stored?
```

### The Specific Challenge

**Normal flow:**
```
1. GET /form
   → Session created
   → Token stored in session["csrf_token"]
   → Token included in HTML

2. POST /form  
   → Browser sends token in form AND cookie
   → Server checks: form_token == session["csrf_token"]
   → ✓ Matches!
```

**Session-less flow:**
```
1. GET /form (no auth, no session)
   → No session created
   → Server generates token but... doesn't store it
   → Token included in HTML

2. POST /form
   → Browser sends token
   → Server generates temp token for comparison
   → But no session to validate against
   → ❌ Can't verify!
```

---

## Solution: Token Signing

### Token-Based CSRF

Generate **signed** tokens that don't require server-side storage:

```python
from eden.security.csrf import generate_csrf_token, get_csrf_token

# get_csrf_token is smart:
# - If session exists: store & return session token
# - If no session: generate signed token (self-validating)

@app.get("/contact")
async def contact_form(request):
    token = get_csrf_token(request)
    # Token works whether session exists or not!
    return request.render("contact.html", {"csrf_token": token})
```

### How Signed Tokens Work

```
1. Server creates token: PAYLOAD|SIGNATURE
   ```
   Token: "user:alice|timestamp:1234|hmac:xyz"
   ```

2. Server signs with secret key using HMAC
   ```
   Signature = HMAC-SHA256("user:alice|timestamp:1234", SECRET)
   ```

3. On form submission, verify signature
   ```
   Recompute: HMAC-SHA256("user:alice|timestamp:1234", SECRET)
   Does it match signature in token? → Pass/Fail
   ```

4. No database needed!
   - Evil site can't forge signature (doesn't know SECRET)
   - Token can't be modified without breaking signature
```

### Eden's Implementation

```python
# Eden handles this automatically

from eden.context import get_csrf_token

@app.get("/contact")
async def contact_form(request):
    # Returns session token if session exists
    # Returns signed token if no session
    token = get_csrf_token(request)
    
    return request.render("contact.html", {"csrf_token": token})

@app.post("/contact")  
async def submit_contact(request):
    # CSRFMiddleware validates signature automatically
    form_data = await request.form()
    
    # If we get here, CSRF token was valid!
    # (Token either matched session or signature was valid)
    
    message = form_data.get("message")
    await ContactForm.create(message=message)
    
    return {"status": "submitted"}
```

---

## Practical Scenarios

### Scenario 1: Public Comments (No Auth)

```python
@app.get("/articles/{id}")
async def show_article(id: int, request):
    article = await Article.get(id)
    
    # No authentication required
    # But comment form needs CSRF token
    csrf_token = get_csrf_token(request)
    
    return request.render("article.html", {
        "article": article,
        "csrf_token": csrf_token
    })

@app.post("/articles/{id}/comments")
async def post_comment(id: int, request):
    # CSRFMiddleware validates token
    # No session required!
    form_data = await request.form()
    
    comment = await Comment.create(
        article_id=id,
        text=form_data["text"],
        ip_address=request.client.host
    )
    
    return request.render("comment.html", {"comment": comment})
```

**Template:**

```html
<form method="POST" action="/articles/{{ article.id }}/comments">
    @csrf  <!-- Handles both session and session-less tokens -->
    
    <textarea name="text"></textarea>
    <button>Post Comment</button>
</form>
```

### Scenario 2: Unauthenticated API (Mobile App)

Mobile apps can't use session cookies. Use signed tokens:

```python
@app.post("/api/v1/register")
async def register(request):
    # No session, no auth
    # But still vulnerable to CSRF
    
    body = await request.json()
    
    # Validate CSRF token from header
    token = request.headers.get("X-CSRF-Token")
    csrf_token_from_session = get_csrf_token(request)
    
    if not verify_csrf_token(token, csrf_token_from_session):
        return {"error": "Invalid CSRF token"}, 403
    
    user = await User.create(**body)
    return {"user_id": user.id}
```

**Client code:**

```javascript
// 1. Get initial page with CSRF token
const response = await fetch('https://yourapp.com/');
const html = await response.text();

// 2. Extract token from meta tag
const token = html.match(/name="csrf_token" content="([^"]+)"/)[1];

// 3. Use in API calls
await fetch('https://yourapp.com/api/v1/register', {
    method: 'POST',
    headers: {
        'X-CSRF-Token': token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'secure'
    })
});
```

### Scenario 3: Hybrid: Logged-In Users + Public Forms

```python
from eden.context import user

@app.get("/checkout")
async def checkout(request):
    csrf_token = get_csrf_token(request)
    
    # User context is optional
    cart = None
    if user:
        cart = await Cart.get(user.id)
    else:
        cart_data = request.session.get("temp_cart", {})
    
    return request.render("checkout.html", {
        "csrf_token": csrf_token,
        "cart": cart,
        "is_authenticated": bool(user)
    })

@app.post("/checkout")
async def process_checkout(request):
    # CSRF token is always validated
    form_data = await request.form()
    
    if user:
        # Authenticated - use user's cart
        cart = await Cart.get(user.id)
    else:
        # Guest checkout
        cart_data = request.session.get("temp_cart", {})
    
    # Process payment...
    return {"order_id": order.id}
```

---

## Exempting Routes from CSRF

Sometimes CSRF checks must be skipped (webhooks, external APIs):

```python
# Configure middleware with exclusions
app.add_middleware(
    "csrf",
    exclude_paths=[
        "/webhook/stripe",      # Stripe doesn't send CSRF tokens
        "/api/external/accept", # External API integration
        "/health",              # Health checks
    ]
)
```

**Or decorators:**

```python
@app.post("/webhook/stripe")
@skip_csrf_check  # Decorator version
async def stripe_webhook(request):
    # Stripe sends signature in header instead of CSRF token
    signature = request.headers.get("Stripe-Signature")
    
    # Verify webhook signature
    body = await request.body()
    if verify_stripe_signature(body, signature):
        # Process webhook
        pass
    
    return {"status": "received"}
```

---

## Testing CSRF Protection

### Unit Tests

```python
import pytest
from unittest.mock import Mock

def test_csrf_token_generation():
    """Test that tokens are generated and signed."""
    request = Mock()
    request.session = None  # No session
    
    token = get_csrf_token(request)
    
    assert token is not None
    assert len(token) > 32  # Should be cryptographically long

def test_csrf_token_validation():
    """Test that tampered tokens fail."""
    token = "valid_token|invalid_signature"
    
    result = verify_csrf_token(token, "valid_token|valid_signature")
    
    assert result is False
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_csrf_form_submission(client):
    """Test form submission with CSRF token."""
    
    # 1. GET form to extract token
    response = client.get("/contact")
    html = response.text
    
    # Extract token from HTML
    import re
    token = re.search(
        r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"',
        html
    ).group(1)
    
    # 2. POST form with token
    response = client.post(
        "/contact",
        data={
            "csrf_token": token,
            "message": "Hello"
        }
    )
    
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_csrf_missing_token_rejected(client):
    """Test that missing CSRF token is rejected."""
    
    response = client.post(
        "/contact",
        data={"message": "Hello"}
        # No csrf_token!
    )
    
    assert response.status_code == 403
```

---

## Troubleshooting

### Problem: CSRF token mismatch on valid forms

**Cause**: Session not enabled or token lost

```python
# ❌ Wrong
app.add_middleware("csrf")  # CSRF without session!

# ✓ Correct
app.add_middleware("session")  # Must come first
app.add_middleware("csrf")     # Then CSRF
```

### Problem: Token works on first request, fails on second

**Cause**: New session created each request (no session persistence)

```python
# Check your SessionMiddleware config
app.add_middleware(
    "session",
    secret_key="keep-same",  # ← Don't regenerate
    # session_cookie_name="session",
)
```

### Problem: AJAX requests failing with CSRF errors

**Cause**: Token not included in headers

```javascript
// ❌ Wrong - token not sent
await fetch('/api/users', {
    method: 'POST',
    body: JSON.stringify({name: 'Alice'})
});

// ✓ Correct - token in header
const token = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    .split('=')[1];

await fetch('/api/users', {
    method: 'POST',
    headers: {
        'X-CSRF-Token': token
    },
    body: JSON.stringify({name: 'Alice'})
});
```

### Problem: CORS requests failing CSRF

**Cause**: CSRF checks before CORS checks

```python
# Order matters!
app.add_middleware("cors")    # CORS first
app.add_middleware("session")  # Then session
app.add_middleware("csrf")     # Then CSRF
```

---

## API Reference

### CSRF Functions

```python
# Generate or get CSRF token
get_csrf_token(request: Request) -> str
    # Returns session token if session exists
    # Returns signed token if no session

# Verify CSRF token  
verify_csrf_token(token: str, expected: str) -> bool
    # Checks session token or validates signature

# Generate new token
generate_csrf_token() -> str
    # Creates a new random token
```

### Middleware Configuration

```python
CSRFMiddleware(
    app,
    exclude_paths: list[str] = None  # Routes to skip CSRF
)

# Example
app.add_middleware(
    "csrf",
    exclude_paths=[
        "/webhook/stripe",
        "/health",
    ]
)
```

---

## Next Steps

- [Security Best Practices](security.md) - Complete security guide
- [Session Middleware](../guides/sessions.md) - Session configuration
- [Forms & Validation](../tutorial/task6_forms.md) - Form handling
- [HTMX Integration](../guides/htmx.md) - Real-time form interactions
