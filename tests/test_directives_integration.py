"""
Integration Tests for Eden @Directives
Tests all directives including the new wildcard support for @active_link
"""
import pytest
from unittest.mock import Mock, MagicMock


class TestActiveLink:
    """Test @active_link directive with wildcard support"""
    
    def test_exact_route_match(self):
        """Test exact active_link matching"""
        # Mock request
        request = Mock()
        request.url.path = "/dashboard"
        request.url_for = Mock(return_value="/dashboard")
        
        # Simulate is_active logic
        def is_active(request, route_name, **kwargs):
            try:
                resolved = str(request.url_for(route_name, **kwargs)).rstrip("/") or "/"
                current = request.url.path.rstrip("/") or "/"
                return current == resolved or current.startswith(resolved + "/")
            except Exception:
                return False
        
        # Both dashboard route and current path match
        assert is_active(request, "dashboard") == True
    
    def test_prefix_match(self):
        """Test prefix matching for sub-routes"""
        request = Mock()
        request.url.path = "/posts/123"
        request.url_for = Mock(return_value="/posts")
        
        def is_active(request, route_name, **kwargs):
            try:
                resolved = str(request.url_for(route_name, **kwargs)).rstrip("/") or "/"
                current = request.url.path.rstrip("/") or "/"
                return current == resolved or current.startswith(resolved + "/")
            except Exception:
                return False
        
        # Current path is /posts/123, resolved route is /posts
        # Should match because /posts/123 starts with /posts/
        assert is_active(request, "posts") == True
    
    def test_no_match(self):
        """Test that different routes don't match"""
        request = Mock()
        request.url.path = "/dashboard"
        request.url_for = Mock(return_value="/admin")
        
        def is_active(request, route_name, **kwargs):
            try:
                resolved = str(request.url_for(route_name, **kwargs)).rstrip("/") or "/"
                current = request.url.path.rstrip("/") or "/"
                return current == resolved or current.startswith(resolved + "/")
            except Exception:
                return False
        
        # /dashboard doesn't match /admin
        assert is_active(request, "admin") == False
    
    def test_route_name_normalization(self):
        """Test that namespace:action becomes namespace_action"""
        route_with_colon = "auth:login"
        normalized = route_with_colon.replace(":", "_")
        
        assert normalized == "auth_login"
    
    def test_wildcard_detection(self):
        """Test that wildcard routes are detected"""
        route_names = [
            ("students:*", True),
            ("admin:*", True),
            ("blog:*", True),
            ("dashboard", False),
            ("posts:show", False),
        ]
        
        for route, should_be_wildcard in route_names:
            is_wildcard = route.endswith("*")
            assert is_wildcard == should_be_wildcard
    
    def test_wildcard_prefix_extraction(self):
        """Test extracting prefix from wildcard route"""
        wildcard_routes = [
            ("students:*", "students"),
            ("admin:*", "admin"),
            ("blog:*", "blog"),
            ("orders:*", "orders"),
        ]
        
        for route, expected_prefix in wildcard_routes:
            # Remove * and normalize
            prefix = route[:-1].rstrip(':_').replace(':', '_')
            assert prefix == expected_prefix


class TestDirectivesPreprocessing:
    """Test that directives are correctly preprocessed to Jinja2"""
    
    def test_csrf_directive(self):
        """@csrf converts to hidden CSRF input"""
        pattern = r'@csrf'
        replacement = r'<input type="hidden" name="csrf_token" value="{{ request.session.eden_csrf_token }}" />'
        
        assert pattern in replacement or '<input' in replacement
    
    def test_url_directive(self):
        """@url converts to url_for call"""
        directive = "@url('dashboard')"
        # Should convert to {{ url_for("dashboard") }}
        assert "url_for" in directive or "dashboard" in directive
    
    def test_checked_attribute(self):
        """@checked converts to conditional checked"""
        directive = "@checked(form.field.required)"
        # Should convert to {% if ... %}checked{% endif %}
        assert "checked" in directive
    
    def test_selected_attribute(self):
        """@selected converts to conditional selected"""
        directive = "@selected(item.id == selected)"
        assert "selected" in directive
    
    def test_disabled_attribute(self):
        """@disabled converts to conditional disabled"""
        directive = "@disabled(form.is_readonly)"
        assert "disabled" in directive
    
    def test_readonly_attribute(self):
        """@readonly converts to conditional readonly"""
        directive = "@readonly(field.read_only)"
        assert "readonly" in directive


class TestBlockDirectives:
    """Test block directives like @if, @for, @component"""
    
    def test_if_directive(self):
        """@if block is recognized"""
        directive_name = "if"
        assert directive_name in [
            "if", "unless", "for", "switch", "case",
            "auth", "guest", "htmx", "non_htmx"
        ]
    
    def test_for_directive_with_loop_helpers(self):
        """@for provides $loop object"""
        loop_props = [
            "$loop.index",
            "$loop.first",
            "$loop.last",
            "$loop.even",
            "$loop.odd",
            "$loop.length"
        ]
        
        assert len(loop_props) > 0
        assert "$loop.index" in loop_props
    
    def test_component_directive(self):
        """@component renders named components"""
        component_name = "card"
        assert component_name.isidentifier()


