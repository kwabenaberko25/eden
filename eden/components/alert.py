"""Built-in Alert component."""
from eden.components import Component, register


@register("alert")
class AlertComponent(Component):
    template_name = "eden/alert.html"

    def get_context_data(self, variant="info", dismissible=False, **kwargs):
        palette = {
            "info":    {"bg": "bg-blue-900/40",    "border": "border-blue-500/50",  "text": "text-blue-300",    "icon": "\u2139\ufe0f"},
            "success": {"bg": "bg-emerald-900/40", "border": "border-emerald-500/50","text": "text-emerald-300", "icon": "\u2705"},
            "warning": {"bg": "bg-amber-900/40",   "border": "border-amber-500/50", "text": "text-amber-300",   "icon": "\u26a0\ufe0f"},
            "danger":  {"bg": "bg-red-900/40",     "border": "border-red-500/50",   "text": "text-red-300",     "icon": "\u274c"},
        }
        colors = palette.get(variant, palette["info"])
        return {"variant": variant, "dismissible": dismissible, **colors, **kwargs}
