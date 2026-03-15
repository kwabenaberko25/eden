"""
Todo List Component — Complex component demonstrating state management with lists.

This example shows:
- Managing lists of items in component state
- Handling parameter passing and type coercion
- Multiple actions that modify structured state
- Serialization of list state across requests
"""

from eden.components import Component, register, action
from typing import List, Optional


@register("todo_list")
class TodoListComponent(Component):
    """
    A todo list component that manages a list of todo items.

    State:
    - items (list): List of todo dicts with 'id', 'text', 'done' keys
    - next_id (int): Next ID to use for new items

    Actions:
    - add_item: Add a new todo item
    - toggle_item: Mark item as done/not done
    - delete_item: Remove an item
    - clear_done: Remove all completed items

    **Template Usage:**
        @component("todo_list") {
            <div class="todo-app">
                <h2>My Tasks</h2>
                <!-- Component renders todo items and forms -->
            </div>
        }
    """

    template_name = "eden/todo_list.html"

    def __init__(self, items: Optional[List[dict]] = None, next_id: int = 1, **kwargs):
        """
        Initialize the TodoListComponent.

        Args:
            items: List of todo dicts (default: empty list).
                  Each item should have: {'id': int, 'text': str, 'done': bool}
            next_id: Next ID to assign to new items (default: 1)
            **kwargs: Additional state
        """
        self.items = items or []
        self.next_id = next_id
        super().__init__(**kwargs)

    def get_context_data(self, **kwargs):
        """
        Prepare template context with computed values.

        Computes:
        - pending_count: Number of incomplete items
        - done_count: Number of completed items
        - all_done: Whether all items are completed
        """
        ctx = super().get_context_data(**kwargs)
        ctx["pending_count"] = sum(1 for item in self.items if not item.get("done", False))
        ctx["done_count"] = sum(1 for item in self.items if item.get("done", False))
        ctx["all_done"] = len(self.items) > 0 and ctx["pending_count"] == 0
        return ctx

    @action
    async def add_item(self, request, text: str):
        """
        Add a new todo item to the list.

        Args:
            request: HTTP request
            text: The todo item text (coerced from form data)

        **Template Form:**
            <form hx-post="{{ action_url('add_item') }}" {{ component_attrs }}>
                <input type="text" name="text" placeholder="What needs to be done?" />
                <button type="submit">Add Todo</button>
            </form>
        """
        if text.strip():  # Only add non-empty items
            self.items.append({
                "id": self.next_id,
                "text": text.strip(),
                "done": False
            })
            self.next_id += 1
        return await self.render()

    @action
    async def toggle_item(self, request, item_id: int):
        """
        Toggle the done status of a todo item.

        Args:
            request: HTTP request
            item_id: ID of the item to toggle (coerced to int)

        **Template Button:**
            @for (item in items) {
                <li class="{{ 'done' if item.done else '' }}">
                    <button 
                        hx-post="{{ action_url('toggle_item') }}" 
                        {{ component_attrs }}
                        hx-include="[name='item_id']"
                        hx-vals='{"item_id": {{ item.id }}}'>
                        {{ item.text }}
                    </button>
                </li>
            }
        """
        for item in self.items:
            if item.get("id") == item_id:
                item["done"] = not item.get("done", False)
                break
        return await self.render()

    @action
    async def delete_item(self, request, item_id: int):
        """
        Delete a todo item by ID.

        Args:
            request: HTTP request
            item_id: ID of the item to delete (coerced to int)
        """
        self.items = [item for item in self.items if item.get("id") != item_id]
        return await self.render()

    @action
    async def clear_done(self, request):
        """
        Remove all completed todo items.

        This action takes no parameters.
        """
        self.items = [item for item in self.items if not item.get("done", False)]
        return await self.render()

    @action
    async def clear_all(self, request):
        """
        Delete all todo items.

        This action clears the entire list.
        """
        self.items = []
        return await self.render()
