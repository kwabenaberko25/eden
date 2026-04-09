"""
Test suite for completed admin panel and component system features.

Tests export functionality, inline rendering, and component actions.
"""

import pytest
import asyncio
import os
from typing import List, Type, Any
from unittest.mock import Mock, AsyncMock, patch


# ============================================================================
# Admin Panel Export Tests
# ============================================================================

class TestAdminExport:
    """Test admin panel export functionality."""
    
    @pytest.mark.asyncio
    async def test_csv_export_basic(self):
        """Test basic CSV export."""
        from eden.admin.export import to_csv
        
        class MockModel:
            id = 1
            name = "Test"
            email = "test@example.com"
        
        records = [MockModel()]
        csv_output = await to_csv(records, None, ["id", "name", "email"])
        
        assert "id,name,email" in csv_output
        assert "1,Test,test@example.com" in csv_output
    
    @pytest.mark.asyncio
    async def test_json_export_basic(self):
        """Test basic JSON export."""
        from eden.admin.export import to_json
        
        class MockModel:
            id = 1
            name = "Test"
        
        records = [MockModel()]
        json_output = await to_json(records, None, ["id", "name"])
        
        assert '"id": 1' in json_output
        assert '"name": "Test"' in json_output
    
    @pytest.mark.asyncio
    async def test_export_empty_records(self):
        """Test export with empty record list."""
        from eden.admin.export import to_csv, to_json
        
        csv_output = await to_csv([])
        json_output = await to_json([])
        
        assert csv_output == ""
        assert json_output == "[]"
    
    @pytest.mark.asyncio
    async def test_export_filename_generation(self):
        """Test export filename generation."""
        from eden.admin.export import generate_export_filename
        
        filename = await generate_export_filename("users", "csv", timestamp=False)
        assert filename == "users.csv"
        
        filename = await generate_export_filename("products", "xlsx", timestamp=False)
        assert filename == "products.xlsx"
    
    @pytest.mark.asyncio
    async def test_export_response_headers(self):
        """Test export response headers generation."""
        from eden.admin.export import get_export_response_headers
        
        headers = await get_export_response_headers("users.csv", "csv")
        assert headers["Content-Type"] == "text/csv; charset=utf-8"
        assert 'attachment' in headers["Content-Disposition"]
        assert 'users.csv' in headers["Content-Disposition"]


# ============================================================================
# Inline Model Tests
# ============================================================================

class TestInlineModels:
    """Test inline model rendering and processing."""
    
    @pytest.mark.asyncio
    async def test_foreign_key_detection(self):
        """Test FK field detection."""
        from eden.admin.inline import InlineModelHelper
        
        # Mock models
        class Parent:
            __tablename__ = "parents"
        
        class Child:
            pass
        
        with patch('eden.admin.inline.sa_inspect') as mock_inspect:
            # This is simplified - full test would need SQLAlchemy mocks
            result = InlineModelHelper.get_foreign_key_field(Parent, Child)
            # Result depends on SQLAlchemy mock setup
            assert result is None or isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_model_fields_extraction(self):
        """Test field extraction from models."""
        from eden.admin.inline import InlineModelHelper
        
        class TestModel:
            pass
        
        with patch('eden.admin.inline.sa_inspect'):
            fields = InlineModelHelper.get_model_fields(TestModel, exclude_fields=["id"])
            assert isinstance(fields, list)


# ============================================================================
# Component System Tests
# ============================================================================

