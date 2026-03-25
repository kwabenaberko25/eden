from __future__ import annotations
import html as html_mod
import platform
import sys
import os
from typing import Any, TYPE_CHECKING
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
    """Render a simple, clean error page (non-debug/generic)."""
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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Outfit:wght@500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            background: #0F172A;
            color: #e2e8f0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .error-container {{
            text-align: center;
            max-width: 520px;
            width: 100%;
        }}
        .error-icon {{
            font-size: 64px;
            margin-bottom: 24px;
            filter: drop-shadow(0 0 15px rgba(255, 255, 255, 0.1));
        }}
        .error-code {{
            font-family: 'Outfit', sans-serif;
            font-size: 14px;
            font-weight: 700;
            color: #3B82F6;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 8px;
        }}
        .error-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 32px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 16px;
        }}
        .error-detail {{
            font-size: 16px;
            color: #94A3B8;
            line-height: 1.6;
            margin-bottom: 32px;
        }}
        .actions {{
            display: flex;
            gap: 12px;
            justify-content: center;
        }}
        .btn-home {{
            display: inline-block;
            background: #2563EB;
            color: white;
            padding: 12px 24px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.2s;
        }}
        .btn-home:hover {{
            background: #1D4ED8;
            transform: translateY(-1px);
        }}
        .btn-secondary {{
            display: inline-block;
            background: #1E293B;
            color: #e2e8f0;
            padding: 12px 24px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            border: 1px solid #334155;
            transition: all 0.2s;
        }}
        .btn-secondary:hover {{
            background: #334155;
        }}
        .brand {{
            margin-top: 48px;
            font-size: 12px;
            color: #475569;
            font-weight: 500;
        }}
        .brand span {{ color: #2563EB; }}
        .traceback {{
            text-align: left;
            margin-top: 28px;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 4px;
            max-width: 100%;
        }}
        .traceback summary {{
            padding: 10px 14px;
            cursor: pointer;
            font-size: 0.82rem;
            color: #f59e0b;
            font-weight: 500;
            user-select: none;
        }}
        .traceback pre {{
            padding: 12px 14px;
            font-size: 0.75rem;
            line-height: 1.5;
            color: #94a3b8;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 320px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">{icon}</div>
        <div class="error-code">{status_code}</div>
        <div class="error-title">{title}</div>
        <div class="error-detail">{safe_detail}</div>
        <div class="actions">
            <a href="/" class="btn-home">← Go Home</a>
            <a href="javascript:history.back()" class="btn-secondary">Go Back</a>
        </div>
        {traceback_html}
        <div class="brand">Powered by <span>Eden 🌿</span></div>
    </div>
</body>
</html>"""

def render_premium_debug_page(
    title: str,
    message: str,
    filename: str,
    lineno: int,
    column: int,
    code_frame: str,
    context_vars: dict,
    request_info: dict[str, Any],
    suggestions: list[str],
    is_htmx: bool,
    badge: str
) -> HTMLResponse:
    """Renders the high-fidelity Eden debug/error page with template variables."""
    jakarta_sans = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap"
    outfit = "https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700&display=swap"
    
    # Format context variables for display
    def format_value(value, max_length=150):
        """Format a value safely for display."""
        try:
            if value is None:
                return '<span class="text-slate-500 italic">None</span>'
            elif isinstance(value, bool):
                return f'<span class="text-blue-400 font-mono">{str(value)}</span>'
            elif isinstance(value, (int, float)):
                return f'<span class="text-emerald-400 font-mono">{value}</span>'
            elif isinstance(value, str):
                escaped = html_mod.escape(value[:max_length])
                if len(value) > max_length:
                    escaped += '...'
                return f'<span class="text-amber-300 font-mono">"{escaped}"</span>'
            elif isinstance(value, dict):
                return f'<span class="text-slate-400 font-mono">dict({len(value)} items)</span>'
            elif isinstance(value, (list, tuple)):
                return f'<span class="text-slate-400 font-mono">{type(value).__name__}({len(value)} items)</span>'
            return html_mod.escape(str(type(value).__name__))
        except Exception:
            return "???"

    # Format suggestions
    suggestions_html = ""
    for suggestion in suggestions:
        suggestions_html += f"""
        <div class="flex items-start gap-3 p-3 bg-blue-500/5 rounded-xl border border-blue-500/10 mb-2 last:mb-0">
             <div class="mt-0.5 text-blue-400">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
             </div>
             <p class="text-[11px] text-slate-300 leading-relaxed font-medium">{suggestion}</p>
        </div>
        """

    # Format payload if exists
    payload_html = ""
    payload = request_info.get("payload")
    if payload:
        import json
        try:
            formatted_payload = json.dumps(payload, indent=2)
            payload_html = f"""
            <div class="mt-8 space-y-3">
                <h2 class="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2 px-1">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path></svg>
                    Request Payload
                </h2>
                <div class="bg-[#0b1222] rounded-xl border border-white/5 p-4 shadow-sm">
                    <pre class="text-[10px] font-mono text-amber-200/80 overflow-x-auto"><code>{html_mod.escape(formatted_payload)}</code></pre>
                </div>
            </div>
            """
        except Exception:
            pass

    context_html = ""
    if context_vars:
        rows: list[str] = []
        for key, val in sorted(context_vars.items()):
            # Filter internal jinja/eden vars for cleaner view
            if key.startswith("__") or key in ("app", "debug", "found_context"):
                continue
            rows.append(f"""
            <tr class="border-b border-slate-800/50 last:border-0">
                <td class="py-2.5 pr-4 font-mono text-xs text-blue-400 align-top w-1/3">{key}</td>
                <td class="py-2.5 font-mono text-xs text-slate-300 break-all">{format_value(val)}</td>
            </tr>
            """)
        context_html = "\n".join(rows)

    html = f"""
    <!DOCTYPE html>
    <html lang="en" class="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} — {filename}:{lineno}{f":{column}" if column > 0 else ""}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="{jakarta_sans}" rel="stylesheet">
        <link href="{outfit}" rel="stylesheet">
        <style>
            body {{ font-family: 'Plus Jakarta Sans', sans-serif; background: #020617; }}
            h1, h2, h3, .font-heading {{ font-family: 'Outfit', sans-serif; }}
            .glass {{ background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.05); }}
            .error-line {{ background: rgba(239, 68, 68, 0.1); border-left: 3px solid #f43f5e; margin-left: -3px; position: relative; }}
            .squiggle {{
                text-decoration: underline wavy #f43f5e;
                text-underline-offset: 4px;
            }}
            .line-no {{ color: #475569; margin-right: 1.25rem; user-select: none; width: 2.2rem; display: inline-block; text-align: right; font-size: 0.75rem; font-weight: 500; }}
            pre {{ font-family: 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', monospace; font-size: 0.85rem; }}
            .column-marker {{ 
                position: absolute; 
                bottom: -2px; 
                height: 3px; 
                width: 1ch;
                background: linear-gradient(90deg, #f43f5e, #fb7185); 
                box-shadow: 0 0 12px rgba(244, 63, 94, 0.6); 
                border-radius: 2px;
                z-index: 10;
            }}
            .error-line .column-marker {{ left: calc({column}ch + 3.45rem); }}

            ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
            ::-webkit-scrollbar-track {{ background: transparent; }}
            ::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 10px; }}
            .code-explorer {{ max-height: 500px; overflow-y: auto; scrollbar-gutter: stable; }}
        </style>
    </head>
    <body class="bg-[#020617] text-slate-200 min-h-screen selection:bg-blue-500/30">
        <!-- Header -->
        <header class="py-12 px-6 md:px-10 max-w-7xl mx-auto space-y-6">
            <div class="flex items-center gap-4 animate-in fade-in slide-in-from-top-4 duration-700">
                <span class="bg-rose-500/20 text-rose-500 text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-md border border-rose-500/30 shadow-[0_0_20px_rgba(244,63,94,0.3)]">
                    CRITICAL ERROR
                </span>
                <span class="text-slate-600 font-mono text-[10px] tracking-widest">ID: EDN-{os.getpid()}-ERR</span>
            </div>
            
            <div class="space-y-2">
                <h1 class="text-4xl md:text-5xl font-black tracking-tight text-white leading-tight">
                    <span class="text-rose-500">{badge}:</span> {html_mod.escape(message.split(' (Did you mean:')[0])}
                </h1>
                <p class="text-slate-500 text-sm font-medium tracking-tight flex items-center gap-2">
                    Occurrence detected in <span class="text-blue-400 font-mono select-all">local-development</span>. Immediate resolution required.
                </p>
            </div>
        </header>

        <main class="max-w-7xl mx-auto px-6 md:px-10 pb-20 space-y-10">
            <section class="space-y-3">
                <div class="flex items-start gap-4">
                    <div class="bg-red-500/10 p-3 rounded-xl border border-red-500/20 mt-1">
                        <svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                        </svg>
                    </div>
                    <div class="space-y-1">
                        <p class="text-xl font-semibold text-white leading-tight">{html_mod.escape(message)}</p>
                        <div class="flex items-center gap-2 text-slate-400 font-medium text-xs">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                            <span class="text-blue-400 select-all font-mono">{filename}</span>
                            <span class="text-slate-600 px-0.5">•</span>
                            <span class="text-slate-300">Line {lineno}{f", Column {column}" if column > 0 else ""}</span>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Code Explorer -->
            <section class="space-y-2">
                <div class="flex items-center justify-between px-1">
                    <h2 class="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg>
                        Code Explorer
                    </h2>
                </div>
                <div class="bg-[#0b1222] rounded-xl border border-white/5 shadow-2xl overflow-hidden">
                    <div class="flex items-center justify-between bg-slate-900/50 px-4 py-2 border-b border-white/5">
                        <div class="flex gap-1.5">
                            <div class="w-2.5 h-2.5 rounded-full bg-red-500/20 border border-red-500/30"></div>
                            <div class="w-2.5 h-2.5 rounded-full bg-amber-500/20 border border-amber-500/30"></div>
                            <div class="w-2.5 h-2.5 rounded-full bg-emerald-500/20 border border-emerald-500/30"></div>
                        </div>
                        <div class="text-[9px] text-slate-500 font-mono tracking-wider uppercase opacity-50">{filename}</div>
                    </div>
                    <div class="code-explorer p-4 text-xs font-mono leading-relaxed overflow-x-auto">
                        {code_frame}
                    </div>
                </div>
            </section>

            <div class="grid md:grid-cols-3 gap-10 items-start">
                <section class="md:col-span-2 space-y-10">
                    <!-- Context Variables -->
                    <div class="space-y-3">
                        <h2 class="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2 px-1">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 1.1.9 2 2 2h12a2 2 0 002-2V7a2 2 0 00-2-2H6a2 2 0 00-2 2zM9 12h.01M13 12h.01M17 12h.01"></path></svg>
                            Context Variables
                        </h2>
                        <div class="bg-[#0b1222] rounded-xl border border-white/5 overflow-hidden shadow-sm">
                            <div class="overflow-x-auto">
                                <table class="w-full text-left border-collapse context-table">
                                    <tbody class="divide-y divide-slate-800/50">
                                        {context_html if context_html else '<tr><td class="p-6 text-center text-slate-500 italic text-sm">No context variables detected</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <!-- Request Info -->
                    <div class="space-y-3">
                        <h2 class="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2 px-1">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                            Request Information
                        </h2>
                        <div class="bg-[#0b1222] rounded-xl border border-white/5 p-6 shadow-sm overflow-hidden">
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div class="space-y-4">
                                    <div>
                                        <div class="text-[9px] text-slate-500 font-bold uppercase tracking-widest mb-1.5 opacity-60">Method & URL</div>
                                        <div class="flex items-center gap-2">
                                            <span class="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[10px] font-black uppercase ring-1 ring-inset ring-blue-500/20">{request_info.get('method')}</span>
                                            <span class="text-xs font-mono text-slate-300 select-all truncate">{request_info.get('url')}</span>
                                        </div>
                                    </div>
                                    <div>
                                        <div class="text-[9px] text-slate-500 font-bold uppercase tracking-widest mb-1.5 opacity-60">Client Host</div>
                                        <div class="flex items-center gap-2 text-xs text-slate-400 font-mono">
                                            {request_info.get('client', 'unknown')}
                                        </div>
                                    </div>
                                </div>
                                <div class="space-y-4">
                                    <div class="text-[9px] text-slate-500 font-bold uppercase tracking-widest mb-1.5 opacity-60">Common Headers</div>
                                    <div class="space-y-2" style="font-size: 10px;">
                                        <div class="flex justify-between items-center">
                                            <span class="text-slate-500 font-mono">User-Agent</span>
                                            <span class="text-slate-400 truncate max-w-[150px] text-right" title="{html_mod.escape(str(request_info.get('headers', {}).get('user-agent', 'N/A')))}">{html_mod.escape(str(request_info.get('headers', {}).get('user-agent', 'N/A'))[:25])}...</span>
                                        </div>
                                        <div class="flex justify-between items-center">
                                            <span class="text-slate-500 font-mono">Host</span>
                                            <span class="text-slate-400">{request_info.get('headers', {}).get('host', 'N/A')}</span>
                                        </div>
                                        <div class="flex justify-between items-center">
                                            <span class="text-slate-500 font-mono">Accept</span>
                                            <span class="text-slate-400 truncate max-w-[150px] text-right">{html_mod.escape(str(request_info.get('headers', {}).get('accept', '*/*'))[:25])}...</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    {payload_html}
                </section>

                <!-- Sidebar -->
                <aside class="space-y-8">
                    <div class="space-y-4">
                        <h2 class="text-sm font-bold uppercase tracking-widest text-slate-500 px-1">Recommended Action</h2>
                        <div class="bg-emerald-500/10 rounded-2xl border border-emerald-500/20 p-5 space-y-4">
                            <div class="flex items-center gap-3">
                                <div class="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center border border-emerald-500/30">
                                    <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>
                                </div>
                                <span class="text-xs font-bold text-emerald-300 uppercase tracking-wider">Analysis Result</span>
                            </div>
                            <div class="space-y-3">
                                {suggestions_html}
                            </div>
                        </div>
                    </div>

                    <div class="space-y-4">
                        <h2 class="text-sm font-bold uppercase tracking-widest text-slate-500 px-1">Support</h2>
                        <div class="bg-blue-600/10 rounded-2xl border border-blue-500/20 p-5 space-y-4">
                            <p class="text-xs text-blue-200/70 leading-relaxed">
                                Need help? The Eden community is here to assist you with template issues and architectural patterns.
                            </p>
                            <div class="flex flex-col gap-2">
                                <a href="https://github.com/kwabenaberko25/eden" target="_blank" class="flex items-center justify-between group p-3 bg-blue-600/20 rounded-xl hover:bg-blue-600/30 transition-all border border-blue-500/20">
                                    <span class="text-xs font-semibold text-blue-300 tracking-wide">Documentation</span>
                                    <svg class="w-3.5 h-3.5 text-blue-400 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                                </a>
                            </div>
                        </div>
                    </div>

                    <div class="space-y-4">
                        <h2 class="text-sm font-bold uppercase tracking-widest text-slate-500 px-1">Eden Framework</h2>
                        <div class="bg-slate-900/30 rounded-2xl border border-white/5 p-5">
                            <div class="text-[10px] text-slate-500 font-semibold mb-3 tracking-widest uppercase">Version</div>
                            <div class="text-lg font-bold text-white flex items-center gap-2">
                                🌿 Eden <span class="text-blue-500">v1.0.0</span>
                            </div>
                        </div>
                    </div>
                </aside>
            </div>
        </main>

        <footer class="py-12 border-t border-white/5 text-center mt-20">
            <p class="text-slate-600 text-[10px] font-bold uppercase tracking-[0.2em] mb-4">You are seeing this page because you are in debug mode.</p>
            <div class="flex items-center justify-center gap-4 grayscale opacity-40">
                <span class="h-px w-8 bg-slate-700"></span>
                <span class="text-slate-400 font-bold text-xs tracking-wider font-heading">Powered by Eden 🌿</span>
                <span class="h-px w-8 bg-slate-700"></span>
            </div>
        </footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=500)

def render_enhanced_template_error(
    app: Eden, 
    request: Request, 
    exc: Exception
) -> HTMLResponse:
    """Render a high-fidelity debug page for template errors."""
    import difflib
    import re
    import inspect
    import jinja2
    from jinja2.exceptions import TemplateSyntaxError, UndefinedError

    status_code = 500
    title = "Template Error"
    name = getattr(exc, "name", "Unknown Template")
    lineno = getattr(exc, "lineno", 0)
    column = getattr(exc, "column", 0)
    
    # Extract message
    message = str(exc) if exc else ""
    exc_message = getattr(exc, "message", None)
    if exc_message: # jinja2 syntax errors often use .message
        message = exc_message
    
    if not message or message.strip() == "":
        message = getattr(exc, "message", None) or getattr(exc, "msg", None) or f"{type(exc).__name__}: An error occurred"
    
    # Determine specific error type for badge
    badge = "Template Error"
    if isinstance(exc, TemplateSyntaxError):
        badge = "Syntax Error"
        # Often TemplateSyntaxError message contains the line info already, let's clean it
        message = re.sub(r"at line \d+", "", message).strip()
    elif isinstance(exc, UndefinedError):
        badge = "Undefined Variable"

    # Fuzzy suggestions
    suggestions = []
    if isinstance(exc, UndefinedError):
        match = re.search(r"'([^']+)' is undefined", message)
        if match:
            missing_var = match.group(1)
            candidates = ["request", "user", "url_for", "static", "csrf_token"]
            matches = difflib.get_close_matches(missing_var, candidates, n=3, cutoff=0.6)
            if matches:
                suggestions.append(f"Check if you meant to use: <code>{', '.join(matches)}</code>")
            suggestions.append(f"Ensure that <code>{missing_var}</code> is passed in the context during template rendering.")
    elif isinstance(exc, TemplateSyntaxError):
        suggestions.append("Check for missing or unclosed Jinja2 tags (e.g., <code>{{{{ ... }}}}</code> vs <code>{{% ... %}}</code>).")
        suggestions.append("Verify that filtering or logic inside tags follows correct Jinja2 syntax.")
    
    if not suggestions:
        suggestions.append("Verify that all variables used in the template are properly defined in your view function.")
        suggestions.append("Check for typos in variable names within the template file.")

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
                    src, filename, _ = loader.get_source(app._templates.env, name)
                    template_source = src
                    if filename and os.path.exists(filename):
                        template_path = filename
        except Exception:
            pass

        # 2. Fallback to physical file search
        if not template_path:
            for d in search_dirs:
                if not d: continue
                p = os.path.join(d, name)
                if os.path.exists(p):
                    template_path = p
                    break

    # Recover context and template info from traceback
    found_context = {}
    if app.debug:
        try:
            # We use inspect.trace() to look at the frames of the exception being handled
            trace = inspect.trace()
            for frame_info in trace:
                frame_filename = os.path.abspath(str(frame_info.filename))
                
                # Try to identify if this is a template frame
                if (not name or name == "Unknown Template") or not template_path:
                    for d in search_dirs:
                        if d and frame_filename.startswith(d):
                            name = os.path.relpath(frame_filename, d)
                            template_path = frame_filename
                            break
                    
                    # Heuristic: if it ends in .html or .jinja and is in a "templates" folder
                    if (not template_path) and (".html" in frame_filename or ".jinja" in frame_filename):
                        if "templates" in frame_filename:
                            template_path = frame_filename
                            name = os.path.basename(frame_filename)

                # Capture line number from the template frame if we don't have it
                if template_path and frame_filename == template_path:
                    if not lineno or lineno <= 0:
                        lineno = frame_info.lineno
                
                # Extract context if present (Jinja2 often names it 'context' or 'ctx')
                if not found_context:
                    for ctx_key in ("context", "ctx"):
                        if ctx_key in frame_info.frame.f_locals:
                            ctx_obj = frame_info.frame.f_locals[ctx_key]
                            if hasattr(ctx_obj, "get_all"): # Jinja2 Context object
                                found_context = ctx_obj.get_all()
                                break
                            elif isinstance(ctx_obj, dict):
                                found_context = ctx_obj
                                break
                    
                    if not found_context and template_path and frame_filename == template_path:
                        found_context = frame_info.frame.f_locals
        except Exception:
            pass

    code_frame = ""
    if template_path or template_source:
        try:
            source_lines = []
            if template_source:
                source_lines = template_source.splitlines(keepends=True)
            elif template_path:
                with open(template_path, encoding="utf-8") as f:
                    source_lines = f.readlines()
            
            if source_lines:
                # Calculate the window to display
                if lineno > 0 and lineno <= len(source_lines):
                    start = max(0, lineno - 6)
                    end = min(len(source_lines), lineno + 5)
                    mark_line = lineno
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
                        if is_error and column > 0:
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
                    code_frame = f"<pre class='p-6 text-sm font-mono leading-relaxed overflow-x-auto bg-slate-900/50 rounded-xl text-slate-300'><code>{html_mod.escape(charjoin(frame_lines))}</code></pre>"
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
            f"<p class='text-slate-500 text-sm mb-8 max-w-xs mx-auto'>The engine couldn't resolve <b class='text-slate-300'>{html_mod.escape(template_name)}</b> in the current load paths.</p>"
            f"<div class='text-[10px] font-mono text-slate-500 bg-black/40 p-5 rounded-2xl inline-block w-full max-w-md break-all text-left border border-white/5 shadow-2xl'>"
            f"<div class='flex items-center gap-2 mb-3 text-indigo-400 font-black tracking-tighter opacity-80'>SEARCH PATHS</div>"
            + "".join([f"<div class='flex gap-2 mb-1.5 last:mb-0'><span class='text-slate-700 font-black'>•</span><span class='opacity-80'>{html_mod.escape(d)}</span></div>" for d in unique_dirs])
            + f"</div></div>"
        )

    # Prepare request info for the renderer
    request_info = {
        "method": getattr(request, "method", "GET"),
        "url": str(getattr(request, "url", "/")),
        "headers": dict(getattr(request, "headers", {})),
        "query_params": dict(getattr(request, "query_params", {})),
        "client": getattr(request.client, "host", "unknown") if hasattr(request, "client") and request.client else "unknown",
    }
    
    try:
        # Try to capture payload if already read
        if hasattr(request, "_json"):
            request_info["payload"] = request._json
        elif hasattr(request, "_form"):
            request_info["payload"] = dict(request._form)
    except Exception:
        pass

    return render_premium_debug_page(
        title=title,
        message=message,
        filename=name,
        lineno=lineno,
        column=column or 0,
        code_frame=code_frame,
        context_vars=found_context,
        request_info=request_info,
        suggestions=suggestions,
        is_htmx=getattr(request, "headers", {}).get("HX-Request") == "true",
        badge=badge
    )

def charjoin(lines: list[str]) -> str:
    return "\n".join(lines)
