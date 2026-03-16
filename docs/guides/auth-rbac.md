# Role-Based Access Control (RBAC) 👑

Eden provides a granular permission system that allows you to secure your application at the role and permission levels.

## Roles vs. Permissions

- **Roles**: Broad categories of users (e.g., `admin`, `manager`, `editor`).
- **Permissions**: Specific atomic actions a user can perform (e.g., `can_delete_post`, `can_publish`).

In Eden, roles typically act as containers for permissions.

---

## Defining a Role Hierarchy

You can define a hierarchy where higher roles automatically inherit permissions from lower roles.

```python
from eden.auth import RoleHierarchy

hierarchy = RoleHierarchy({
    "superadmin": ["admin", "manager", "user"],
    "admin": ["manager", "user"],
    "manager": ["user"],
    "user": []
})

# Attach to app state
app.state.role_hierarchy = hierarchy
```

---

## Securing Routes

### The `@roles_required` Decorator
Requires the user to have at least one of the specified roles.

```python
from eden.auth import roles_required

@app.get("/admin/settings")
@roles_required(["admin", "superadmin"])
async def admin_settings(request):
    return render_template("admin/settings.html")
```

### The `@permissions_required` Decorator
Requires the user to have **all** of the specified permissions.

```python
from eden.auth import permissions_required

@app.post("/posts/{id}/delete")
@permissions_required(["can_delete_posts"])
async def delete_post(request, id: int):
    post = await Post.get(id)
    await post.delete()
    return redirect("/posts")
```

---

## Dynamic Checks in Logic

Sometimes decorators aren't enough, and you need to check permissions inside your function body.

```python
async def update_profile(request):
    user = request.user
    
    # Check if user can edit this specific profile
    if not user.is_superuser and user.id != target_user_id:
        if not user.has_permission("can_edit_others"):
            raise PermissionError("Access Denied")
```

---

## Usage in Templates

Eden's templating engine makes it easy to hide UI elements based on authentication state.

```html
@if(user.has_role('admin')) {
    <button class="btn-danger">Delete Project</button>
}

@if(user.has_permission('can_invite')) {
    <a href="/invite">Invite Team Member</a>
}
```

---

## Row-Level Security (RLS)

A common pattern is restricting a query based on the user's role.

```python
async def list_documents(request):
    query = Document.query()
    
    # Non-admins only see their own documents
    if not request.user.has_role("admin"):
        query = query.filter(owner_id=request.user.id)
        
    documents = await query.all()
    return render_template("docs.md", documents=documents)
```

---

**Next Steps**: [Social Login (OAuth)](auth-oauth.md)
