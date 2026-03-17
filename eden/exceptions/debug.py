
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
    code_frame: str,
    context_vars: dict,
    is_htmx: bool,
    badge: str
) -> HTMLResponse:
    """Renders the high-fidelity Eden debug/error page with template variables."""
    import html as html_mod
    import platform
    import sys

    Jakarta_Sans = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap"
    Outfit = "https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700&display=swap"
    
    # Get system info
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    os_name = platform.system()
    
    # Determine if we have Pygments code or raw pre
    is_raw = code_frame.strip().startswith("<pre>")
    
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

    context_html = ""
    if context_vars:
        rows = []
        for key, val in sorted(context_vars.items()):
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
        <title>{title} — {filename}:{lineno}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="{Jakarta_Sans}" rel="stylesheet">
        <link href="{Outfit}" rel="stylesheet">
        <style>
            body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
            h1, h2, h3, .font-heading {{ font-family: 'Outfit', sans-serif; }}
            .glass {{ background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.05); }}
            .error-line {{ background: rgba(239, 68, 68, 0.15); border-left: 3px solid #ef4444; margin-left: -3px; }}
            .line-no {{ color: #475569; margin-right: 1.5rem; user-select: none; width: 2.5rem; display: inline-block; text-align: right; }}
            pre {{ font-family: 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', monospace; font-size: 0.825rem; }}
            ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
            ::-webkit-scrollbar-track {{ background: #0f172a; }}
            ::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 4px; }}
            ::-webkit-scrollbar-thumb:hover {{ background: #475569; }}
            .code-explorer {{ max-height: 500px; overflow-y: auto; }}
        </style>
    </head>
    <body class="bg-[#020617] text-slate-200 min-h-screen selection:bg-blue-500/30">
        <!-- Header -->
        <header class="sticky top-0 z-50 glass border-b border-white/5 py-4 px-6 md:px-12">
            <div class="max-w-7xl mx-auto flex items-center justify-between">
                <div class="flex items-center gap-4">
                    <span class="bg-red-500/20 text-red-400 text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full border border-red-500/30">
                        {badge}
                    </span>
                    <h1 class="text-xl font-bold tracking-tight text-white">{title}</h1>
                </div>
                <div class="flex items-center gap-3 text-[10px] font-medium text-slate-500 uppercase tracking-wider">
                    <div class="flex items-center gap-1.5 bg-slate-900/50 px-3 py-1.5 rounded-lg border border-white/5">
                        <span class="w-2 h-2 rounded-full bg-blue-500"></span> Python {python_version}
                    </div>
                    <div class="flex items-center gap-1.5 bg-slate-900/50 px-3 py-1.5 rounded-lg border border-white/5">
                        <span class="w-2 h-2 rounded-full bg-emerald-500"></span> {os_name}
                    </div>
                </div>
            </div>
        </header>

        <main class="max-w-7xl mx-auto px-6 md:px-12 py-8 md:py-12 space-y-10">
            <!-- Summary Card -->
            <section class="space-y-4">
                <div class="flex items-start gap-4">
                    <div class="bg-red-500/10 p-4 rounded-2xl border border-red-500/20 mt-1">
                        <svg class="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                        </svg>
                    </div>
                    <div class="space-y-2">
                        <p class="text-2xl font-semibold text-white leading-tight">{html_mod.escape(message)}</p>
                        <div class="flex items-center gap-2 text-slate-400 font-medium">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                            <span class="text-blue-400 select-all">{filename}</span>
                            <span class="text-slate-600 px-1">at</span>
                            <span class="bg-slate-800 text-slate-300 px-2 py-0.5 rounded-md text-sm">Line {lineno}</span>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Code Explorer -->
            <section class="space-y-4">
                <div class="flex items-center justify-between px-1">
                    <h2 class="text-sm font-bold uppercase tracking-widest text-slate-500 flex items-center gap-2">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg>
                        Code Explorer
                    </h2>
                </div>
                <div class="bg-[#0f172a] rounded-2xl border border-white/5 shadow-2xl overflow-hidden">
                    <div class="flex items-center justify-between bg-slate-900/50 px-4 py-3 border-b border-white/5">
                        <div class="flex gap-1.5">
                            <div class="w-3 h-3 rounded-full bg-red-500/50"></div>
                            <div class="w-3 h-3 rounded-full bg-amber-500/50"></div>
                            <div class="w-3 h-3 rounded-full bg-emerald-500/50"></div>
                        </div>
                        <div class="text-[10px] text-slate-500 font-mono tracking-wider">{filename}</div>
                    </div>
                    <div class="code-explorer p-6 text-sm font-mono leading-relaxed overflow-x-auto">
                        {code_frame}
                    </div>
                </div>
            </section>

            <div class="grid md:grid-cols-3 gap-10 items-start">
                <!-- Context Variables -->
                <section class="md:col-span-2 space-y-4">
                    <h2 class="text-sm font-bold uppercase tracking-widest text-slate-500 flex items-center gap-2 px-1">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 1.1.9 2 2 2h12a2 2 0 002-2V7a2 2 0 00-2-2H6a2 2 0 00-2 2zM9 12h.01M13 12h.01M17 12h.01"></path></svg>
                        Context Variables
                    </h2>
                    <div class="bg-[#0f172a] rounded-2xl border border-white/5 overflow-hidden">
                        <div class="overflow-x-auto">
                            <table class="w-full text-left border-collapse">
                                <tbody class="divide-y divide-slate-800/50">
                                    {context_html if context_html else '<tr><td class="p-8 text-center text-slate-500 italic text-sm">No context variables detected</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>

                <!-- Sidebar Info -->
                <aside class="space-y-8">
                    <div class="space-y-4">
                        <h2 class="text-sm font-bold uppercase tracking-widest text-slate-500 px-1">Support</h2>
                        <div class="bg-blue-600/10 rounded-2xl border border-blue-500/20 p-5 space-y-4">
                            <p class="text-xs text-blue-200/70 leading-relaxed">
                                Need help? The Eden community is here to assist you with template issues and architectural patterns.
                            </p>
                            <div class="flex flex-col gap-2">
                                <a href="https://github.com/eden-framework/eden" target="_blank" class="flex items-center justify-between group p-3 bg-blue-600/20 rounded-xl hover:bg-blue-600/30 transition-all border border-blue-500/20">
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
                                🌿 Eden <span class="text-blue-500">v0.1.0</span>
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
    from jinja2.exceptions import TemplateSyntaxError, UndefinedError

    status_code = 500
    title = "Template Error"
    name = getattr(exc, "name", "Unknown Template")
    lineno = getattr(exc, "lineno", 0)
    
    # Extract message
    message = str(exc) if exc else ""
    if not message or message.strip() == "":
        message = getattr(exc, "message", None) or getattr(exc, "msg", None) or f"{type(exc).__name__}: An error occurred"
    
    # Determine specific error type for badge
    badge = "Template Error"
    if isinstance(exc, TemplateSyntaxError):
        badge = "Syntax Error"
    elif isinstance(exc, UndefinedError):
        badge = "Undefined Variable"

    # Fuzzy suggestions
    if isinstance(exc, UndefinedError):
        match = re.search(r"'([^']+)' is undefined", message)
        if match:
            missing_var = match.group(1)
            candidates = ["request", "user", "url_for", "static"]
            matches = difflib.get_close_matches(missing_var, candidates, n=3, cutoff=0.6)
            if matches:
                message += f" (Did you mean: {', '.join(matches)}?)"

    # Find the template file
    search_dirs = []
    if hasattr(app, "_templates") and app._templates:
        try:
            from jinja2 import FileSystemLoader
            if isinstance(app._templates.env.loader, FileSystemLoader):
                search_dirs.extend(app._templates.env.loader.searchpath)
        except (ImportError, AttributeError):
            pass
    
    if not search_dirs:
        template_dir = getattr(app, "template_dir", "templates")
        search_dirs = [template_dir] if isinstance(template_dir, str) else (template_dir or [])

    template_path = None
    if name and name != "Unknown Template":
        for d in search_dirs:
            if not d: continue
            p = os.path.join(d, name)
            if os.path.exists(p):
                template_path = p
                break

    # Recover context from traceback
    found_context = {}
    if app.debug:
        try:
            for frame_info in inspect.trace():
                if (not name or name == "Unknown Template"):
                    for d in search_dirs:
                        if d and d in frame_info.filename:
                            name = os.path.relpath(frame_info.filename, d)
                            template_path = frame_info.filename
                            break

                if (not lineno or lineno <= 0) and template_path:
                    if frame_info.filename == template_path:
                        lineno = frame_info.lineno
                
                if not found_context:
                    for ctx_key in ("context", "ctx"):
                        if ctx_key in frame_info.frame.f_locals:
                            ctx_obj = frame_info.frame.f_locals[ctx_key]
                            if hasattr(ctx_obj, "get_all"):
                                found_context = ctx_obj.get_all()
                                break
                            elif isinstance(ctx_obj, dict):
                                found_context = ctx_obj
                                break
                    if not found_context and template_path and frame_info.filename == template_path:
                        found_context = frame_info.frame.f_locals
        except Exception:
            pass

    code_frame = ""
    if template_path:
        try:
            with open(template_path, encoding="utf-8") as f:
                source_lines = f.readlines()
                if lineno > 0 and lineno <= len(source_lines):
                    start = max(0, lineno - 6)
                    end = min(len(source_lines), lineno + 5)
                    mark_line = lineno
                else:
                    start, end, mark_line = 0, min(len(source_lines), 10), -1

                try:
                    from pygments import highlight
                    from pygments.formatters import HtmlFormatter
                    from pygments.lexers import get_lexer_for_filename

                    lexer = get_lexer_for_filename(template_path)
                    formatter = HtmlFormatter(style="monokai", nowrap=True)
                    highlighted_lines = []
                    for i in range(start, end):
                        curr_lineno = i + 1
                        is_error = curr_lineno == mark_line
                        raw_line = source_lines[i]
                        html_line = highlight(raw_line, lexer, formatter)
                        klass = "error-line" if is_error else "normal-line"
                        highlighted_lines.append(
                            f'<div class="{klass}"><span class="line-no">{curr_lineno:4}</span>{html_line}</div>'
                        )
                    code_frame = f'<pre class="p-0 border-0 bg-transparent"><code>{"".join(highlighted_lines)}</code></pre>'
                except Exception:
                    frame_lines = []
                    for i in range(start, end):
                        curr_lineno = i + 1
                        is_error = curr_lineno == mark_line
                        line_content = source_lines[i].rstrip()
                        prefix = " > " if is_error else "   "
                        frame_lines.append(f"{curr_lineno:4}{prefix}{line_content}")
                    code_frame = f"<pre class='p-6 text-sm font-mono leading-relaxed overflow-x-auto bg-slate-900/50 rounded-xl'><code>{html_mod.escape(charjoin(frame_lines))}</code></pre>"
        except Exception as read_exc:
            code_frame = f"<div class='p-8 border border-red-500/20 bg-red-500/5 rounded-2xl'><p class='text-red-400 font-medium'>Could not read template source</p></div>"
    else:
        code_frame = f"<div class='p-12 text-center bg-slate-800/20 rounded-2xl border border-white/5'><div class='text-slate-400 font-medium'>Source template not found</div></div>"

    context_vars = {k: v for k, v in found_context.items() if not k.startswith("__") and k not in ("range", "dict", "request")}

    return render_premium_debug_page(
        title=title,
        message=message,
        filename=name,
        lineno=lineno,
        code_frame=code_frame,
        context_vars=context_vars,
        is_htmx=getattr(request, "headers", {}).get("HX-Request") == "true",
        badge=badge
    )

def charjoin(lines: list[str]) -> str:
    return "\n".join(lines)
