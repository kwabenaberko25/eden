"""
Tests for Eden Design System, expanded filters, new directives,
HTMX integration, and CDN asset injection.
"""
import json
import pytest
from jinja2 import Environment
from eden.templating import (
    EdenDirectivesExtension,
    EdenTemplates,
    # Utility filters
    truncate_filter,
    slugify_filter,
    json_encode,
    default_if_none,
    pluralize_filter,
    title_case,
    mask_filter,
    file_size_filter,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Utility Filters (pure-Python)
# ═══════════════════════════════════════════════════════════════════════════════

class TestUtilityFilters:
    def test_truncate_short(self):
        assert truncate_filter("Hello", 10) == "Hello"

    def test_truncate_long(self):
        assert truncate_filter("Hello World, this is a long string", 10) == "Hello Worl…"

    def test_truncate_custom_end(self):
        assert truncate_filter("Hello World", 5, "...") == "Hello..."

    def test_slugify_basic(self):
        assert slugify_filter("Hello World") == "hello-world"

    def test_slugify_special_chars(self):
        assert slugify_filter("Hello, World! @2024") == "hello-world-2024"

    def test_slugify_underscores(self):
        assert slugify_filter("my_variable_name") == "my-variable-name"

    def test_json_encode_dict(self):
        result = json_encode({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_json_encode_list(self):
        result = json_encode([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]

    def test_default_if_none_with_none(self):
        assert default_if_none(None, "fallback") == "fallback"

    def test_default_if_none_with_value(self):
        assert default_if_none("actual", "fallback") == "actual"

    def test_default_if_none_zero_is_not_none(self):
        assert default_if_none(0, "fallback") == 0

    def test_pluralize_singular(self):
        assert pluralize_filter(1, "item", "items") == "item"

    def test_pluralize_plural(self):
        assert pluralize_filter(5, "item", "items") == "items"

    def test_pluralize_zero(self):
        assert pluralize_filter(0, "item", "items") == "items"

    def test_title_case(self):
        assert title_case("hello world") == "Hello World"

    def test_mask_email(self):
        assert mask_filter("user@example.com") == "u***@example.com"

    def test_mask_string(self):
        assert mask_filter("secret123") == "s*******3"

    def test_mask_short(self):
        assert mask_filter("ab") == "**"

    def test_file_size_bytes(self):
        assert file_size_filter(500) == "500 B"

    def test_file_size_kb(self):
        assert file_size_filter(1536) == "1.5 KB"

    def test_file_size_mb(self):
        assert file_size_filter(1_048_576) == "1.0 MB"

    def test_file_size_gb(self):
        assert file_size_filter(1_073_741_824) == "1.0 GB"

    def test_file_size_invalid(self):
        assert file_size_filter("invalid") == "0 B"


# ═══════════════════════════════════════════════════════════════════════════════
# Utility filters via Jinja templates
# ═══════════════════════════════════════════════════════════════════════════════

class TestUtilityFiltersInTemplates:
    def _render(self, tmp_path, template_str, **ctx):
        tdir = tmp_path / "templates"
        tdir.mkdir(exist_ok=True)
        (tdir / "t.html").write_text(template_str)
        tmpl = EdenTemplates(directory=str(tdir))
        return tmpl.get_template("t.html").render(**ctx)

    def test_truncate_in_template(self, tmp_path):
        r = self._render(tmp_path, '{{ text | truncate(5) }}', text="Hello World")
        assert r.strip() == "Hello…"

    def test_slugify_in_template(self, tmp_path):
        r = self._render(tmp_path, '{{ text | slugify }}', text="Eden Framework!")
        assert r.strip() == "eden-framework"

    def test_json_encode_in_template(self, tmp_path):
        r = self._render(tmp_path, '{{ data | json_encode }}', data={"x": 1})
        assert json.loads(r.strip()) == {"x": 1}

    def test_default_if_none_in_template(self, tmp_path):
        r = self._render(tmp_path, '{{ val | default_if_none("N/A") }}', val=None)
        assert r.strip() == "N/A"

    def test_pluralize_in_template(self, tmp_path):
        r = self._render(tmp_path, '{{ count }} item{{ count | pluralize("", "s") }}', count=3)
        assert "3 items" in r

    def test_mask_in_template(self, tmp_path):
        r = self._render(tmp_path, '{{ email | mask }}', email="admin@eden.dev")
        assert r.strip() == "a***@eden.dev"

    def test_file_size_in_template(self, tmp_path):
        r = self._render(tmp_path, '{{ size | file_size }}', size=2048)
        assert r.strip() == "2.0 KB"


# ═══════════════════════════════════════════════════════════════════════════════
# Design System Filters
# ═══════════════════════════════════════════════════════════════════════════════

class TestDesignSystemFilters:
    def _render(self, tmp_path, template_str, **ctx):
        tdir = tmp_path / "templates"
        tdir.mkdir(exist_ok=True)
        (tdir / "t.html").write_text(template_str)
        tmpl = EdenTemplates(directory=str(tdir))
        return tmpl.get_template("t.html").render(**ctx)

    def test_eden_color(self, tmp_path):
        r = self._render(tmp_path, '{{ "primary" | eden_color }}')
        assert r.strip() == "#2563EB"

    def test_eden_bg(self, tmp_path):
        r = self._render(tmp_path, '{{ "primary" | eden_bg }}')
        assert r.strip() == "bg-blue-600"

    def test_eden_text(self, tmp_path):
        r = self._render(tmp_path, '{{ "muted" | eden_text }}')
        assert r.strip() == "text-slate-400"

    def test_eden_border(self, tmp_path):
        r = self._render(tmp_path, '{{ "default" | eden_border }}')
        assert r.strip() == "border-gray-700"

    def test_eden_shadow(self, tmp_path):
        r = self._render(tmp_path, '{{ "primary" | eden_shadow }}')
        assert r.strip() == "shadow-blue-500/20"


# ═══════════════════════════════════════════════════════════════════════════════
# New Directives
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewDirectives:
    def test_unless_true(self, tmp_path):
        tdir = tmp_path / "templates"
        tdir.mkdir()
        (tdir / "t.html").write_text('@unless (hidden) {\n  Visible\n}\n')
        tmpl = EdenTemplates(directory=str(tdir))
        r = tmpl.get_template("t.html").render(hidden=False)
        assert "Visible" in r

    def test_unless_false(self, tmp_path):
        tdir = tmp_path / "templates"
        tdir.mkdir()
        (tdir / "t.html").write_text('@unless (hidden) {\n  Visible\n}\n')
        tmpl = EdenTemplates(directory=str(tdir))
        r = tmpl.get_template("t.html").render(hidden=True)
        assert "Visible" not in r

    def test_checked_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('<input type="checkbox" @checked(is_active)>', "test.html")
        assert '{% if is_active %}checked{% endif %}' in result

    def test_selected_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('<option @selected(val == "a")>A</option>', "test.html")
        assert '{% if val == "a" %}selected{% endif %}' in result

    def test_disabled_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('<button @disabled(loading)>Go</button>', "test.html")
        assert '{% if loading %}disabled{% endif %}' in result

    def test_readonly_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('<input @readonly(locked)>', "test.html")
        assert '{% if locked %}readonly{% endif %}' in result

    def test_eden_head_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('@eden_head', "test.html")
        assert '{{ eden_head() }}' in result

    def test_eden_scripts_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('@eden_scripts', "test.html")
        assert '{{ eden_scripts() }}' in result

    def test_htmx_block_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('@htmx {\n  <div>HTMX only</div>\n}\n', "test.html")
        assert '{% if request.headers.get("HX-Request") == "true" %}' in result
        assert '{% endif %}' in result

    def test_non_htmx_block_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('@non_htmx {\n  <div>Full page</div>\n}\n', "test.html")
        assert '{% if request.headers.get("HX-Request") != "true" %}' in result

    def test_extends_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('@extends("eden/base.html")', "test.html")
        assert '{% extends "eden/base.html" %}' in result

    def test_extends_single_quotes(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess("@extends('eden/base.html')", "test.html")
        assert "{% extends 'eden/base.html' %}" in result

    def test_include_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('@include("partials/header.html")', "test.html")
        assert '{% include "partials/header.html" %}' in result

    def test_block_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('@block("content") {\n  <p>Hello</p>\n}\n', "test.html")
        assert '{% block content %}' in result
        assert '{% endblock %}' in result

    def test_block_without_quotes(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('@block(content) {\n  <p>Hello</p>\n}\n', "test.html")
        assert '{% block content %}' in result

    def test_super_directive(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('@super', "test.html")
        assert '{{ super() }}' in result

    def test_super_with_parens(self):
        ext = EdenDirectivesExtension(Environment())
        result = ext.preprocess('@super()', "test.html")
        assert '{{ super() }}' in result


# ═══════════════════════════════════════════════════════════════════════════════
# HTMX Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestHtmxIntegration:
    def test_htmx_response_trigger(self):
        from eden.htmx import HtmxResponse
        resp = HtmxResponse("<p>OK</p>").trigger("showToast")
        assert resp.headers["HX-Trigger"] == "showToast"

    def test_htmx_response_trigger_with_detail(self):
        from eden.htmx import HtmxResponse
        resp = HtmxResponse("<p>OK</p>").trigger("notify", {"msg": "Saved"})
        parsed = json.loads(resp.headers["HX-Trigger"])
        assert parsed == {"notify": {"msg": "Saved"}}

    def test_htmx_response_redirect(self):
        from eden.htmx import HtmxResponse
        resp = HtmxResponse("").hx_redirect("/dashboard")
        assert resp.headers["HX-Redirect"] == "/dashboard"

    def test_htmx_response_refresh(self):
        from eden.htmx import HtmxResponse
        resp = HtmxResponse("").refresh()
        assert resp.headers["HX-Refresh"] == "true"

    def test_htmx_response_swap(self):
        from eden.htmx import HtmxResponse
        resp = HtmxResponse("").swap("outerHTML")
        assert resp.headers["HX-Reswap"] == "outerHTML"

    def test_htmx_response_retarget(self):
        from eden.htmx import HtmxResponse
        resp = HtmxResponse("").retarget("#main")
        assert resp.headers["HX-Retarget"] == "#main"

    def test_htmx_response_push_url(self):
        from eden.htmx import HtmxResponse
        resp = HtmxResponse("").push_url("/new-page")
        assert resp.headers["HX-Push-Url"] == "/new-page"

    def test_htmx_response_chaining(self):
        from eden.htmx import HtmxResponse
        resp = (
            HtmxResponse("<p>Done</p>")
            .trigger("saved")
            .swap("innerHTML")
            .push_url("/items")
        )
        assert resp.headers["HX-Trigger"] == "saved"
        assert resp.headers["HX-Reswap"] == "innerHTML"
        assert resp.headers["HX-Push-Url"] == "/items"

    def test_is_htmx_true(self):
        from eden.htmx import is_htmx
        from unittest.mock import MagicMock
        req = MagicMock()
        req.headers = {"HX-Request": "true"}
        assert is_htmx(req) is True

    def test_is_htmx_false(self):
        from eden.htmx import is_htmx
        from unittest.mock import MagicMock
        req = MagicMock()
        req.headers = {}
        assert is_htmx(req) is False

    def test_hx_vals_filter(self):
        from eden.htmx import hx_vals
        result = hx_vals({"id": 42, "name": "test"})
        parsed = json.loads(result)
        assert parsed["id"] == 42

    def test_hx_headers_filter(self):
        from eden.htmx import hx_headers
        result = hx_headers({"X-Custom": "abc"})
        parsed = json.loads(result)
        assert parsed["X-Custom"] == "abc"

    def test_hx_vals_in_template(self, tmp_path):
        tdir = tmp_path / "templates"
        tdir.mkdir()
        (tdir / "t.html").write_text('hx-vals=\'{{ data | hx_vals }}\'')
        tmpl = EdenTemplates(directory=str(tdir))
        r = tmpl.get_template("t.html").render(data={"page": 2})
        assert '"page": 2' in r


# ═══════════════════════════════════════════════════════════════════════════════
# CDN Asset Injection
# ═══════════════════════════════════════════════════════════════════════════════

class TestCDNAssets:
    def test_eden_head_contains_cdn(self):
        from eden.assets import eden_head
        html = str(eden_head())
        assert "alpinejs" in html
        assert "htmx.org" in html
        assert "tailwindcss" in html
        assert "Plus+Jakarta+Sans" in html

    def test_eden_head_disable_alpine(self):
        from eden.assets import eden_head
        html = str(eden_head(alpine=False))
        assert "alpinejs" not in html
        assert "htmx.org" in html

    def test_eden_scripts_output(self):
        from eden.assets import eden_scripts
        html = str(eden_scripts())
        assert "eden-ready" in html

    def test_eden_head_in_template(self, tmp_path):
        tdir = tmp_path / "templates"
        tdir.mkdir()
        (tdir / "t.html").write_text('@eden_head')
        tmpl = EdenTemplates(directory=str(tdir))
        r = tmpl.get_template("t.html").render()
        assert "alpinejs" in r
        assert "htmx.org" in r

    def test_version_globals(self, tmp_path):
        tdir = tmp_path / "templates"
        tdir.mkdir()
        (tdir / "t.html").write_text('{{ alpine_version }}-{{ htmx_version }}-{{ tailwind_version }}')
        tmpl = EdenTemplates(directory=str(tdir))
        r = tmpl.get_template("t.html").render()
        assert "3.14.9" in r
        assert "2.0.4" in r

    def test_base_template_renders(self, tmp_path):
        tdir = tmp_path / "templates"
        tdir.mkdir()
        (tdir / "page.html").write_text(
            '@extends("eden/base.html")\n'
            '@block("title") { My Page }\n'
            '@block("content") {\n<p>Hello Eden</p>\n}\n'
        )
        tmpl = EdenTemplates(directory=str(tdir))
        r = tmpl.get_template("page.html").render()
        assert "My Page" in r
        assert "Hello Eden" in r
        assert "alpinejs" in r
        assert "htmx.org" in r
        assert "tailwindcss" in r
        assert "Plus Jakarta Sans" in r


# ═══════════════════════════════════════════════════════════════════════════════
# Design System Python API
# ═══════════════════════════════════════════════════════════════════════════════

class TestDesignSystemAPI:
    def test_color_lookup(self):
        from eden.design import eden_color
        assert eden_color("primary") == "#2563EB"

    def test_color_fallback(self):
        from eden.design import eden_color
        assert eden_color("custom-hex") == "custom-hex"

    def test_spacing(self):
        from eden.design import spacing
        assert spacing(4) == "1rem"
        assert spacing(1) == "0.25rem"

    def test_font_lookup(self):
        from eden.design import eden_font
        assert "Plus Jakarta Sans" in eden_font("primary")
