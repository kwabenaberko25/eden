# Server-Side Components (SSCs)

Server-Side Components (SSCs) are one of Eden's most powerful features. They allow you to build interactive, React-like UI components using **pure Python**. No complex JavaScript frameworks required!

SSCs leverage **HTMX** under the hood to handle updates, making your application feel fast and modern while keeping your logic on the server.

---

## 1. Creating a Component

To create a component, simply inherit from the `Component` class and define a `render()` method.

```python
from eden.components import Component, register

@register("user-card")
class UserCard(Component):
    def __init__(self, user):
        self.user = user

    def render(self):
        return f"""
        <div class="p-4 border rounded shadow">
            <h3 class="text-lg font-bold">{self.user.name}</h3>
            <p>{self.user.email}</p>
            <button hx-post="{self.url('like')}" class="mt-2 bg-blue-500 text-white p-2">
                Like
            </button>
        </div>
        """
```

### Key Concepts:
- **`@register("name")`**: This gives your component a unique identity.
- **`render()`**: This method returns the HTML for your component.
- **`self.url("action")`**: Generates a URL for a specific component action.

---

## 2. Component Actions

Actions allow your components to handle interactions like button clicks or form submissions. Use the `@action` decorator to define them.

```python
from eden.components import action

@register("counter")
class Counter(Component):
    count = 0

    @action("increment")
    def increment(self, request):
        self.count += 1
        return self.render()

    def render(self):
        return f"""
        <div id="counter">
            <p>Count: {self.count}</p>
            <button hx-post="{self.url('increment')}" hx-target="#counter">
                +1
            </button>
        </div>
        """
```

### Why use Actions?
- **No Manual Routes**: Eden automatically handles routing for any method marked with `@action`.
- **Automatic Context**: Actions receive the `request` object and any parameters sent via GET or POST.

---

## 3. Using Components in Templates

You can drop components into your standard Eden templates using the `@component` directive.

```html
<!-- index.html -->
<div class="grid grid-cols-3 gap-4">
    @foreach(user in users) {
        @component("user-card", user=user)
    }
</div>
```

---

## 4. URL Shorthand: `@url('component:...')`

Eden provides a killer shorthand for generating component URLs directly in your HTML. This is perfect for HTMX attributes.

### Different Usage Ways:

#### A. Bare Action (Simple)
If you just need to call an action:
```html
<button hx-get="@url('component:refresh-list')">Refresh</button>
```

#### B. With Parameters
Pass data directly to your action method:
```html
<button hx-post="@url('component:delete-item', item_id=item.id)">
    Delete
</button>
```

#### C. In Python Logic
Inside your component class, use `self.url()`:
```python
class MyComponent(Component):
    def render(self):
        delete_url = self.url("delete", id=123)
        return f'<button hx-delete="{delete_url}">Delete</button>'
```

---

## 🏛️ Advanced Example: Student Grade Editor (School Management)

Let's see how SSCs shine in a real-world scenario. Imagine a teacher's dashboard where they need to update student grades without reloading the page.

```python
from eden.components import Component, register, action
from models import Student, Grade

@register("grade-editor")
class GradeEditor(Component):
    def __init__(self, student_id):
        self.student_id = student_id
        self.message = ""

    async def get_student(self):
        return await Student.get(self.student_id)

    @action("save")
    async def save_grade(self, request):
        form = await request.form()
        grade_val = form.get("score")
        
        # Logic to update database
        student = await self.get_student()
        await student.update_grade(grade_val)
        
        self.message = f"Saved grade {grade_val} for {student.name}!"
        return self.render()

    async def render(self):
        student = await self.get_student()
        return f"""
        <div id="grade-editor-{self.student_id}" class="eden-card p-6">
            <h4 class="font-bold">{student.name}</h4>
            <form hx-post="{self.url('save')}" hx-target="#grade-editor-{self.student_id}">
                <input type="number" name="score" value="{student.current_grade}" 
                       class="eden-input w-24">
                <button type="submit" class="eden-btn-primary ml-2">Update</button>
            </form>
            @if(self.message) {{
                <p class="mt-2 text-emerald-400 text-sm">{self.message}</p>
            }}
        </div>
        """
```

---

## 🏆 Professional Patterns & Best Practices

To build enterprise-grade components, follow these patterns:

### 1. Unique IDs are Mandatory
Always wrap your component in a `div` with a unique ID that includes an instance identifier (like `self.student_id`). This ensures HTMX targets the *correct* instance on the page.

### 2. Composition over Complexity
Break large components into smaller ones. Instead of one `Dashboard` component, use a `Sidebar` component, a `TopBar` component, and multiple `Widget` components.

### 3. Async Rendering
Always prefer `async def render(self)` if you are fetching data from a database. Eden handles async rendering natively.

### 4. Use the `@url` Directive in Templates
While `self.url()` is great in Python, use `@url('component:...')` in your `.html` files for cleaner code.

---

## 💡 Pro Tip: State Management
Since SSCs render on the server, you can easily fetch data from your database or session inside `render()` or `@action`. This keeps your data secure and your frontend lightweight.
