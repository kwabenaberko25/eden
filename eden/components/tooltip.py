"""Built-in Tooltip component."""
from eden.components import Component, register


@register("tooltip")
class TooltipComponent(Component):
    template_name = "eden/tooltip.html"

    def get_context_data(self, text="", position="top", **kwargs):
        pos_map = {
            "top":    "bottom-full left-1/2 -translate-x-1/2 mb-2",
            "bottom": "top-full left-1/2 -translate-x-1/2 mt-2",
            "left":   "right-full top-1/2 -translate-y-1/2 mr-2",
            "right":  "left-full top-1/2 -translate-y-1/2 ml-2",
        }
        return {"text": text, "pos_class": pos_map.get(position, pos_map["top"]), **kwargs}