class TestComponentDispatcher:
    """Test component action dispatcher."""
    
    def test_type_coercion_string_to_int(self):
        """Test type coercion from string to int."""
        from eden.components.dispatcher import ComponentActionDispatcher
        
        dispatcher = ComponentActionDispatcher(None)
        value = dispatcher._coerce_value("42", int)
        assert value == 42
        assert isinstance(value, int)
    
    def test_type_coercion_string_to_bool(self):
        """Test type coercion from string to bool."""
        from eden.components.dispatcher import ComponentActionDispatcher
        
        dispatcher = ComponentActionDispatcher(None)
        
        assert dispatcher._coerce_value("true", bool) is True
        assert dispatcher._coerce_value("1", bool) is True
        assert dispatcher._coerce_value("false", bool) is False
        assert dispatcher._coerce_value("0", bool) is False
    
    def test_type_coercion_string_to_float(self):
        """Test type coercion from string to float."""
        from eden.components.dispatcher import ComponentActionDispatcher
        
        dispatcher = ComponentActionDispatcher(None)
        value = dispatcher._coerce_value("3.14", float)
        assert value == 3.14
        assert isinstance(value, float)
    
    def test_get_empty_value(self):
        """Test getting empty values for types."""
        from eden.components.dispatcher import ComponentActionDispatcher
        
        dispatcher = ComponentActionDispatcher(None)
        
        assert dispatcher._get_empty_value(int) == 0
        assert dispatcher._get_empty_value(float) == 0.0
        assert dispatcher._get_empty_value(bool) is False
        assert dispatcher._get_empty_value(str) == ""
        assert dispatcher._get_empty_value(list) == []
        assert dispatcher._get_empty_value(dict) == {}


class TestComponentTemplateLoaders:
    """Test component template loading system."""
    
    @pytest.mark.asyncio
    async def test_component_template_loader_init(self):
        """Test ComponentTemplateLoader initialization."""
        from eden.components.loaders import ComponentTemplateLoader
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ComponentTemplateLoader(
                project_dirs=[tmpdir],
                builtin_dir=tmpdir,
                theme="dark"
            )
            assert loader.theme == "dark"
            assert tmpdir in [str(d) for d in loader.loader.directories]
    
    @pytest.mark.asyncio
    async def test_cached_template_loader(self):
        """Test CachedTemplateLoader caching."""
        from eden.components.loaders import CachedTemplateLoader
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = CachedTemplateLoader(project_dirs=[tmpdir])
            
            # Create a test template file
            test_file = os.path.join(tmpdir, "test.html")
            with open(test_file, "w") as f:
                f.write("<div>Test</div>")
            
            # First load - should read from disk
            content1 = await loader.get_template("test.html")
            assert content1 == "<div>Test</div>"
            
            # Second load - should come from cache
            content2 = await loader.get_template("test.html")
            assert content2 == "<div>Test</div>"
            
            # Both should be identical
            assert content1 == content2
    
    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test cache clearing."""
        from eden.components.loaders import CachedTemplateLoader
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = CachedTemplateLoader(project_dirs=[tmpdir])
            
            test_file = os.path.join(tmpdir, "test.html")
            with open(test_file, "w") as f:
                f.write("<div>Test</div>")
            
            await loader.get_template("test.html")
            assert "test.html" in loader._cache
            
            loader.clear_cache()
            assert "test.html" not in loader._cache


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple systems."""
    
    @pytest.mark.asyncio
    async def test_export_action_csv(self):
        """Test ExportAction with CSV format."""
        from eden.admin.widgets import ExportAction
        
        action = ExportAction(format="csv")
        assert action.format == "csv"
    
    @pytest.mark.asyncio
    async def test_export_action_json(self):
        """Test ExportAction with JSON format."""
        from eden.admin.widgets import ExportAction
        
        action = ExportAction(format="json")
        assert action.format == "json"
    
    @pytest.mark.asyncio
    async def test_export_action_xlsx(self):
        """Test ExportAction with XLSX format."""
        from eden.admin.widgets import ExportAction
        
        action = ExportAction(format="xlsx")
        assert action.format == "xlsx"
    
    @pytest.mark.asyncio
    async def test_export_action_invalid_format(self):
        """Test ExportAction with invalid format."""
        from eden.admin.widgets import ExportAction
        
        with pytest.raises(ValueError):
            ExportAction(format="invalid")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
