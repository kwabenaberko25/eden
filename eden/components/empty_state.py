"""Built-in Empty State component."""
from eden.components import Component, register


@register("empty_state")
class EmptyStateComponent(Component):
    """
    Renders a friendly empty-state illustration with a CTA.

    Usage::

        @component("empty_state",
                   title="No projects yet",
                   description="Create your first project to get started.",
                   action_url="/projects/new",
                   action_label="New Project",
                   icon="📂") {}

        {# With HTMX trigger #}
        @component("empty_state",
                   title="No results found",
                   icon="🔍",
                   description="Try a different search term.") {}
    """

    template_name = "eden/empty_state.html"

    def get_context_data(
        self,
        title: str = "Nothing here yet",
        description: str = "",
        icon: str = "📭",
        action_url: str = "",
        action_label: str = "Get Started",
        action_htmx: str = "",   # Optional hx-get replacement
        action_target: str = "",  # Optional hx-target
        **kwargs,
    ) -> dict:
        return {
            "title": title,
            "description": description,
            "icon": icon,
            "action_url": action_url,
            "action_label": action_label,
            "action_htmx": action_htmx,
            "action_target": action_target,
            **kwargs,
        }
