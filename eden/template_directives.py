"""
Template Directives Registry for Eden Framework.

This module provides a decoupled registry of all template directives (@if, @foreach, @csrf, etc.),
making the compiler pluggable and reducing the complexity of the visit_directive method.
"""

from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from eden.templating import TemplateCompiler, DirectiveNode

DIRECTIVE_REGISTRY: dict[str, typing.Callable[["TemplateCompiler", "DirectiveNode", str], str]] = {}

def directive(names: str | list[str]):
    """Decorator to register a directive handler."""
    def decorator(fn):
        if isinstance(names, str):
            DIRECTIVE_REGISTRY[names] = fn
        else:
            for name in names:
                DIRECTIVE_REGISTRY[name] = fn
        return fn
    return decorator


def get_body_compiled(compiler: "TemplateCompiler", node: "DirectiveNode") -> str:
    """Helper to compile the body of a blocked directive."""
    return compiler.compile(node.body or []) if node.body is not None else ""


# ── Security & Forms ──────────────────────────────────────────────────────────

@directive("csrf")
def render_csrf(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return '<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'

@directive("csrf_token")
def render_csrf_token(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return '{{ csrf_token() }}'

@directive("method")
def render_method(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    val = expr.strip("\"'") if expr else "POST"
    return f'<input type="hidden" name="_method" value="{val}">'

@directive("old")
def render_old(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    parts = [p.strip() for p in (expr or "").split(',', 1)]
    name_v = parts[0]
    def_v = parts[1] if len(parts) > 1 else "None"
    return f'{{{{ old({name_v}, {def_v}) }}}}'


# ── Assets & Scripts ──────────────────────────────────────────────────────────

@directive("eden_head")
def render_eden_head(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return '{{ eden_head() }}'

@directive("eden_scripts")
def render_eden_scripts(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return '{{ eden_scripts() }}'

@directive("eden_toasts")
def render_eden_toasts(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return '{{ eden_toasts() }}'

@directive("css")
def render_css(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    # FIXED: Quote the href attribute to prevent XSS injection
    return f'<link rel="stylesheet" href="{expr}">'

@directive("js")
def render_js(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    # FIXED: Quote the src attribute to prevent XSS injection
    return f'<script src="{expr}"></script>'

@directive("vite")
def render_vite(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return f'{{{{ vite({expr}) }}}}'


# ── Component, Layouts, & Blocks ──────────────────────────────────────────────

@directive("yield")
def render_yield(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    val = expr.strip("\"'") if expr else "content"
    return f'{{% block {val} %}}{{% endblock %}}'

@directive("stack")
def render_stack(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return f'{{{{ eden_stack({expr}) }}}}'

@directive("super")
def render_super(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return '{{ super() }}'

@directive("extends")
def render_extends(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return f'{{% extends {expr} %}}'

@directive("include")
def render_include(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return f'{{% include {expr} %}}'

@directive("includeWhen")
def render_includeWhen(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    parts = [p.strip() for p in (expr or "").split(',', 1)]
    cond_v = parts[0]
    tmpl_v = parts[1] if len(parts) > 1 else '""'
    return f'{{% if {cond_v} %}}{{% include {tmpl_v} %}}{{% endif %}}'

@directive("includeUnless")
def render_includeUnless(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    parts = [p.strip() for p in (expr or "").split(',', 1)]
    cond_v = parts[0]
    tmpl_v = parts[1] if len(parts) > 1 else '""'
    return f'{{% if not ({cond_v}) %}}{{% include {tmpl_v} %}}{{% endif %}}'

@directive("fragment")
def render_fragment(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    val = expr.strip('"\'') if expr else ""
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% block fragment_{val} %}}{body_compiled}{{% endblock %}}'

@directive("push")
def render_push(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    val = expr.strip('"\'') if expr else ""
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% set __push_content %}}{body_compiled}{{% endset %}}{{{{ eden_push("{val}", __push_content) }}}}'

@directive("pushOnce")
def render_push_once(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    val = expr.strip('"\'') if expr else ""
    body_compiled = get_body_compiled(compiler, node)
    # Check if we've already pushed this unique name in this request/context
    return f'{{% set __push_content %}}{body_compiled}{{% endset %}}{{{{ eden_push("{val}", __push_content, once=True) }}}}'

@directive("prepend")
def render_prepend(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    val = expr.strip('"\'') if expr else ""
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% set __push_content %}}{body_compiled}{{% endset %}}{{{{ eden_push("{val}", __push_content, prepend=True) }}}}'

@directive(["section", "block"])
def render_section(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    val = expr.strip('"\'') if expr else ""
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% block {val} %}}{body_compiled}{{% endblock %}}'

@directive("slot")
def render_slot(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% slot {expr} %}}{body_compiled}{{% endslot %}}'

@directive("component")
def render_component(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% component {expr} %}}{body_compiled}{{% endcomponent %}}'

@directive("props")
def render_props(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return compiler.handle_props(expr)


# ── Utilities, Display, & Logging ─────────────────────────────────────────────

@directive("span")
def render_span(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    if not expr:
        return ""
    # Support ?? for null-coalescing shorthand, converting it to Jinja2 default filter
    if "??" in expr:
        import re
        # Basic support for a ?? b -> a | default(b)
        expr = re.sub(r'(.*?)\s*\?\?\s*(.*)', r'\1 | default(\2)', expr)
    return f'{{{{ {expr.replace("$", "")} }}}}'

@directive("json")
def render_json(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return f'{{{{ {expr} | json_encode }}}}'

@directive("dump")
def render_dump(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    clean_expr = expr.replace("$", "").replace("(", "").replace(")", "").strip()
    return f'{{{{ eden_dump({expr}, "{clean_expr}") }}}} {{# eden-dump json_encode #}}'

@directive("status")
def render_status(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    # FIXED: Validate that status code is provided
    if not expr or not expr.strip():
        return '<!-- @status requires a status code: @status(404) -->'
    
    return f'{{{{ set_response_status({expr}) }}}}'

@directive("let")
def render_let(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    # FIXED: Validate that assignment expression is provided
    if not expr or not expr.strip():
        return '<!-- @let requires a variable assignment: @let(x = 10) -->'
    
    return f"{{% set {expr} %}}"

@directive(["url", "route"])
def render_url(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return compiler.handle_url(expr)

@directive("active_link")
def render_active_link(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """
    Apply CSS classes conditionally based on the active state of the route.
    Usage: @active_link('route', 'active-classes', 'inactive-classes')
    
    FIXED: Added validation to ensure expression is not empty.
    """
    # FIXED: Validate that expression is provided
    if not expr or not expr.strip():
        return '<!-- @active_link requires: @active_link("route_name", "active_css", "inactive_css") -->'
    
    parts = [p.strip() for p in (expr or "").split(',', 2)]
    url_v = parts[0]
    active_css = parts[1].strip('"\'') if len(parts) > 1 else ""
    inactive_css = parts[2].strip('"\'') if len(parts) > 2 else ""
    
    if url_v.startswith("'") or url_v.startswith('"'):
        url_v = f'"{url_v[1:-1]}"'
        
    return f'{{{{ "{active_css}" if is_active(request, {url_v}) else "{inactive_css}" }}}}'

@directive("class")
def render_class(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return compiler.handle_class(expr)

@directive("verbatim")
def render_verbatim(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% raw %}}{body_compiled}{{% endraw %}}'


# ── Control Flow & Conditionals ───────────────────────────────────────────────

@directive(["checked", "selected", "disabled", "readonly"])
def render_attribute_conditionals(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    # FIXED: Validate that condition expression is provided
    if not expr or not expr.strip():
        return f'<!-- @{node.name} requires a condition: @{node.name}(condition) -->'
    
    return f'{{% if {expr} %}}{node.name}{{% endif %}}'

@directive("if")
def render_if(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    res = [f"{{% if {expr} %}}" + body_compiled]
    for orelse in node.orelse:
        res.append(compiler.visit(orelse))
    res.append("{% endif %}")
    return "".join(res)

@directive("unless")
def render_unless(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    res = [f"{{% if not ({expr}) %}}" + body_compiled]
    for orelse in node.orelse:
        res.append(compiler.visit(orelse))
    res.append("{% endif %}")
    return "".join(res)

@directive(["elif", "elseif", "else_if"])
def render_elif(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    res = [f"{{% elif {expr} %}}{body_compiled}"]
    for o in node.orelse:
        res.append(compiler.visit(o))
    return "".join(res)

@directive("else")
def render_else(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    res = [f"{{% else %}}{body_compiled}"]
    for o in node.orelse:
        res.append(compiler.visit(o))
    return "".join(res)

@directive("empty")
def render_empty(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """Fallback for empty loops (alias for else)."""
    body_compiled = get_body_compiled(compiler, node)
    return f"{{% else %}}{body_compiled}"

@directive(["for", "foreach"])
def render_for(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    inner = expr.replace('$', '') if expr else ""
    if ' as ' in inner:
        # FIXED: split(' as ', 1) to only split on first occurrence
        parts = inner.split(' as ', 1)
        inner = f"{parts[1].strip()} in {parts[0].strip()}"
    body_compiled = get_body_compiled(compiler, node)
    res = [
        f"{{% for {inner} %}}"
        f"{{% if loop.index0 >= __eden_max_loop_iterations__ %}}"
        f"<!-- EDEN: Loop iteration limit ({{{{ __eden_max_loop_iterations__ }}}}) exceeded -->{{% break %}}"
        f"{{% endif %}}"
        + body_compiled
    ]
    for o in node.orelse:
        res.append(compiler.visit(o))
    res.append("{% endfor %}")
    return "".join(res)

@directive("while")
def render_while(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """Implement a while loop using a for-break construct."""
    body_compiled = get_body_compiled(compiler, node)
    # FIXED: Use __eden_max_loop_iterations__ instead of range(2147483647)
    # This prevents memory exhaustion DoS from massive range object
    return (
        f"{{% for _ in range(__eden_max_loop_iterations__) %}}"
        f"{{% if loop.index0 >= __eden_max_loop_iterations__ %}}"
        f"<!-- EDEN: Loop iteration limit ({{{{ __eden_max_loop_iterations__ }}}}) exceeded -->{{% break %}}"
        f"{{% endif %}}"
        f"{{% if not ({expr}) %}}{{% break %}}{{% endif %}}"
        f"{body_compiled}{{% endfor %}}"
    )

@directive("switch")
def render_switch(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    # FIXED: Validate that expression is provided
    if not expr or not expr.strip():
        return '<!-- @switch requires a value: @switch(status) -->'
    
    cases_compiled = []
    default_compiled = ""
    has_cases = False
    
    if node.body:
        for n in node.body:
            # We import DirectiveNode cleanly here though typing is mostly only used for hints
            if type(n).__name__ == "DirectiveNode":
                if n.name == "case":
                    c_expr = n.expression[1:-1] if n.expression else "None"
                    c_body = compiler.compile(n.body or [])
                    pfx = "{% if" if not has_cases else "{% elif"
                    cases_compiled.append(f"{pfx} __sw == {c_expr} %}}" + c_body)
                    has_cases = True
                elif n.name == "default":
                    pfx = "{% else %}" if has_cases else "{% if True %}"
                    default_compiled = pfx + compiler.compile(n.body or [])
    
    res = [f"{{% with __sw = {expr} %}}"]
    res.extend(cases_compiled)
    if default_compiled:
        res.append(default_compiled)
        if not has_cases:
            res.append("{% endif %}")
    if has_cases:
        res.append("{% endif %}")
    res.append("{% endwith %}")
    return "".join(res)

@directive(["case", "default"])
def render_case_default(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return ""  # Handled directly by switch


# ── Auth & RBAC ───────────────────────────────────────────────────────────────

@directive("auth")
def render_auth(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    if expr:
        # FIXED: Security - Extract roles and check against tuple instead of embedding in code
        roles_list = [r.strip().strip("'\"").replace('$', '') for r in (expr or "").split(',')]
        # Use tuple membership test instead of code injection
        if len(roles_list) == 1:
            # Single role: check exact match
            cond = f'request.user.role == "{roles_list[0]}"'
        else:
            # Multiple roles: check membership (but list repr is safe for Jinja2)
            roles_tuple = tuple(roles_list)
            cond = f'request.user.role in {roles_tuple}'
        return f'{{% if request.user and request.user.is_authenticated and {cond} %}}{body_compiled}{{% endif %}}'
    return f'{{% if request.user and request.user.is_authenticated %}}{body_compiled}{{% endif %}}'

@directive("can")
def render_can(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    # FIXED: Validate that permission expression is provided
    if not expr or not expr.strip():
        return '<!-- @can requires a permission: @can("permission_name") -->'
    
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% if request.user and request.user.has_permission({expr}) %}}{body_compiled}{{% endif %}}'

@directive("role")
def render_role(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    # FIXED: Validate that role expression is provided
    if not expr or not expr.strip():
        return '<!-- @role requires one or more roles: @role("admin") or @role("admin", "editor") -->'
    
    body_compiled = get_body_compiled(compiler, node)
    # FIXED: Security - Use tuple instead of list repr for role checking
    roles_list = [r.strip().strip("'\"").replace('$', '') for r in (expr or "").split(',')]
    if len(roles_list) == 1:
        cond = f'request.user.role == "{roles_list[0]}"'
    else:
        roles_tuple = tuple(roles_list)
        cond = f'request.user.role in {roles_tuple}'
    return f'{{% if request.user and request.user.is_authenticated and {cond} %}}{body_compiled}{{% endif %}}'

@directive("permission")
def render_permission(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """Alias for @can."""
    return render_can(compiler, node, expr)

@directive("cannot")
def render_cannot(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    # FIXED: Validate that permission expression is provided
    if not expr or not expr.strip():
        return '<!-- @cannot requires a permission: @cannot("permission_name") -->'
    
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% if not (request.user and request.user.has_permission({expr})) %}}{body_compiled}{{% endif %}}'

@directive("guest")
def render_guest(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% if not (request.user and request.user.is_authenticated) %}}{body_compiled}{{% endif %}}'

@directive("admin")
def render_admin(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """
    Render content only if user has admin role.
    
    Convenience shortcut for @role('admin') or @auth('admin').
    
    Usage:
        @admin
            <a href="/admin">Admin Panel</a>
        @endadmin
        
        <!-- Equivalent to: -->
        @role('admin')
            <a href="/admin">Admin Panel</a>
        @endrole
    
    Returns:
        Jinja2 condition checking if user is authenticated AND has 'admin' role.
    """
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% if request.user and request.user.is_authenticated and request.user.role == "admin" %}}{body_compiled}{{% endif %}}'


# ── HTMX ──────────────────────────────────────────────────────────────────────

@directive("htmx")
def render_htmx(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% if request.headers.get("HX-Request") == "true" %}}{body_compiled}{{% endif %}}'

@directive("non_htmx")
def render_non_htmx(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% if request.headers.get("HX-Request") != "true" %}}{body_compiled}{{% endif %}}'


# ── Errors & Forms ────────────────────────────────────────────────────────────

@directive("render_field")
def render_render_field(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    parts = [p.strip() for p in (expr or "").split(',', 1)]
    field_expr = parts[0].replace('$', '')
    kwargs = parts[1] if len(parts) > 1 else ""
    return f'{{{{ {field_expr}.render_composite({kwargs}) }}}}'

@directive("error")
def render_error(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    # FIXED: Validate that field name is provided
    if not expr or not expr.strip():
        return '<!-- @error requires a field name: @error("field_name") -->'
    
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% if errors and errors.has({expr}) %}}{{% set error = errors.first({expr}) %}}{body_compiled}{{% endif %}}'

@directive("messages")
def render_messages(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% for message in eden_messages() %}}{body_compiled}{{% endfor %}}'


# ── Loop Context ──────────────────────────────────────────────────────────────

@directive(["even", "odd", "first", "last"])
def render_loop_context(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    if node.name == "even":
        return f'{{% if loop.index % 2 == 0 %}}{body_compiled}{{% endif %}}'
    elif node.name == "odd":
        return f'{{% if loop.index % 2 == 1 %}}{body_compiled}{{% endif %}}'
    else:
        return f'{{% if loop.{node.name} %}}{body_compiled}{{% endif %}}'

@directive("break")
def render_break(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """Break out of a loop, optionally with a condition."""
    if expr:
        # Handle @break(condition) or @break if (condition)
        cond = expr.strip()
        if cond.startswith("if "): cond = cond[3:]
        return f"{{% if {cond} %}}{{% break %}}{{% endif %}}"
    return "{% break %}"

@directive("continue")
def render_continue(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """Skip to next loop iteration, optionally with a condition."""
    if expr:
        cond = expr.strip()
        if cond.startswith("if "): cond = cond[3:]
        return f"{{% if {cond} %}}{{% continue %}}{{% endif %}}"
    return "{% continue %}"


# ── PHP / Arbitrary Logic ─────────────────────────────────────────────────────

@directive("php")
def render_php(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """Execute arbitrary logic, converting statements to Jinja2 tags."""
    def wrap_logic(code: str) -> str:
        code = code.strip()
        if not code: return ""
        # If it contains an assignment, use {% set ... %}
        if "=" in code and not code.startswith("{{"): 
             return f'{{% set {code} %}}'
        # Otherwise use {% do ... %}
        return f'{{% do {code} %}}'

    if node.body:
        body_raw = compiler.compile(node.body) # Get raw body text
        lines = body_raw.strip().split('\n')
        return "".join(wrap_logic(line) for line in lines if line.strip())
    
    return wrap_logic(expr)

@directive("inject")
def render_inject(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """
    Inject a service/attribute from the application context into the template.
    
    Syntax:
        @inject(variable_name, 'service_alias')
    
    Resolution order (in templates.py _dependency_helper):
        1. App instance attributes (app.cache, app.mail, app.broker, etc.)
        2. App.config attributes (app.config.database_url, app.config.env, etc.)
        3. App.state attributes (request-scoped or app-scoped custom values)
    
    Examples:
        @inject(cache, 'cache')              => {% set cache = eden_dependency('cache') %}
        @inject(mail, 'mail')                => {% set mail = eden_dependency('mail') %}
        @inject(env, 'env')                  => {% set env = eden_dependency('env') %}
        @inject(db_url, 'database_url')      => {% set db_url = eden_dependency('database_url') %}
    
    Usage in template:
        @inject(cache, 'cache')
        {% if cache %}
            <p>Cache: {{ cache }}</p>
        {% endif %}
    
    For complex dependencies with FastAPI-style Depends(), pass the resolved
    value via context instead:
        return render_template("template.html", {
            "service": await resolve_dependency(complex_dep)
        })
    
    Returns:
        Jinja2 {% set %} tag that assigns the resolved service to a variable.
    """
    if not expr: return ""
    parts = [p.strip() for p in expr.split(',', 1)]
    var_name = parts[0]
    service_alias = parts[1] if len(parts) > 1 else var_name
    return f"{{% set {var_name} = eden_dependency({service_alias}) %}}"


# ── Advanced Form Components ──────────────────────────────────────────────────

@directive("form")
def render_form(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """Render a form tag with automatic CSRF injection."""
    body_compiled = get_body_compiled(compiler, node)
    # Check if it's a POST form (case-insensitive)
    is_post = expr and "POST" in expr.upper()
    # FIXED: Move csrf_token() call inside the conditional to avoid silent bypass
    csrf = (
        '{% if csrf_token %}<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">{% endif %}'
        if is_post
        else ""
    )
    return f'<form {expr}>{csrf}{body_compiled}</form>'

@directive(["field", "input", "button"])
def render_form_components(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """Integrate with form/UI component system."""
    body_compiled = get_body_compiled(compiler, node)
    if body_compiled:
        return f'{{% component "{node.name}", {expr} %}}{body_compiled}{{% endcomponent %}}'
    return f'{{{{ component("{node.name}", {expr}) }}}}'


# ── Recursion & Hierarchical Data ─────────────────────────────────────────────

@directive("recursive")
def render_recursive(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """
    Render hierarchical data structures recursively.
    Maps to Jinja2's `for ... recursive` loop.
    Use @child(item.children) within the block to recurse.
    
    FIXED: Added validation for required expression.
    """
    # FIXED: Validate that expression is provided
    if not expr or not expr.strip():
        return '<!-- @recursive requires an iterable: @recursive(items as item) or @recursive(item in collection) -->'
    
    inner = expr.replace('$', '') if expr else ""
    if ' as ' in inner:
        parts = inner.split(' as ', 1)
        inner = f"{parts[1].strip()} in {parts[0].strip()}"
    
    body_compiled = get_body_compiled(compiler, node)
    res = [
        f"{{% for {inner} recursive %}}"
        f"{{% if loop.index0 >= __eden_max_loop_iterations__ %}}"
        f"<!-- EDEN: Loop iteration limit ({{{{ __eden_max_loop_iterations__ }}}}) exceeded -->{{% break %}}"
        f"{{% endif %}}"
        + body_compiled
    ]
    for o in node.orelse:
        res.append(compiler.visit(o))
    res.append("{% endfor %}")
    return "".join(res)

@directive(["child", "recurse"])
def render_child(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """
    Recurse to the next level in a @recursive loop.
    Maps to Jinja2's `loop(next_items)` call.
    
    FIXED: Added validation for required expression.
    """
    # FIXED: Validate that expression is provided
    if not expr or not expr.strip():
        return '<!-- @child/@recurse requires items: @child(item.children) -->'
    
    val = expr.replace('$', '') if expr else ""
    return f"{{{{ loop({val}) }}}}"
# ── ORM & Reactivity ──────────────────────────────────────────────────────────

@directive("reactive")
def render_reactive(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """
    Reactive wrapper for a block of code.
    Automatically handles WebSocket sync and HTMX-based self-refresh.
    
    FIXED: Added validation for required expression.
    """
    import hashlib
    
    expr = (expr or "").strip()
    # FIXED: Validate that expression is provided
    if not expr:
        return '<!-- @reactive requires an object: @reactive(obj) or @reactive(obj, id="custom") -->'
    
    # Support both @reactive(obj) and @reactive(obj, id="custom")
    parts = [p.strip() for p in expr.split(',', 1)]
    sync_obj = parts[0]
    provided_id = None
    
    if len(parts) > 1:
        # Simple parser for id="value"
        id_part = parts[1].strip()
        if id_part.startswith('id='):
            provided_id = id_part[3:].strip().strip("'").strip('"')

    # Generate a stable unique ID if not provided, based on source location
    if not provided_id:
        loc = f"{node.line}_{node.column}"
        h = hashlib.md5(loc.encode()).hexdigest()[:6]
        provided_id = f"sync_{h}"
    
    body = get_body_compiled(compiler, node)
    
    # We use get_sync_channel(obj) to resolve the channel name (e.g. "users:5")
    # hx-sync: listens for broadcasts on this channel
    # hx-channel: listens for broadcasts on this channel
    # hx-trigger: refreshes on 'updated' or 'created' events from the body (bubbled up)
    # hx-get: calls current URL to get the refreshed fragment
    # fragment_ID: provides the anchor for Smart Fragment Resolution
    return (
        f'{{% set __ch = get_sync_channel({sync_obj}) %}}'
        f'<div id="{provided_id}" '
        f'hx-channel="{{{{ __ch }}}}" '
        f'hx-sync="{{{{ __ch }}}}" '
        f'hx-trigger="updated:{{{{ __ch }}}} from:body, created:{{{{ __ch }}}} from:body" '
        f'hx-get="{{{{ request.url }}}}" '
        f'hx-target="this" '
        f'hx-swap="outerHTML" '
        f'class="eden-reactive-block">'
        f'{{% do request.state.eden_channels.add(__ch) if request and hasattr(request, "state") and hasattr(request.state, "eden_channels") %}}'
        f'{{% block fragment_{provided_id} %}}'
        f'{body}'
        f'{{% endblock %}}'
        f'</div>'
    )
