# 🏗️ Walkthrough: Building a Real-Time Kanban Board

This guide provides a professional, end-to-end walkthrough of building a **Stateful Kanban Board** using the Eden Framework's advanced UI orchestration engine. We will synchronize Python logic, HTMX actions, and scoped assets into a singular, cohesive organism.

---

## 🎯 The Objective

We will build a multi-tenant Kanban board where users can:

1. **Drag-and-Drop** tasks between columns (HTMX + Alpine.js).
2. **Add Tasks** via a modal with live validation (Widget Engine).
3. **Persist State** automatically across re-renders (Action Engine).

---

## 🛠️ Step 1: The Python Component (`TaskBoard`)

The component class handles the state (tasks, columns) and the server-side actions.

```python
from typing import List, Dict
from eden.components import Component, action
from eden.db import Model, f

class TaskBoard(Component):
    """
    A stateful Kanban Board component that persists state automatically.
    """
    # State attributes (Automatically persisted via HMAC signature)
    tenant_id: str
    columns: List[str] = ["Todo", "In Progress", "Done"]
    tasks: List[Dict] = []

    @action
    async def move_task(self, task_id: int, new_status: str):
        """Update a task's status and re-render."""
        # Find and update the task in the state
        for task in self.tasks:
            if task["id"] == int(task_id):
                task["status"] = new_status
                break
        
        # In a real app, you would persist to a relational DB:
        # await TaskStore.update_status(task_id, new_status)
        
        return self  # Re-renders the entire component fragment

    @action
    async def add_task(self, title: str):
        """Add a new task to the 'Todo' column."""
        new_id = len(self.tasks) + 1
        self.tasks.append({
            "id": new_id, 
            "title": title, 
            "status": "Todo"
        })
        return self

    def get_template_name(self):
        return "eden/kanban.html"
```

---

## 🎨 Step 2: The Orchestrated Template

We use `@reactive` for the layout logic and the **Widget Engine** for the task creation form.

```html
<!-- templates/eden/kanban.html -->
<div id="{{ component_id }}" class="kanban-container" x-data="{ newTaskTitle: '' }">
    
    <!-- 📦 Part 1: Scoped Assets -->
    @reactive {
        <style>
            .kanban-board { 
                display: flex; 
                gap: 1.5rem; 
                overflow-x: auto; 
                padding: 1.5rem; 
                min-height: 50vh;
            }
            .kanban-col { 
                background: rgba(255, 255, 255, 0.02); 
                min-width: 320px; 
                border-radius: 16px; 
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
            .task-card { 
                background: var(--eden-card-bg);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 1rem;
                margin-bottom: 0.75rem;
                cursor: grab;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .task-card:hover { 
                transform: translateY(-2px); 
                box-shadow: 0 8px 24px rgba(0,0,0,0.3);
            }
            .task-card:active { cursor: grabbing; scale: 1.02; }
            .sortable-ghost { opacity: 0.3; background: var(--eden-primary); }
        </style>
        
        <script>
            // This runs in the scoped asset pipeline
            console.log("Kanban Component Ready.");
        </script>
    }

    <!-- 🏗️ Part 2: The Board Layout -->
    <div class="kanban-board">
        @foreach(col in columns) {
            <div class="kanban-col p-6 h-full"
                 hx-post="{{ action_url('move_task') }}"
                 hx-trigger="taskDropped"
                 hx-ext="json-enc">
                
                <h3 class="font-bold mb-6 text-white/50 text-xs uppercase tracking-[0.2em]">
                    {{ col }}
                </h3>
                
                <div class="space-y-4" data-status="{{ col }}">
                    @foreach(task in tasks if task.status == col) {
                        <div class="task-card"
                             draggable="true"
                             data-id="{{ task.id }}"
                             @dragstart="event.dataTransfer.setData('text/plain', {{ task.id }})">
                            <p class="text-sm font-medium">{{ task.title }}</p>
                        </div>
                    }
                </div>
            </div>
        }
    </div>

    <!-- 🛠️ Part 3: The "Widget Engine" Form -->
    <div class="mt-12 p-8 border-t border-white/5 bg-white/[0.01]">
        <h4 class="text-[10px] font-bold mb-6 uppercase tracking-[0.3em] text-white/20">New Operation</h4>
        <form hx-post="{{ action_url('add_task') }}" 
              hx-indicator="#add-spinner"
              @submit.prevent="$el.reset()">
            <div class="flex items-center gap-4">
                <div class="flex-1">
                    {{ form["title"]
                        .add_class("eden-input-glass w-full")
                        .attr("placeholder", "Define the objective...")
                        .render_composite() | safe 
                    }}
                </div>
                <button type="submit" class="eden-btn-primary px-8">Dispatch</button>
            </div>
        </form>
    </div>
</div>
```

---

## 🧠 Step 3: Synthesis Breakdown

### 1. The Action Engine (HTMX Synchronization)

The board leverages Eden's **State Serialization**. When a task is added or moved:

1. HTMX sends the encrypted component state (`__state`) back to the server.
2. The Action Engine re-initializes `TaskBoard` from that state.
3. The `@action` method (`move_task` or `add_task`) executes.
4. The modified component instance is re-rendered to HTML and sent back.

### 2. The Widget Engine (Fluent API)

The form field `form["title"]` is dynamically transformed:

```python
{{ form["title"]
    .add_class("eden-input-glass w-full")
    .attr("placeholder", "Define the objective...")
    .render_composite() | safe 
}}
```
This demonstrates the **Fluent API**'s power to bridge the gap between static Python schemas and modern, high-fidelity UI requirements.

### 3. Asset Bundling (`@reactive`)

The CSS inside the `@reactive` block is **Scoped**. This means:

- It only affects elements within the Kanban component.
- The CSS is extracted and optimized into a single file by Eden's production compiler.
- It prevents global CSS pollution, a common problem in large SaaS applications.

---

## 💎 Elite Best Practices

1. **Transactional Integrity**: Wrap your `@action` logic in `async with db.transaction()` if you are modifying multiple tables.
2. **Persistence**: In production, the component's `self.tasks` should mirror a database query. Use `on_init` to populate data from `eden.db.QuerySet`.
3. **OOB Updates**: If adding a task should update a global "Task Counter" elsewhere on the page, return a multi-fragment response using `return await self.render() + self.render_counter()`.
