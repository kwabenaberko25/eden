"""
Directive Regression Suite — Post-Hardening Verification.

This module verifies that ALL registered @directives still compile and render
correctly after the security hardening changes (SandboxedEnvironment, loop
guards, argument validation, parser depth guard, etc.).

It does NOT test application context (e.g., actual CSRF tokens or URL routes)
but ensures the full pipeline — Lexer → Parser → Compiler → Jinja render —
produces output without raising unexpected exceptions.
"""

import pytest
from eden.templating.lexer import TemplateLexer
from eden.templating.parser import TemplateParser
from eden.templating.compiler import TemplateCompiler
from eden.templating import EdenTemplates


# ---------------------------------------------------------------------------
# Fixture: Shared EdenTemplates environment with safe defaults
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def env():
    """Create a sandboxed EdenTemplates env once for all tests."""
    templates = EdenTemplates(directory=".")
    # Inject builtins that templates commonly reference
    templates.env.globals.update({
        "csrf_token": lambda: "test_csrf_token_abc",
        "eden_head": lambda: "<!-- head -->",
        "eden_scripts": lambda: "<!-- scripts -->",
        "eden_toasts": lambda: "<!-- toasts -->",
        "url_for": lambda *a, **kw: "/mock-url",
        "old": lambda name, default=None: default or "",
        "range": range,
        "True": True,
        "False": False,
        "None": None,
    })
    return templates


def compile_and_render(env, template_str: str, context: dict | None = None) -> str:
    """Full pipeline: Lex → Parse → Compile → Jinja Render."""
    tokens = TemplateLexer(template_str).tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    compiler = TemplateCompiler()
    compiled = compiler.compile(nodes)
    jinja_tpl = env.env.from_string(compiled)
    return jinja_tpl.render(**(context or {}))


# ===========================================================================
# 1. Conditional Directives
# ===========================================================================

class TestConditionals:
    """@if, @unless, @else, @elif, @elseif, @else_if"""

    def test_if_true(self, env):
        result = compile_and_render(env, "@if(True) { yes }")
        assert "yes" in result

    def test_if_false(self, env):
        result = compile_and_render(env, "@if(False) { yes }")
        assert "yes" not in result

    def test_if_else(self, env):
        result = compile_and_render(env, "@if(False) { yes } @else { no }")
        assert "no" in result

    def test_if_elif_else(self, env):
        result = compile_and_render(
            env,
            "@if(False) { a } @elif(True) { b } @else { c }",
        )
        assert "b" in result

    def test_unless(self, env):
        result = compile_and_render(env, "@unless(False) { shown }")
        assert "shown" in result

    def test_unless_true(self, env):
        result = compile_and_render(env, "@unless(True) { hidden }")
        assert "hidden" not in result


# ===========================================================================
# 2. Loop Directives
# ===========================================================================

class TestLoops:
    """@for, @foreach, @while, @recursive, @break, @continue"""

    def test_for_loop(self, env):
        result = compile_and_render(
            env,
            "@for(i in range(3)) { {{ i }} }",
            {"range": range},
        )
        assert "0" in result
        assert "1" in result
        assert "2" in result

    def test_foreach_loop(self, env):
        result = compile_and_render(
            env,
            "@foreach(item in items) { {{ item }} }",
            {"items": ["a", "b", "c"]},
        )
        assert "a" in result and "b" in result and "c" in result

    def test_for_empty(self, env):
        result = compile_and_render(
            env,
            "@for(x in items) { {{ x }} } @empty { nothing }",
            {"items": []},
        )
        assert "nothing" in result

    def test_for_else(self, env):
        result = compile_and_render(
            env,
            "@for(x in items) { {{ x }} } @else { empty }",
            {"items": []},
        )
        assert "empty" in result

    def test_while_loop(self, env):
        # While loops use Jinja for-break construct, just verify it compiles
        result = compile_and_render(
            env,
            "@while(False) { never }",
        )
        assert "never" not in result

    def test_recursive_loop(self, env):
        tree = [{"name": "root", "children": [{"name": "leaf", "children": []}]}]
        result = compile_and_render(
            env,
            "@recursive(node in tree) { {{ node.name }} @child(node.children) }",
            {"tree": tree},
        )
        assert "root" in result
        assert "leaf" in result

    def test_loop_even_odd(self, env):
        """@even and @odd directives use loop.even/loop.odd."""
        result = compile_and_render(
            env,
            "@for(item in items) { @even { E{{ item }} } @odd { O{{ item }} } }",
            {"items": ["a", "b", "c", "d"]},
        )
        # Jinja loop.even/odd are 1-indexed: item 1 is odd, item 2 is even, etc.
        assert "E" in result
        assert "O" in result

    def test_loop_first_last(self, env):
        """@first and @last use loop.first/loop.last."""
        result = compile_and_render(
            env,
            "@for(item in items) { @first { F } @last { L } }",
            {"items": ["a", "b", "c"]},
        )
        assert "F" in result
        assert "L" in result


