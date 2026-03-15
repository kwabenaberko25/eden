"""Built-in Progress Bar component."""
from eden.components import Component, register


@register("progress")
class ProgressComponent(Component):
    """
    Renders an animated progress bar.

    Usage::

        @component("progress", value=72) {}

        @component("progress", value=45, label="Upload", variant="success") {}

        @component("progress", value=90, show_percent=True, variant="warning") {}
    """

    template_name = "eden/progress.html"

    _VARIANT_COLORS = {
        "primary": "bg-blue-500",
        "success": "bg-emerald-500",
        "warning": "bg-amber-500",
        "danger":  "bg-red-500",
        "info":    "bg-sky-400",
    }

    def get_context_data(
        self,
        value: int | float = 0,
        label: str = "",
        variant: str = "primary",
        show_percent: bool = False,
        striped: bool = False,
        animated: bool = True,
        height: str = "h-2",
        **kwargs,
    ) -> dict:
        value = max(0, min(100, float(value)))
        fill_class = self._VARIANT_COLORS.get(variant, "bg-blue-500")
        return {
            "value": value,
            "label": label,
            "fill_class": fill_class,
            "show_percent": show_percent,
            "striped": striped,
            "animated": animated,
            "height": height,
            **kwargs,
        }
