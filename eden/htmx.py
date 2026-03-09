"""
Eden — HTMX Integration

Provides ``HtmxResponse`` with helper methods for setting HTMX response
headers (triggers, redirects, swaps, retargets) and request introspection
utilities.
"""

from typing import Any

from starlette.responses import HTMLResponse


class HtmxResponse(HTMLResponse):
    """
    An HTML response with fluent helpers for HTMX response headers.

    Usage::

        return HtmxResponse("<p>Saved!</p>").trigger("showToast", {"message": "Done"})
    """

    def trigger(self, event: str, detail: Any = None) -> "HtmxResponse":
        """Set ``HX-Trigger`` header to fire a client-side event."""
        import json
        if detail is not None:
            self.headers["HX-Trigger"] = json.dumps({event: detail})
        else:
            self.headers["HX-Trigger"] = event
        return self

    def trigger_after_settle(self, event: str, detail: Any = None) -> "HtmxResponse":
        """Set ``HX-Trigger-After-Settle`` header."""
        import json
        if detail is not None:
            self.headers["HX-Trigger-After-Settle"] = json.dumps({event: detail})
        else:
            self.headers["HX-Trigger-After-Settle"] = event
        return self

    def trigger_after_swap(self, event: str, detail: Any = None) -> "HtmxResponse":
        """Set ``HX-Trigger-After-Swap`` header."""
        import json
        if detail is not None:
            self.headers["HX-Trigger-After-Swap"] = json.dumps({event: detail})
        else:
            self.headers["HX-Trigger-After-Swap"] = event
        return self

    def hx_redirect(self, url: str) -> "HtmxResponse":
        """Set ``HX-Redirect`` header for a client-side redirect."""
        self.headers["HX-Redirect"] = url
        return self

    def refresh(self) -> "HtmxResponse":
        """Set ``HX-Refresh`` header to force a full page refresh."""
        self.headers["HX-Refresh"] = "true"
        return self

    def swap(self, strategy: str) -> "HtmxResponse":
        """Set ``HX-Reswap`` header to override the swap strategy."""
        self.headers["HX-Reswap"] = strategy
        return self

    def retarget(self, selector: str) -> "HtmxResponse":
        """Set ``HX-Retarget`` header to redirect the swap target."""
        self.headers["HX-Retarget"] = selector
        return self

    def push_url(self, url: str) -> "HtmxResponse":
        """Set ``HX-Push-Url`` header to update the browser URL."""
        self.headers["HX-Push-Url"] = url
        return self

    def reselect(self, selector: str) -> "HtmxResponse":
        """Set ``HX-Reselect`` header to pick a fragment from the response."""
        self.headers["HX-Reselect"] = selector
        return self


# ── Request introspection helpers ─────────────────────────────────────────────

def is_htmx(request: Any) -> bool:
    """Check if the request was made by HTMX."""
    headers = getattr(request, "headers", {})
    return headers.get("HX-Request") == "true"


def hx_target(request: Any) -> str:
    """Return the ``HX-Target`` header value (the CSS ID of the target)."""
    return getattr(request, "headers", {}).get("HX-Target", "")


def hx_trigger_name(request: Any) -> str:
    """Return the ``HX-Trigger-Name`` header (name of the triggering element)."""
    return getattr(request, "headers", {}).get("HX-Trigger-Name", "")


def hx_trigger_id(request: Any) -> str:
    """Return the ``HX-Trigger`` header (ID of the triggering element)."""
    return getattr(request, "headers", {}).get("HX-Trigger", "")


def hx_current_url(request: Any) -> str:
    """Return the ``HX-Current-URL`` header."""
    return getattr(request, "headers", {}).get("HX-Current-URL", "")


# ── Template filters ─────────────────────────────────────────────────────────

def hx_vals(data: Any) -> str:
    """Serialize a dict to JSON for use in ``hx-vals`` attributes."""
    import json

    from markupsafe import Markup
    if isinstance(data, dict):
        return Markup(json.dumps(data))
    return str(data)


def hx_headers(data: Any) -> str:
    """Serialize a dict to JSON for use in ``hx-headers`` attributes."""
    import json

    from markupsafe import Markup
    if isinstance(data, dict):
        return Markup(json.dumps(data))
    return str(data)
