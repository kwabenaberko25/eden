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
    val = expr.strip("'\"") if expr else "POST"
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

@directive("css")
def render_css(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return f'<link rel="stylesheet" href={expr}>'

@directive("js")
def render_js(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return f'<script src={expr}></script>'

@directive("vite")
def render_vite(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return f'{{{{ vite({expr}) }}}}'


# ── Component, Layouts, & Blocks ──────────────────────────────────────────────

@directive("yield")
def render_yield(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    val = expr.strip("'\"") if expr else "content"
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
    return f'{{{{ {expr.replace("$", "")} }}}}' if expr else ""

@directive("json")
def render_json(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return f'{{{{ {expr} | json_encode }}}}'

@directive("dump")
def render_dump(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    clean_expr = expr.replace("$", "").replace("(", "").replace(")", "").strip()
    return f'{{{{ eden_dump({expr}, "{clean_expr}") }}}} {{# eden-dump json_encode #}}'

@directive("status")
def render_status(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return f'{{{{ set_response_status({expr}) }}}}'

@directive("let")
def render_let(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return f"{{% set {expr} %}}"

@directive(["url", "route"])
def render_url(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    return compiler.handle_url(expr)

@directive("active_link")
def render_active_link(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    parts = [p.strip() for p in (expr or "").split(',', 1)]
    url_v = parts[0]
    css_v = parts[1].strip('"\'')
    if url_v.startswith("'") or url_v.startswith('"'):
        url_v = f'"{url_v[1:-1]}"'
    return f'{{{{ "{css_v}" if is_active(request, {url_v}) else "" }}}}'

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
        parts = inner.split(' as ')
        inner = f"{parts[1].strip()} in {parts[0].strip()}"
    body_compiled = get_body_compiled(compiler, node)
    res = [f"{{% for {inner} %}}" + body_compiled]
    for o in node.orelse:
        res.append(compiler.visit(o))
    res.append("{% endfor %}")
    return "".join(res)

@directive("while")
def render_while(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """Implement a while loop using a for-break construct."""
    body_compiled = get_body_compiled(compiler, node)
    # We use a large range as a practical infinite loop since Jinja2 doesn't have native while
    return f"{{% for _ in range(2147483647) %}}{{% if not ({expr}) %}}{{% break %}}{{% endif %}}{body_compiled}{{% endfor %}}"

@directive("switch")
def render_switch(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
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
        roles_list = [r.strip().strip("'\"").replace('$', '') for r in (expr or "").split(',')]
        cond = f'request.user.role == "{roles_list[0]}"' if len(roles_list) == 1 else f'request.user.role in {roles_list}'
        return f'{{% if request.user and request.user.is_authenticated and {cond} %}}{body_compiled}{{% endif %}}'
    return f'{{% if request.user and request.user.is_authenticated %}}{body_compiled}{{% endif %}}'

@directive("can")
def render_can(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% if request.user and request.user.has_permission({expr}) %}}{body_compiled}{{% endif %}}'

@directive("role")
def render_role(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    roles_list = [r.strip().strip("'\"").replace('$', '') for r in (expr or "").split(',')]
    cond = f'request.user.role == "{roles_list[0]}"' if len(roles_list) == 1 else f'request.user.role in {roles_list}'
    return f'{{% if request.user and request.user.is_authenticated and {cond} %}}{body_compiled}{{% endif %}}'

@directive("permission")
def render_permission(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """Alias for @can."""
    return render_can(compiler, node, expr)

@directive("cannot")
def render_cannot(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% if not (request.user and request.user.has_permission({expr})) %}}{body_compiled}{{% endif %}}'

@directive("guest")
def render_guest(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    body_compiled = get_body_compiled(compiler, node)
    return f'{{% if not (request.user and request.user.is_authenticated) %}}{body_compiled}{{% endif %}}'


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
    """Inject a service into the template context."""
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
    csrf = '{% if csrf_token %}<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">{% endif %}' if is_post else ""
    return f'<form {expr}>{csrf}{body_compiled}</form>'

@directive(["field", "input", "button"])
def render_form_components(compiler: "TemplateCompiler", node: "DirectiveNode", expr: str) -> str:
    """Integrate with form/UI component system."""
    body_compiled = get_body_compiled(compiler, node)
    if body_compiled:
        return f'{{% component "{node.name}", {expr} %}}{body_compiled}{{% endcomponent %}}'
    return f'{{{{ component("{node.name}", {expr}) }}}}'
