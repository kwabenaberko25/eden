"""Built-in Modal component."""
from eden.components import Component, register


@register("modal")
class ModalComponent(Component):
    template_name = "eden/modal.html"

    def get_context_data(self, id="modal", title="", size="md", **kwargs):
        size_map = {"sm": "max-w-sm", "md": "max-w-lg", "lg": "max-w-2xl", "xl": "max-w-4xl"}
        return {"id": id, "title": title, "size_class": size_map.get(size, "max-w-lg"), **kwargs}
