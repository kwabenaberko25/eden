# Getting Started with Eden

This tutorial will show you how to create a new application using your local installation of the **Eden** web framework. We will cover project setup, models, forms, separated views, HTML templates, and routing.

## 1. Project Setup (Without Going Online)

You can build your new app entirely offline by "sourcing" your local Eden project. We'll use `uv` (or standard `pip` if you prefer) to install Eden directly from its source folder.

```bash
# 1. Create a new folder for your app
mkdir my_awesome_app
cd my_awesome_app

# 2. Create and activate a virtual environment
uv venv
# On Windows: .venv\Scripts\activate
# On Mac/Linux: source .venv/bin/activate

# 3. Install your local Eden project in editable mode
# Replace 'C:\ideas\eden' with the actual path to your eden framework repository
uv pip install -e C:\ideas\eden
```

Your new project is now ready. 

## 2. Recommended Directory Structure

In your `my_awesome_app` folder, create the following files to keep your code organized and separated:

```text
my_awesome_app/
├── app.py           # The main entrypoint and router
├── models.py        # Database entities
├── forms.py         # Data validation and input structures
├── views.py         # Route handlers / controllers
└── templates/       # HTML files separated from Python
    ├── base.html
    └── home.html
```

---

## 3. Defining Models (`models.py`)

Eden provides a highly expressive ORM. Define your models here. Because Eden recently implemented *Auto-Session Injection*, you won't need to manually pass sessions to read/write most data!

```python
import uuid
from sqlalchemy.orm import Mapped
from eden import EdenModel, StringField, BoolField, IntField
from eden.db.fields import ForeignKeyField

class User(EdenModel):
    name: Mapped[str] = StringField(max_length=100)
    email: Mapped[str] = StringField(max_length=150, unique=True)
    is_active: Mapped[bool] = BoolField(default=True)

class Post(EdenModel):
    title: Mapped[str] = StringField(max_length=200)
    content: Mapped[str] = StringField()
    author_id: Mapped[uuid.UUID] = ForeignKeyField("users.id")
```

---

## 4. Defining Forms (`forms.py`)

Define how you receive and validate user data using Pydantic schemas and Eden's `BaseForm`.

```python
from pydantic import BaseModel, EmailStr
from eden.forms import BaseForm

class UserSchema(BaseModel):
    name: str
    email: EmailStr
    age: int

class UserForm(BaseForm):
    schema = UserSchema
```

---

## 5. Separated HTML Templates (`templates/`)

Do not embed HTML in your `.py` files. Instead, use Eden's templating engine (which includes powerful directives like `@for` and `@if`) by placing `.html` files in your `templates/` folder.

**`templates/base.html`** (The layout wrapper):
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>My Eden App</title>
    <!-- Add your Tailwind CSS or local stylesheets here -->
</head>
<body class="bg-gray-900 text-white">
    <main class="container mx-auto p-4">
        <!-- Everything else gets injected here -->
        {% block content %}{% endblock content %}
    </main>
</body>
</html>
```

**`templates/home.html`** (The page content):
```html
{% extends "base.html" %}

{% block content %}
    <h1 class="text-3xl font-bold text-blue-500 mb-6">User Directory</h1>
    
    @if (users) {
        <ul class="space-y-2">
        @for (user in users) {
            <li class="p-4 bg-gray-800 rounded-lg shadow-sm">
                {{ user.name }} <span class="text-gray-400">({{ user.email }})</span>
            </li>
        }
        </ul>
    } @else {
        <p class="text-gray-400">No users found in the database.</p>
    }
{% endblock content %}
```

---

## 6. Creating Views (`views.py`)

Keep your view logic ultra-clean by simply fetching data with the ORM and passing it to your templates.

```python
from eden.templating import EdenTemplates
from models import User
from forms import UserForm

# Initialize the template engine pointing to your templates folder
templates = EdenTemplates(directory="templates")

async def home(request):
    """
    Handles GET /
    Fetches users and renders the HTML template.
    """
    # Fetch data cleanly; session is handled automatically by Eden!
    users = await User.all()
    
    # Return the rendered template response
    return templates.template_response("home.html", {
        "request": request,
        "users": users
    })

async def create_user(request):
    """
    Handles POST /users/new
    """
    if request.method == "POST":
        form_data = await request.form()
        form = UserForm(data=form_data)
        
        if form.is_valid():
            # Save the new user to the database
            await User.create(**form.data)
            # You would typically return a redirect here
            return templates.template_response("home.html", {
                 "request": request, 
                 "users": await User.all(),
                 "success": True
            })
            
    # Fallback/GET: Render empty form (or form with errors)
    return templates.template_response("create_user.html", {
        "request": request, 
        "form": UserForm()
    })
```

---

## 7. Pointing it all together (`app.py`)

Finally, hook your routes, initialize your database, and run the `Eden` application.

```python
from eden import Eden, Database
from views import home, create_user

# 1. Initialize Database (e.g., local sqlite file)
db = Database("sqlite+aiosqlite:///app.db")

# 2. Initialize Eden server
app = Eden(debug=True)

# 3. Setup Routes cleanly
app.get("/")(home)
app.get("/users/new")(create_user)
app.post("/users/new")(create_user)

@app.on_startup
async def startup():
    await db.connect(create_tables=True)

if __name__ == "__main__":
    app.run(port=8888)
```

## Running the App
Once standard configuration is in place, you can boot your server locally:

```bash
# If your app.py is designed to run directly
python app.py

# Or via Eden's CLI tool if your project structure hooks into it automatically:
uv run eden run
```
