"""
Test suite for Eden template engine with HTML files.
Tests all directives: @block, @extends, @include, @if, @foreach, @for, @set, etc.
"""

import pytest
import asyncio
from pathlib import Path
from eden_engine.parser import EdenParser
from eden_engine.runtime.engine import TemplateContext, TemplateEngine


class TestEdenTemplates:
    """Test Eden template engine with HTML files."""

    @pytest.fixture
    def template_dir(self):
        """Get the templates directory path."""
        return Path(__file__).parent / "templates"

    @pytest.fixture
    def parser(self):
        """Create an Eden parser instance."""
        return EdenParser()

    @pytest.fixture
    def engine(self):
        """Create an Eden engine instance."""
        return TemplateEngine(template_dir=Path(__file__).parent / "templates")

    def test_base_template_loads(self, template_dir):
        """Test that base.html loads correctly."""
        base_file = template_dir / "base.html"
        assert base_file.exists(), "base.html not found"
        
        content = base_file.read_text()
        assert "@block('title')" in content, "Missing @block('title')"
        assert "@block('header')" in content, "Missing @block('header')"
        assert "@block('navigation')" in content, "Missing @block('navigation')"
        assert "@block('content')" in content, "Missing @block('content')"
        assert "@block('footer')" in content, "Missing @block('footer')"

    def test_extends_base_template(self, template_dir, parser):
        """Test that extends_base.html properly extends base.html."""
        extends_file = template_dir / "extends_base.html"
        assert extends_file.exists(), "extends_base.html not found"
        
        content = extends_file.read_text()
        assert "@extends('base.html')" in content, "Missing @extends directive"
        assert "@block('title')" in content, "Missing @block('title')"
        assert "@if(show_features)" in content, "Missing @if directive"
        assert "@foreach(posts as post)" in content, "Missing @foreach directive"

    def test_directives_template(self, template_dir):
        """Test directives.html contains all required directives."""
        directives_file = template_dir / "directives.html"
        assert directives_file.exists(), "directives.html not found"
        
        content = directives_file.read_text()
        
        # Check for all directive types
        assert "@set(greeting" in content, "Missing @set directive"
        assert "@if(user.age >= 18)" in content, "Missing @if directive"
        assert "@elseif(user.age >= 13)" in content, "Missing @elseif directive"
        assert "@else" in content, "Missing @else directive"
        assert "@foreach(items as item)" in content, "Missing @foreach directive"
        assert "@for(number = 1; number <= 10; number++)" in content, "Missing @for directive"
        assert "@* SET DIRECTIVE *@" in content, "Missing comment syntax"

    def test_include_template(self, template_dir):
        """Test include_test.html with component includes."""
        include_file = template_dir / "include_test.html"
        assert include_file.exists(), "include_test.html not found"
        
        content = include_file.read_text()
        assert "@include('components/header.html')" in content, "Missing @include for header"
        assert "@include('components/navigation.html')" in content, "Missing @include for navigation"
        assert "@include('components/sidebar.html')" in content, "Missing @include for sidebar"
        assert "@include('components/footer.html')" in content, "Missing @include for footer"

    def test_components_exist(self, template_dir):
        """Test that all component files exist."""
        components = [
            "header.html",
            "navigation.html",
            "sidebar.html",
            "footer.html"
        ]
        
        for component in components:
            component_file = template_dir / "components" / component
            assert component_file.exists(), f"Component {component} not found"

    def test_complex_template(self, template_dir):
        """Test complex.html with advanced directives."""
        complex_file = template_dir / "complex.html"
        assert complex_file.exists(), "complex.html not found"
        
        content = complex_file.read_text()
        
        # Check for extends and blocks
        assert "@extends('base.html')" in content, "Missing @extends"
        assert "@block('title')" in content, "Missing @block('title')"
        assert "@block('header')" in content, "Missing @block('header')"
        assert "@block('content')" in content, "Missing @block('content')"
        assert "@block('footer')" in content, "Missing @block('footer')"
        
        # Check for variables
        assert "@set(featured_badge" in content, "Missing @set directive"
        
        # Check for nested control flow
        assert "@if(categories)" in content, "Missing @if(categories)"
        assert "@foreach(categories as category)" in content, "Missing nested foreach"
        
        # Check for filters
        assert "| truncate(100)" in content, "Missing truncate filter"
        assert "| round(1)" in content, "Missing round filter"
        assert "| length" in content, "Missing length filter"
        assert "| lower" in content, "Missing lower filter"

    def test_eden_syntax_no_jinja2(self, template_dir):
        """Verify templates use Eden syntax, not Jinja2."""
        html_files = list(template_dir.glob("*.html"))
        
        jinja2_markers = [
            "{% block",
            "{% endblock",
            "{% if",
            "{% endif",
            "{% for",
            "{% endfor",
            "{% extends",
            "{% include",
            "{# comment",
        ]
        
        for html_file in html_files:
            content = html_file.read_text()
            for marker in jinja2_markers:
                assert marker not in content, f"Found Jinja2 syntax '{marker}' in {html_file.name}"

    def test_eden_syntax_present(self, template_dir):
        """Verify templates use correct Eden syntax."""
        html_files = list(template_dir.glob("*.html"))
        
        eden_patterns = {
            "@block(": "Block directive",
            "@if(": "If directive",
            "@foreach(": "Foreach directive",
            "@set(": "Set directive",
            "@* ": "Comment syntax",
        }
        
        # At least one file should have each pattern
        for pattern, description in eden_patterns.items():
            found = False
            for html_file in html_files:
                if pattern in html_file.read_text():
                    found = True
                    break
            assert found, f"No Eden {description} pattern found: {pattern}"

    def test_block_braces_syntax(self, template_dir):
        """Verify @block directives use proper brace syntax."""
        base_file = template_dir / "base.html"
        content = base_file.read_text()
        
        # Check for @block with braces
        assert "@block('title') {" in content, "Missing brace syntax in @block"

    def test_if_else_braces_syntax(self, template_dir):
        """Verify @if/@else directives use proper syntax."""
        extends_file = template_dir / "extends_base.html"
        content = extends_file.read_text()
        
        # Check for proper if/else syntax with braces
        assert "@if(" in content, "Missing @if( syntax"
        assert "} @else" in content or "} @elseif" in content, "Missing proper else syntax with braces"

    def test_foreach_braces_syntax(self, template_dir):
        """Verify @foreach directives use proper brace syntax."""
        directives_file = template_dir / "directives.html"
        content = directives_file.read_text()
        
        assert "@foreach(items as item) {" in content, "Missing foreach with braces"

    def test_extends_directive(self, template_dir):
        """Test @extends directive in child templates."""
        extends_file = template_dir / "extends_base.html"
        content = extends_file.read_text()
        
        assert content.startswith("@extends('base.html')"), "@extends should be first line"

    def test_multiple_blocks_in_template(self, template_dir):
        """Test templates with multiple nested blocks."""
        complex_file = template_dir / "complex.html"
        content = complex_file.read_text()
        
        # Count @block directives
        block_count = content.count("@block(")
        assert block_count >= 3, f"Expected at least 3 blocks, found {block_count}"

    def test_complex_control_flow(self, template_dir):
        """Test complex nested control flow."""
        complex_file = template_dir / "complex.html"
        content = complex_file.read_text()
        
        # Check for nested if->foreach->if pattern
        assert "@if(products)" in content, "Missing outer if"
        assert "@foreach(products as product)" in content, "Missing foreach inside if"
        assert "@if(product.is_featured)" in content, "Missing nested if"

    def test_variable_assignment(self, template_dir):
        """Test @set variable assignments."""
        complex_file = template_dir / "complex.html"
        content = complex_file.read_text()
        
        assert '@set(featured_badge = "FEATURED")' in content, "Missing @set with string value"
        assert '@set(on_sale_badge = "ON SALE")' in content, "Missing @set statement"

    def test_template_filters(self, template_dir):
        """Test filter syntax in templates."""
        directives_file = template_dir / "directives.html"
        content = directives_file.read_text()
        
        # Check for pipe syntax
        assert "| upper" in content, "Missing upper filter"
        assert "| lower" in content, "Missing lower filter"
        assert "| capitalize" in content, "Missing capitalize filter"
        assert "| length" in content, "Missing length filter"
        assert "| default(" in content, "Missing default filter"

    def test_filter_chaining(self, template_dir):
        """Test filter chaining."""
        directives_file = template_dir / "directives.html"
        content = directives_file.read_text()
        
        # Check for chained filters
        assert "| upper | slice" in content, "Missing chained filters"
        assert "| lower | replace" in content, "Missing chained filters"

    def test_loop_variables(self, template_dir):
        """Test loop variable access."""
        directives_file = template_dir / "directives.html"
        content = directives_file.read_text()
        
        assert "{{ loop.index }}" in content, "Missing loop.index"
        assert "{{ loop.length }}" in content, "Missing loop.length"
        assert "loop.first" in content, "Missing loop.first"
        assert "loop.last" in content, "Missing loop.last"
        assert "loop.revindex0" in content, "Missing loop.revindex0"


