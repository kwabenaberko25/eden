"""
Eden — Validators

A comprehensive set of async-friendly validators that work standalone or
as Pydantic annotated types / field validators.

Usage (standalone):
    from eden.validators import validate_email, validate_phone

    result = validate_email("hello@example.com")   # ValidationResult
    if not result.ok:
        print(result.error)

Usage (Pydantic field):
    from pydantic import BaseModel
    from eden.validators.types import Email, PhoneNumber, GPSCoordinate

    class Profile(BaseModel):
        email: Email
        phone: PhoneNumber
        location: GPSCoordinate
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

# ─────────────────────────────────────────────────────────────────────────────
# Result object
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Returned by every standalone validator."""
    ok: bool
    value: Any = None
    error: str | None = None

    @property
    def is_valid(self) -> bool:
        """Returns True if there was no validation error."""
        return self.ok

    def __bool__(self) -> bool:
        return self.ok


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ok(value: Any) -> ValidationResult:
    return ValidationResult(ok=True, value=value)

def _err(msg: str) -> ValidationResult:
    return ValidationResult(ok=False, error=msg)


# ─────────────────────────────────────────────────────────────────────────────
# Regex constants
# ─────────────────────────────────────────────────────────────────────────────

# RFC 5322-ish — stricter than a simple regex but not a full parser
_EMAIL_RE = re.compile(
    r"^(?:[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]"
    r"|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")"
    r"@(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}\.?"
    r"|\[(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\])$"
)

# E.164 international + common local formats
_PHONE_RE = re.compile(
    r"^\+?(\d[\s\-\.]?){7,14}\d$"
)

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

# Luhn check pattern helpers — actual check done in code
_CREDIT_CARD_RE = re.compile(r"^\d{13,19}$")

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")

