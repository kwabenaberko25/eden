"""Built-in Pagination component."""
from eden.components import Component, register


@register("pagination")
class PaginationComponent(Component):
    """
    Renders a paginated page navigation bar.

    Works with Eden's ``Page`` object from ``eden.db.pagination``.
    Supports HTMX-powered seamless page changes.

    Usage::

        @component("pagination", page=page) {}

        @component("pagination", page=page, htmx=True, target="#results") {}

        {# With custom URL query param #}
        @component("pagination", page=page, url_param="p") {}
    """

    template_name = "eden/pagination.html"

    def get_context_data(
        self,
        page: object,
        url_param: str = "page",
        htmx: bool = False,
        target: str = "",
        show_info: bool = True,
        **kwargs,
    ) -> dict:
        # Build page range (smart: show at most 7 page numbers)
        total_pages = getattr(page, "total_pages", 1)
        current = getattr(page, "page", 1)
        page_range = _build_page_range(current, total_pages)

        return {
            "page": page,
            "url_param": url_param,
            "htmx": htmx,
            "target": target,
            "show_info": show_info,
            "page_range": page_range,
            **kwargs,
        }


def _build_page_range(current: int, total: int, window: int = 2) -> list:
    """
    Return a condensed page range list.
    Inserts ``None`` as a sentinel for '…' ellipses.

    Example for page 5 of 12:
        [1, None, 3, 4, 5, 6, 7, None, 12]
    """
    if total <= 1:
        return []

    pages: list[int | None] = []
    # Always show first + last; show `window` pages around current
    left = max(2, current - window)
    right = min(total - 1, current + window)

    pages.append(1)
    if left > 2:
        pages.append(None)  # ellipsis
    for p in range(left, right + 1):
        pages.append(p)
    if right < total - 1:
        pages.append(None)  # ellipsis
    if total > 1:
        pages.append(total)

    return pages
