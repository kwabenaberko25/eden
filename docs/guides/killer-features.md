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

---

## ⚙️ 3. Background Task Orchestration (Taskiq)

Eden abstracts away the complexity of distributed task queues. With the `EdenBroker`, you can run one-shot or periodic tasks with standard Python decorators.

```python
@app.task.every(hours=1)
async def send_daily_digest():
    """Eden handles the cron/scheduling automatically."""
    ...
```

---

## 🎯 4. Fragment-Based HTMX Workflow

Eden's templating engine is uniquely aware of HTMX. You can mark specific regions of your template and have Eden render **only those regions** during an AJAX request, without creating separate partial files.

```html
<div id="stats">
    @fragment("stats_grid") {
        <div class="stat">...</div>
    }
</div>
```

---

## 🏗️ 5. Server-Side Components (Python-Only)

Eden introduces a revolutionary component system that allows you to build interactive UI widgets entirely in Python. These components manage their own state and handle interactivity via HTMX without requiring you to manage complex frontend state machines.

### The "WOW" Factor: No-JS Interactivity
A component encapsulates its logic, markup, and **reactive state**. When an action is triggered, Eden re-instantiates the component, restores its state, and renders the update.

```python
@register("newsletter")
class NewsletterComponent(Component):
    template_name = "newsletter.html"
    
    def __init__(self, email="", is_subscribed=False, **kwargs):
        self.email = email
        self.is_subscribed = is_subscribed
        super().__init__(**kwargs)
    
    @action
    async def subscribe(self, request, email: str):
        # Business logic in pure Python
        await db.save_subscriber(email)
        self.is_subscribed = True
        return await self.render()
```

### Usage in Templates
```html
@component("newsletter", email="hello@eden.io")
```

---

## 🎪 The "Killer" Synergy: The AI Video Processor Loop

The true power of Eden is how these features work together. Let's look at a "Killer" scenario: An AI-powered video processing pipeline.

### 1. The Route (HTTP)

The user submits a video. We save it to the DB and kick off a background task.

```python
@app.post("/videos/process")
async def process(request):
    data = await request.form()
    video = await Video.create(title=data["title"], status="processing")
    
    # Defer to background worker
    await app.task.defer(ai_process_video, video.id, request.user.id)
    
    return request.render("video_details.html", {"video": video})
```

### 2. The Worker (Background Task)
The worker does the heavy AI lifting and then signals the frontend.

```python
@app.task()
async def ai_process_video(video_id: int, user_id: int):
    # Perform expensive AI processing...
    video = await Video.get(id=video_id)
    video.status = "ready"
    video.ai_tags = ["epic", "cinematic"]
    await video.save() # Triggers Reactive ORM broadcast!
```

### 3. The UI (WebSocket + HTMX)

The frontend listens for the model update and refreshes the status surgically using `@fragment`.

```html
<!-- video_details.html -->
<div hx-ext="ws" ws-connect="/ws/updates">
    <h1>{{ video.title }}</h1>
    
    <div id="video-status" 
         hx-get="@url('video:details', id=video.id)" 
         hx-trigger="videos:updated from:body">
         @fragment("status_badge") {
            <span class="badge {{ video.status }}">
                {{ video.status | title_case }}
            </span>
         }
    </div>
</div>
```

### Why this is a "Killer" Scenario:

1.  **Reactive ORM**: `video.save()` automatically sent the `videos:updated` event.
2.  **WebSockets**: The `ws-connect` bridge carried that event to the browser.
3.  **HTMX**: The `hx-trigger` matched the event and requested a refresh.
4.  **Auto-Fragments**: Eden's `TemplateResponse` saw `HX-Target="video-status"` and rendered **only** the `status_badge` fragment.

**Total JavaScript written: 0 lines.**

---

> [!IMPORTANT]
> **Eden Philosophy**:
> - **convention over complexity**: Real-time sync and fragments should be defaults, not "add-ons."
> - **Unified API**: One framework, one import, one language.
> - **Premium by Default**: Every component and interaction feels high-end out of the box.
