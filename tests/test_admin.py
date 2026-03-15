"""
Eden — Admin Panel Tests

Tests for AdminSite, ModelAdmin, and the admin registration system.
"""

import pytest
from unittest.mock import MagicMock

from eden.admin import AdminSite, admin
from eden.admin.options import ModelAdmin


# ── ModelAdmin Tests ──────────────────────────────────────────────────


class TestModelAdmin:
    """Tests for ModelAdmin configuration."""

    def test_default_values(self):
        ma = ModelAdmin()
        assert ma.per_page == 25
        assert ma.ordering == ["-created_at"]
        assert ma.list_display == []
        assert ma.search_fields == []

    def test_custom_values(self):
        class CustomAdmin(ModelAdmin):
            list_display = ["email", "name"]
            search_fields = ["email"]
            per_page = 50
            ordering = ["-email"]

        ma = CustomAdmin()
        assert ma.list_display == ["email", "name"]
        assert ma.search_fields == ["email"]
        assert ma.per_page == 50

    def test_verbose_name(self):
        ma = ModelAdmin()
        mock_model = MagicMock()
        mock_model.__name__ = "UserProfile"

        assert ma.get_verbose_name(mock_model) == "User Profile"
        assert ma.get_verbose_name_plural(mock_model) == "User Profiles"

    def test_custom_verbose_name(self):
        class CustomAdmin(ModelAdmin):
            verbose_name = "Person"
            verbose_name_plural = "People"

        ma = CustomAdmin()
        mock_model = MagicMock()
        assert ma.get_verbose_name(mock_model) == "Person"
        assert ma.get_verbose_name_plural(mock_model) == "People"


# ── AdminSite Tests ───────────────────────────────────────────────────


class TestAdminSite:
    """Tests for the AdminSite model registry."""

    def test_register_model(self):
        site = AdminSite()
        mock_model = type("TestModel", (), {"__tablename__": "test_models"})

        site.register(mock_model)
        assert site.is_registered(mock_model)

    def test_register_with_custom_admin(self):
        site = AdminSite()
        mock_model = type("TestModel", (), {"__tablename__": "test_models"})

        class CustomAdmin(ModelAdmin):
            list_display = ["name"]

        site.register(mock_model, CustomAdmin)
        assert site.is_registered(mock_model)
        assert isinstance(site._registry[mock_model], CustomAdmin)

    def test_unregister(self):
        site = AdminSite()
        mock_model = type("TestModel", (), {"__tablename__": "test_models"})

        site.register(mock_model)
        assert site.is_registered(mock_model)

        site.unregister(mock_model)
        assert not site.is_registered(mock_model)

    def test_get_registry(self):
        site = AdminSite()
        model1 = type("Model1", (), {"__tablename__": "model1"})
        model2 = type("Model2", (), {"__tablename__": "model2"})

        site.register(model1)
        site.register(model2)

        registry = site.get_registry()
        assert len(registry) == 2
        assert model1 in registry
        assert model2 in registry

    def test_register_as_decorator(self):
        site = AdminSite()

        @site.register
        class MyModel:
            __tablename__ = "my_models"

        assert site.is_registered(MyModel)

    def test_global_admin_instance(self):
        """The global admin singleton should be available."""
        assert isinstance(admin, AdminSite)
