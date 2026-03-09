"""Built-in Avatar component."""
from eden.components import Component, register


@register("avatar")
class AvatarComponent(Component):
    template_name = "eden/avatar.html"

    def get_context_data(self, src="", alt="User", size="md", fallback="", **kwargs):
        size_map = {"sm": "w-8 h-8 text-xs", "md": "w-10 h-10 text-sm", "lg": "w-14 h-14 text-base", "xl": "w-20 h-20 text-lg"}
        initials = fallback or "".join(w[0].upper() for w in alt.split()[:2] if w)
        return {
            "src": src, "alt": alt, "initials": initials,
            "size_class": size_map.get(size, size_map["md"]),
            **kwargs,
        }
