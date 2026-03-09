"""Built-in Data Table component."""
from eden.components import Component, register


@register("data_table")
class DataTableComponent(Component):
    """
    Renders an accessible, styled data table.

    Accepts either:
    - ``headers`` / ``rows`` lists (simple mode), or
    - ``columns`` / ``queryset`` (model-aware mode — reads attrs by name)

    Usage::

        {# Simple list mode #}
        @component("data_table",
                   headers=["Name", "Email", "Role"],
                   rows=[[u.name, u.email, u.role] for u in users]) {}

        {# Column-definition mode #}
        @component("data_table",
                   columns=[
                       {"label": "Name", "field": "name"},
                       {"label": "Email", "field": "email"},
                   ],
                   queryset=users,
                   empty_message="No users found.") {}

        {# Sortable headers via HTMX #}
        @component("data_table",
                   headers=["Name", "Email"],
                   rows=rows,
                   sortable=True,
                   sort_url="/users?sort=") {}
    """

    template_name = "eden/data_table.html"

    def get_context_data(
        self,
        headers: list[str] | None = None,
        rows: list[list] | None = None,
        columns: list[dict] | None = None,
        queryset: object | None = None,
        empty_message: str = "No records found.",
        sortable: bool = False,
        sort_url: str = "",
        striped: bool = True,
        hoverable: bool = True,
        **kwargs,
    ) -> dict:
        # Build a unified structure of headers + row data
        _headers: list[str] = []
        _rows: list[list] = []

        if columns and queryset is not None:
            _headers = [c.get("label", c.get("field", "")) for c in columns]
            for obj in queryset:
                row = []
                for col in columns:
                    field = col.get("field", "")
                    row.append(getattr(obj, field, ""))
                _rows.append(row)
        else:
            _headers = list(headers or [])
            _rows = [list(r) for r in (rows or [])]

        return {
            "headers": _headers,
            "rows": _rows,
            "empty_message": empty_message,
            "sortable": sortable,
            "sort_url": sort_url,
            "striped": striped,
            "hoverable": hoverable,
            **kwargs,
        }