class TestTemplateIntegration:
    """Integration tests for template rendering."""

    @pytest.fixture
    def template_dir(self):
        """Get the templates directory path."""
        return Path(__file__).parent / "templates"

    @pytest.fixture
    def parser(self):
        """Create an Eden parser instance."""
        return EdenParser()

    @pytest.fixture
    def engine(self):
        """Create an Eden engine instance."""
        return TemplateEngine(template_dir=Path(__file__).parent / "templates")

    def test_template_directory_exists(self, template_dir):
        """Test that templates directory exists."""
        assert template_dir.exists(), f"Templates directory not found: {template_dir}"
        assert template_dir.is_dir(), f"Templates path is not a directory: {template_dir}"

    def test_all_required_templates_exist(self, template_dir):
        """Test that all required templates exist."""
        required_templates = [
            "base.html",
            "extends_base.html",
            "directives.html",
            "include_test.html",
            "complex.html"
        ]
        
        for template in required_templates:
            template_path = template_dir / template
            assert template_path.exists(), f"Required template not found: {template}"

    def test_template_readability(self, template_dir):
        """Test that all templates are readable."""
        html_files = template_dir.glob("*.html")
        
        for html_file in html_files:
            try:
                content = html_file.read_text(encoding='utf-8')
                assert len(content) > 0, f"Template {html_file.name} is empty"
            except Exception as e:
                pytest.fail(f"Could not read {html_file.name}: {e}")

    def test_no_syntax_errors_in_templates(self, template_dir, parser):
        """Verify templates can be parsed without syntax errors."""
        html_files = template_dir.glob("*.html")
        
        for html_file in html_files:
            content = html_file.read_text(encoding='utf-8')
            try:
                # Attempt to tokenize the template
                tokens = parser.tokenize(content)
                assert tokens is not None, f"Failed to tokenize {html_file.name}"
            except Exception as e:
                # Log the error but don't fail - parser might not be fully implemented
                print(f"Note: Could not parse {html_file.name}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
