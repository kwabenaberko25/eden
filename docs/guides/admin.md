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

---

## 📊 Dashboard Widgets

The admin home screen is more than just a list of models. You can add custom widgets to display key application metrics or recent activity.

```python
from eden.admin import admin, StatWidget, ChartWidget

@admin.dashboard
class MainDashboard:
    def get_widgets(self):
        return [
            StatWidget(label="Total Revenue", value="$12,500", icon="currency-dollar"),
            StatWidget(label="Active Users", value=150, icon="users"),
            ChartWidget(
                label="Registrations (7 Days)", 
                data_api="@url('admin:user_stats')",
                type="line"
            )
        ]
```

---

## 🎨 Custom List Rendering

Sometimes a simple text value isn't enough. You can render custom HTML (like images or badges) directly in the list view.

```python
from eden.templating import html_safe

@admin.register(User)
class UserAdmin:
    list_display = ["avatar_preview", "email", "status_badge"]
    
    @admin.display(description="Avatar")
    def avatar_preview(self, obj):
        return html_safe(f'<img src="{obj.avatar_url}" class="h-8 w-8 rounded-full border">')
        
    @admin.display(description="Status")
    def status_badge(self, obj):
        color = "green" if obj.is_active else "gray"
        return html_safe(f'<span class="badge badge-{color}">{obj.status}</span>')
```

---

---

## 🏢 Multi-Tenancy in the Admin

In a SaaS application, your admins (staff) must be isolated from each other. Eden's admin handles this via `get_queryset` and `get_tenant`.

```python
@admin.register(Post)
class PostAdmin:
    async def get_queryset(self, request):
        # Only show posts belonging to a staff member's tenant
        if not request.user.is_superuser:
            return await Post.filter(tenant_id=request.tenant.id).all()
        return await Post.all()
        
    async def save_model(self, request, obj, form, change):
        # Automatically assign the current tenant on creation
        if not change:
            obj.tenant_id = request.tenant.id
        await super().save_model(request, obj, form, change)
```

## 🛠️ JSON & Advanced Fields

Manage complex settings directly with the `JsonWidget` and `CodeWidget`.

```python
@admin.register(Setting)
class SettingAdmin:
    fieldsets = [
        ("Configuration", {
            "fields": ["config_json"],
            "description": "Raw JSON configuration for this service."
        })
    ]
    
    formfield_overrides = {
        # Renders a sleek Monaco-powered code editor in the admin
        "config_json": {"widget": admin.widgets.CodeWidget(language="json")}
    }
```

## ⚡ Advanced Bulk Actions

---

## 🛠️ Theme Overrides

The Eden Admin Panel is built with a sleek, customizable CSS variables system. You can inject your own branding values.

```python
# settings.py
ADMIN_THEME = {
    "primary": "#6366f1", # Indigo
    "accent": "#f43f5e",  # Rose
    "font_family": "Outfit, sans-serif"
}
```

---

## Best Practices

- ✅ **Search fields**: Always include `search_fields` for models with more than 100 records.
- ✅ **List filter**: Use `list_filter` for boolean fields or foreign keys with limited choices.
- ✅ **Permission awareness**: Always use `has_permission` to restrict the admin to trusted developers/staff only.
- ✅ **Inlines for UX**: Use `StackedInline` or `TabularInline` to manage related records without jumping between pages.

---

**Next Steps**: [Deployment & Observability](deployment.md)
