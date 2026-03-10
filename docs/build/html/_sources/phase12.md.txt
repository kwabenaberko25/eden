# Phase 12: Administrative Excellence (Admin Panel) 🏛️

A Eden is only as good as its management console. In this phase, we master the **Eden Admin Panel**—a beautiful, auto-generated interface for managing your application's data.

---

## 🏗️ Registering Models

Eden's admin is strictly opt-in. You decide which models are exposed to the portal.

```python
from eden.admin import admin, ModelAdmin
from .models import Sector, Drone

# Basic registration
admin.register(Sector)

# Advanced registration with customization
@admin.register(Drone)
class DroneAdmin(ModelAdmin):
    list_display = ["serial_number", "model_type", "status"]
    search_fields = ["serial_number"]
    list_filter = ["status"]
```

---

## 🛰️ Mounting the Admin

To activate the portal, mount it in your `app.py`.

```python
# Default mount at /admin
app.mount_admin()
```

The admin panel is automatically protected by the `roles_required(["admin"])` guard, ensuring that only commanders can access the controls.

---

## 🎨 Customizing Views

`ModelAdmin` allows you to control how data is presented and searched.

| Option | Description |
| :--- | :--- |
| `list_display` | Columns shown in the list view. |
| `search_fields` | Models fields reachable via the search bar. |
| `list_filter` | Sidebar filters for narrowing down records. |

---

## ✅ Verification

To verify your Administrative Excellence:

1. **Test Access**: Login as an admin user and navigate to `/admin/`. Verify the dashboard appears.
2. **Test CRUD**: Create a new record through the admin UI and verify it appears in your database.
3. **Test Customization**: Verify that `list_display` correctly shows your chosen columns.

If your management portal is sleek, secure, and functional, your Admin engine is **100% Verified**. You are ready for **Phase 13: Interstellar Logistics (Payments)**.

