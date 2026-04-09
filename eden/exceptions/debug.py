from __future__ import annotations
import inspect
import traceback
import difflib
import platform
import re
import os
import sys
from datetime import datetime
from typing import Any, TYPE_CHECKING, Optional, Union, Callable
import html as html_mod

import jinja2
from jinja2.exceptions import TemplateSyntaxError, UndefinedError
from starlette.responses import HTMLResponse

if TYPE_CHECKING:
    from eden.requests import Request
    from eden.app import Eden

try:
    import pygments
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_for_filename
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False

# ── Error Page Constants ──────────────────────────────────────────────────

STATUS_MESSAGES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
}

STATUS_ICONS = {
    400: "🔍",
    401: "🔐",
    403: "🚫",
    404: "📂",
    405: "🚫",
    408: "⌛",
    429: "🚦",
    500: "💥",
}

def render_error_response(
    status_code: int,
    detail: str,
    traceback_text: str | None = None,
) -> str:
    """Render a premium, self-contained error page (zero-dependency)."""
    title = STATUS_MESSAGES.get(status_code, "Error")
    icon = STATUS_ICONS.get(status_code, "❌")
    safe_detail = html_mod.escape(detail)

    traceback_html = ""
    if traceback_text:
        safe_tb = html_mod.escape(traceback_text)
        traceback_html = f"""
        <details class="traceback">
            <summary>Stack Trace (debug mode)</summary>
            <pre>{safe_tb}</pre>
        </details>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{status_code} — {title}</title>
    <style>
        :root {{
            --bg: #020617;
            --card: rgba(15, 23, 42, 0.7);
            --border: rgba(255, 255, 255, 0.1);
            --primary: #3b82f6;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--font-sans);
            background-color: var(--bg);
            background-image: radial-gradient(circle at 50% 50%, #1e1b4b 0%, #020617 100%);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            line-height: 1.5;
        }}
        .error-container {{
            text-align: center;
            max-width: 520px;
            width: 100%;
            padding: 48px;
            background: var(--card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 24px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.6s ease-out;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .error-icon {{
            font-size: 64px;
            margin-bottom: 24px;
            filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.3));
        }}
        .error-code {{
            font-size: 14px;
            font-weight: 700;
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 0.2em;
            margin-bottom: 12px;
        }}
        .error-title {{
            font-size: 32px;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 16px;
            letter-spacing: -0.02em;
        }}
        .error-detail {{
            font-size: 16px;
            color: var(--text-muted);
            line-height: 1.6;
            margin-bottom: 32px;
        }}
        .actions {{
            display: flex;
            gap: 12px;
            justify-content: center;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 12px 24px;
            border-radius: 12px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .btn-home {{
            background: var(--primary);
            color: white;
            box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.39);
        }}
        .btn-home:hover {{
            background: #2563eb;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(59, 130, 246, 0.23);
        }}
        .btn-secondary {{
            background: rgba(255, 255, 255, 0.05);
            color: var(--text);
            border: 1px solid var(--border);
        }}
        .btn-secondary:hover {{
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-2px);
        }}
        .brand {{
            margin-top: 48px;
            font-size: 12px;
            color: #475569;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .brand span {{ color: var(--primary); }}
        .traceback {{
            text-align: left;
            margin-top: 32px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
        }}
        .traceback summary {{
            padding: 14px 20px;
            cursor: pointer;
            font-size: 13px;
            color: #fbbf24;
            font-weight: 600;
            user-select: none;
            background: rgba(255, 255, 255, 0.02);
            transition: background 0.2s;
        }}
        .traceback summary:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}
        .traceback pre {{
            padding: 20px;
            font-size: 12px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            line-height: 1.7;
            color: var(--text-muted);
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 400px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">{icon}</div>
        <div class="error-code">{status_code} Error</div>
        <div class="error-title">{title}</div>
        <div class="error-detail">{safe_detail}</div>
        <div class="actions">
            <a href="/" class="btn btn-home">Back to Home</a>
            <a href="javascript:history.back()" class="btn btn-secondary">Previous Page</a>
        </div>
        {traceback_html}
        <div class="brand">Powered by <span>Eden Framework 🌿</span></div>
    </div>
</body>
</html>"""
def collect_debug_metadata(request: "Request") -> dict[str, Any]:
    """
    Standardize metadata extraction from the request for the debug page.
    """
    import os
    import platform
    from datetime import datetime
    
    # Try to get version from eden
    try:
        from eden import __version__
    except ImportError:
        __version__ = "1.0.0"

    metadata = {
        "Request": {
            "URL": str(request.url),
            "Method": request.method,
            "Headers": dict(request.headers),
            "Path": request.url.path,
        },
        "Environment": {
            "System": platform.system(),
            "Platform": platform.platform(),
            "Release": platform.release(),
            "Python": f"{platform.python_implementation()} {platform.python_version()}",
            "PID": os.getpid(),
            "User": os.getenv("USER") or os.getenv("USERNAME") or "Unknown",
            "CWD": os.getcwd(),
            "Eden Version": __version__,
        },
    }

    # Add optional features if they exist
    # Add optional features if they exist
    if "session" in request.scope:
        metadata["Session"] = dict(request.session)
    
    if request.cookies:
        metadata["Cookies"] = dict(request.cookies)

    # Get payload for POST/PUT if available and not too large
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            # Note: This might be tricky as we can't always await here in a sync context
            # but usually by this point standard middlewares have parsed it.
            if hasattr(request, "_form") and request._form is not None:
                metadata["Payload (Form)"] = dict(request._form)
            elif hasattr(request, "_json") and request._json is not None:
                metadata["Payload (JSON)"] = request._json
        except Exception as e:
            from eden.logging import get_logger
            get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)
            
    return metadata

