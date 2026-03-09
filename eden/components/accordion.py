"""Built-in Accordion component."""
from eden.components import Component, register


@register("accordion")
class AccordionComponent(Component):
    template_name = "eden/accordion.html"

    def get_context_data(self, items=None, multiple=False, **kwargs):
        """
        ``items`` is a list of dicts: [{"title": "...", "content": "..."}, ...]
        """
        items = items or []
        return {"items": items, "multiple": multiple, **kwargs}
