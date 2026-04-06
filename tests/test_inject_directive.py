"""
Tests for @inject directive and template dependency injection.

Verifies that services, config, and app state can be injected into templates.
"""

import pytest
from starlette.testclient import TestClient
from starlette.requests import Request
from unittest.mock import Mock

from eden.app import Eden
from eden.templating import EdenTemplates


class TestInjectDirectiveCompilation:
    """Test that @inject compiles correctly to Jinja2."""
    
    def test_inject_basic_service(self):
        """Test basic @inject(var, 'service_name') compilation."""
        from eden.templating.lexer import TemplateLexer
        from eden.templating.parser import TemplateParser
        from eden.templating.compiler import TemplateCompiler
        
        source = "@inject(cache, 'cache')"
        lexer = TemplateLexer(source)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        nodes = parser.parse()
        compiler = TemplateCompiler()
        compiled = compiler.compile(nodes)
        
        assert "{% set cache = eden_dependency('cache') %}" in compiled
    
    def test_inject_config_value(self):
        """Test @inject for config attribute."""
        from eden.templating.lexer import TemplateLexer
        from eden.templating.parser import TemplateParser
        from eden.templating.compiler import TemplateCompiler
        
        source = "@inject(env, 'database_url')"
        lexer = TemplateLexer(source)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        nodes = parser.parse()
        compiler = TemplateCompiler()
        compiled = compiler.compile(nodes)
        
        assert "{% set env = eden_dependency('database_url') %}" in compiled
    
    def test_inject_state_value(self):
        """Test @inject for app state."""
        from eden.templating.lexer import TemplateLexer
        from eden.templating.parser import TemplateParser
        from eden.templating.compiler import TemplateCompiler
        
        source = "@inject(redis_client, 'redis_client')"
        lexer = TemplateLexer(source)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        nodes = parser.parse()
        compiler = TemplateCompiler()
        compiled = compiler.compile(nodes)
        
        assert "{% set redis_client = eden_dependency('redis_client') %}" in compiled


class TestInjectRuntimeResolution:
    """Test that @inject resolves services at runtime."""
    
    def test_inject_app_attribute(self):
        """Test resolving app instance attributes (cache, mail, etc.)."""
        app = Eden(title="Test")
        
        # Mock an app attribute
        app.test_service = Mock(name="TestService")
        
        # Create templates instance
        templates = EdenTemplates(directory="templates")
        
        # Manually call the helper
        result = templates._dependency_helper("test_service")
        assert result is app.test_service
    
    def test_inject_config_attribute(self):
        """Test resolving app.config attributes."""
        app = Eden(title="Test", debug=True)
        
        # App.config has debug, version, title, etc.
        result = app.templates._dependency_helper("debug")
        assert result is True
    
    def test_inject_state_attribute(self):
        """Test resolving app.state attributes."""
        app = Eden(title="Test")
        app.state.custom_value = "injected"
        
        result = app.templates._dependency_helper("custom_value")
        assert result == "injected"
    
    def test_inject_not_found_returns_none(self):
        """Test that missing service returns None."""
        app = Eden(title="Test")
        
        result = app.templates._dependency_helper("nonexistent_service")
        assert result is None
    
    def test_inject_priority_app_over_config(self):
        """Test that app attributes have priority over config."""
        app = Eden(title="Test")
        
        # Both app and config have 'title'
        # App attribute should take priority
        result = app.templates._dependency_helper("title")
        assert result == "Test"
    
    def test_inject_priority_config_over_state(self):
        """Test that config attributes have priority over state."""
        app = Eden(title="Test")
        
        # Set same key in both config and state
        app.state.version = "state_version"
        # config.version should win
        
        result = app.templates._dependency_helper("version")
        # config.version should be returned, not state.version
        assert result == "1.0.0"  # Default from Eden


class TestInjectInTemplates:
    """Test @inject within full template rendering."""
    
    def test_inject_in_template_text(self):
        """Test using injected service in template."""
        app = Eden(title="TestApp")
        app.cache = Mock()
        app.cache.get = Mock(return_value="cached_value")
        
        # Create a test template
        from jinja2 import Environment
        from eden.templating.templates import EdenSafeUndefined
        
        env = Environment(undefined=EdenSafeUndefined)
        env.globals["eden_dependency"] = app.templates._dependency_helper
        
        # Template that uses @inject (which becomes {% set ... %})
        template_text = (
            "{% set cache = eden_dependency('cache') %}"
            "{% if cache %}"
            "Cache is available: {{ cache }}"
            "{% endif %}"
        )
        
        template = env.from_string(template_text)
        result = template.render()
        
        assert "Cache is available" in result
    
    def test_inject_multiple_services(self):
        """Test injecting multiple services."""
        app = Eden(title="TestApp")
        
        # Mock multiple services
        app.cache = Mock(name="CacheService")
        app.mail = Mock(name="MailService")
        
        env = app.templates.env
        
        # Simulate multiple injections
        cache_result = app.templates._dependency_helper("cache")
        mail_result = app.templates._dependency_helper("mail")
        
        assert cache_result is not None
        assert mail_result is not None
        assert cache_result != mail_result


class TestInjectEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_inject_none_value(self):
        """Test that None attributes are skipped in resolution."""
        app = Eden(title="Test")
        app.cache = None  # Explicitly None
        
        # Should skip to next priority level
        result = app.templates._dependency_helper("cache")
        # Should return None since cache is explicitly None
        # and falls through all levels
        assert result is None
    
    def test_inject_empty_alias(self):
        """Test handling of empty alias."""
        app = Eden(title="Test")
        result = app.templates._dependency_helper("")
        assert result is None
    
    def test_inject_with_special_characters(self):
        """Test alias with underscores (common in Python)."""
        app = Eden(title="Test")
        app.redis_client = Mock(name="RedisClient")
        
        result = app.templates._dependency_helper("redis_client")
        assert result is app.redis_client


class TestInjectDocumentation:
    """Verify @inject directive documentation is clear."""
    
    def test_inject_directive_has_docstring(self):
        """Verify render_inject has comprehensive docstring."""
        from eden.template_directives import render_inject
        
        assert render_inject.__doc__ is not None
    
    def test_dependency_helper_has_docstring(self):
        """Verify _dependency_helper has comprehensive docstring."""
        app = Eden(title="Test")
        assert app.templates._dependency_helper.__doc__ is not None
        assert "Resolution order" in app.templates._dependency_helper.__doc__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