def render_premium_debug_page(
    title: str,
    message: str,
    filename: str,
    lineno: int,
    column: int,
    code_frame: str,
    context_vars: dict,
    metadata: dict[str, Any],
    traceback_html: str = "",
    suggestions: list[str] | None = None,
    status_code: int = 500,
    badge: str = "ERROR"
) -> HTMLResponse:
    """Renders the high-fidelity Eden debug/error page with code context and request details."""
    # CDNs removed for zero-dependency premium design
    
    # Format context variables for display
    def format_value(value, max_length=150):
        """Format a value safely for display."""
        try:
            if value is None:
                return '<span class="val-null italic">None</span>'
            elif isinstance(value, bool):
                return f'<span class="val-bool">{str(value)}</span>'
            elif isinstance(value, (int, float)):
                return f'<span class="val-num">{value}</span>'
            elif isinstance(value, str):
                escaped = html_mod.escape(value[:max_length])
                if len(value) > max_length:
                    escaped += "..."
                return f'<span class="val-str">"{escaped}"</span>'
            elif isinstance(value, dict):
                return f'<span class="val-meta">dict({len(value)} items)</span>'
            elif isinstance(value, (list, tuple)):
                return f'<span class="val-meta">{type(value).__name__}({len(value)} items)</span>'
            return html_mod.escape(str(type(value).__name__))
        except Exception:
            return "???"

    # Format suggestions
    suggestions_html = ""
    if suggestions:
        for suggestion in suggestions:
            suggestions_html += f"""
            <div class="suggestion-item">
                <div class="suggestion-icon">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                </div>
                <p class="suggestion-text">{suggestion}</p>
            </div>
            """

    # Prepare Metadata Tabs
    def dict_to_table(d, title):
        if not d:
            return f'<p class="no-data">No {title} data available</p>'
        
        rows = []
        for k, v in sorted(d.items()):
            rows.append(f"""
            <tr class="table-row">
                <td class="table-key">{html_mod.escape(str(k))}</td>
                <td class="table-val">{format_value(v)}</td>
            </tr>
            """)
        return f'<table class="data-table"><tbody>{"".join(rows)}</tbody></table>'

    request_data = metadata.get("Request", {})
    env_data = metadata.get("Environment", {})
    session_data = metadata.get("Session", {})
    cookies_data = metadata.get("Cookies", {})
    payload_data_form = metadata.get("Payload (Form)", {})
    payload_data_json = metadata.get("Payload (JSON)", {})

    tabs = {
        "Request": dict_to_table(request_data, "request"),
        "Environment": dict_to_table(env_data, "environment"),
        "Session": dict_to_table(session_data, "session"),
        "Cookies": dict_to_table(cookies_data, "cookies")
    }

    if payload_data_form:
        tabs["Payload (Form)"] = dict_to_table(payload_data_form, "payload (form)")
    if payload_data_json:
        import json
        try:
            formatted_payload = json.dumps(payload_data_json, indent=2)
            tabs["Payload (JSON)"] = f'<pre class="json-payload"><code>{html_mod.escape(formatted_payload)}</code></pre>'
        except:
            pass

    tabs_nav = []
    tabs_content = []
    
    for i, (name, content) in enumerate(tabs.items()):
        safe_id = name.lower().replace(" ", "-").replace("(", "").replace(")", "")
        is_active = i == 0
        active_class = "active" if is_active else ""
        hidden_style = "" if is_active else 'style="display:none"'
        
        tabs_nav.append(f"""
        <button onclick="switchTab(this, '{safe_id}')" 
                id="tab-btn-{safe_id}" 
                data-tab-link="{safe_id}"
                class="tab-btn {active_class}">
            {name}
        </button>
        """)
        
        tabs_content.append(f"""
        <div id="tab-content-{safe_id}" class="tab-pane" {hidden_style}>
            {content}
        </div>
        """)

    context_html = ""
    if context_vars:
        rows: list[str] = []
        for key, val in sorted(context_vars.items()):
            if key.startswith("__") or key in ("app", "debug", "found_context"):
                continue
            rows.append(f"""
            <tr class="table-row">
                <td class="table-key-alt">{key}</td>
                <td class="table-val">{format_value(val)}</td>
            </tr>
            """)
        context_html = "".join(rows)

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} — {filename}:{lineno}{f":{column + 1}" if column >= 0 else ""}</title>
        <style>
            :root {{
                --bg: #020617;
                --card: rgba(15, 23, 42, 0.6);
                --border: rgba(255, 255, 255, 0.06);
                --primary: #3b82f6;
                --rose: #f43f5e;
                --emerald: #10b981;
                --amber: #f59e0b;
                --indigo: #6366f1;
                --text: #f8fafc;
                --text-muted: #94a3b8;
                --text-extra-muted: #64748b;
                --font-sans: ui-sans-serif, system-ui, -apple-system, sans-serif;
                --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: var(--font-sans);
                background-color: var(--bg);
                color: #cbd5e1;
                min-height: 100vh;
                line-height: 1.5;
            }}
            .glass {{ background: var(--card); backdrop-filter: blur(12px); border: 1px solid var(--border); }}
            
            /* Header */
            header {{
                position: sticky;
                top: 0;
                z-index: 50;
                padding: 1rem 1.5rem;
                margin-bottom: 2rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 1px solid var(--border);
            }}
            .header-info {{ display: flex; align-items: center; gap: 0.75rem; }}
            .header-icon {{
                background: rgba(244, 63, 94, 0.1);
                color: var(--rose);
                width: 2rem;
                height: 2rem;
                border-radius: 0.5rem;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 1px solid rgba(244, 63, 94, 0.2);
            }}
            .header-title {{ font-weight: 700; color: white; font-size: 0.875rem; }}
            .header-subtitle {{ color: var(--text-extra-muted); font-size: 0.625rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }}
            
            /* Layout */
            main {{ max-width: 80rem; margin: 0 auto; padding: 0 1.5rem 6rem; }}
            .grid {{ display: grid; grid-template-columns: 1fr; gap: 3rem; align-items: start; }}
            @media (min-width: 1024px) {{ .grid {{ grid-template-columns: 2fr 1fr; }} }}

            /* Exception Summary */
            .exception-header {{ margin-bottom: 3rem; animation: slideUp 0.4s ease-out; }}
            @keyframes slideUp {{ from {{ transform: translateY(10px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
            .message-title {{ color: var(--rose); font-weight: 700; font-size: 1.25rem; margin-bottom: 1rem; }}
            .message-title span {{ color: var(--rose); filter: brightness(1.2); }}
            .meta-tags {{ display: flex; flex-wrap: wrap; gap: 1rem; font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-extra-muted); }}
            .meta-tag {{ background: rgba(255, 255, 255, 0.05); padding: 0.25rem 0.625rem; border-radius: 9999px; border: 1px solid var(--border); display: flex; gap: 0.375rem; }}
            .tag-key {{ opacity: 0.6; }}
            .tag-val-file {{ color: var(--indigo); }}
            .tag-val-line {{ color: var(--emerald); }}
            .tag-val-col {{ color: var(--amber); }}
            
            .btn-copy {{
                margin-left: auto;
                background: rgba(244, 63, 94, 0.1);
                color: var(--rose);
                border: 1px solid rgba(244, 63, 94, 0.2);
                padding: 0.25rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.625rem;
                font-weight: 700;
                text-transform: uppercase;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            .btn-copy:hover {{ background: rgba(244, 63, 94, 0.2); }}

            /* Suggestions */
            .suggestions {{ margin-top: 1.5rem; }}
            .suggestion-item {{ display: flex; gap: 0.75rem; padding: 0.75rem; background: rgba(59, 130, 246, 0.05); border-radius: 0.75rem; border: 1px solid rgba(59, 130, 246, 0.1); margin-bottom: 0.5rem; last-child: 0; }}
            .suggestion-icon {{ color: var(--primary); margin-top: 0.125rem; width: 0.875rem; }}
            .suggestion-icon svg {{ width: 0.875rem; height: 0.875rem; }}
            .suggestion-text {{ font-size: 0.6875rem; color: var(--text-extra-muted); font-weight: 500; line-height: 1.5; }}
            .suggestion-text code {{ background: rgba(59, 130, 246, 0.15); color: #93c5fd; padding: 0.1rem 0.25rem; border-radius: 0.25rem; }}

            /* Explorer */
            .explorer-section {{ margin-top: 3rem; animation: slideUp 0.4s ease-out 0.1s backwards; }}
            .section-label {{ font-size: 0.625rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.2em; color: var(--text-extra-muted); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }}
            .explorer-card {{ border-radius: 1.5rem; border: 1px solid var(--border); overflow: hidden; background: #0b1222; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }}
            .explorer-header {{ background: rgba(255, 255, 255, 0.02); padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); display: flex; gap: 0.375rem; }}
            .dot {{ width: 0.625rem; height: 0.625rem; border-radius: 9999px; }}
            .dot-red {{ background: rgba(244, 63, 94, 0.2); border: 1px solid rgba(244, 63, 94, 0.4); }}
            .dot-yellow {{ background: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.4); }}
            .dot-green {{ background: rgba(16, 185, 129, 0.2); border: 1px solid rgba(16, 185, 129, 0.4); }}
            .code-box {{ padding: 1.5rem; font-size: 0.75rem; line-height: 1.6; overflow-x: auto; max-height: 520px; }}
            
            /* Code Highlighter Classes */
            .error-line {{ background: rgba(244, 63, 94, 0.1); border-left: 3px solid var(--rose); margin-left: -3px; }}
            .line-no {{ color: var(--text-extra-muted); opacity: 0.4; width: 3.5rem; display: inline-block; text-align: right; padding-right: 1.5rem; user-select: none; font-weight: 700; font-family: var(--font-mono); font-size: 0.7rem; }}
            .column-marker {{ position: absolute; bottom: -2px; height: 3px; width: 1ch; background: linear-gradient(90deg, #f43f5e, #fb7185); box-shadow: 0 0 15px rgba(244, 63, 94, 0.9); border-radius: 2px; z-index: 30; pointer-events: none; }}

            /* Tabs */
            .tabs-nav {{ border-bottom: 1px solid var(--border); display: flex; gap: 2rem; padding: 0 0.5rem; margin-bottom: 1.5rem; }}
            .tab-btn {{ background: none; border: none; padding-bottom: 0.75rem; color: var(--text-extra-muted); font-size: 0.625rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; cursor: pointer; transition: all 0.2s; position: relative; }}
            .tab-btn:hover {{ color: var(--text-muted); }}
            .tab-btn.active {{ color: var(--primary); }}
            .tab-btn.active::after {{ content: ''; position: absolute; bottom: -1px; left: 0; width: 100%; height: 2px; background: var(--primary); }}
            
            .data-table {{ width: 100%; border-collapse: collapse; text-align: left; }}
            .table-row {{ border-bottom: 1px solid rgba(255, 255, 255, 0.05); }}
            .table-row:last-child {{ border-bottom: none; }}
            .table-row:hover {{ background: rgba(255, 255, 255, 0.015); }}
            .table-key {{ padding: 0.75rem 1rem; font-family: var(--font-mono); font-size: 0.6875rem; color: var(--primary); width: 33%; vertical-align: top; word-break: break-all; }}
            .table-key-alt {{ padding: 0.75rem 1rem; font-family: var(--font-mono); font-size: 0.6875rem; color: var(--indigo); width: 33%; vertical-align: top; word-break: break-all; }}
            .table-val {{ padding: 0.75rem 1rem; font-family: var(--font-mono); font-size: 0.6875rem; color: var(--text-muted); word-break: break-all; }}
            .no-data {{ color: var(--text-extra-muted); font-style: italic; font-size: 0.75rem; padding: 1rem; }}
            .json-payload {{ padding: 1rem; background: rgba(0, 0, 0, 0.2); font-size: 0.6875rem; color: #fde68a; overflow-x: auto; }}

            /* Value Formatting */
            .val-null {{ color: var(--text-extra-muted); font-style: italic; }}
            .val-bool {{ color: var(--primary); font-weight: 600; }}
            .val-num {{ color: var(--emerald); font-weight: 600; }}
            .val-str {{ color: var(--amber); }}
            .val-meta {{ color: var(--text-extra-muted); font-style: italic; }}

            /* Sidebar */
            .sidebar {{ animation: slideUp 0.4s ease-out 0.3s backwards; }}
            .side-card {{ background: rgba(15, 23, 42, 0.3); padding: 1.25rem; border-radius: 1.5rem; border: 1px solid var(--border); margin-bottom: 2rem; }}
            .side-label {{ font-size: 0.625rem; font-weight: 600; text-transform: uppercase; color: var(--text-extra-muted); margin-bottom: 0.75rem; letter-spacing: 0.1em; }}
            .side-val {{ font-size: 1.125rem; font-weight: 700; color: white; display: flex; align-items: center; gap: 0.5rem; }}
            .side-val span {{ color: var(--primary); }}

            /* Footer */
            footer {{ margin-top: 5rem; padding: 3rem 0; border-top: 1px solid var(--border); text-align: center; }}
            .footer-tag {{ font-size: 0.625rem; font-weight: 700; text-transform: uppercase; color: var(--text-extra-muted); letter-spacing: 0.2em; margin-bottom: 1rem; }}
            .footer-brand {{ display: flex; align-items: center; justify-content: center; gap: 1rem; opacity: 0.4; }}
            .f-line {{ width: 2rem; height: 1px; background: var(--text-extra-muted); }}
            .f-text {{ font-size: 0.75rem; font-weight: 700; color: var(--text-muted); letter-spacing: 0.05em; }}
        </style>
    </head>
    <body class="selection:bg-rose-500/20">
        <header class="glass">
            <div class="header-info">
                <div class="header-icon">
                    <svg style="width:1.25rem;height:1.25rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                </div>
                <div>
                    <h1 class="header-title">{badge}: {title}</h1>
                    <p class="header-subtitle">Eden Framework Diagnostic Utility</p>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:1.5rem">
                <span style="font-family:var(--font-mono);font-size:0.625rem;color:var(--text-extra-muted)">{filename}:{lineno}{f":{column + 1}" if column >= 0 else ""}</span>
                <button onclick="window.location.reload()" style="background:none;border:none;cursor:pointer;color:var(--text-extra-muted);transition:color 0.2s" onmouseover="this.style.color='white'" onmouseout="this.style.color='var(--text-extra-muted)'">
                    <svg style="width:1rem;height:1rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                </button>
            </div>
        </header>

        <main>
            <section class="exception-header">
                <h2 class="message-title">
                    <span>{badge}:</span> {html_mod.escape(message.split(' (Did you mean:')[0])}
                </h2>
                <div class="meta-tags">
                    <div class="meta-tag"><span class="tag-key">FILE:</span> <span class="tag-val-file">{html_mod.escape(str(filename))}</span></div>
                    <div class="meta-tag"><span class="tag-key">LINE:</span> <span class="tag-val-line">{lineno}</span></div>
                    {f'<div class="meta-tag"><span class="tag-key">COL:</span> <span class="tag-val-col">{column + 1}</span></div>' if column >= 0 else ''}
                    <button onclick="copyToClipboard(event, `{html_mod.escape(message.replace("'", "\\'"))}`)" class="btn-copy">
                        <svg style="width:0.75rem;height:0.75rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>
                        Copy Error
                    </button>
                </div>
                {suggestions_html}
            </section>

            <section class="explorer-section">
                <div class="section-label">
                    <svg style="width:0.875rem;height:0.875rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg>
                    Source Explorer
                </div>
                <div class="explorer-card">
                    <div class="explorer-header">
                        <div class="dot dot-red"></div>
                        <div class="dot dot-yellow"></div>
                        <div class="dot dot-green"></div>
                    </div>
                    <div class="code-box">
                        {code_frame}
                    </div>
                </div>
            </section>

            <div class="grid" style="margin-top:3rem">
                <div style="display:flex;flex-direction:column;gap:3rem">
                    <section>
                        <div class="tabs-nav">
                            {"".join(tabs_nav)}
                        </div>
                        <div class="explorer-card" style="background:#0b1222">
                            {"".join(tabs_content)}
                        </div>
                    </section>
                    {traceback_html}
                </div>

                <div class="sidebar">
                    <section style="margin-bottom: 3rem">
                        <div class="section-label">
                            <svg style="width:0.875rem;height:0.875rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 1.1.9 2 2 2h12a2 2 0 002-2V7a2 2 0 00-2-2H6a2 2 0 00-2 2zM9 12h.01M13 12h.01M17 12h.01"></path></svg>
                            Frame Locals
                        </div>
                        <div class="explorer-card">
                            <div style="overflow-x:auto">
                                <table class="data-table">
                                    <tbody>
                                        {context_html if context_html else '<tr><td style="padding:2rem;text-align:center;color:var(--text-extra-muted);font-style:italic;font-size:0.75rem">No local variables to display</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </section>

                    <section class="side-card">
                        <div class="side-label">Eden Framework</div>
                        <div class="side-val">🌿 Eden <span>v1.0.0</span></div>
                    </section>
                </div>
            </div>
        </main>

        <footer>
            <p class="footer-tag">You are seeing this page because you are in debug mode.</p>
            <div class="footer-brand">
                <span class="f-line"></span>
                <span class="f-text">Powered by Eden 🌿</span>
                <span class="f-line"></span>
            </div>
        </footer>

        <script>
            function switchTab(el, tabId) {{
                const tabBtns = document.querySelectorAll('.tab-btn');
                const tabPanes = document.querySelectorAll('.tab-pane');

                tabBtns.forEach(btn => btn.classList.remove('active'));
                tabPanes.forEach(pane => pane.style.display = 'none');

                if (el) el.classList.add('active');
                
                const activePane = document.getElementById(`tab-content-${{tabId}}`);
                if (activePane) activePane.style.display = 'block';
            }}

            function copyToClipboard(event, text) {{
                navigator.clipboard.writeText(text).then(() => {{
                    const btn = event.currentTarget;
                    const originalHTML = btn.innerHTML;
                    btn.innerHTML = `<svg style="width:0.75rem;height:0.75rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> Copied!`;
                    btn.style.color = 'var(--emerald)';
                    setTimeout(() => {{
                        btn.innerHTML = originalHTML;
                        btn.style.color = 'var(--rose)';
                    }}, 2000);
                }}).catch(err => console.error('Failed to copy: ', err));
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=status_code)

def render_enhanced_template_error(
    app: "Eden", 
    request: "Request", 
    exc: Exception
) -> HTMLResponse:
    """Render a high-fidelity debug page for template errors."""
    status_code = getattr(exc, "status_code", 500)
    title = "Template Error"
    
    # Initialize basic info
    name = getattr(exc, "name", None) or getattr(exc, "filename", None) or "Unknown Template"
    lineno = getattr(exc, "lineno", 0) or getattr(exc, "line", 0)
    column: int = getattr(exc, "column", -1) or -1
    found_context = {}

    # 1. Recover context and template info from traceback (Do this first!)
    if exc.__traceback__:
        tb = exc.__traceback__
        try:
            # Walk back from the error to find the template frame
            # summary = traceback.extract_tb(tb)
            tb_iter = list(traceback.walk_tb(tb))
            
            # Walk BACKWARDS (from most specific/deepest to highest)
            for i in range(len(tb_iter) - 1, -1, -1):
                frame_obj, frame_lineno = tb_iter[i]
                frame_filename = os.path.abspath(str(frame_obj.f_code.co_filename))

                # Check for template file extension matching
                if frame_filename.endswith((".html", ".eden", ".j2")):
                    # We found a template frame. Take its coordinates.
                    name = frame_filename
                    lineno = frame_lineno
                    
                    # Try to get column from the traceback summary if accessible
                    summary = traceback.extract_tb(tb)
                    if i < len(summary):
                        fs = summary[i]
                        column = getattr(fs, "colno", -1) or -1

                    # Also try to get found_context from this frame
                    if not found_context:
                        for ctx_key in ("context", "ctx"):
                            if ctx_key in frame_obj.f_locals:
                                ctx_obj_val = frame_obj.f_locals[ctx_key]
                                if hasattr(ctx_obj_val, "get_all"):  # Jinja2 Context object
                                    found_context = ctx_obj_val.get_all()
                                    break
                                elif isinstance(ctx_obj_val, dict):
                                    found_context = ctx_obj_val
                                    break
                        if not found_context:
                            found_context = dict(frame_obj.f_locals)
                    break
        except Exception as e:
            from eden.logging import get_logger
            get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)

    # 2. Extract message & Fallback coordinates
    message = str(exc) if exc else ""
    
    # Try to get coordinates from exception if traceback didn't yield them
    if column < 0:
        if getattr(exc, "column", None) is not None:
            try:
                column = int(getattr(exc, "column", -1))
            except (ValueError, TypeError):
                pass
        elif getattr(exc, "offset", None) is not None:
            try:
                column = int(getattr(exc, "offset", 1)) - 1
            except (ValueError, TypeError):
                pass

    exc_message = getattr(exc, "message", None)
    if exc_message: # jinja2 syntax errors often use .message
        message = exc_message
    
    if not message or message.strip() == "":
        message = f"{type(exc).__name__}: An error occurred"
    
    # Determine specific error type for badge
    badge = "Template Error"
    if isinstance(exc, TemplateSyntaxError):
        badge = "Syntax Error"
        if lineno and not re.search(r"\bline\s+\d+\b", message, flags=re.IGNORECASE):
            message = f"{message} (Line {lineno})"
        else:
            message = re.sub(r"(?:at\s+)?line\s+(\d+)", r"Line \1", message, flags=re.IGNORECASE)
        message = message.strip().strip(":").strip()
    elif isinstance(exc, UndefinedError):
        badge = "Undefined Variable"

    # 3. Fuzzy suggestions (Now that we have found_context)
    suggestions = []
    EDEN_DIRECTIVES = [
        "if", "else", "elif", "for", "parent", "unless", "set", "section", 
        "yield", "auth", "guest", "include", "extends", "component", "slot", 
        "switch", "case", "default"
    ]

    if isinstance(exc, UndefinedError):
        match = re.search(r"'([^']+)' is undefined", message)
        if match:
            missing_var = match.group(1)
            candidates = ["request", "user", "url_for", "static", "csrf_token"]
            if found_context:
                candidates.extend(found_context.keys())
            
            matches = difflib.get_close_matches(missing_var, candidates, n=3, cutoff=0.7)
            if matches:
                suggestions.append(f"Check if you meant to use: {', '.join([f'<code>{m}</code>' for m in matches])}")
            
            suggestions.append(f"Ensure that <code>{missing_var}</code> is explicitly passed into the <code>render()</code> context in your view.")
    
    elif isinstance(exc, TemplateSyntaxError):
        # 1. Spelling check for directives
        if "@" in message or "directive" in message.lower():
            word_match = re.search(r"@(\w+)", message)
            if word_match:
                d_name = word_match.group(1)
                if d_name not in EDEN_DIRECTIVES:
                    matches = difflib.get_close_matches(d_name, EDEN_DIRECTIVES, n=1, cutoff=0.7)
                    if matches:
                        suggestions.append(f"The directive <code>@{d_name}</code> is unknown. Did you mean <code>@{matches[0]}</code>?")

        # 2. Block unclosed errors
        if "Unclosed block" in message or "unexpected end of template" in message.lower():
            suggestions.append("A block (likely <code>@for</code>, <code>@if</code>, or <code>@section</code>) is missing its closing <code>}</code>.")
            suggestions.append("Check that every opening <code>{</code> following a directive has a corresponding <code>}</code>.")
        
        # 3. Common Jinja2 syntax mistakes
        if "{%" in message or "%}" in message:
            suggestions.append("Eden uses a modern <code>@directive { ... }</code> style. Replace <code>{% directive %}</code> with the <code>@</code> syntax.")
        
        # 4. Filter issues
        if "no filter named" in message.lower():
            filter_match = re.search(r"filter named '([^']+)'", message.lower())
            if filter_match:
                suggestions.append(f"The filter <code>{filter_match.group(1)}</code> might not be registered or is misspelled.")
        
        # 5. Missing @ in directives
        if re.search(r"\b(?:for|if|unless|section|auth)\s*\(", message):
            suggestions.append("It looks like you're using a directive without the <code>@</code> prefix. In Eden, use <code>@for (...) { ... }</code>.")

    elif isinstance(exc, TypeError):
        if "NoneType" in message and "iterable" in message:
            suggestions.append("You are trying to loop over a variable that is <code>None</code>. Check if the query returned any results.")
        else:
            suggestions.append("There is a type mismatch in your template expression. Ensure your variables are of the expected types (e.g., don't add strings to integers).")
    
    if not suggestions:
        suggestions.append("Verify the syntax at the marked line. Eden templates require strict <code>@directive { ... }</code> structure.")
        suggestions.append("Check for typos in variable names or misplaced brackets.")

    # Find the template file
    search_dirs = []
    if hasattr(app, "_templates") and app._templates:
        try:
            from jinja2 import FileSystemLoader, ChoiceLoader
            loader = app._templates.env.loader
            
            def get_search_paths(ld):
                if isinstance(ld, FileSystemLoader):
                    return list(ld.searchpath)
                elif isinstance(ld, ChoiceLoader):
                    paths = []
                    for l in ld.loaders:
                        paths.extend(get_search_paths(l))
                    return paths
                return []

            search_dirs.extend(get_search_paths(loader))
        except (ImportError, AttributeError):
            pass
    
    # Normalize search_dirs to absolute paths for better matching
    search_dirs = [os.path.abspath(d) for d in search_dirs if d]
    if not search_dirs:
        template_dir = getattr(app, "template_dir", "templates")
        if isinstance(template_dir, str):
            search_dirs = [os.path.abspath(template_dir)]
        else:
            search_dirs = [os.path.abspath(d) for d in (template_dir or []) if d]

    template_path = None
    template_source = None
    
    if name and name != "Unknown Template":
        # 1. Try to get source from loader (supports DictLoader, etc)
        try:
            if hasattr(app, "_templates") and app._templates:
                loader = app._templates.env.loader
                if loader:
                    template_name = name
                    if os.path.isabs(template_name):
                        if os.path.exists(template_name):
                            template_path = template_name
                            with open(template_path, encoding="utf-8") as f:
                                template_source = f.read()
                        else:
                            template_name = os.path.basename(template_name)

                    if not template_path:
                        src, filename, _ = loader.get_source(app._templates.env, template_name)
                        template_source = src
                        if filename and os.path.exists(filename):
                            template_path = filename
        except Exception as e:
            from eden.logging import get_logger
            get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)

    # 2. Fallback to physical file search
    if not template_path:
        if os.path.isabs(name) and os.path.exists(name):
            template_path = name
        else:
            for d in search_dirs:
                if not d:
                    continue
                p = os.path.join(d, name)
                if os.path.exists(p):
                    template_path = p
                    break

    code_frame = ""
    safe_lineno = int(lineno or 0)
    if template_path or template_source:
        try:
            source_lines = []
            if template_source:
                source_lines = template_source.splitlines(keepends=True)
            elif template_path:
                with open(template_path, encoding="utf-8") as f:
                    source_lines = f.readlines()
            
            if source_lines:
                # --- ENHANCE COORDINATES: Try to determine column if missing ---
                safe_lineno = int(lineno or 0)
                if column < 0 and safe_lineno > 0 and safe_lineno <= len(source_lines):
                    if isinstance(exc, UndefinedError):
                        coord_match = re.search(r"'([^']+)' is undefined", str(exc))
                        if coord_match:
                            missing_var_name = coord_match.group(1)
                            target_line = source_lines[safe_lineno - 1]
                            word_match = re.search(rf"\b{re.escape(missing_var_name)}\b", target_line)
                            if word_match:
                                column = int(word_match.start())
                            elif missing_var_name in target_line:
                                column = int(target_line.find(missing_var_name))

                # --- HEURISTIC: Backward Search for Missing @ Directives ---
                if isinstance(exc, UndefinedError) and safe_lineno > 0:
                    curr_lineno = safe_lineno
                    match = re.search(r"'([^']+)' is undefined", str(exc))
                    if match:
                        missing_var = match.group(1)
                        # Look back up to 10 lines
                        for i in range(max(0, curr_lineno - 10), curr_lineno):
                            line_text = source_lines[i]
                            # Check for directive-like patterns without @
                            # e.g. "for (item in items) {" or "if (user.active) {"
                            directive_pattern = r"\b(if|for|section|auth|guest|unless|switch)\s*\("
                            directive_match = re.search(directive_pattern, line_text)
                            if directive_match:
                                if "{" in line_text or i < curr_lineno - 1:
                                    keyword = directive_match.group(1)
                                    sugg_text = (
                                        f"It looks like you might be trying to use a <code>@{keyword}</code> directive at line {i+1}. "
                                        f"In Eden, directives MUST be prefixed with <code>@</code> (e.g., <code>@{keyword} (...) {{ ... }}</code>)."
                                    )
                                    suggestions.append(sugg_text)
                                    break
                            
                            # Also check for directives with @ but no {
                            # e.g. "@for (item in items)" without {
                            at_directive_pattern = r"@(?:for|if|elif|else|unless|auth|guest|section)\s*\("
                            if re.search(at_directive_pattern, line_text) and "{" not in line_text:
                                if missing_var in line_text or i < curr_lineno - 1:
                                    suggestions.append(f"The <code>@directive</code> at line {i+1} is missing an opening <code>{{</code>. Eden requires directives to use braces to define scope.")
                                    break
                
                elif isinstance(exc, TemplateSyntaxError) and safe_lineno > 0:
                    curr_lineno = safe_lineno
                    # Look back up to 5 lines for Jinja syntax or missing braces
                    for i in range(max(0, curr_lineno - 5), min(len(source_lines), curr_lineno)):
                        line_text = source_lines[i].strip()
                        if "{%" in line_text or "%}" in line_text:
                            suggestions.append("Eden uses a modern <code>@directive { ... }</code> syntax instead of Jinja's <code>{% block %}</code> syntax. Please migrate to the Eden syntax.")
                            break
                        
                        # Check for missing opening brace after a directive
                        if re.search(r"@(?:for|if|elif|else|unless|auth|guest|section)\b[^{]*$", line_text) and "{" not in line_text and "}" not in line_text:
                            suggestions.append(f"Ensure you include an opening <code>{{</code> for your <code>@directive</code> block at line {i+1}.")
                            break
                        
                        # Check for missing closing brace (if next line is an empty block closing or similar, or it's just missing)
                        if "{" in line_text and "}" not in line_text and "unexpected" in str(exc).lower():
                            suggestions.append("Make sure you have a corresponding closing <code>}</code> for your template directives.")
                            break
                # ---------------------------------------------------------
                # Calculate the window to display
                if safe_lineno > 0 and safe_lineno <= len(source_lines):
                    start = max(0, safe_lineno - 6)
                    end = min(len(source_lines), safe_lineno + 5)
                    mark_line = safe_lineno
                else:
                    start, end, mark_line = 0, min(len(source_lines), 10), -1

                try:
                    if not HAS_PYGMENTS:
                        raise ImportError("Pygments not available")

                    lexer = get_lexer_for_filename(template_path or name or "template.html")
                    formatter = HtmlFormatter(style="monokai", nowrap=True)
                    highlighted_lines: list[str] = []
                    for i in range(start, end):
                        curr_lineno = i + 1
                        is_error = curr_lineno == mark_line
                        raw_line = source_lines[i]
                        html_line = highlight(raw_line, lexer, formatter)
                        
                        klass = "error-line" if is_error else "normal-line"
                        
                        # Add column marker if it's the error line
                        marker_html = ""
                        if is_error and column >= 0:
                            marker_html = f'<div class="column-marker" style="left: calc({column}ch + 3.2rem)"></div>'
                        
                        highlighted_lines.append(
                            f'<div class="{klass}"><span class="line-no">{curr_lineno:4}</span>{html_line}{marker_html}</div>'
                        )
                    code_frame = f'<pre class="p-0 border-0 bg-transparent"><code>{"".join(highlighted_lines)}</code></pre>'
                except Exception:
                    # Fallback if pygments fails or isn't installed
                    frame_lines = []
                    for i in range(start, end):
                        curr_lineno = i + 1
                        is_error = curr_lineno == mark_line
                        line_content = source_lines[i].rstrip()
                        prefix = " > " if is_error else "   "
                        frame_lines.append(f"{curr_lineno:4}{prefix}{line_content}")
                        if is_error and column > 0:
                            safe_col = column or 0
                            frame_lines.append(" " * (safe_col + 6) + "^")
                    code_frame = f"<pre class='p-6 text-sm font-mono leading-relaxed overflow-x-auto bg-slate-900/50 rounded-xl text-slate-300'><code>{html_mod.escape(chr(10).join(frame_lines))}</code></pre>"
            else:
                code_frame = f"<div class='p-8 border border-red-500/20 bg-red-500/5 rounded-2xl'><p class='text-red-400 font-medium'>Could not read template source</p></div>"
        except Exception:
            code_frame = f"<div class='p-8 border border-red-500/20 bg-red-500/5 rounded-2xl'><p class='text-red-400 font-medium'>Could not read template source</p></div>"
    else:
        unique_dirs = sorted(list(set(search_dirs)))
        code_frame = (
            f"<div class='p-12 text-center bg-slate-900/40 rounded-3xl border border-white/5 shadow-inner'>"
            f"<div class='h-16 w-16 bg-red-500/10 rounded-2xl flex items-center justify-center text-red-500 mx-auto mb-6 shadow-lg shadow-red-500/5'>"
            f"<svg class='w-8 h-8' fill='none' stroke='currentColor' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z'></path></svg></div>"
            f"<h3 class='text-white font-bold text-lg mb-2'>Source template not found</h3>"
            f"<p class='text-slate-500 text-sm mb-8 max-w-xs mx-auto'>The engine couldn't resolve <b class='text-slate-300'>{html_mod.escape(str(name))}</b> in the current load paths.</p>"
            f"<div class='text-[10px] font-mono text-slate-500 bg-black/40 p-5 rounded-2xl inline-block w-full max-w-md break-all text-left border border-white/5 shadow-2xl'>"
            f"<div class='flex items-center gap-2 mb-3 text-indigo-400 font-black tracking-tighter opacity-80'>SEARCH PATHS</div>"
            + "".join([f"<div class='flex gap-2 mb-1.5 last:mb-0'><span class='text-slate-700 font-black'>•</span><span class='opacity-80'>{html_mod.escape(d)}</span></div>" for d in unique_dirs])
            + f"</div></div>"
        )

    # Prepare Metadata
    metadata = collect_debug_metadata(request)

    # Final coordinate cleanup
    # Preserve template-specific badges like Syntax Error and Undefined Variable.
    if badge == "Template Error":
        if status_code == 404:
            badge = "Not Found 🔍"
        elif status_code == 403:
            badge = "Forbidden 🚫"
        elif status_code == 401:
            badge = "Unauthorized 🔑"
        elif status_code >= 500:
            badge = "Error 💥"

    safe_column = int(column or -1)
    return render_premium_debug_page(
        title=title,
        message=message,
        filename=name,
        lineno=safe_lineno,
        column=safe_column,
        code_frame=code_frame,
        context_vars=found_context,
        metadata=metadata,
        suggestions=suggestions,
        badge=badge,
        status_code=status_code
    )

def render_enhanced_exception(
    app: "Eden", 
    request: "Request", 
    exc: Exception
) -> HTMLResponse:
    """
    Renders a high-fidelity debug page for any Python exception.
    """
    status_code = getattr(exc, "status_code", 500)
    title = type(exc).__name__
    message = str(exc)
    
    # 1. Capture the most relevant frame from traceback
    tb = exc.__traceback__
    summary = traceback.extract_tb(tb)
    
    filename = "Unknown"
    lineno = 0
    column = -1
    frame = None
    
    if summary:
        last_frame = summary[-1]
        filename = last_frame.filename
        lineno = int(last_frame.lineno or 0)
        # Use colno if available (Python 3.11+)
        column = int(getattr(last_frame, "colno", -1) or -1)
    
    # SyntaxError special handling
    if isinstance(exc, SyntaxError):
        if exc.filename: filename = str(exc.filename)
        if exc.lineno: lineno = int(exc.lineno)
        if getattr(exc, "offset", None) is not None: 
            column = int(getattr(exc, "offset", 1)) - 1

    # 2. Extract local variables for that frame
    context_vars: dict[str, Any] = {}
    frames: list[Any] = []
    curr_tb = tb
    while curr_tb:
        frames.append(curr_tb.tb_frame)
        curr_tb = curr_tb.tb_next
    
    if frames:
        frame = frames[-1]
        if frame is not None:
            for k, v in frame.f_locals.items():
                if not k.startswith("__"):
                    context_vars[k] = v

    # 3. Generate Code Frame
    code_frame = ""
    safe_lineno = int(lineno or 0)
    safe_column = int(column or -1)
    
    if os.path.exists(filename) and safe_lineno > 0:
        try:
            with open(filename, encoding="utf-8") as f:
                source_lines = f.readlines()
            
            if safe_lineno <= len(source_lines):
                start = max(0, safe_lineno - 6)
                end = min(len(source_lines), safe_lineno + 5)
                code_slice = "".join(source_lines[start:end])
                
                try:
                    from pygments import highlight
                    from pygments.lexers import get_lexer_for_filename
                    from pygments.formatters import HtmlFormatter
                    lexer = get_lexer_for_filename(filename)
                    formatter = HtmlFormatter(nowrap=True)
                    highlighted = highlight(code_slice, lexer, formatter)
                    highlighted_lines = highlighted.splitlines()
                except Exception:
                    highlighted_lines = [html_mod.escape(line.rstrip()) for line in source_lines[start:end]]

                inner_frame = ""
                for i, line in enumerate(highlighted_lines):
                    curr_ln = start + i + 1
                    is_active = (curr_ln == safe_lineno)
                    marker = ""
                    if is_active and safe_column >= 0:
                        marker = f'<div class="column-marker" style="margin-left: {safe_column}ch">^</div>'
                    
                    line_class = "code-line-active" if is_active else ""
                    inner_frame += f'<div class="code-line {line_class}" data-line="{curr_ln}">'
                    inner_frame += f'<span class="line-number">{curr_ln}</span>'
                    inner_frame += f'<span class="line-content">{line}</span>'
                    inner_frame += f'</div>{marker}'
                
                code_frame = f'<pre style="margin:0;padding:0;border:0;background:transparent"><code>{inner_frame}</code></pre>'
        except Exception:
            code_frame = f"<div style='padding:2rem;border:1px solid rgba(244,63,94,0.2);background:rgba(244,63,94,0.05);border-radius:1rem'><p style='color:var(--rose);font-weight:600'>Could not read source file: {filename}</p></div>"

    # 4. Generate Traceback Section
    formatted_tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    traceback_html = f"""
    <div style="margin-top:2rem">
        <h2 class="section-label" style="margin-bottom:0.75rem;padding:0 0.25rem">
            <svg style="width:0.875rem;height:0.875rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2a4 4 0 00-4-4H5m11 0h.01M16 21h4a2 2 0 002-2v-9a2 2 0 00-2-2H4a2 2 0 00-2 2v9a2 2 0 002 2h4"></path></svg>
            Stack Traceback
        </h2>
        <div class="explorer-card" style="padding:1rem">
            <pre style="font-size:0.625rem;font-family:var(--font-mono);color:var(--text-muted);overflow-x:auto;line-height:1.6"><code>{html_mod.escape(formatted_tb)}</code></pre>
        </div>
    </div>
    """

    # 5. Suggestions
    suggestions = []
    if isinstance(exc, NameError):
        var_name = str(exc).split("'")[1] if "'" in str(exc) else ""
        if var_name:
            suggestions.append(f"Ensure that <code>{var_name}</code> is defined before it is used.")
            if frame is not None:
                matches = difflib.get_close_matches(var_name, frame.f_locals.keys(), n=3, cutoff=0.6)
                if matches:
                    suggestions.append(f"Did you mean: {', '.join([f'<code>{m}</code>' for m in matches])}?")
    elif isinstance(exc, ImportError):
        suggestions.append("Check if the package is installed in your virtual environment.")
        suggestions.append("Verify the import path spelling and module presence.")
    elif isinstance(exc, AttributeError):
        attr_match = re.search(r"object has no attribute '([^']+)'", message)
        if attr_match:
            missing_attr = attr_match.group(1)
            # Try to find the object in locals to suggest alternatives
            obj_name_match = re.search(r"'([^']+)' object has no attribute", message)
            if obj_name_match:
                obj_type_name = obj_name_match.group(1)
                for var_name, var_val in context_vars.items():
                    if type(var_val).__name__ == obj_type_name:
                        matches = difflib.get_close_matches(missing_attr, dir(var_val), n=3, cutoff=0.7)
                        if matches:
                            suggestions.append(f"Did you mean one of these attributes on <code>{var_name}</code>: {', '.join([f'<code>{m}</code>' for m in matches])}?")
                            break
        suggestions.append("Check for typos in attribute names or ensure the object is of the expected type.")
    
    if not suggestions:
        suggestions.append("Verify the logic at the failing line and check related variable states.")
        suggestions.append("Look at the stack traceback below to trace the execution path.")

    # Prepare Metadata
    metadata = collect_debug_metadata(request)

    badge = "Exception"
    if status_code == 404: badge = "Not Found 🔍"
    elif status_code == 403: badge = "Forbidden 🚫"
    elif status_code == 401: badge = "Unauthorized 🔑"
    elif status_code >= 500: badge = "Error 💥"

    return render_premium_debug_page(
        title=title,
        message=message,
        filename=os.path.basename(filename),
        lineno=safe_lineno,
        column=safe_column,
        code_frame=code_frame,
        context_vars=context_vars,
        metadata=metadata,
        traceback_html=traceback_html,
        suggestions=suggestions,
        badge=badge,
        status_code=status_code
    )

def charjoin(lines: list[str]) -> str:
    return "\n".join(lines)