_POSTCODE_PATTERNS: dict[str, re.Pattern] = {
    "GB": re.compile(r"^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$", re.I),
    "US": re.compile(r"^\d{5}(?:-\d{4})?$"),
    "CA": re.compile(r"^[A-Z]\d[A-Z] ?\d[A-Z]\d$", re.I),
    "AU": re.compile(r"^\d{4}$"),
    "DE": re.compile(r"^\d{5}$"),
    "GH": re.compile(r"^[A-Z]{2}-\d{3,4}-\d{4}$", re.I),  # Ghana Post GPS Code
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Email
# ─────────────────────────────────────────────────────────────────────────────

def validate_email(value: str) -> ValidationResult:
    """
    Validate an email address (RFC 5322 structural check).

    For DNS-level verification, install ``email-validator`` and use
    Pydantic's ``EmailStr`` type instead.

    >>> validate_email("user@example.com").ok
    True
    >>> validate_email("not-an-email").ok
    False
    """
    value = value.strip().lower()
    if not value:
        return _err("Email is required.")
    if len(value) > 320:
        return _err("Email must not exceed 320 characters.")
    if not _EMAIL_RE.match(value):
        return _err(f"'{value}' is not a valid email address.")
    local, domain = value.rsplit("@", 1)
    if len(local) > 64:
        return _err("Email local-part must not exceed 64 characters.")
    return _ok(value)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Phone Number
# ─────────────────────────────────────────────────────────────────────────────

def validate_phone(
    value: str,
    *,
    country_code: str | None = None,
    allow_extensions: bool = False,
) -> ValidationResult:
    """
    Validate a phone number.

    Supports E.164 international format (``+233501234567``) and common
    local formats with spaces, dashes, or dots.

    Args:
        value:            Raw phone string.
        country_code:     ISO 2-letter country hint (e.g. ``"GH"``).
        allow_extensions: Allow ``ext``/``x`` suffixes (e.g. ``+1-800-555-1234 x99``).

    >>> validate_phone("+233501234567").ok
    True
    >>> validate_phone("not-a-phone").ok
    False
    """
    if not value:
        return _err("Phone number is required.")

    raw = value.strip()

    # Strip extension if permitted
    if allow_extensions:
        raw = re.sub(r"[\s\-]*(ext|x)[\s\-]*\d+$", "", raw, flags=re.I).strip()

    # Strip common formatting characters for digit counting
    digits_only = re.sub(r"[\s\-\.\(\)]", "", raw)
    if raw.startswith("+"):
        digits_only = "+" + digits_only.lstrip("+")

    if not _PHONE_RE.match(digits_only):
        return _err(f"'{value}' is not a valid phone number.")

    # Country-specific prefix checks
    if country_code == "GH":
        local = digits_only.lstrip("+")
        # Ghanaian numbers start with 0 locally or +233 internationally
        if not (local.startswith("233") or local.startswith("0")):
            return _err("Ghanaian numbers must start with +233 or 0.")
        core = local[3:] if local.startswith("233") else local[1:]
        if not re.match(r"^[235]\d{8}$", core):
            return _err(f"'{value}' is not a valid Ghanaian phone number.")

    return _ok(digits_only)


# ─────────────────────────────────────────────────────────────────────────────
# 3. GPS / Geographic Coordinates
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Coordinate:
    lat: float
    lng: float

    def __str__(self) -> str:
        return f"{self.lat}, {self.lng}"


def validate_gps(
    value: str | tuple | dict,
    *,
    lat_range: tuple[float, float] = (-90.0, 90.0),
    lng_range: tuple[float, float] = (-180.0, 180.0),
) -> ValidationResult:
    """
    Validate GPS latitude/longitude.

    Accepts:
    - A string like ``"5.6037, -0.1870"``
    - A tuple/list like ``(5.6037, -0.1870)``
    - A dict like ``{"lat": 5.6037, "lng": -0.1870}``

    >>> validate_gps("5.6037, -0.1870").ok
    True
    >>> validate_gps((200, 0)).ok
    False
    """
    try:
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(",")]
            if len(parts) != 2:
                return _err("GPS string must be in format 'lat, lng'.")
            lat, lng = float(parts[0]), float(parts[1])
        elif isinstance(value, (tuple, list)):
            if len(value) != 2:
                return _err("GPS sequence must have exactly 2 elements: (lat, lng).")
            lat, lng = float(value[0]), float(value[1])
        elif isinstance(value, dict):
            lat = float(value.get("lat", value.get("latitude", None)))
            lng = float(value.get("lng", value.get("longitude", value.get("lon", None))))
        else:
            return _err("GPS value must be a string, tuple, list, or dict.")
    except (TypeError, ValueError):
        return _err("GPS coordinates must be numeric values.")

    if not (lat_range[0] <= lat <= lat_range[1]):
        return _err(f"Latitude must be between {lat_range[0]} and {lat_range[1]}. Got {lat}.")
    if not (lng_range[0] <= lng <= lng_range[1]):
        return _err(f"Longitude must be between {lng_range[0]} and {lng_range[1]}. Got {lng}.")

    return _ok(Coordinate(lat=lat, lng=lng))


# ─────────────────────────────────────────────────────────────────────────────
# 4. URL
# ─────────────────────────────────────────────────────────────────────────────

def validate_url(
    value: str,
    *,
    allowed_schemes: tuple[str, ...] = ("http", "https"),
    require_tld: bool = True,
) -> ValidationResult:
    """
    Validate a URL.

    >>> validate_url("https://eden.dev").ok
    True
    >>> validate_url("ftp://files.example.com", allowed_schemes=("ftp",)).ok
    True
    >>> validate_url("not-a-url").ok
    False
    """
    if not value:
        return _err("URL is required.")
    try:
        parsed = urlparse(value.strip())
    except Exception:
        return _err(f"'{value}' could not be parsed as a URL.")

    if parsed.scheme not in allowed_schemes:
        return _err(f"URL scheme '{parsed.scheme}' is not allowed. Expected one of {allowed_schemes}.")
    if not parsed.netloc:
        return _err(f"'{value}' has no host/domain.")
    if require_tld:
        host = parsed.hostname or ""
        if "." not in host or host.endswith("."):
            return _err(f"'{host}' does not appear to be a valid domain (missing TLD).")
    return _ok(value.strip())


# ─────────────────────────────────────────────────────────────────────────────
# 5. IP Address
# ─────────────────────────────────────────────────────────────────────────────

