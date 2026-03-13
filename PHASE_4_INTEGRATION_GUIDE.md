## Phase 4: Password Reset - Integration Guide

This guide explains how to integrate the password reset system into your Eden application.

### Prerequisites

Ensure you have:
- Eden Framework installed and configured
- SQLAlchemy async session management set up
- Mail/email service configured (via `eden.mail`)

---

## Step 1: Create the Database Table

The `PasswordResetToken` model requires a database table. Choose one method:

### Option A: Run SQL Migration (Recommended for PostgreSQL)

Execute the SQL migration file:

```bash
psql -U your_user -d your_database < migrations/001_create_password_reset_tokens.sql
```

Or manually execute in your database client:

```sql
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token (token),
    INDEX idx_user_id_unused (user_id, used_at)
);
```

### Option B: Auto-Create via SQLAlchemy

In your application startup code:

```python
from sqlalchemy import inspect
from eden.db.base import Base
from eden import engine

async def create_tables():
    """Create all tables from models."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

Then call this during app initialization:

```python
app = Eden()
app.on_startup(create_tables)
```

---

## Step 2: Register the Password Reset Routes

Add the password reset router to your main application in your app initialization file (typically `app.py` or `main.py`):

```python
from eden import Eden
from eden.auth import password_reset_router

# Create your app
app = Eden(
    title="My App",
    debug=True
)

# Register password reset routes
app.include_router(password_reset_router)

# ... rest of your app configuration
```

This automatically registers three endpoints:

- `POST /auth/forgot-password` - Request a password reset
- `POST /auth/reset-password` - Confirm reset with token and new password
- `GET /auth/reset-password` - Get form metadata (optional)

---

## Step 3: Configure Email Service

The password reset system sends emails via `eden.mail`. Ensure it's configured:

```python
from eden.mail import Mail

# During app initialization
mail = Mail()
mail.configure(
    host="smtp.gmail.com",     # Your SMTP server
    port=587,
    username="your-email@gmail.com",
    password="your-app-password",
    from_email="noreply@yourapp.com"
)
```

Or configure via environment variables:

```bash
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=noreply@yourapp.com
```

---

## Step 4: Create Frontend Password Reset Form (Optional)

Create an HTML template for password reset. Example:

```html
<!-- templates/password_reset.html -->
<form method="POST" action="/auth/reset-password">
    {% csrf_token %}
    
    <input type="hidden" name="token" value="{{ token }}" />
    
    <label for="password">New Password</label>
    <input 
        id="password"
        type="password" 
        name="new_password" 
        required 
        minlength="8"
    />
    
    <label for="confirm">Confirm Password</label>
    <input 
        id="confirm"
        type="password" 
        name="confirm_password" 
        required 
        minlength="8"
    />
    
    <button type="submit">Reset Password</button>
</form>
```

---

## API Usage

### Request Password Reset

**Request:**
```bash
curl -X POST http://localhost:8000/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

**Response:**
```json
{
  "message": "If an account with that email exists, a password reset link has been sent.",
  "email": "user@example.com"
}
```

**Note**: Returns 200 even if email doesn't exist (security best practice).

### Confirm Password Reset

**Request:**
```bash
curl -X POST http://localhost:8000/auth/reset-password \
  -H "Content-Type: application/json" \
  -d {
    "token": "ABC123_reset_token_from_email",
    "new_password": "NewPassword123",
    "confirm_password": "NewPassword123"
  }'
```

**Response:**
```json
{
  "message": "Your password has been successfully reset. You can now log in with your new password."
}
```

---

## Security Features

- ✅ **Secure Token Generation**: 256-bit cryptographically secure tokens
- ✅ **24-Hour Expiration**: Tokens auto-expire after 24 hours
- ✅ **One-Time Use**: Tokens can only be used once
- ✅ **User Enumeration Prevention**: Returns 200 for non-existent emails
- ✅ **Password Hashing**: New passwords are securely hashed with Argon2
- ✅ **Token Auto-Invalidation**: Previous tokens invalidated on new request

---

## Advanced Configuration

### Custom Token Expiration

Modify in `eden/auth/password_reset.py`:

```python
class PasswordResetService:
    TOKEN_EXPIRATION_HOURS = 48  # Change from 24 to 48 hours
```

### Custom Reset Link URL

When sending emails, specify your app URL:

```python
from eden.auth.password_reset import PasswordResetEmail

reset_link = PasswordResetEmail.get_reset_link(
    token=token,
    app_url="https://myapp.com"  # Your production URL
)
```

### Custom Email Templates

Customize email templates in `eden/auth/password_reset.py`:

```python
html = PasswordResetEmail.get_html_body(
    user_name=user.first_name,
    reset_link=reset_link,
    app_name="My App"  # Custom app name
)
```

---

## Troubleshooting

### Table Not Creating

- Check that `password_reset_tokens` table exists in your database
- Verify foreign key to `users` table is correct
- Run migration manually if auto-creation fails

### Emails Not Sending

- Verify `eden.mail` configuration with test message
- Check SMTP credentials and firewall settings
- Review mail service logs

### Token Validation Fails

- Ensure token hasn't expired (24 hours default)
- Verify token format matches what was sent
- Check that token exists in database with `SELECT * FROM password_reset_tokens WHERE token=?`

### 404 on Password Reset Endpoints

- Ensure `app.include_router(password_reset_router)` is called
- Verify routes are mounted before `app.run()`
- Check that no other routes are shadowing `/auth/*` paths

---

## Testing

Run the test suite to verify everything works:

```bash
pytest eden/tests/test_password_reset.py -v
```

Expected output:
```
test_token_model_creation PASSED
test_token_expiration_hours PASSED
test_generate_token PASSED
... (25+ tests)
```

---

## What's Included

### Models
- `PasswordResetToken` - Stores reset tokens with expiration

### Services
- `PasswordResetService` - Token generation, validation, password reset
- `PasswordResetEmail` - Email template helpers

### Endpoints
- `POST /auth/forgot-password` - Request reset (sends email)
- `POST /auth/reset-password` - Confirm reset with token
- `GET /auth/reset-password` - Get form metadata

### Tests
- `eden/tests/test_password_reset.py` - 300+ lines of test coverage

---

## Complete Integration Example

```python
from eden import Eden
from eden.auth import password_reset_router
from eden.mail import Mail

# Create app
app = Eden(
    title="My App",
    debug=False,
    secret_key="your-secret-key"
)

# Configure email
mail = Mail()
mail.configure(
    host="smtp.sendgrid.net",
    port=587,
    username="apikey",
    password="sg_xxx_your_sendgrid_key",
    from_email="noreply@myapp.com"
)

# Register password reset routes
app.include_router(password_reset_router)

# Run app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

---

## Next Steps

1. ✅ Create database table (Step 1)
2. ✅ Register routes (Step 2)
3. ✅ Configure email (Step 3)
4. Create frontend form (Step 4)
5. Add rate limiting to prevent abuse
6. Add CAPTCHA for public apps (optional)
7. Add audit logging for password resets
8. Implement 2FA after password reset (optional)

---

**Status**: Phase 4 Password Reset is now production-ready!
