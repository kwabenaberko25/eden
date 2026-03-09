"""Built-in Card component."""
from eden.components import Component, register


@register("card")
class CardComponent(Component):
    template_name = "eden/card.html"

    def get_context_data(self, title="", subtitle="", hoverable=True, **kwargs):
        return {"title": title, "subtitle": subtitle, "hoverable": hoverable, **kwargs}
