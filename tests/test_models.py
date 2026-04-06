"""
Tests for Eden Model Config.
"""

import pytest

from eden.models import ModelConfig, model_config
from eden.db import Model, mapped_column, String


class TestArticle(Model):
    """Test article model."""
    title: str = mapped_column(String(200))
    content: str = mapped_column(String(1000))
    published: bool = mapped_column(String(5))


def test_model_config_creation():
    """Test ModelConfig creation."""
    config = ModelConfig(
        ordering=["-created_at"],
        verbose_name="Article",
        api_resource=True,
        admin_list_display=["title", "published"]
    )

    assert config.ordering == ["-created_at"]
    assert config.verbose_name == "Article"
    assert config.api_resource is True
    assert config.admin_list_display == ["title", "published"]


def test_model_config_defaults():
    """Test ModelConfig default values."""
    config = ModelConfig()

    assert config.ordering == []
    assert config.api_resource is True
    assert config.tenant_isolated is True
    assert config.admin_list_per_page == 25
    assert config.cache_timeout == 0


def test_model_config_apply_defaults():
    """Test applying defaults based on model."""
    config = ModelConfig()
    config._model_cls = TestArticle

    config._apply_defaults()

    assert config.verbose_name == "Testarticle"  # Auto-generated
    assert config.verbose_name_plural == "Testarticles"
    assert config.db_table == "testarticles"
    assert config.api_readonly_fields == ["id", "created_at", "updated_at"]


def test_model_config_api_fields():
    """Test API fields property."""
    config = ModelConfig()
    config._model_cls = TestArticle
    config.api_exclude_fields = ["content"]

    fields = config.api_fields

    assert "title" in fields
    assert "published" in fields
    assert "content" not in fields  # Excluded


def test_model_config_admin_fields():
    """Test admin fields property."""
    config = ModelConfig()
    config._model_cls = TestArticle
    config.admin_exclude_fields = ["content"]

    fields = config.admin_fields

    assert "title" in fields
    assert "published" in fields
    assert "content" not in fields  # Excluded


def test_model_config_api_field_info():
    """Test API field info method."""
    config = ModelConfig(
        api_readonly_fields=["id"],
        api_required_fields=["title"],
        api_nested_fields=["author"]
    )

    # Test readonly field
    info = config.get_api_field_info("id")
    assert info["readonly"] is True
    assert info["required"] is False
    assert info["nested"] is False

    # Test required field
    info = config.get_api_field_info("title")
    assert info["readonly"] is False
    assert info["required"] is True
    assert info["nested"] is False

    # Test nested field
    info = config.get_api_field_info("author")
    assert info["readonly"] is False
    assert info["required"] is False
    assert info["nested"] is True

    # Test regular field
    info = config.get_api_field_info("content")
    assert info["readonly"] is False
    assert info["required"] is False
    assert info["nested"] is False


def test_model_config_admin_field_info():
    """Test admin field info method."""
    config = ModelConfig(
        admin_readonly_fields=["id"],
        admin_list_editable=["title"],
        admin_list_display=["id", "title", "content"]
    )

    # Test readonly field
    info = config.get_admin_field_info("id")
    assert info["readonly"] is True
    assert info["editable"] is False
    assert info["link"] is True  # First display field is link by default

    # Test editable field
    info = config.get_admin_field_info("title")
    assert info["readonly"] is False
    assert info["editable"] is True
    assert info["link"] is False

    # Test regular field
    info = config.get_admin_field_info("content")
    assert info["readonly"] is False
    assert info["editable"] is False
    assert info["link"] is False


def test_model_config_with_list_display_links():
    """Test admin field info with explicit display links."""
    config = ModelConfig(
        admin_list_display=["id", "title", "content"],
        admin_list_display_links=["title"]
    )

    info = config.get_admin_field_info("title")
    assert info["link"] is True

    info = config.get_admin_field_info("id")
    assert info["link"] is False


def test_model_config_indexes():
    """Test indexes configuration."""
    config = ModelConfig(
        indexes=[
            {"fields": ["title"]},
            {"fields": ["published", "created_at"], "unique": True},
        ]
    )

    assert len(config.indexes) == 2
    assert config.indexes[0]["fields"] == ["title"]
    assert config.indexes[1]["fields"] == ["published", "created_at"]
    assert config.indexes[1]["unique"] is True


def test_model_config_permissions():
    """Test permissions configuration."""
    config = ModelConfig(
        permissions=[
            ("can_publish", "Can publish articles"),
            ("can_archive", "Can archive articles"),
        ],
        default_permissions=["add", "change", "delete", "view"]
    )

    assert len(config.permissions) == 2
    assert config.permissions[0] == ("can_publish", "Can publish articles")
    assert config.default_permissions == ["add", "change", "delete", "view"]


def test_model_config_validation():
    """Test validation configuration."""
    config = ModelConfig(
        unique_together=[["title", "published"]],
        validators=[lambda x: x]  # Mock validator
    )

    assert config.unique_together == [["title", "published"]]
    assert len(config.validators) == 1


def test_model_config_api_options():
    """Test API-specific options."""
    config = ModelConfig(
        api_resource=True,
        api_readonly_fields=["id", "created_at"],
        api_exclude_fields=["internal_notes"],
        api_nested_fields=["author"],
        api_required_fields=["title"],
        api_extra_actions=[
            {"name": "publish", "method": "POST"},
            {"name": "archive", "method": "POST"},
        ]
    )

    assert config.api_resource is True
    assert "id" in config.api_readonly_fields
    assert "internal_notes" in config.api_exclude_fields
    assert "author" in config.api_nested_fields
    assert "title" in config.api_required_fields
    assert len(config.api_extra_actions) == 2


def test_model_config_admin_options():
    """Test admin-specific options."""
    config = ModelConfig(
        admin_list_display=["title", "published", "created_at"],
        admin_list_filter=["published", "created_at"],
        admin_search_fields=["title", "content"],
        admin_ordering=["-created_at"],
        admin_readonly_fields=["id"],
        admin_list_editable=["published"],
        admin_list_per_page=50,
        admin_date_hierarchy="created_at",
        admin_save_as=True,
        admin_save_on_top=True,
        admin_preserve_filters=True
    )

    assert config.admin_list_display == ["title", "published", "created_at"]
    assert config.admin_list_filter == ["published", "created_at"]
    assert config.admin_search_fields == ["title", "content"]
    assert config.admin_ordering == ["-created_at"]
    assert config.admin_readonly_fields == ["id"]
    assert config.admin_list_editable == ["published"]
    assert config.admin_list_per_page == 50
    assert config.admin_date_hierarchy == "created_at"
    assert config.admin_save_as is True
    assert config.admin_save_on_top is True
    assert config.admin_preserve_filters is True


def test_model_config_convenience_function():
    """Test model_config convenience function."""
    config = model_config(
        ordering=["-created_at"],
        verbose_name="Article",
        api_resource=True
    )

    assert isinstance(config, ModelConfig)
    assert config.ordering == ["-created_at"]
    assert config.verbose_name == "Article"
    assert config.api_resource is True