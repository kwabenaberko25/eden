"""Built-in Tabs component."""
from eden.components import Component, register


@register("tabs")
class TabsComponent(Component):
    template_name = "eden/tabs.html"

    def get_context_data(self, tabs=None, active=0, **kwargs):
        """
        ``tabs`` is a list of dicts: [{"label": "Tab 1", "id": "tab1"}, ...]
        """
        tabs = tabs or []
        return {"tabs": tabs, "active": active, **kwargs}
