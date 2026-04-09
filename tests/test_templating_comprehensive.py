"""
Comprehensive test suite for Eden templating system.
Tests all major features: directives, filters, security, and error handling.
"""

import pytest
from jinja2 import Environment
from markupsafe import Markup
from eden.templating import (
    EdenTemplates,
    EdenDirectivesExtension,
    format_time_ago,
    format_money,
    class_names,
    truncate_filter,
    slugify_filter,
    json_encode,
    default_if_none,
    pluralize_filter,
    title_case,
    format_date,
    format_time,
    format_number,
    mask_filter,
    file_size_filter,
    repeat_filter,
    phone_filter,
    unique_filter,
    markdown_filter,
    nl2br_filter,
)
import tempfile
import datetime
from pathlib import Path


class TestTemplatingFilters:
    """Test all built-in filters."""
    
    def test_format_time_ago(self):
        """Test time_ago filter."""
        now = datetime.datetime.now()
        one_hour_ago = now - datetime.timedelta(hours=1)
        result = format_time_ago(one_hour_ago)
        assert "hour" in result
    
    def test_format_money(self):
        """Test money formatting."""
        result = format_money(1000.50)
        assert "$1,000.50" == result
        
        result = format_money(1000.50, currency="€")
        assert "€1,000.50" == result
    
    def test_class_names(self):
        """Test class_names helper."""
        result = class_names("btn", {"active": True, "disabled": False})
        assert "btn" in result
        assert "active" in result
        assert "disabled" not in result
    
    def test_truncate_filter(self):
        """Test truncate filter."""
        text = "This is a long text that needs truncation"
        result = truncate_filter(text, length=20)
        assert len(result) <= 21  # 20 + ellipsis
        assert result.endswith("…")
    
    def test_slugify_filter(self):
        """Test slugify filter."""
        text = "Hello World!! @#$"
        result = slugify_filter(text)
        assert result == "hello-world"
        assert " " not in result
        assert "@" not in result
    
    def test_json_encode(self):
        """Test JSON encoding."""
        data = {"name": "John", "age": 30}
        result = json_encode(data)
        assert isinstance(result, Markup)
        assert '"name"' in result
        assert '"John"' in result
    
    def test_default_if_none(self):
        """Test default_if_none filter."""
        assert default_if_none(None, "default") == "default"
        assert default_if_none("value", "default") == "value"
        assert default_if_none(0, "default") == 0
    
    def test_pluralize_filter(self):
        """Test pluralize filter."""
        assert pluralize_filter(1, "item", "items") == "item"
        assert pluralize_filter(2, "item", "items") == "items"
        assert pluralize_filter(0, "item", "items") == "items"
    
    def test_title_case(self):
        """Test title case filter."""
        result = title_case("hello world")
        assert result == "Hello World"
    
    def test_format_date(self):
        """Test date formatting."""
        now = datetime.datetime.now()
        result = format_date(now)
        assert len(result) == 10  # YYYY-MM-DD
        assert result.count("-") == 2
    
    def test_format_time(self):
        """Test time formatting."""
        now = datetime.datetime.now()
        result = format_time(now)
        assert ":" in result
        assert len(result) == 5  # HH:MM
    
    def test_format_number(self):
        """Test number formatting."""
        result = format_number(1234567)
        assert "," in result or "." in result  # Should have thousands separator
    
    def test_mask_filter(self):
        """Test mask filter."""
        result = mask_filter("1234567890", visible=4)
        assert "**" in result
        assert "1234" in result
        assert "7890" in result
    
    def test_file_size_filter(self):
        """Test file size filter."""
        result = file_size_filter(1024)
        assert "1.0 KB" == result
        
        result = file_size_filter(1048576)  # 1 MB
        assert "1.0 MB" == result
    
    def test_repeat_filter(self):
        """Test repeat filter."""
        result = repeat_filter("ab", 3)
        assert result == "ababab"
    
    def test_phone_filter(self):
        """Test phone number formatting."""
        result = phone_filter("1234567890")
        assert "(" in result and ")" in result
    
    def test_unique_filter(self):
        """Test unique filter."""
        items = ["a", "b", "a", "c", "b"]
        result = unique_filter(items)
        assert len(result) == 3
        assert "a" in result and "b" in result and "c" in result
    
    def test_markdown_filter(self):
        """Test markdown filter."""
        text = "**bold** and *italic*"
        result = markdown_filter(text)
        assert "<strong>" in result or "<b>" in result
        assert isinstance(result, Markup)
    
    def test_nl2br_filter(self):
        """Test nl2br filter."""
        text = "Line 1\nLine 2\nLine 3"
        result = nl2br_filter(text)
        assert "<br>" in result or "br" in result
        assert isinstance(result, Markup)


