"""
Counter Component — Interactive counter with increment/decrement actions.

This is a complete, working example demonstrating:
- Passing reactive state to components
- Handling actions with parameter coercion
- Re-rendering components after state changes
- Full HTMX integration
"""

from eden.components import Component, register, action


@register("counter")
class CounterComponent(Component):
    """
    A simple counter component that manages a numeric count value.

    State:
    - count (int): The current counter value (default: 0)
    - step (int): The amount to increment/decrement by (default: 1)
    - title (str): Display title for the counter (default: "Counter")

    Actions:
    - increment: Add 'step' to count
    - decrement: Subtract 'step' from count
    - set_count: Set count to a specific value
    - reset: Reset count to 0
    
    **Basic Usage in Template:**
        @component("counter", count=0) {
            <div class="counter">
                <h3>{{ title }}</h3>
                <p class="count">{{ count }}</p>
                <button hx-post="{{ action_url('increment') }}" {{ component_attrs }}>
                    +{{ step }}
                </button>
                <button hx-post="{{ action_url('decrement') }}" {{ component_attrs }}>
                    -{{ step }}
                </button>
            </div>
        }

    **Advanced Usage with Parameters:**
        @component("counter", count=0, step=5, title="Score") {
            <div class="score-board">
                <h2>{{ title }} (step: {{ step }})</h2>
                <p>Score: <strong>{{ count }}</strong></p>
                <button hx-post="{{ action_url('increment') }}" {{ component_attrs }}>
                    Add {{ step }}
                </button>
                <button hx-post="{{ action_url('decrement') }}" {{ component_attrs }}>
                    Subtract {{ step }}
                </button>
                <button hx-post="{{ action_url('reset') }}" {{ component_attrs }}>
                    Reset
                </button>
                <form hx-post="{{ action_url('set_count') }}" {{ component_attrs }}>
                    <input type="number" name="value" />
                    <button type="submit">Set Count</button>
                </form>
            </div>
        }
    """

    template_name = "eden/counter.html"

    def __init__(self, count: int = 0, step: int = 1, title: str = "Counter", **kwargs):
        """
        Initialize a Counter component.

        Args:
            count: Starting value for the counter (default: 0)
            step: Amount to increment/decrement by (default: 1)
            title: Display title (default: "Counter")
            **kwargs: Additional state to preserve across requests
        """
        self.count = count
        self.step = step
        self.title = title
        super().__init__(**kwargs)

    def get_context_data(self, **kwargs):
        """
        Prepare template context with computed values.

        Extends the default context with:
        - can_decrement: Whether decrement is allowed (count > 0)
        """
        ctx = super().get_context_data(**kwargs)
        ctx["can_decrement"] = self.count > 0
        return ctx

    @action
    async def increment(self, request):
        """
        Increment the counter by the step amount.

        This action is triggered via:
            <button hx-post="{{ action_url('increment') }}" {{ component_attrs }}>
                +{{ step }}
            </button>

        The framework:
        1. Extracts hx-vals (count, step, title) from the request
        2. Reinstantiates CounterComponent with those values
        3. Calls increment() on the new instance
        4. Returns the re-rendered component
        """
        self.count += self.step
        return await self.render()

    @action
    async def decrement(self, request):
        """
        Decrement the counter by the step amount.

        See increment() for detailed flow documentation.
        """
        self.count -= self.step
        if self.count < 0:
            self.count = 0
        return await self.render()

    @action("reset")
    async def reset_counter(self, request):
        """
        Reset the counter to zero.

        Custom action slug: 'reset' (method name is reset_counter)
        Can be called via: {{ action_url('reset') }}
        """
        self.count = 0
        return await self.render()

    @action
    async def set_count(self, request, value: int):
        """
        Set the counter to a specific value.

        This demonstrates action parameter passing and type coercion.

        Args:
            request: HTTP request object (always available)
            value: New counter value (coerced from string to int automatically)

        **Template Usage:**
            <form hx-post="{{ action_url('set_count') }}" {{ component_attrs }}>
                <input type="number" name="value" required />
                <button type="submit">Set Count</button>
            </form>

        **How it works:**
        1. Form is submitted with name="value"
        2. Framework extracts 'value' from request.form_data
        3. Type hint (int) triggers automatic int() conversion
        4. set_count() is called with converted value
        5. Updated component is rendered and returned
        """
        self.count = max(0, value)  # Ensure non-negative
        return await self.render()