def validate_ip(
    value: str,
    *,
    version: int | None = None,  # 4, 6, or None for both
    allow_private: bool = True,
) -> ValidationResult:
    """
    Validate an IPv4 or IPv6 address.

    >>> validate_ip("192.168.1.1").ok
    True
    >>> validate_ip("::1").ok
    True
    >>> validate_ip("192.168.1.1", allow_private=False).ok
    False
    """
    if not value:
        return _err("IP address is required.")
    try:
        addr = ipaddress.ip_address(value.strip())
    except ValueError:
        return _err(f"'{value}' is not a valid IP address.")

    if version == 4 and not isinstance(addr, ipaddress.IPv4Address):
        return _err(f"'{value}' is not a valid IPv4 address.")
    if version == 6 and not isinstance(addr, ipaddress.IPv6Address):
        return _err(f"'{value}' is not a valid IPv6 address.")
    if not allow_private and addr.is_private:
        return _err(f"'{value}' is a private IP address and is not allowed.")

    return _ok(str(addr))


# ─────────────────────────────────────────────────────────────────────────────
# 6. Credit / Debit Card (Luhn algorithm)
# ─────────────────────────────────────────────────────────────────────────────

def _luhn_check(number: str) -> bool:
    digits = [int(d) for d in reversed(number)]
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


CARD_BRANDS: dict[str, re.Pattern] = {
    "Visa":             re.compile(r"^4\d{12}(?:\d{3})?(?:\d{3})?$"),
    "Mastercard":       re.compile(r"^5[1-5]\d{14}$|^2(?:2[2-9][1-9]|2[3-9]\d|[3-6]\d{2}|7[01]\d|720)\d{12}$"),
    "Amex":             re.compile(r"^3[47]\d{13}$"),
    "Discover":         re.compile(r"^6(?:011|5\d{2})\d{12}$"),
    "Diners Club":      re.compile(r"^3(?:0[0-5]|[68]\d)\d{11}$"),
    "JCB":              re.compile(r"^(?:2131|1800|35\d{3})\d{11}$"),
    "UnionPay":         re.compile(r"^62\d{14,17}$"),
}


def validate_credit_card(value: str) -> ValidationResult:
    """
    Validate a credit/debit card number using the Luhn algorithm.

    Returns the detected card ``brand`` in ``value``.

    >>> validate_credit_card("4111111111111111").ok
    True
    >>> validate_credit_card("1234567890123456").ok
    False
    """
    digits = re.sub(r"[\s\-]", "", value)
    if not _CREDIT_CARD_RE.match(digits):
        return _err("Card number must contain 13–19 digits.")
    if not _luhn_check(digits):
        return _err("Card number failed the Luhn check — it may contain a typo.")

    brand = "Unknown"
    for name, pattern in CARD_BRANDS.items():
        if pattern.match(digits):
            brand = name
            break

    return _ok({"number": digits, "brand": brand})


# ─────────────────────────────────────────────────────────────────────────────
# 7. Date / DateTime
# ─────────────────────────────────────────────────────────────────────────────

def validate_date(
    value: str | date | datetime,
    *,
    fmt: str = "%Y-%m-%d",
    min_date: date | None = None,
    max_date: date | None = None,
    not_in_past: bool = False,
    not_in_future: bool = False,
) -> ValidationResult:
    """
    Validate a date value and optionally enforce bounds.

    >>> validate_date("2025-12-31").ok
    True
    >>> validate_date("not-a-date").ok
    False
    """
    if isinstance(value, datetime):
        d = value.date()
    elif isinstance(value, date):
        d = value
    else:
        try:
            d = datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            return _err(f"'{value}' does not match the expected date format '{fmt}'.")

    today = date.today()
    if not_in_past and d < today:
        return _err(f"Date '{d}' cannot be in the past.")
    if not_in_future and d > today:
        return _err(f"Date '{d}' cannot be in the future.")
    if min_date and d < min_date:
        return _err(f"Date '{d}' must be on or after {min_date}.")
    if max_date and d > max_date:
        return _err(f"Date '{d}' must be on or before {max_date}.")

    return _ok(d)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Colour
