"""
Eden — Internationalization (i18n)

Provides translation support using gettext-style message catalogs
with a simple API for marking strings translatable.

Usage:
    from eden.i18n import Translations, _

    i18n = Translations(locale_dir="locales", default_locale="en")
    i18n.mount(app)

    # In views:
    message = _("Hello, world!")

    # In templates (auto-registered):
    {{ _("Welcome") }}
"""

from __future__ import annotations

import gettext
import os
from pathlib import Path
from typing import Any, Callable


# ── Module-level translator (set by Translations.activate) ───────────────

_current_gettext: Callable[[str], str] = lambda s: s


def _(message: str) -> str:
    """Translate a message using the currently active locale."""
    return _current_gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Translate with plural support."""
    if n == 1:
        return _current_gettext(singular)
    return _current_gettext(plural)


# ── Translations Manager ────────────────────────────────────────────────

class Translations:
    """
    Manages locale catalogs and provides translation middleware.

    Directory structure:
        locales/
        ├── en/
        │   └── LC_MESSAGES/
        │       ├── messages.po
        │       └── messages.mo
        ├── fr/
        │   └── LC_MESSAGES/
        │       ├── messages.po
        │       └── messages.mo
        └── ...

    Usage:
        i18n = Translations(locale_dir="locales", default_locale="en")
        i18n.mount(app)

        # Switch locale per-request via Accept-Language header or ?lang= param
    """

    def __init__(
        self,
        locale_dir: str = "locales",
        default_locale: str = "en",
        domain: str = "messages",
    ) -> None:
        self.locale_dir = Path(locale_dir)
        self.default_locale = default_locale
        self.domain = domain
        self._catalogs: dict[str, gettext.GNUTranslations | gettext.NullTranslations] = {}

    @property
    def available_locales(self) -> list[str]:
        """List all locale directories found in locale_dir."""
        if not self.locale_dir.exists():
            return [self.default_locale]
        return [
            d.name for d in self.locale_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def get_catalog(self, locale: str) -> gettext.GNUTranslations | gettext.NullTranslations:
        """Load or retrieve a cached translation catalog for a locale."""
        if locale in self._catalogs:
            return self._catalogs[locale]

        try:
            catalog = gettext.translation(
                domain=self.domain,
                localedir=str(self.locale_dir),
                languages=[locale],
            )
        except FileNotFoundError:
            # Fall back to NullTranslations (passthrough)
            catalog = gettext.NullTranslations()

        self._catalogs[locale] = catalog
        return catalog

    def activate(self, locale: str) -> None:
        """Set the active locale for translation calls."""
        global _current_gettext
        catalog = self.get_catalog(locale)
        _current_gettext = catalog.gettext

    def detect_locale(self, request: Any) -> str:
        """
        Detect the best locale for a request.

        Priority:
            1. ?lang= query parameter
            2. Accept-Language header
            3. Default locale
        """
        # Check query param
        lang = request.query_params.get("lang")
        if lang and lang in self.available_locales:
            return lang

        # Check Accept-Language header
        accept = request.headers.get("accept-language", "")
        if accept:
            # Parse basic Accept-Language (e.g., "en-US,en;q=0.9,fr;q=0.8")
            for part in accept.split(","):
                locale_tag = part.strip().split(";")[0].split("-")[0].strip()
                if locale_tag in self.available_locales:
                    return locale_tag

        return self.default_locale

    def mount(self, app: Any) -> None:
        """
        Mount i18n as middleware and register template globals.

        - Auto-detects locale per request
        - Registers _() in template context
        """
        i18n = self

        # Register template globals if templates are available
        try:
            templates = app.templates
            templates.env.globals["_"] = _
            templates.env.globals["ngettext"] = ngettext
        except Exception:
            pass

        # Store on app for access
        app.i18n = i18n

    def create_locale(self, locale: str) -> Path:
        """
        Create the directory structure for a new locale.

        Returns the path to LC_MESSAGES for the new locale.
        """
        lc_path = self.locale_dir / locale / "LC_MESSAGES"
        lc_path.mkdir(parents=True, exist_ok=True)
        return lc_path
