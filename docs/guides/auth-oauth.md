# Social Login (OAuth 2.0) 🌐

Eden ships with built-in support for major OAuth providers, allowing your users to sign in with accounts they already have.

## Supported Providers

- **Google**
- **GitHub**
- **Discord**
- **Twitter/X**

---

## Configuration

OAuth requires sensitive credentials (Client ID and Secret) usually obtained from the provider's developer portal.

### 1. Register your App
Register your application with the provider and set the **Redirect URI**. In Eden, the standard format is:
`https://yourdomain.com/auth/oauth/{provider}/callback`

### 2. Environment Variables
Add your keys to your `.env` file:
```bash
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-yyyy
```

---

## Mounting OAuth Routes

Use the `OAuthManager` to register providers and mount the necessary routes to your app.

```python
import os
from eden.auth.oauth import OAuthManager

oauth = OAuthManager()

# Register Google
oauth.register_google(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
)

# Mount routes (/auth/oauth/google/login, etc.)
oauth.mount(app)
```

---

## Customizing the Flow

### User Creation Hook
By default, Eden creates a new user if one doesn't exist. you can intercept this to add custom logic (e.g., assigning a default role).

```python
@oauth.on_user_created
async def setup_oauth_user(user, provider_data):
    user.role = "member"
    await user.save()
    
    # Send a welcome ping
    await logger.info(f"New user {user.email} joined via {provider_data['provider']}")
```

### Account Linking
If a user signs in with Google using an email that already exists in your database (and was verified), Eden will automatically link the Google account to the existing record.

---

## Template Integration

Simply link to the generated login route.

```html
<a href="/auth/oauth/google/login" class="btn btn-google">
    <img src="/static/google-icon.svg"> Sign in with Google
</a>

<a href="/auth/oauth/github/login" class="btn btn-github">
    Sign in with GitHub
</a>
```

---

## Security Features

- **State Verification**: Prevents CSRF attacks during the OAuth handshake.
- **Secure Cookies**: Successful login issues a standard Eden session cookie.
- **Provider Scopes**: Customize what data you request from the provider.
  ```python
  oauth.register_google(..., scope=["openid", "email", "profile"])
  ```

---

**Next Steps**: [Multi-Tenancy Patterns](tenancy.md)