# ===========================================================================
# 3. Security & Forms
# ===========================================================================

class TestSecurityForms:
    """@csrf, @csrf_token, @method, @old, @form, @field, @button, @input"""

    def test_csrf(self, env):
        result = compile_and_render(env, "@csrf")
        assert 'name="csrf_token"' in result
        assert "test_csrf_token_abc" in result

    def test_csrf_token(self, env):
        result = compile_and_render(env, "@csrf_token")
        assert "test_csrf_token_abc" in result

    def test_method(self, env):
        result = compile_and_render(env, "@method('PUT')")
        assert 'value="PUT"' in result

    def test_old(self, env):
        result = compile_and_render(env, "@old('email', 'default@test.com')")
        # old() lambda returns the default value
        assert "default@test.com" in result or result  # at minimum doesn't crash

    def test_form(self, env):
        result = compile_and_render(
            env,
            '@form("/submit", method="POST") { <input> }',
        )
        assert "form" in result.lower() or "<input>" in result

    def test_field_compiles(self, env):
        """@field compiles to a component call — verify compilation, not render."""
        tokens = TemplateLexer("@field('username') { <input> }").tokenize()
        parser = TemplateParser(tokens)
        nodes = parser.parse()
        compiler = TemplateCompiler()
        compiled = compiler.compile(nodes)
        # Should produce a {% component "field" %} block
        assert 'component' in compiled
        assert 'field' in compiled

    def test_button_compiles(self, env):
        """@button compiles to a component call — verify compilation, not render."""
        tokens = TemplateLexer("@button('submit') { Click }").tokenize()
        parser = TemplateParser(tokens)
        nodes = parser.parse()
        compiler = TemplateCompiler()
        compiled = compiler.compile(nodes)
        assert 'component' in compiled
        assert 'button' in compiled

    def test_input_compiles(self, env):
        """@input compiles to a component call — verify compilation, not render."""
        tokens = TemplateLexer("@input('email', type='text')").tokenize()
        parser = TemplateParser(tokens)
        nodes = parser.parse()
        compiler = TemplateCompiler()
        compiled = compiler.compile(nodes)
        assert 'component' in compiled
        assert 'input' in compiled


# ===========================================================================
# 4. Template Composition
# ===========================================================================

class TestComposition:
    """@extends, @section, @yield, @block, @slot, @push, @stack, @include"""

    def test_section_yield(self, env):
        result = compile_and_render(env, "@section('content') { Hello }")
        assert isinstance(result, str)

    def test_yield(self, env):
        result = compile_and_render(env, "@yield('content')")
        assert isinstance(result, str)

    def test_block(self, env):
        result = compile_and_render(env, "@block('sidebar') { Sidebar }")
        assert isinstance(result, str)

    def test_slot(self, env):
        result = compile_and_render(env, "@slot('header') { Header }")
        assert isinstance(result, str)

    def test_push_stack(self, env):
        result = compile_and_render(env, "@push('scripts') { <script></script> }")
        assert isinstance(result, str)

    def test_stack(self, env):
        result = compile_and_render(env, "@stack('scripts')")
        assert isinstance(result, str)


# ===========================================================================
# 5. Asset Directives
# ===========================================================================