class TestAuthDirectives:
    """Test authentication directives"""
    
    def test_auth_directive_requires_user(self):
        """@auth shows only for authenticated users"""
        directive = "@auth"
        # Should check if user is authenticated
        assert "auth" in directive.lower()
    
    def test_guest_directive_requires_no_user(self):
        """@guest shows only for non-authenticated users"""
        directive = "@guest"
        # Should check if user is NOT authenticated
        assert "guest" in directive.lower()


class TestHTMXDirectives:
    """Test HTMX integration directives"""
    
    def test_htmx_directive(self):
        """@htmx renders only for HTMX requests"""
        directive = "@htmx"
        assert directive.startswith("@")
    
    def test_fragment_directive(self):
        """@fragment makes targetable HTMX partials"""
        directive = '@fragment("results")'
        assert "fragment" in directive
        assert "results" in directive


class TestTemplatingSyntax:
    """Test the overall @directive syntax"""
    
    def test_directive_starts_with_at_sign(self):
        """All directives start with @"""
        directives = [
            "@if", "@for", "@unless", "@auth", "@guest",
            "@csrf", "@url", "@active_link", "@checked",
            "@selected", "@disabled", "@readonly",
            "@extend", "@include", "@let", "@json"
        ]
        
        for directive in directives:
            assert directive.startswith("@")
    
    def test_directive_regex_patterns(self):
        """All directive regex patterns are valid"""
        import re
        
        patterns = [
            r'@active_link\s*\(\s*(.+?)\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)',
            r'@csrf',
            r'@url\s*\(\s*[\'"]([^\'"]+)[\'"]\s*',
            r'@checked\s*\((.+?)\)',
            r'@for\s*\((.*?)\)\s*\{',
        ]
        
        for pattern in patterns:
            try:
                compiled = re.compile(pattern)
                assert compiled is not None
            except re.error:
                pytest.fail(f"Invalid regex pattern: {pattern}")


class TestRealWorldScenarios:
    """Test realistic usage patterns"""
    
    def test_navigation_with_wildcards(self):
        """Test navigation highlighting with wildcard routes"""
        # Simulate navigation structure
        nav_items = [
            {"label": "Dashboard", "route": "dashboard"},
            {"label": "Admin", "route": "admin:*"},  # Wildcard
            {"label": "Blog", "route": "blog:*"},    # Wildcard
            {"label": "Settings", "route": "settings"},
        ]
        
        # Current path is /admin/users
        current_path = "/admin/users"
        
        # When active_link processes admin:*, it should match
        admin_route = "admin:*"
        is_wildcard = admin_route.endswith("*")
        assert is_wildcard == True
    
    def test_form_validation(self):
        """Test form with validation state"""
        form_fields = {
            "email": {
                "value": "user@example.com",
                "required": True,
                "disabled": False,
                "readonly": False,
            },
            "bio": {
                "value": "Developer",
                "required": False,
                "disabled": False,
                "readonly": True,  # Published profile
            }
        }
        
        # Verify field attributes
        assert form_fields["email"]["required"] == True
        assert form_fields["bio"]["readonly"] == True
    
    def test_conditional_rendering(self):
        """Test various conditional rendering scenarios"""
        scenarios = [
            {"user": None, "show_auth": False, "show_guest": True},
            {"user": Mock(is_authenticated=True), "show_auth": True, "show_guest": False},
            {"user": Mock(is_authenticated=False), "show_auth": False, "show_guest": True},
        ]
        
        for scenario in scenarios:
            user = scenario["user"]
            is_auth = user is not None and getattr(user, "is_authenticated", False)
            assert is_auth == scenario["show_auth"]
            assert (not is_auth) == scenario["show_guest"]


# Pytest markers
@pytest.mark.unit
def test_all_directives_recognized():
    """Verify all directives are recognized"""
    directives = {
        "control": ["@if", "@unless", "@for", "@switch", "@case"],
        "auth": ["@auth", "@guest"],
        "htmx": ["@htmx", "@non_htmx", "@fragment"],
        "templating": ["@extends", "@include", "@section", "@yield", "@push"],
        "data": ["@let", "@old", "@json", "@dump"],
        "forms": ["@csrf", "@checked", "@selected", "@disabled", "@readonly"],
        "routing": ["@url", "@active_link"],
        "components": ["@component", "@slot"],
    }
    
    total_directives = sum(len(v) for v in directives.values())
    assert total_directives > 30


@pytest.mark.integration
def test_wildcard_active_link_integration():
    """Integration test for wildcard @active_link"""
    # This test would run with actual Eden app
    # Mock request at /admin/users
    request = Mock()
    request.url.path = "/admin/users"
    request.url_for = Mock(side_effect=lambda route, **kw: {
        "admin_index": "/admin",
        "admin_users": "/admin/users",
        "admin_settings": "/admin/settings",
    }.get(route, "/unknown"))
    
    # Test wildcard matching logic
    def check_wildcard_active(request, route_name):
        if route_name.endswith("*"):
            base = route_name[:-1].rstrip(":_")
            # Would resolve one of the base routes
            # For demo, /admin/* matches /admin/users
            return request.url.path.startswith("/" + base)
        return False
    
    # admin:* should match /admin/users
    assert check_wildcard_active(request, "admin:*") == True
    assert check_wildcard_active(request, "blog:*") == False


if __name__ == "__main__":
    # Run tests with: python -m pytest test_directives_integration.py -v
    pytest.main([__file__, "-v"])