# ─────────────────────────────────────────────────────────────────────────────

def validate_color(value: str) -> ValidationResult:
    """
    Validate a CSS hex colour (#RGB, #RRGGBB, #RRGGBBAA).

    >>> validate_color("#FF5733").ok
    True
    >>> validate_color("#GGG").ok
    False
    """
    if not value:
        return _err("Colour value is required.")
    if not _HEX_COLOR_RE.match(value.strip()):
        return _err(f"'{value}' is not a valid hex colour (expected #RGB, #RRGGBB, or #RRGGBBAA).")
    return _ok(value.strip().upper())


# ─────────────────────────────────────────────────────────────────────────────
# 9. Slug
# ─────────────────────────────────────────────────────────────────────────────

def validate_slug(value: str, *, max_length: int = 255) -> ValidationResult:
    """
    Validate a URL slug (lowercase letters, numbers, hyphens).

    >>> validate_slug("my-awesome-post").ok
    True
    >>> validate_slug("My Post!").ok
    False
    """
    if not value:
        return _err("Slug is required.")
    if len(value) > max_length:
        return _err(f"Slug must not exceed {max_length} characters.")
    if not _SLUG_RE.match(value):
        return _err(f"'{value}' is not a valid slug (lowercase letters, numbers, and hyphens only).")
    return _ok(value)


# ─────────────────────────────────────────────────────────────────────────────
# 10. Username
# ─────────────────────────────────────────────────────────────────────────────

def validate_username(
    value: str,
    *,
    min_length: int = 3,
    max_length: int = 30,
    allow_dots: bool = True,
    allow_dashes: bool = True,
) -> ValidationResult:
    """
    Validate a username: alphanumeric + optional ``_``, ``.``, ``-``.

    >>> validate_username("eden_user").ok
    True
    >>> validate_username("a").ok
    False
    """
    if not value:
        return _err("Username is required.")
    if not (min_length <= len(value) <= max_length):
        return _err(f"Username must be between {min_length} and {max_length} characters.")

    allowed = r"a-zA-Z0-9_"
    if allow_dots:
        allowed += r"\."
    if allow_dashes:
        allowed += r"\-"
    pattern = re.compile(rf"^[{allowed}]+$")

    if not pattern.match(value):
        extra = []
        if allow_dots:
            extra.append("dots")
        if allow_dashes:
            extra.append("dashes")
        extras = (", " + ", ".join(extra)) if extra else ""
        return _err(f"Username may only contain letters, digits, underscores{extras}.")

    if value.startswith((".", "-", "_")) or value.endswith((".", "-", "_")):
        return _err("Username must not start or end with a special character.")

    return _ok(value)


# ─────────────────────────────────────────────────────────────────────────────
# 11. Password Strength
# ─────────────────────────────────────────────────────────────────────────────

def validate_password(
    value: str,
    *,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = True,
    special_chars: str = r"!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~",
) -> ValidationResult:
    """
    Validate password strength.

    Returns a ``score`` (0–5) in addition to pass/fail.

    >>> validate_password("Str0ng!Pass").ok
    True
    >>> validate_password("weak").ok
    False
    """
    errors = []
    score = 0

    if len(value) < min_length:
        errors.append(f"at least {min_length} characters")
    else:
        score += 1

    if require_uppercase and not re.search(r"[A-Z]", value):
        errors.append("an uppercase letter")
    else:
        score += 1

    if require_lowercase and not re.search(r"[a-z]", value):
        errors.append("a lowercase letter")
    else:
        score += 1

    if require_digit and not re.search(r"\d", value):
        errors.append("a digit")
    else:
        score += 1

    if require_special and not re.search(rf"[{special_chars}]", value):
        errors.append("a special character")
    else:
        score += 1

    if errors:
        return _err("Password must contain: " + ", ".join(errors) + ".")

    return _ok({"password": value, "score": score})


# ─────────────────────────────────────────────────────────────────────────────
# 12. Postcode / ZIP Code
# ─────────────────────────────────────────────────────────────────────────────