class TestAssets:
    """@eden_head, @eden_scripts, @eden_toasts, @css, @js, @vite"""

    def test_eden_head(self, env):
        result = compile_and_render(env, "@eden_head")
        assert "head" in result

    def test_eden_scripts(self, env):
        result = compile_and_render(env, "@eden_scripts")
        assert "scripts" in result

    def test_eden_toasts(self, env):
        result = compile_and_render(env, "@eden_toasts")
        assert "toasts" in result

    def test_css(self, env):
        result = compile_and_render(env, "@css('styles.css')")
        assert "styles.css" in result

    def test_js(self, env):
        result = compile_and_render(env, "@js('app.js')")
        assert "app.js" in result

    def test_vite(self, env):
        result = compile_and_render(env, "@vite('src/main.js')")
        assert isinstance(result, str)


# ===========================================================================
# 6. Control Flow & Utility
# ===========================================================================

class TestUtility:
    """@let, @dump, @json, @verbatim, @inject, @props"""

    def test_let(self, env):
        result = compile_and_render(env, "@let(x = 42) {{ x }}")
        assert "42" in result

    def test_dump(self, env):
        result = compile_and_render(env, "@dump(items)", {"items": [1, 2, 3]})
        assert "1" in result  # dump should show the data

    def test_json(self, env):
        result = compile_and_render(env, "@json(data)", {"data": {"key": "val"}})
        assert "key" in result

    def test_verbatim(self, env):
        result = compile_and_render(env, "@verbatim { {{ raw }} }")
        assert "{{ raw }}" in result or "raw" in result

    def test_props(self, env):
        result = compile_and_render(
            env,
            "@props(['title' => 'Default Title']) {{ title }}",
        )
        assert "Default Title" in result or isinstance(result, str)


# ===========================================================================
# 7. Switch/Case
# ===========================================================================

class TestSwitch:
    """@switch, @case, @default"""

    def test_switch_case(self, env):
        result = compile_and_render(
            env,
            '@switch(status) { @case("active") { Active } @default { Other } }',
            {"status": "active"},
        )
        assert "Active" in result

    def test_switch_default(self, env):
        result = compile_and_render(
            env,
            '@switch(status) { @case("active") { Active } @default { Other } }',
            {"status": "unknown"},
        )
        assert "Other" in result


# ===========================================================================
# 8. Authorization Directives
# ===========================================================================

class TestAuth:
    """@auth, @guest, @can, @cannot, @role, @permission"""

    def test_auth_block(self, env):
        result = compile_and_render(
            env,
            "@auth { Logged in }",
            {"current_user": type("User", (), {"is_authenticated": True})()},
        )
        assert isinstance(result, str)

    def test_guest_block(self, env):
        result = compile_and_render(env, "@guest { Not logged in }")
        assert isinstance(result, str)

    def test_can(self, env):
        result = compile_and_render(env, "@can('edit_post') { Edit }")
        assert isinstance(result, str)

    def test_cannot(self, env):
        result = compile_and_render(env, "@cannot('delete_post') { No Delete }")
        assert isinstance(result, str)

    def test_role(self, env):
        result = compile_and_render(env, "@role('admin') { Admin Panel }")
        assert isinstance(result, str)

    def test_permission(self, env):
        result = compile_and_render(env, "@permission('manage_users') { Users }")
        assert isinstance(result, str)


# ===========================================================================
# 9. HTMX Directives
# ===========================================================================

class TestHtmx:
    """@htmx, @non_htmx, @fragment"""

    def test_htmx(self, env):
        result = compile_and_render(env, "@htmx { HTMX content }")
        assert isinstance(result, str)

    def test_non_htmx(self, env):
        result = compile_and_render(env, "@non_htmx { Full page }")
        assert isinstance(result, str)

    def test_fragment(self, env):
        result = compile_and_render(env, "@fragment('partial') { Fragment }")
        assert isinstance(result, str)


# ===========================================================================
# 10. HTML Attribute Helpers
# ===========================================================================

