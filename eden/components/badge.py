"""Built-in Badge component."""
from eden.components import Component, register


@register("badge")
class BadgeComponent(Component):
    template_name = "eden/badge.html"

    def get_context_data(self, text="", variant="default", size="sm", pill=True, **kwargs):
        palette = {
            "default": "bg-slate-700 text-slate-300",
            "primary": "bg-blue-600 text-white",
            "success": "bg-emerald-600 text-white",
            "warning": "bg-amber-500 text-slate-900",
            "danger":  "bg-red-600 text-white",
        }
        size_map = {"xs": "text-xs px-1.5 py-0.5", "sm": "text-xs px-2 py-0.5", "md": "text-sm px-2.5 py-1"}
        return {
            "text": text,
            "color_class": palette.get(variant, palette["default"]),
            "size_class": size_map.get(size, size_map["sm"]),
            "pill": pill,
            **kwargs,
        }
