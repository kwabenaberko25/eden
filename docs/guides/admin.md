# The Eden Admin Panel 🛠️

Eden comes with a professional, auto-generated administration interface that allows you to manage your application's data with safety and style.

## Mounting the Admin

To enable the admin panel, simply register your models and mount it to your `Eden` app.

```python
from eden.admin import admin
from models import User, Post

# Register models
admin.register(User)
admin.register(Post)

# Mount to app (Dashboard available at /admin/ by default)
app.mount_admin()
```

---

## Customizing the View

You can control how your models are displayed and edited within the dashboard.

```python
@admin.register(Post)
class PostAdmin:
    list_display = ["title", "author", "created_at", "is_published"]
    search_fields = ["title", "content"]
    list_filter = ["is_published", "author"]
    
    # Organize fields into groups
    fieldsets = [
        ("Content", {"fields": ["title", "content"]}),
        ("Status", {"fields": ["is_published", "published_at"]}),
    ]
```

---

## Related Models (Inlines) 🔗

Manage related data on the same page using inlines.

```python
class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1

@admin.register(Post)
class PostAdmin:
    inlines = [CommentInline]
```

---

## Admin Actions

Perform bulk operations on selected records.

```python
@admin.action(description="Mark selected posts as published")
async def make_published(request, queryset):
    await queryset.update(is_published=True)
```

---

## Permissions & Security

By default, the Admin Panel is restricted to users with the `admin` role. You can customize this behavior by overriding the `has_permission` method.

```python
class MyAdminSite(admin.AdminSite):
    async def has_permission(self, request):
        return request.user.is_authenticated and request.user.is_superuser
```

---

## Design Customization

The Admin Panel adheres to the Eden design system, providing a clean, glassmorphic layout that matches your application's premium feel.

---

**Next Steps**: [Deployment & Observability](deployment.md)
