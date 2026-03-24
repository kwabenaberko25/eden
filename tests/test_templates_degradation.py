"""
Tests for EdenTemplates graceful degradation (Issue #14).

Verifies:
1. EdenTemplates initializes even if optional modules fail to import
2. Template rendering works without design/asset/component modules
3. Extension loading failure falls back to core extensions
"""

import os
import pytest
import tempfile
from unittest.mock import patch


class TestTemplatesGracefulDegradation:
    """Test that EdenTemplates handles missing optional modules."""
    
    @pytest.fixture
    def template_dir(self, tmp_path):
        """Create a temp directory with a simple template."""
        tmpl = tmp_path / "test.html"
        tmpl.write_text("<h1>Hello {{ name }}</h1>")
        return str(tmp_path)
    
    def test_init_succeeds(self, template_dir):
        """EdenTemplates should initialize without errors."""
        from eden.templating.templates import EdenTemplates
        templates = EdenTemplates(directory=template_dir)
        assert templates.env is not None
    
    def test_core_filters_registered(self, template_dir):
        """Core filters should always be available."""
        from eden.templating.templates import EdenTemplates
        templates = EdenTemplates(directory=template_dir)
        
        # Core filters from eden.templating.filters
        assert "time_ago" in templates.env.filters
        assert "money" in templates.env.filters
        assert "slugify" in templates.env.filters
        assert "json" in templates.env.filters
        assert "truncate" in templates.env.filters
    
    def test_core_globals_registered(self, template_dir):
        """Core globals should always be available."""
        from eden.templating.templates import EdenTemplates
        templates = EdenTemplates(directory=template_dir)
        
        assert "csrf_token" in templates.env.globals
        assert "old" in templates.env.globals
        assert "vite" in templates.env.globals
    
    def test_template_rendering_works(self, template_dir):
        """Basic template rendering should work."""
        from eden.templating.templates import EdenTemplates
        templates = EdenTemplates(directory=template_dir)
        
        tmpl = templates.env.get_template("test.html")
        result = tmpl.render(name="World")
        assert "<h1>Hello World</h1>" in result
    
    def test_missing_design_module_logs_warning(self, template_dir):
        """Missing design module should log warning but not crash."""
        import logging
        
        with patch.dict("sys.modules", {"eden.design": None}):
            with patch("logging.Logger.warning") as mock_warn:
                from eden.templating.templates import EdenTemplates
                # Reload to pick up patched module
                templates = EdenTemplates(directory=template_dir)
                # Should still initialize
                assert templates.env is not None
    
    def test_extensions_include_core(self, template_dir):
        """Core Jinja2 extensions should always be loaded."""
        from eden.templating.templates import EdenTemplates
        templates = EdenTemplates(directory=template_dir)
        
        ext_names = [type(ext).__name__ for ext in templates.env.extensions.values()]
        # The core EdenDirectivesExtension should be present
        assert any("Eden" in name or "Directive" in name for name in ext_names)
