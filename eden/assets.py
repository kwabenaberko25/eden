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
FONTAWESOME_VERSION = "6.7.2"

# ── CDN URLs ─────────────────────────────────────────────────────────────────

ALPINE_CDN = f"https://cdn.jsdelivr.net/npm/alpinejs@{ALPINE_VERSION}/dist/cdn.min.js"
HTMX_CDN = f"https://unpkg.com/htmx.org@{HTMX_VERSION}"
TAILWIND_CDN = "https://cdn.tailwindcss.com"
FONTAWESOME_CDN = f"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/{FONTAWESOME_VERSION}/css/all.min.css"

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
    fontawesome: bool = True,
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
    if fontawesome:
        parts.append(f'<link rel="stylesheet" href="{FONTAWESOME_CDN}">')
    
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

        /* Messaging (Toasts) */
        .eden-toast-container {
            position: fixed; top: 1.5rem; right: 1.5rem; z-index: 9999;
            display: flex; flex-direction: column; gap: 0.75rem; pointer-events: none;
        }
        .eden-toast {
            pointer-events: auto; width: 22rem; padding: 1rem; border-radius: 0.75rem;
            display: flex; align-items: start; gap: 0.85rem;
            animation: eden-toast-in 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        @keyframes eden-toast-in {
            from { opacity: 0; transform: translateX(2rem) scale(0.9); }
            to { opacity: 1; transform: translateX(0) scale(1); }
        }
        .eden-toast-success { border-left: 4px solid #10B981; }
        .eden-toast-error { border-left: 4px solid #EF4444; }
        .eden-toast-warning { border-left: 4px solid #F59E0B; }
        .eden-toast-info { border-left: 4px solid #3B82F6; }
        .eden-toast-debug { border-left: 4px solid #6366F1; }
        
        .eden-toast-close {
            background: transparent; border: none; padding: 0.25rem; cursor: pointer;
            color: #94A3B8; transition: color 0.2s;
        }
        .eden-toast-close:hover { color: white; }
    </style>""")

    if htmx:
        parts.append(f'<script src="{HTMX_CDN}"></script>')
    if alpine:
        parts.append(f'<script defer src="{ALPINE_CDN}"></script>')

    return Markup("\n    ".join(parts))


def eden_scripts() -> Markup:
    """
    Return end-of-body ``<script>`` tags for Eden.
    Includes the 'eden-sync' HTMX extension for real-time model updates.
    """
    return Markup(
        "<!-- Eden Scripts -->\n"
        "<script>\n"
        "  (function() {\n"
        "    // Eden framework runtime\n"
        "    document.documentElement.classList.add('eden-ready');\n"
        "\n"
        "    // Auto-inject CSRF token into HTMX requests\n"
        "    document.addEventListener('htmx:configRequest', (event) => {\n"
        "      const csrfToken = document.cookie.split('; ')\n"
        "        .find(row => row.startsWith('csrftoken='))\n"
        "        ?.split('=')[1];\n"
        "      if (csrfToken) {\n"
        "        event.detail.headers['X-CSRF-Token'] = csrfToken;\n"
        "      }\n"
        "    });\n"
        "\n"
        "    // --- eden-sync HTMX Extension ---\n"
        "    let socket = null;\n"
        "    const subscriptions = new Set();\n"
        "    \n"
        "    function connect() {\n"
        "      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';\n"
        "      const url = `${protocol}//${window.location.host}/_eden/sync`;\n"
        "      socket = new WebSocket(url);\n"
        "      \n"
        "      socket.onopen = () => {\n"
        "        console.log('[Eden] Real-time sync connected');\n"
        "        // Resubscribe on reconnect\n"
        "        subscriptions.forEach(channel => {\n"
        "          socket.send(JSON.stringify({action: 'subscribe', channel}));\n"
        "        });\n"
        "      };\n"
        "      \n"
        "      socket.onmessage = (event) => {\n"
        "        const data = JSON.parse(event.data);\n"
        "        if (data.event) {\n"
        "          // Dispatch event globally and to specific elements\n"
        "          document.dispatchEvent(new CustomEvent(data.event, { detail: data.data }));\n"
        "          const channel = data.event.split(':')[0];\n"
        "          const elements = document.querySelectorAll(`[hx-sync=\"${channel}\"]`);\n"
        "          elements.forEach(el => {\n"
        "            htmx.trigger(el, data.event, data.data);\n"
        "          });\n"
        "        }\n"
        "      };\n"
        "      \n"
        "      socket.onclose = () => {\n"
        "        console.log('[Eden] Real-time sync disconnected, retrying in 2s...');\n"
        "        setTimeout(connect, 2000);\n"
        "      };\n"
        "    }\n"
        "\n"
        "    htmx.defineExtension('eden-sync', {\n"
        "      onEvent: function(name, evt) {\n"
        "        if (name === 'htmx:afterProcessNode') {\n"
        "          const el = evt.target;\n"
        "          const channel = el.getAttribute('hx-sync');\n"
        "          if (channel && !subscriptions.has(channel)) {\n"
        "            subscriptions.add(channel);\n"
        "            if (socket && socket.readyState === WebSocket.OPEN) {\n"
        "              socket.send(JSON.stringify({action: 'subscribe', channel}));\n"
        "            }\n"
        "          }\n"
        "        }\n"
        "      }\n"
        "    });\n"
        "    \n"
        "    // Force HTMX to use the extension globally\n"
        "    document.body.setAttribute('hx-ext', 'eden-sync');\n"
        "    connect();\n"
        "\n"
        "    // --- Messaging (Toasts) ---\n"
        "    function showToast(msg, level = 'info') {\n"
        "      let container = document.querySelector('.eden-toast-container');\n"
        "      if (!container) {\n"
        "        container = document.createElement('div');\n"
        "        container.className = 'eden-toast-container';\n"
        "        document.body.appendChild(container);\n"
        "      }\n"
        "      const toast = document.createElement('div');\n"
        "      toast.className = `eden-toast glass eden-toast-${level}`;\n"
        "      toast.innerHTML = `\n"
        "        <div style=\"flex-grow: 1;\">\n"
        "          <p style=\"margin: 0; font-size: 0.875rem; font-weight: 500; color: #F1F5F9;\">${msg}</p>\n"
        "        </div>\n"
        "        <button class=\"eden-toast-close\" onclick=\"this.parentElement.remove()\">\n"
        "          <svg style=\"width: 1rem; height: 1rem;\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">\n"
        "            <path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M6 18L18 6M6 6l12 12\"></path>\n"
        "          </svg>\n"
        "        </button>\n"
        "      `;\n"
        "      container.appendChild(toast);\n"
        "      setTimeout(() => {\n"
        "        toast.style.opacity = '0';\n"
        "        toast.style.transform = 'translateX(2rem)';\n"
        "        toast.style.transition = 'all 0.4s ease';\n"
        "        setTimeout(() => toast.remove(), 400);\n"
        "      }, 5000);\n"
        "    }\n"
        "    \n"
        "    document.addEventListener('eden:message', (e) => showToast(e.detail.message, e.detail.level_tag));\n"
        "  })();\n"
        "</script>"
    )
