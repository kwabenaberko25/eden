"""Built-in Stat Card component."""
from eden.components import Component, register


@register("stat")
class StatComponent(Component):
    """
    Renders a KPI / statistic card.

    Usage::

        @component("stat", value="4,821", label="Active Users", icon="👥", trend="up", change="+12%") {}

        @component("stat", value="$9,200", label="Revenue", trend="up", change="+8.3%") {}

        @component("stat", value="32", label="Open Tickets", trend="down", change="-5") {}
    """

    template_name = "eden/stat.html"

    def get_context_data(
        self,
        value: str = "—",
        label: str = "",
        icon: str = "",
        trend: str = "",          # "up", "down", or ""
        change: str = "",         # e.g. "+12%" or "-3"
        description: str = "",
        **kwargs,
    ) -> dict:
        trend_color = ""
        trend_icon = ""
        if trend == "up":
            trend_color = "text-emerald-400"
            trend_icon = "↑"
        elif trend == "down":
            trend_color = "text-red-400"
            trend_icon = "↓"

        return {
            "value": value,
            "label": label,
            "icon": icon,
            "trend": trend,
            "trend_color": trend_color,
            "trend_icon": trend_icon,
            "change": change,
            "description": description,
            **kwargs,
        }
