"""
Eden — CDN Asset Management

Version-pinned CDN configuration for AlpineJS, HTMX, and TailwindCSS.
Provides ``eden_head()`` and ``eden_scripts()`` helpers for templates.
"""

from markupsafe import Markup

# ── Pinned versions ──────────────────────────────────────────────────────────

ALPINE_VERSION = "3.14.9"
HTMX_VERSION = "2.0.4"
TAILWIND_VERSION = "4"

# ── CDN URLs ─────────────────────────────────────────────────────────────────

ALPINE_CDN = f"https://cdn.jsdelivr.net/npm/alpinejs@{ALPINE_VERSION}/dist/cdn.min.js"
HTMX_CDN = f"https://unpkg.com/htmx.org@{HTMX_VERSION}"
TAILWIND_CDN = "https://cdn.tailwindcss.com"

# Google Fonts (Plus Jakarta Sans + Outfit)
FONTS_CDN = (
    "https://fonts.googleapis.com/css2?"
    "family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&"
    "family=Outfit:wght@400;500;600;700&"
    "display=swap"
)

# ── Template helpers ─────────────────────────────────────────────────────────


def eden_head(
    *,
    alpine: bool = True,
    htmx: bool = True,
    tailwind: bool = True,
    fonts: bool = True,
) -> Markup:
    """
    Return ``<head>`` tags for Eden's front-end stack.

    Usage in a template::

        {{ eden_head() }}
        {# or with the @eden_head directive #}
    """
    parts: list[str] = [
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
    ]
    if fonts:
        parts.append('<link rel="preconnect" href="https://fonts.googleapis.com">')
        parts.append('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>')
        parts.append(f'<link rel="stylesheet" href="{FONTS_CDN}">')
    if tailwind:
        parts.append(f'<script src="{TAILWIND_CDN}"></script>')
    
    # Enforce premium default styles
    parts.append("""<style>
        :root {
            --eden-obsidian: #0F172A;
        }
        body {
            background-color: var(--eden-obsidian);
            color: #F1F5F9; /* slate-100 */
            font-family: 'Plus Jakarta Sans', sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            margin: 0;
            transition: background-color 0.3s ease;
        }
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Outfit', sans-serif;
        }
        .glass {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #0F172A; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }
        
        /* Micro-animations */
        .hover-lift { transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1); }
        .hover-lift:hover { transform: translateY(-2px) scale(1.02); }
    </style>""")

    if htmx:
        parts.append(f'<script src="{HTMX_CDN}"></script>')
    if alpine:
        parts.append(f'<script defer src="{ALPINE_CDN}"></script>')

    return Markup("\n    ".join(parts))


def eden_scripts() -> Markup:
    """
    Return end-of-body ``<script>`` tags for Eden.

    Currently a no-op placeholder — all CDN scripts are loaded in the head.
    Use this for future custom Eden JS (e.g. toast notifications, live reload).
    """
    return Markup(
        "<!-- Eden Scripts -->\n"
        "<script>\n"
        "  // Eden framework runtime\n"
        "  document.documentElement.classList.add('eden-ready');\n"
        "\n"
        "  // Auto-inject CSRF token into HTMX requests\n"
        "  document.addEventListener('htmx:configRequest', (event) => {\n"
        "    const csrfToken = document.cookie.split('; ')\n"
        "      .find(row => row.startsWith('csrftoken='))\n"
        "      ?.split('=')[1];\n"
        "    if (csrfToken) {\n"
        "      event.detail.headers['X-CSRF-Token'] = csrfToken;\n"
        "    }\n"
        "  });\n"
        "</script>"
    )
