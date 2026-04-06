"""
Integration tests for Eden Django-inspired features.
Tests the complete workflow of ControlPanel, ModelSchema, QuerySet, ChoiceField, and ModelConfig working together.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from starlette.responses import HTMLResponse

from eden.panel import ControlPanel, PanelConfig
from eden.schemas import ModelSchema
from eden.querysets import QuerySet, Manager
from eden.enums import ChoiceField, ChoiceEnum
from eden.models import ModelConfig
from eden.db import Model, mapped_column, String
import uuid


class Status(ChoiceEnum):
    """Status choices for testing."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Article(Model):
    """Test article model with all features."""
    title: str = mapped_column(String(200))
    content: str = mapped_column(String(1000))
    status: str = ChoiceField(choices=Status, default=Status.DRAFT)
    author_name: str = mapped_column(String(100))

    # ModelConfig
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Article"
        api_resource = True
        admin_list_display = ["title", "status", "author_name"]
        admin_list_filter = ["status"]
        admin_search_fields = ["title", "content", "author_name"]


class ArticleSchema(ModelSchema):
    """Schema for article forms."""

    class Meta:
        model = Article
        exclude_fields = []
        read_only_fields = ["id"]
        required_fields = ["title", "status"]


class ArticleManager(Manager):
    """Custom manager for articles."""

    def published(self):
        """Get published articles."""
        return self.filter(status=Status.PUBLISHED.value)

    def by_author(self, author_name: str):
        """Get articles by author."""
        return self.filter(author_name=author_name)


@pytest.mark.asyncio
async def test_complete_workflow():
    """Test the complete workflow of all features working together."""

    # 1. Test ModelConfig
    config = Article.Meta
    assert config.verbose_name == "Article"
    assert config.api_resource is True
    assert "title" in config.admin_list_display
    assert "status" in config.admin_list_filter

    # 2. Test ChoiceField
    status_field = Article.__annotations__['status']
    assert status_field.choices == Status
    assert status_field.default == Status.DRAFT

    # 3. Test Manager
    manager = ArticleManager(Article)
    assert isinstance(manager, ArticleManager)

    # Mock the queryset
    mock_qs = AsyncMock()
    manager.get_queryset = AsyncMock(return_value=mock_qs)

    # Test custom methods
    published_qs = manager.published()
    assert published_qs is not mock_qs  # Should be a new queryset

    author_qs = manager.by_author("John Doe")
    assert author_qs is not mock_qs

    # 4. Test ModelSchema
    schema = ArticleSchema(
        title="Test Article",
        content="This is a test article content.",
        status=Status.PUBLISHED,
        author_name="John Doe"
    )

    assert schema.title == "Test Article"
    assert schema.status == Status.PUBLISHED

    # Test validation
    is_valid = await schema.is_valid({
        "title": "Test Article",
        "content": "This is a test article content.",
        "status": Status.PUBLISHED,
        "author_name": "John Doe"
    })
    assert is_valid is True

    # 5. Test ControlPanel integration
    panel = ControlPanel()

    # Register the article panel
    from eden.panel import BasePanel

    class ArticlePanel(BasePanel):
        display_fields = ["title", "status", "author_name"]
        search_fields = ["title", "content", "author_name"]
        filter_fields = ["status"]

    panel.register(Article)(ArticlePanel)

    assert 'article' in panel.panels
    assert isinstance(panel.panels['article'], ArticlePanel)

    # Test panel configuration
    article_panel = panel.panels['article']
    assert 'title' in article_panel.display_fields
    assert 'status' in article_panel.search_fields


@pytest.mark.asyncio
async def test_panel_with_real_data():
    """Test panel operations with mock data."""

    # Create mock article data
    mock_articles = [
        Article(
            id=uuid.uuid4(),
            title="First Article",
            content="Content of first article",
            status=Status.PUBLISHED.value,
            author_name="Alice"
        ),
        Article(
            id=uuid.uuid4(),
            title="Second Article",
            content="Content of second article",
            status=Status.DRAFT.value,
            author_name="Bob"
        )
    ]

    # Setup panel
    panel = ControlPanel()
    from eden.panel import BasePanel

    class ArticlePanel(BasePanel):
        display_fields = ["title", "status", "author_name"]
        search_fields = ["title", "author_name"]
        filter_fields = ["status"]

    panel.register(Article)(ArticlePanel)
    article_panel = panel.panels['article']

    # Mock request
    request = MagicMock()
    request.query_params = {}

    # Mock queryset
    mock_queryset = AsyncMock()
    mock_queryset.all.return_value = mock_articles
    mock_queryset.count.return_value = len(mock_articles)

    article_panel.get_queryset = AsyncMock(return_value=mock_queryset)

    # Test list data
    list_data = await article_panel.get_list_data(request)

    assert 'items' in list_data
    assert 'total' in list_data
    assert list_data['total'] == 2
    assert len(list_data['items']) == 2

    # Test detail data
    mock_article = mock_articles[0]
    mock_detail_qs = AsyncMock()
    mock_detail_qs.filter.return_value.first.return_value = mock_article

    # Temporarily replace the model's query method
    original_query = Article.query
    Article.query = mock_detail_qs

    try:
        detail_data = await article_panel.get_detail_data(request, str(mock_article.id))

        assert 'object' in detail_data
        assert 'fields' in detail_data
        assert detail_data['object'] == mock_article

    finally:
        Article.query = original_query