def validate_postcode(value: str, *, country: str = "US") -> ValidationResult:
    """
    Validate a postcode/ZIP code for a given country.

    Supported countries: GB, US, CA, AU, DE, GH.

    >>> validate_postcode("10001", country="US").ok
    True
    >>> validate_postcode("SW1A 1AA", country="GB").ok
    True
    """
    if not value:
        return _err("Postcode is required.")
    code = country.upper()
    pattern = _POSTCODE_PATTERNS.get(code)
    if pattern is None:
        return _err(f"No postcode validator available for country '{country}'.")
    if not pattern.match(value.strip()):
        return _err(f"'{value}' is not a valid {country} postcode.")
    return _ok(value.strip().upper())


# ─────────────────────────────────────────────────────────────────────────────
# 13. Range (numeric)
# ─────────────────────────────────────────────────────────────────────────────

def validate_range(
    value: int | float | Decimal,
    *,
    min_val: int | float | Decimal | None = None,
    max_val: int | float | Decimal | None = None,
) -> ValidationResult:
    """
    Validate that a number falls within an inclusive range.

    >>> validate_range(5, min_val=1, max_val=10).ok
    True
    >>> validate_range(0, min_val=1).ok
    False
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return _err(f"'{value}' is not a valid number.")
    if min_val is not None and v < float(min_val):
        return _err(f"Value must be ≥ {min_val}. Got {v}.")
    if max_val is not None and v > float(max_val):
        return _err(f"Value must be ≤ {max_val}. Got {v}.")
    return _ok(v)


# ─────────────────────────────────────────────────────────────────────────────
# 14. File / MIME type
# ─────────────────────────────────────────────────────────────────────────────

COMMON_MIME_GROUPS: dict[str, list[str]] = {
    "image":    ["image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"],
    "video":    ["video/mp4", "video/webm", "video/ogg", "video/quicktime"],
    "audio":    ["audio/mpeg", "audio/ogg", "audio/wav", "audio/webm"],
    "document": [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/csv",
    ],
    "archive":  ["application/zip", "application/x-tar", "application/x-gzip"],
}


def validate_file_type(
    filename: str,
    content_type: str,
    *,
    allowed_mime_types: list[str] | None = None,
    allowed_groups: list[str] | None = None,
    max_size_mb: float | None = None,
    size_bytes: int | None = None,
) -> ValidationResult:
    """
    Validate an uploaded file's MIME type (and optionally its size).

    >>> validate_file_type("photo.jpg", "image/jpeg", allowed_groups=["image"]).ok
    True
    >>> validate_file_type("virus.exe", "application/x-msdownload", allowed_groups=["image"]).ok
    False
    """
    allowed: set[str] = set(allowed_mime_types or [])
    for group in (allowed_groups or []):
        allowed.update(COMMON_MIME_GROUPS.get(group, []))

    if allowed and content_type not in allowed:
        return _err(
            f"File type '{content_type}' is not allowed. "
            f"Allowed types: {', '.join(sorted(allowed))}."
        )

    if max_size_mb is not None and size_bytes is not None:
        max_bytes = int(max_size_mb * 1024 * 1024)
        if size_bytes > max_bytes:
            return _err(
                f"File size {size_bytes / 1024 / 1024:.2f} MB exceeds the "
                f"maximum of {max_size_mb} MB."
            )

    return _ok({"filename": filename, "content_type": content_type})


# ─────────────────────────────────────────────────────────────────────────────
# 15. IBAN (International Bank Account Number)
# ─────────────────────────────────────────────────────────────────────────────

_IBAN_LENGTHS: dict[str, int] = {
    "GB": 22, "DE": 22, "FR": 27, "ES": 24, "IT": 27,
    "NL": 18, "BE": 16, "GH": 0,  # Ghana uses BBAN/local, no standard IBAN assigned
}


def validate_iban(value: str) -> ValidationResult:
    """
    Validate an IBAN using the MOD-97 algorithm (ISO 7064).

    >>> validate_iban("GB82WEST12345698765432").ok
    True
    >>> validate_iban("INVALID").ok
    False
    """
    iban = re.sub(r"\s+", "", value.strip()).upper()
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{4,}$", iban):
        return _err("IBAN format is invalid.")

    country = iban[:2]
    expected_len = _IBAN_LENGTHS.get(country)
    if expected_len and len(iban) != expected_len:
        return _err(f"IBAN for {country} must be {expected_len} characters. Got {len(iban)}.")

    # MOD-97 check: move first 4 chars to end, convert letters to numbers
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    if int(numeric) % 97 != 1:
        return _err("IBAN failed the MOD-97 checksum.")

    return _ok(iban)


# ─────────────────────────────────────────────────────────────────────────────
# 16. National ID (Ghana-style example + extensible)
# ─────────────────────────────────────────────────────────────────────────────

_NATIONAL_ID_PATTERNS: dict[str, re.Pattern] = {
    "GH": re.compile(r"^GHA-\d{9}-\d$"),      # Ghana NIA card format
    "US": re.compile(r"^\d{3}-\d{2}-\d{4}$"),  # SSN
    "GB": re.compile(r"^[A-Z]{2}\d{6}[A-D]$"), # NI Number
}


def validate_national_id(value: str, *, country: str) -> ValidationResult:
    """
    Validate a national ID / SSN for a given country.

    Supported: GH (Ghana NIA), US (SSN), GB (NI Number).

    >>> validate_national_id("GHA-123456789-0", country="GH").ok
    True
    """
    country = country.upper()
    pattern = _NATIONAL_ID_PATTERNS.get(country)
    if pattern is None:
        return _err(f"No national ID validator available for country '{country}'.")
    if not pattern.match(value.strip().upper()):
        return _err(f"'{value}' is not a valid {country} national ID.")
    return _ok(value.strip().upper())


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Annotated Types
# These can be used directly as field type annotations in Pydantic models.
# ─────────────────────────────────────────────────────────────────────────────

class _PydanticValidator:
    """Base mixin for annotated Pydantic validator types."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def _validate(cls, value: Any) -> Any:
        raise NotImplementedError


