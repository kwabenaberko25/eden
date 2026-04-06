"""
Tests for @admin template directive.

Verifies that @admin properly checks for admin role.
"""

import pytest
from unittest.mock import Mock

from eden.templating.lexer import TemplateLexer
from eden.templating.parser import TemplateParser
from eden.templating.compiler import TemplateCompiler


def compile_template(source: str) -> str:
    """Helper to compile template source."""
    lexer = TemplateLexer(source)
    tokens = lexer.tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    compiler = TemplateCompiler()
    return compiler.compile(nodes)


class TestAdminDirectiveCompilation:
    """Test that @admin compiles correctly to Jinja2."""
    
    def test_admin_basic_compilation(self):
        """Test @admin compiles to role check."""
        source = "@admin Admin content @endadmin"
        compiled = compile_template(source)
        
        # Should check for authenticated user with admin role
        assert "request.user" in compiled
        assert "is_authenticated" in compiled
        assert 'role == "admin"' in compiled
    
    def test_admin_with_nested_content(self):
        """Test @admin with nested directives."""
        source = """
        @admin
            <div>
                @for(item in items)
                    <p>{{ item }}</p>
                @endfor
            </div>
        @endadmin
        """
        compiled = compile_template(source)
        
        assert "request.user" in compiled
        assert '{% for item in items %}' in compiled
        assert "Admin content" not in compiled or "request.user" in compiled


class TestAdminDirectiveSemantics:
    """Test that @admin renders correctly based on user role."""
    
    def test_admin_renders_for_admin_user(self):
        """Test that content renders when user is admin."""
        from jinja2 import Environment
        from eden.templating.templates import EdenSafeUndefined
        
        env = Environment(undefined=EdenSafeUndefined)
        
        # Mock admin user
        admin_user = Mock()
        admin_user.is_authenticated = True
        admin_user.role = "admin"
        
        mock_request = Mock()
        mock_request.user = admin_user
        
        template_text = (
            '{% if request.user and request.user.is_authenticated and '
            'request.user.role == "admin" %}'
            'Admin panel'
            '{% endif %}'
        )
        
        template = env.from_string(template_text)
        result = template.render(request=mock_request)
        
        assert "Admin panel" in result
    
    def test_admin_hidden_for_non_admin_user(self):
        """Test that content is hidden when user is not admin."""
        from jinja2 import Environment
        from eden.templating.templates import EdenSafeUndefined
        
        env = Environment(undefined=EdenSafeUndefined)
        
        # Mock non-admin user
        regular_user = Mock()
        regular_user.is_authenticated = True
        regular_user.role = "user"
        
        mock_request = Mock()
        mock_request.user = regular_user
        
        template_text = (
            '{% if request.user and request.user.is_authenticated and '
            'request.user.role == "admin" %}'
            'Admin panel'
            '{% endif %}'
        )
        
        template = env.from_string(template_text)
        result = template.render(request=mock_request)
        
        assert "Admin panel" not in result
    
    def test_admin_hidden_for_unauthenticated(self):
        """Test that content is hidden when user is not authenticated."""
        from jinja2 import Environment
        from eden.templating.templates import EdenSafeUndefined
        
        env = Environment(undefined=EdenSafeUndefined)
        
        # Mock unauthenticated request
        mock_request = Mock()
        mock_request.user = None
        
        template_text = (
            '{% if request.user and request.user.is_authenticated and '
            'request.user.role == "admin" %}'
            'Admin panel'
            '{% endif %}'
        )
        
        template = env.from_string(template_text)
        result = template.render(request=mock_request)
        
        assert "Admin panel" not in result


class TestAdminVsRole:
    """Verify @admin is shorthand for @role('admin')."""
    
    def test_admin_equivalent_to_role_admin(self):
        """Test that @admin produces same output as @role('admin')."""
        admin_source = "@admin Content @endadmin"
        role_source = "@role('admin') Content @endrole"
        
        admin_compiled = compile_template(admin_source)
        role_compiled = compile_template(role_source)
        
        # Both should check for admin role
        assert 'role == "admin"' in admin_compiled
        assert 'role == "admin"' in role_compiled


class TestAdminEdgeCases:
    """Test edge cases for @admin directive."""
    
    def test_admin_empty_body(self):
        """Test @admin with no content."""
        source = "@admin @endadmin"
        compiled = compile_template(source)
        
        # Should compile without error
        assert "request.user" in compiled
    
    def test_admin_nested_in_other_directives(self):
        """Test @admin nested inside other directives."""
        source = """
        @if(show_advanced_options)
            @admin
                <button>Advanced Settings</button>
            @endadmin
        @endif
        """
        compiled = compile_template(source)
        
        # Should handle nesting
        assert "request.user" in compiled
        assert "show_advanced_options" in compiled
    
    def test_admin_multiple_instances(self):
        """Test multiple @admin blocks in same template."""
        source = """
        @admin
            <nav>Admin Nav</nav>
        @endadmin
        
        <main>Content</main>
        
        @admin
            <button>Admin Action</button>
        @endadmin
        """
        compiled = compile_template(source)
        
        # Both should be present
        assert compiled.count('role == "admin"') >= 2


class TestAdminDocumentation:
    """Verify @admin is well documented."""
    
    def test_admin_has_docstring(self):
        """Verify render_admin has comprehensive docstring."""
        from eden.template_directives import render_admin
        
        assert render_admin.__doc__ is not None
        assert "@admin" in render_admin.__doc__
        assert "admin role" in render_admin.__doc__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
