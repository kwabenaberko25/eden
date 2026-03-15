"""Built-in Spinner / Loading Indicator component."""
from eden.components import Component, register


@register("spinner")
class SpinnerComponent(Component):
    """
    Renders an animated circular spinner for loading states.

    Usage::

        @component("spinner") {}

        @component("spinner", size="lg", color="emerald") {}

        @component("spinner", label="Saving…") {}
    """

    template_name = "eden/spinner.html"

    _SIZE_CLASSES = {
        "xs":  "w-4 h-4 border-2",
        "sm":  "w-5 h-5 border-2",
        "md":  "w-8 h-8 border-[3px]",
        "lg":  "w-12 h-12 border-4",
        "xl":  "w-16 h-16 border-4",
    }

    _COLOR_CLASSES = {
        "blue":    "border-blue-500",
        "emerald": "border-emerald-500",
        "amber":   "border-amber-500",
        "red":     "border-red-500",
        "white":   "border-white",
        "gray":    "border-gray-400",
    }

    def get_context_data(
        self,
        size: str = "md",
        color: str = "blue",
        label: str = "",
        center: bool = True,
        **kwargs,
    ) -> dict:
        size_class  = self._SIZE_CLASSES.get(size, self._SIZE_CLASSES["md"])
        color_class = self._COLOR_CLASSES.get(color, self._COLOR_CLASSES["blue"])
        return {
            "size_class": size_class,
            "color_class": color_class,
            "label": label,
            "center": center,
            **kwargs,
        }