class EdenEmail(str, _PydanticValidator):
    """Pydantic-compatible email type using Eden's validator."""

    @classmethod
    def _validate(cls, value: Any) -> EdenEmail:
        result = validate_email(str(value))
        if not result.ok:
            raise ValueError(str(result.error))
        return cls(result.value)


class EdenPhone(str, _PydanticValidator):
    """Pydantic-compatible phone type using Eden's validator."""

    @classmethod
    def _validate(cls, value: Any) -> EdenPhone:
        result = validate_phone(str(value))
        if not result.ok:
            raise ValueError(result.error)
        return cls(result.value)


class EdenSlug(str, _PydanticValidator):
    """Pydantic-compatible slug type."""

    @classmethod
    def _validate(cls, value: Any) -> EdenSlug:
        result = validate_slug(str(value))
        if not result.ok:
            raise ValueError(result.error)
        return cls(result.value)


class EdenURL(str, _PydanticValidator):
    """Pydantic-compatible URL type."""

    @classmethod
    def _validate(cls, value: Any) -> EdenURL:
        result = validate_url(str(value))
        if not result.ok:
            raise ValueError(result.error)
        return cls(result.value)


class EdenColor(str, _PydanticValidator):
    """Pydantic-compatible hex colour type."""

    @classmethod
    def _validate(cls, value: Any) -> EdenColor:
        result = validate_color(str(value))
        if not result.ok:
            raise ValueError(result.error)
        return cls(result.value)


# ─────────────────────────────────────────────────────────────────────────────
# Public API surface
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Result
    "ValidationResult",
    # Standalone validators
    "validate_email",
    "validate_phone",
    "validate_gps",
    "validate_url",
    "validate_ip",
    "validate_credit_card",
    "validate_date",
    "validate_color",
    "validate_slug",
    "validate_username",
    "validate_password",
    "validate_postcode",
    "validate_range",
    "validate_file_type",
    "validate_iban",
    "validate_national_id",
    # Pydantic annotated types
    "EdenEmail",
    "EdenPhone",
    "EdenSlug",
    "EdenURL",
    "EdenColor",
    # Helpers
    "Coordinate",
    "CARD_BRANDS",
    "COMMON_MIME_GROUPS",
]
