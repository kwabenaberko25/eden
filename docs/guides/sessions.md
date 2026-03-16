# Session Management & Lifecycle 🔐

Sessions are the backbone of stateful web applications in Eden, allowing you to track users securely across multiple requests.

## Overview

Eden uses a database-backed session system combined with signed, secure cookies. This approach offers better security than client-side only JWTs for web applications, as sessions can be instantly revoked.

---

## Configuration

Control session behavior in your `app.py` or `.env`:

```python
app.config.SESSION_COOKIE_NAME = "eden_sess"
app.config.SESSION_TIMEOUT = timedelta(days=7)
app.config.SESSION_COOKIE_SECURE = True # HTTPS Only
```

---

## The Login Flow

When a user logs in, you create a `Session` record and set the corresponding cookie.

```python
from eden.auth import Session

async def login_view(request):
    user = await authenticate(request)
    
    # Create the session record
    session = await Session.create(
        user_id=user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    response = redirect("/dashboard")
    response.set_cookie("eden_sess", session.id, httponly=True)
    return response
```

---

## Session Middleware

Eden includes a built-in middleware that automatically populates `request.user` based on the session cookie.

```python
app.add_middleware("auth")
```

### How it works:
1. **Lookup**: Middleware reads the cookie.
2. **Validate**: Checks the database for a matching, non-expired session.
3. **Hydrate**: Fetches the `User` record and attaches it to `request.user`.

---

## Manual Revocation (Logout)

To log a user out, simply delete the session record.

```python
async def logout(request):
    session_id = request.cookies.get("eden_sess")
    
    if session_id:
        await Session.filter(id=session_id).delete()
        
    response = redirect("/")
    response.delete_cookie("eden_sess")
    return response
```

### Remote Logout
Since sessions are in the database, you can implement a "Log out of all devices" feature:
```python
await Session.filter(user_id=user.id).delete()
```

---

## Security Best Practices

- **HttpOnly**: Eden sets this by default to prevent XSS from stealing session IDs.
- **SameSite**: Set to `Lax` or `Strict` to mitigate CSRF.
- **Rotation**: Consider generating a new session ID after a privilege change (e.g., login).

---

**Next Steps**: [Role-Based Access (RBAC)](auth-rbac.md)