@pytest.mark.asyncio
async def test_schema_with_panel_integration():
    """Test schema working with panel data."""

    # Create schema
    schema = ArticleSchema(
        title="Integration Test",
        content="Testing schema and panel integration",
        status=Status.PUBLISHED,
        author_name="Test Author"
    )

    # Mock save operation
    mock_article = Article(
        id=uuid.uuid4(),
        title="Integration Test",
        content="Testing schema and panel integration",
        status=Status.PUBLISHED.value,
        author_name="Test Author"
    )

    Article.create = AsyncMock(return_value=mock_article)

    try:
        saved = await schema.save()
        assert saved.title == "Integration Test"
        assert saved.status == Status.PUBLISHED.value

        Article.create.assert_called_once()

    finally:
        delattr(Article, 'create')


@pytest.mark.asyncio
async def test_queryset_with_schema():
    """Test QuerySet operations with schema data."""

    # Create queryset
    qs = QuerySet(Article)

    # Test filtering
    filtered = qs.filter(status=Status.PUBLISHED.value)
    assert filtered is not qs

    # Test with manager
    manager = ArticleManager(Article)
    published_manager = manager.published()

    # The manager should delegate to queryset
    assert hasattr(published_manager, 'filter')


@pytest.mark.asyncio
async def test_model_config_api_fields():
    """Test ModelConfig API field handling."""

    config = Article.Meta

    # Test API fields
    api_fields = config.api_fields
    assert "title" in api_fields
    assert "content" in api_fields
    assert "status" in api_fields
    assert "author_name" in api_fields

    # Test field info
    title_info = config.get_api_field_info("title")
    assert title_info["required"] is True  # From schema
    assert title_info["readonly"] is False

    status_info = config.get_api_field_info("status")
    assert status_info["required"] is True  # From schema


@pytest.mark.asyncio
async def test_choice_field_validation():
    """Test ChoiceField validation with different inputs."""

    # Test valid choices
    assert Status.validate_choice("draft") is True
    assert Status.validate_choice("published") is True
    assert Status.validate_choice("archived") is True
    assert Status.validate_choice("invalid") is False

    # Test field validation
    field = ChoiceField(choices=Status)

    assert field.validate("draft") == []
    assert len(field.validate("invalid")) == 1

    # Test display names
    assert Status.get_display_name("draft") == "Draft"
    assert Status.get_display_name("published") == "Published"


@pytest.mark.asyncio
async def test_end_to_end_crud_workflow():
    """Test complete CRUD workflow using all components."""

    # 1. Create article via schema
    schema = ArticleSchema(
        title="End-to-End Test",
        content="Testing the complete workflow",
        status=Status.PUBLISHED,
        author_name="Test User"
    )

    # Mock the database save
    mock_saved_article = Article(
        id=uuid.uuid4(),
        title="End-to-End Test",
        content="Testing the complete workflow",
        status=Status.PUBLISHED.value,
        author_name="Test User"
    )

    Article.create = AsyncMock(return_value=mock_saved_article)

    try:
        saved_article = await schema.save()
        assert saved_article.id is not None

        # 2. Query via manager
        manager = ArticleManager(Article)
        mock_qs = AsyncMock()
        mock_qs.filter.return_value.all.return_value = [saved_article]
        manager.get_queryset = AsyncMock(return_value=mock_qs)

        # 3. Display via panel
        panel = ControlPanel()
        from eden.panel import BasePanel

        class TestPanel(BasePanel):
            display_fields = ["title", "status", "author_name"]

        panel.register(Article)(TestPanel)
        article_panel = panel.panels['article']

        # Mock panel data retrieval
        request = MagicMock()
        request.query_params = {}

        mock_panel_qs = AsyncMock()
        mock_panel_qs.all.return_value = [saved_article]
        mock_panel_qs.count.return_value = 1
        article_panel.get_queryset = AsyncMock(return_value=mock_panel_qs)

        list_data = await article_panel.get_list_data(request)
        assert list_data['total'] == 1
        assert list_data['items'][0].title == "End-to-End Test"

    finally:
        delattr(Article, 'create')


if __name__ == "__main__":
    # Run basic smoke tests if pytest is not available
    import asyncio

    async def run_smoke_tests():
        print("Running smoke tests...")

        try:
            # Test basic imports
            from eden.panel import ControlPanel
            from eden.schemas import ModelSchema
            from eden.querysets import QuerySet
            from eden.enums import ChoiceField
            from eden.models import ModelConfig
            print("✓ All modules imported successfully")

            # Test basic functionality
            config = ModelConfig(verbose_name="Test")
            assert config.verbose_name == "Test"
            print("✓ ModelConfig works")

            status_field = ChoiceField(choices=Status)
            assert status_field.choices == Status
            print("✓ ChoiceField works")

            qs = QuerySet(Article)
            assert qs._model_cls == Article
            print("✓ QuerySet works")

            print("All smoke tests passed!")

        except Exception as e:
            print(f"✗ Smoke test failed: {e}")
            raise

    asyncio.run(run_smoke_tests())