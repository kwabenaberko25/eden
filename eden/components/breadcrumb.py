"""Built-in Breadcrumb component."""
from eden.components import Component, register


@register("breadcrumb")
class BreadcrumbComponent(Component):
    template_name = "eden/breadcrumb.html"

    def get_context_data(self, items=None, separator="/", **kwargs):
        """
        ``items`` is a list of dicts: [{"label": "Home", "href": "/"}, ...]
        The last item is considered the current (active) page.
        """
        items = items or []
        return {"items": items, "separator": separator, **kwargs}
