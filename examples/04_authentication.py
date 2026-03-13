"""
04_authentication.py — User Login & Protected Routes

Add user authentication with login, logout, and permission-based
access control.

Run:
    python examples/04_authentication.py
"""

from eden import Eden, Model, StringField, Request, login_required, render_template

app = Eden(title="Auth App", debug=True, secret_key="super-secret")
app.state.database_url = "sqlite+aiosqlite:///auth.db"


class User(Model):
    """User model."""
    username = StringField(max_length=100, unique=True)
    email = StringField(max_length=200)
    password_hash = StringField()


class Post(Model):
    """User's blog post."""
    title = StringField(max_length=200)
    content = StringField()
    user_id = IntField()


@app.get("/")
async def index():
    return render_template("index.html")


@app.post("/login")
async def login(request: Request):
    """Handle login form."""
    form = await request.form()
    # Hash password, lookup user, set session
    request.session["user_id"] = 1  # Example
    return {"redirect": "/dashboard"}


@app.get("/dashboard")
@login_required
async def dashboard(request: Request):
    """Protected route - requires login."""
    user_id = request.session.get("user_id")
    return render_template("dashboard.html", {"user_id": user_id})


@app.post("/logout")
async def logout(request: Request):
    """Clear session."""
    request.session.clear()
    return {"redirect": "/"}


if __name__ == "__main__":
    app.setup_defaults()
    app.run(port=8000)

# What you learned:
#   - @login_required decorator
#   - Session management: request.session
#   - Password hashing (use argon2-cffi)
#   - Protected routes
#
# Next: See 05_advanced_orm.py for relationships and queries
