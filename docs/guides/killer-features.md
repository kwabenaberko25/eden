# 🚀 Eden Framework: Killer Features & Elite Architecture

Eden isn't just a library; it's a **curated developer experience**. We've eliminated the friction of integrating disparate tools by building a unified ecosystem. This guide deep-dives into the "Killer Features" that make Eden the most productive framework for modern, async Python development.

---

## 💎 1. The Unified Developer API

One of the most significant changes in the latest Eden versions is the **Consolidated Import Pattern**. No more jumping between `sqlalchemy`, `starlette`, and `pydantic`.

### The "Eden Way"
We've exported the most common tools directly from the `eden` package.

```python
# Before (Legacy/Messy)
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy import select, func
from starlette.requests import Request
from starlette.responses import JSONResponse
from pydantic import BaseModel

# After (Eden Elite 🌿)
from eden import Model, f, Mapped, select, func, Request, json, Schema, v
```

### Why it's useful:
- **Intelligent Context**: When you import `f` (the field helper) from `eden`, it knows about both your database schema AND how that field should look in a form or an API.
- **Zero-Boilerplate**: Common types like `Request`, `json` responses, and `select` queries are always one import away.

---

## ⚡ 2. Native Real-time Sync (Reactive ORM)

Eden features a "Zero-Configuration" real-time layer. Any change in your database can be instantly reflected on every connected user's screen without a single line of JavaScript.

### Deep Dive: Reactive Models
To make a model reactive, simply set `__reactive__ = True`. Eden will automatically broadcast events to a WebSocket channel derived from your table name.

```python
from eden import Model, f, Mapped

class Notification(Model):
    __reactive__ = True
    message: Mapped[str] = f()
    is_read: Mapped[bool] = f(default=False)
```

### Usage Examples:
**1. Live Progress Bars:**
Update a `Project` model in a background task, and the progress bar on the dashboard updates automatically.

**2. Collaborative Dashboards:**
```html
<div hx-sync="notifications" 
     hx-trigger="notifications:created" 
     hx-get="/notifications/list" 
     hx-target="#notif-bell">
    <!-- This bell icon updates in real-time for ALL users -->
    <i class="fas fa-bell"></i>
</div>
```

> [!TIP]
> **Pro Tip**: You can also broadcast manually from your code using `from eden import manager; await manager.broadcast("my-channel", {"data": "..."})`.

---

## 🤖 3. Agentic AI & Vector Mastery

Eden is built for the era of AI. We provide native support for **Vector Embeddings**, enabling you to build semantic search and RAG systems with ease.

### The `VectorModel`
By inheriting from `VectorModel`, your objects become searchable by "meaning," not just keywords.

```python
from eden.db.ai import VectorModel, VectorField

class Insight(VectorModel):
    text: Mapped[str] = f()
    # High-dimensional vector support (e.g., OpenAI text-embedding-3-small)
    vector: Mapped[list[float]] = VectorField(dimensions=1536)

# Semantic Retrieval
async def get_related_insights(query_embedding):
    # Built-in cosine similarity search
    return await Insight.semantic_search(query_embedding, limit=10)
```

---

## 🧩 4. Full-Stack Component Architecture

Eden Components are self-contained logic and UI units. They bridge the gap between backend server-side rendering and frontend interactivity.

### Component Actions (`@action`)
Marking a method with `@action` makes it a public endpoint that the component can call itself.

```python
from eden import Component, action, hx

class LikeButton(Component):
    post_id: int
    likes: int = 0

    @action
    async def toggle_like(self, request, **state):
        # Business logic directly in the component
        self.likes += 1
        return self.render() # Re-render just the button

    def template(self):
        return """
        <button hx-post="{{ action_url('toggle_like') }}" 
                hx-target="this" 
                hx-swap="outerHTML">
            ❤️ {{ likes }} Likes
        </button>
        """
```

### Why this is a Killer Feature:
- **Encapsulation**: Your JavaScript (via HTMX), CSS, and Python logic are all in one class.
- **Dynamic Routing**: No need to register a route for every button click. Eden handles the dispatching automatically via the `/_components/` internal router.

---

## 📝 5. Smart Form Schemas (UI-Aware)

We've evolved beyond basic Pydantic validation. Eden Schemas understand **intent**.

### The `field()` (or `v()`) Helper
The `field` function allows you to define validation and UI metadata in a single place.

```python
from eden.forms import Schema, v, EmailStr

class ProfileUpdateSchema(Schema):
    full_name: str = v(min_length=3, label="Full Name", placeholder="John Doe")
    email: EmailStr = v(widget="email", help_text="We'll never share your email.")
    bio: str = v(widget="textarea", max_length=500)

# Rendering in a template
# {{ form.full_name }} -> Renders a themed, validated input with label & placeholder
```

---

## 🛣️ 6. Named Routes & Dynamic URLs

Stop hardcoding `/auth/login`. Use Eden's robust routing aliases.

```python
# In your router
router = Router(name="app")
@router.get("/profile/{username}", name="user_profile")
async def profile(request, username): ...

# In your template
# <a href="@url('app:user_profile', username='cobby')">My Profile</a>
```

### Benefits:
- **Refactor-Friendly**: Change the URL path in Python, and all your links update automatically.
- **Namespaced**: Keep your "auth" routes separate from your "admin" routes with ease.

---

> [!IMPORTANT]
> **Summary of Philosophies**:
> 1. **Convention over Configuration**: Real-time sync, component dispatching, and form rendering "move out of your way."
> 2. **Aesthetics by Default**: Everything rendered by Eden uses the Premium Design Tokens.
> 3. **Consolidated Power**: One single import `from eden import *` gives you the keys to the kingdom.
