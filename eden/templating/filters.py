from __future__ import annotations

import datetime
import re
import json as _json
from typing import Any
from markupsafe import Markup

from markupsafe import escape

def format_time_ago(value: datetime.datetime) -> Markup:
    """Format a datetime as a human-readable \"time ago\" string."""
    if not value:
        return escape("")

    now = datetime.datetime.now()
    if value.tzinfo:
        now = datetime.datetime.now(value.tzinfo)

    diff = now - value

    if diff.days > 365:
        return escape(f"{diff.days // 365} years ago")
    if diff.days > 30:
        return escape(f"{diff.days // 30} months ago")
    if diff.days > 0:
        return escape(f"{diff.days} days ago")
    if diff.seconds >= 3600:
        return escape(f"{diff.seconds // 3600} {'hour' if diff.seconds // 3600 == 1 else 'hours'} ago")
    if diff.seconds >= 60:
        return escape(f"{diff.seconds // 60} {'minute' if diff.seconds // 60 == 1 else 'minutes'} ago")
    return escape("just now")

def format_money(value: int | float | None, currency: str = "$") -> Markup:
    """Format a value as currency."""
    if value is None:
        return escape("")
    return escape(f"{currency}{value:,.2f}")

def class_names(base: str, conditions: dict[str, bool]) -> Markup:
    """Angular-style class names helper."""
    classes = [base]
    for cls, cond in conditions.items():
        if cond:
            classes.append(cls)
    return escape(" ".join(classes))

def add_class(field: Any, css_class: str) -> Any:
    if hasattr(field, "add_class"):
        return field.add_class(css_class)
    return field

def remove_class(field: Any, css_class: str) -> Any:
    if hasattr(field, "remove_class"):
        return field.remove_class(css_class)
    return field

def add_error_class(field: Any, css_class: str) -> Any:
    if hasattr(field, "add_error_class"):
        return field.add_error_class(css_class)
    return field

def attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "attr"):
        return field.attr(name, str(value))
    return field

def set_attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "set_attr"):
        return field.set_attr(name, str(value))
    return field

def append_attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "append_attr"):
        return field.append_attr(name, str(value))
    return field

def remove_attr(field: Any, name: str) -> Any:
    if hasattr(field, "remove_attr"):
        return field.remove_attr(name)
    return field

def add_error_attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "add_error_attr"):
        return field.add_error_attr(name, str(value))
    return field

def field_type(field: Any) -> str:
    if hasattr(field, "field_type"):
        return field.field_type
    return ""

def widget_type(field: Any) -> str:
    if hasattr(field, "widget_type"):
        return field.widget_type
    return ""

def truncate_filter(value: Any, length: int = 50, end: str = "…") -> Markup:
    """Truncate a string to *length* characters, appending *end* if truncated."""
    s = str(value)
    if len(s) <= length:
        return escape(s)
    return escape(s[:length].rstrip() + end)

def slugify_filter(value: Any) -> Markup:
    """Convert text to a URL-friendly slug."""
    s = str(value).lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    return escape(re.sub(r'[\s_]+', '-', s).strip('-'))

def json_encode(value: Any) -> str:
    """Serialize value to JSON (safe for ``x-data`` attributes)."""
    return Markup(_json.dumps(value))

def default_if_none(value: Any, default: Any = "") -> Any:
    """Return *default* when *value* is ``None``."""
    return default if value is None else value

def pluralize_filter(count: Any, singular: str = "", plural: str = "s") -> str:
    """Return *singular* or *plural* suffix based on *count*."""
    try:
        n = int(count)
    except (TypeError, ValueError):
        n = 0
    return singular if n == 1 else plural

def title_case(value: Any) -> Markup:
    """Convert text to Title Case."""
    return escape(str(value).title())

def format_date(value: Any, fmt: str = "%Y-%m-%d") -> Markup:
    """Format a date object or ISO string."""
    if not value: return escape("")
    if isinstance(value, str):
        try:
            value = datetime.datetime.fromisoformat(value)
        except ValueError:
            return escape(value)
    if hasattr(value, "strftime"):
        return escape(value.strftime(fmt))
    return escape(str(value))

def format_time(value: Any, fmt: str = "%H:%M") -> Markup:
    """Format a time/datetime object or ISO string."""
    if not value: return escape("")
    if isinstance(value, str):
        try:
            value = datetime.datetime.fromisoformat(value)
        except ValueError:
            return escape(value)
    if hasattr(value, "strftime"):
        return escape(value.strftime(fmt))
    return escape(str(value))

def format_number(value: Any) -> Markup:
    """Format a number with thousand separators."""
    try:
        return escape("{:,}".format(float(value)))
    except (TypeError, ValueError):
        return escape(str(value))

def mask_filter(value: Any, visible: int = 1) -> Markup:
    """Mask a string, showing first and last 'visible' characters.
    
    For non-email strings:
    - If the string is too short to show both first and last (len <= visible * 2),
      the entire string is masked.
    - Otherwise, the first `visible` and last `visible` characters are shown,
      with the middle replaced by asterisks.
    
    For email strings:
    - Shows the first `visible` characters of the local part, masks the rest,
      and preserves the domain.
    
    Args:
        value: The value to mask (converted to string).
        visible: Number of characters to show at each end (default: 1).
    
    Returns:
        The masked string as a Markup-safe object.
    
    Examples:
        >>> mask_filter("secret123")       # "s*******3"
        >>> mask_filter("ab")              # "**"
        >>> mask_filter("user@example.com") # "u***@example.com"
    """
    from markupsafe import escape
    
    s = str(value)
    if not s:
        return escape("")
    if "@" in s:
        local, domain = s.split("@", 1)
        # For emails, show start of local part by default
        visible_local = local[:visible]
        return escape(f"{visible_local}***@{domain}")
    
    # Too short to show first+last — fully mask
    if len(s) <= visible * 2:
        return escape("*" * len(s))
    
    # Show first `visible` and last `visible`, mask the middle
    return escape(s[:visible] + "*" * (len(s) - visible * 2) + s[-visible:])

def file_size_filter(value: Any) -> Markup:
    """Format a byte count as a human-readable file size."""
    try:
        size = float(value)
    except (TypeError, ValueError):
        return escape("0 B")
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024:
            if unit == "B":
                return escape(f"{int(size)} {unit}")
            return escape(f"{size:.1f} {unit}")
        size /= 1024
    return escape(f"{size:.1f} PB")
    
def repeat_filter(value: Any, count: int = 1) -> Markup:
    """Repeat a string *count* times."""
    return escape(str(value) * count)

def phone_filter(value: Any, country_code: str = "US") -> Markup:
    """Format a string as a phone number."""
    s = str(value)
    digits = re.sub(r'\D', '', s)
    if country_code == "US" and len(digits) == 10:
        return escape(f"({digits[:3]}) {digits[3:6]}-{digits[6:]}")
    return escape(s)

def unique_filter(value: Any) -> list:
    """Remove duplicates from a list while preserving order."""
    if not isinstance(value, (list, tuple, set)):
        return value
    seen = set()
    return [x for x in value if not (x in seen or seen.add(x))]

def markdown_filter(value: Any) -> Markup:
    """Safely render Markdown to HTML."""
    try:
        import markdown
        return Markup(markdown.markdown(str(value)))
    except ImportError:
        return Markup(str(value))

def nl2br_filter(value: Any) -> Markup:
    """Replace newlines with <br> tags."""
    if not value: return Markup("")
    from markupsafe import escape
    return Markup(str(escape(value)).replace('\n', '<br>\n'))