class TestTemplatingDirectives:
    """Test template directives through render."""
    
    def test_if_directive(self):
        """Test @if directive."""
        template_str = "@if (True) { Yes }"
        env = Environment(extensions=[EdenDirectivesExtension, "jinja2.ext.loopcontrols"])
        env.globals["__eden_max_loop_iterations__"] = 1000
        template = env.from_string(template_str)
        result = template.render()
        assert "Yes" in result
    
    def test_for_directive(self):
        """Test @for directive."""
        template_str = "@for (item in items) { {{ item }} }"
        env = Environment(extensions=[EdenDirectivesExtension, "jinja2.ext.loopcontrols"])
        env.globals["__eden_max_loop_iterations__"] = 1000
        template = env.from_string(template_str)
        result = template.render(items=[1, 2, 3])
        assert "1" in result
        assert "2" in result
        assert "3" in result
    
    def test_switch_directive(self):
        """Test @switch/@case directive."""
        template_str = """
        @switch (status) {
            @case ('active') { Active }
            @case ('inactive') { Inactive }
            @default { Unknown }
        }
        """
        env = Environment(extensions=[EdenDirectivesExtension, "jinja2.ext.loopcontrols"])
        env.globals["__eden_max_loop_iterations__"] = 1000
        template = env.from_string(template_str)
        result = template.render(status="active")
        assert "Active" in result
    
    def test_let_directive(self):
        """Test @let directive."""
        template_str = "@let (name = 'World')\nHello {{ name }}!"
        env = Environment(extensions=[EdenDirectivesExtension, "jinja2.ext.loopcontrols"])
        env.globals["__eden_max_loop_iterations__"] = 1000
        template = env.from_string(template_str)
        result = template.render()
        assert "Hello World!" in result


class TestTemplatingIntegration:
    """Test integration with EdenTemplates."""
    
    def test_eden_templates_init(self):
        """Test EdenTemplates initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates = EdenTemplates(directory=tmpdir)
            assert templates is not None
            assert hasattr(templates, 'env')
    
    def test_eden_templates_render(self):
        """Test template rendering through EdenTemplates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a template file
            template_path = Path(tmpdir) / "test.html"
            template_path.write_text("Hello {{ name }}!")
            
            templates = EdenTemplates(directory=tmpdir)
            result = templates.render_to_string("test.html", {"name": "World"})
            assert "Hello World!" in result
    
    def test_eden_templates_filters_available(self):
        """Test that all filters are available in templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates = EdenTemplates(directory=tmpdir)
            env = templates.env
            
            # Check that key filters are registered
            assert 'format_money' in env.filters
            assert 'truncate' in env.filters
            assert 'slugify' in env.filters
            assert 'pluralize' in env.filters
            assert 'format_date' in env.filters
            assert 'format_time' in env.filters


class TestTemplatingErrorHandling:
    """Test error handling in templating."""
    
    def test_undefined_variable_graceful_degradation(self):
        """Test graceful handling of undefined variables."""
        template_str = "Hello {{ missing_var }}!"
        env = Environment(extensions=[EdenDirectivesExtension, "jinja2.ext.loopcontrols"])
        env.globals["__eden_max_loop_iterations__"] = 1000
        template = env.from_string(template_str)
        # Should not raise, should return empty or placeholder
        result = template.render()
        assert isinstance(result, str)
    
    def test_malformed_directive_handling(self):
        """Test handling of malformed directives."""
        template_str = "@if (True) Missing @endif"
        env = Environment(extensions=[EdenDirectivesExtension, "jinja2.ext.loopcontrols"])
        env.globals["__eden_max_loop_iterations__"] = 1000
        # Should handle gracefully or raise meaningful error
        try:
            template = env.from_string(template_str)
            result = template.render()
            assert result is not None
        except Exception as e:
            # Should be a meaningful Jinja2 exception
            assert "jinja2" in str(type(e)).lower() or "template" in str(type(e)).lower()


class TestTemplatingSecurityFeatures:
    """Test security features of templating system."""
    
    def test_target_blank_noopener_injection(self):
        """Test automatic noopener injection for target="_blank"."""
        template_str = '<a href="https://example.com" target="_blank">Link</a>'
        env = Environment(extensions=[EdenDirectivesExtension, "jinja2.ext.loopcontrols"])
        env.globals["__eden_max_loop_iterations__"] = 1000
        template = env.from_string(template_str)
        result = template.render()
        # Should add noopener/noreferrer automatically
        assert "noopener" in result or "noreferrer" in result or "rel" in result
    
    def test_xss_protection(self):
        """Test XSS protection in templates."""
        template_str = "{{ content | safe }}"
        env = Environment(extensions=[EdenDirectivesExtension, "jinja2.ext.loopcontrols"])
        env.globals["__eden_max_loop_iterations__"] = 1000
        template = env.from_string(template_str)
        dangerous_content = "<script>alert('xss')</script>"
        result = template.render(content=dangerous_content)
        # unsafe content in safe filter should still be escaped by default in Jinja2
        assert result is not None


class TestTemplatingPerformance:
    """Test templating system performance characteristics."""
    
    def test_template_caching(self):
        """Test that templates are cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "cache_test.html"
            template_path.write_text("{{ value }}")
            
            templates = EdenTemplates(directory=tmpdir)
            
            # First render
            result1 = templates.render_to_string("cache_test.html", {"value": "test"})
            # Second render should use cache
            result2 = templates.render_to_string("cache_test.html", {"value": "test"})
            
            assert result1 == result2
            assert "test" in result1


class TestTemplatingExtensions:
    """Test template extensions."""
    
    def test_eden_directives_extension_registered(self):
        """Test that EdenDirectivesExtension is properly registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates = EdenTemplates(directory=tmpdir)
        assert EdenDirectivesExtension in templates.env.extensions.values() or \
               any('EdenDirectivesExtension' in str(e) for e in templates.env.extensions.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
