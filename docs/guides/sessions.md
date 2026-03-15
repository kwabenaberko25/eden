# Sessions 🔐

Session management is critical for web applications. Eden provides secure, async-first session handling.

## Configuration

```python
from eden import Eden
from eden.middleware import SessionMiddleware

app = Eden(__name__)

# Configure session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(\"SECRET_KEY\"),
    session_cookie=\"sessionid\",
    max_age=86400 * 7,  # 7 days
    https_only=True,
    same_site=\"Lax\"
)
```

## Usage

```python
@app.post(\"/login\")
async def login(request):
    \"\"\"Store user in session.\"\"\"
    user = await authenticate(request)
    if user:
        request.session[\"user_id\"] = str(user.id)
        request.session[\"username\"] = user.username
        return {\"success\": True}
    return {\"error\": \"Invalid credentials\"}, 401

@app.get(\"/profile\")
async def profile(request):
    \"\"\"Access session data.\"\"\"
    user_id = request.session.get(\"user_id\")
    if not user_id:
        return {\"error\": \"Not logged in\"}, 401
    
    user = await User.get(int(user_id))
    return user.to_dict()

@app.post(\"/logout\")
async def logout(request):
    \"\"\"Clear session.\"\"\"
    request.session.clear()
    return {\"success\": True}
```

## Best Practices

- ✅ Store minimal data in sessions (IDs, not full objects)
- ✅ Use `https_only=True` in production
- ✅ Set appropriate `max_age` for security
- ✅ Clear sessions on logout
- ✅ Regenerate session IDs on privilege escalation