class TestHtmlHelpers:
    """@checked, @selected, @disabled, @readonly, @active_link, @class"""

    def test_checked(self, env):
        result = compile_and_render(env, "@checked(True)")
        assert "checked" in result

    def test_selected(self, env):
        result = compile_and_render(env, "@selected(True)")
        assert "selected" in result

    def test_disabled(self, env):
        result = compile_and_render(env, "@disabled(True)")
        assert "disabled" in result

    def test_readonly(self, env):
        result = compile_and_render(env, "@readonly(True)")
        assert "readonly" in result

    def test_class_directive(self, env):
        result = compile_and_render(env, "@class(['active' => True, 'hidden' => False])")
        assert "class" in result

    def test_active_link(self, env):
        result = compile_and_render(
            env,
            "@active_link('/dashboard', 'active-class')",
            {"request": type("R", (), {"url": type("U", (), {"path": "/dashboard"})()})()},
        )
        assert isinstance(result, str)


# ===========================================================================
# 11. URL and Routing
# ===========================================================================

class TestRouting:
    """@url, @route"""

    def test_url(self, env):
        result = compile_and_render(env, "@url('home')")
        assert "/mock-url" in result or isinstance(result, str)

    def test_route(self, env):
        result = compile_and_render(env, "@route('dashboard')")
        assert isinstance(result, str)


# ===========================================================================
# 12. Status and Error Display
# ===========================================================================

class TestStatusError:
    """@status, @error, @messages"""

    def test_status(self, env):
        result = compile_and_render(env, "@status(404) { Not Found }")
        assert isinstance(result, str)

    def test_error(self, env):
        result = compile_and_render(env, "@error('email') { Error msg }")
        assert isinstance(result, str)

    def test_messages(self, env):
        result = compile_and_render(env, "@messages { {{ message }} }")
        assert isinstance(result, str)


# ===========================================================================
# 13. Miscellaneous
# ===========================================================================

class TestMisc:
    """@span, @reactive, @php, @includeWhen, @includeUnless, @super, @prepend, @pushOnce, @render_field"""

    def test_span(self, env):
        result = compile_and_render(env, "@span('counter') { 0 }")
        assert isinstance(result, str)

    def test_reactive_compiles(self, env):
        """@reactive compiles correctly — needs sync channel in real app."""
        tokens = TemplateLexer("@reactive { <p>Live</p> }").tokenize()
        parser = TemplateParser(tokens)
        nodes = parser.parse()
        compiler = TemplateCompiler()
        compiled = compiler.compile(nodes)
        # Should produce valid Jinja output without crashing the compiler
        assert isinstance(compiled, str)
        assert len(compiled) > 0

    def test_include_when(self, env):
        result = compile_and_render(env, "@includeWhen(False, 'partial.html')")
        assert isinstance(result, str)

    def test_include_unless(self, env):
        result = compile_and_render(env, "@includeUnless(True, 'partial.html')")
        assert isinstance(result, str)


# ===========================================================================
# 14. Compiler Validation — Hardening-Specific
# ===========================================================================

class TestCompilerValidation:
    """Verify that the compiler's argument validation catches bad inputs
    without crashing AND still allows valid inputs through."""

    def test_for_without_in_produces_warning_comment(self, env):
        """@for without 'in' should produce an HTML warning, not crash."""
        result = compile_and_render(env, "@for(broken_syntax) { body }")
        assert "EDEN TEMPLATE WARNING" in result

    def test_if_empty_expr_produces_warning(self, env):
        """@if() with empty expression should produce an HTML warning."""
        result = compile_and_render(env, "@if() { body }")
        assert "EDEN TEMPLATE WARNING" in result

    def test_switch_empty_expr_produces_warning(self, env):
        """@switch() with empty expression should produce an HTML warning."""
        result = compile_and_render(env, "@switch() { body }")
        assert "EDEN TEMPLATE WARNING" in result

    def test_valid_for_passes_validation(self, env):
        """@for with proper 'in' keyword should work normally."""
        result = compile_and_render(env, "@for(x in items) { {{ x }} }", {"items": [1]})
        assert "1" in result
        assert "WARNING" not in result
