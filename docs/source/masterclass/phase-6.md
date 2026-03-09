# Phase 6: The Fruit (Performance, Async & Tooling) 🍎

Your application is now feature-complete, but as it grows, it must remain fast and manageable. Phase 6 covers the "Elite" features required for scale: Background Tasks, Caching, and automated Administration.

---

## ⏳ 1. Background Tasks (Async Deferral)

Heavy operations should never block the main request thread. Eden makes asynchronicity as simple as a decorator.

### Example A: Image Resizing on Upload

When a user uploads a high-res photo, we resize it in the background so the user doesn't wait for the processing.

```python
from eden import Eden
from PIL import Image # Pip install Pillow

app = Eden()

@app.task()
async def resize_image(path: str):
    # This runs in a separate worker process!
    with Image.open(path) as img:
        img.thumbnail((800, 800))
        img.save(path.replace(".png", "_thumb.png"))
    print(f"✅ Thumbnail generated for {path}")

@app.post("/upload")
async def handle_upload(request):
    # ... save file ...
    # Defer the heavy work to the background
    await resize_image.defer(file_path)
    return {"message": "Upload successful! Processing thumbnail..."}
```

---

### Example B: Bulk CSV Processing

Processing a 50,000-row CSV would timeout a standard request. Defer it!

```python
import csv

@app.task()
async def process_csv_import(file_path: str, user_id: int):
    count = 0
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            await Contact.create(**row, owner_id=user_id)
            count += 1
    # Notify user via WebSocket or Email when done
    print(f"📊 Imported {count} contacts for User {user_id}")
```

---

---

## 🗓️ 2. Scheduled Tasks (The Scheduler)

Some tasks aren't triggered by users—they happen on a timer.

### Example: Daily Analytics Digest

```python
@app.task.every("0 9 * * *") # Every day at 9:00 AM
async def daily_digest():
    stats = await Task.get_daily_stats()
    await send_mail(
        to="admin@myapp.com",
        subject="📈 Daily Analytics Digest",
        template="emails/digest.html",
        context={"stats": stats}
    )
```

---
```

---

## 🚀 3. Rocket-Fast Caching

Eden includes a sophisticated caching layer that supports Redis or In-Memory backends.

```python
from eden import cache_view

@app.get("/market-data")
@cache_view(timeout=60 * 5) # Cache for 5 minutes
async def get_market_data():
    # Expensive API call or DB query
    return await fetch_expensive_stats()

# Pro-Tip: Cache unique versions per user!
@app.get("/my-profile")
@cache_view(timeout=3600, vary_on_user=True)
async def get_private_data(request):
    return {"data": request.user.profile_blob}
```

---

---

## 🛠️ 4. The Admin Panel & OpenAPI

Eden automatically builds your internal tools so you can focus on the product.

### Auto-Generated Admin

Simply register your models, and Eden generates a secure, premium CRUD interface at `/admin`.

```python
from eden import admin_site, ModelAdmin

class TaskAdmin(ModelAdmin):
    list_display = ("title", "status", "priority", "owner")
    search_fields = ("title", "description")
    list_filter = ("status", "priority")

admin_site.register(Task, TaskAdmin)
```

---

### Interactive Documentation

Every route you write is automatically analyzed and documented in the OpenAPI format. Access your live docs at `/docs`.

```python
# No extra code required! Eden inspects your Pydantic 
# models and Route signatures to generate Swagger UI.
```

---

### 🎉 Phase 6 Complete

You have mastered the performance and maintenance layers of Eden. Your app is now fast, observable, and easy to manage via the Admin panel.

**Up Next: [Phase 7: The Harvest (Build & Deployment)](./phase-7.md)**
