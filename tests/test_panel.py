"""
Tests for Eden Control Panel.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from starlette.responses import HTMLResponse

from eden.panel import ControlPanel, PanelConfig, BasePanel
from eden.db import Model, mapped_column, String
from sqlalchemy import Uuid
import uuid


class TestUser(Model):
    """Test user model."""
    name: str = mapped_column(String(100))
    email: str = mapped_column(String(255))


class TestUserPanel(BasePanel):
    """Test panel for users."""
    display_fields = ["name", "email"]
    search_fields = ["name", "email"]
    filter_fields = ["name"]


@pytest.mark.asyncio
async def test_panel_creation():
    """Test panel creation and registration."""
    panel = ControlPanel()

    # Register a panel
    panel.register(TestUser)(TestUserPanel)

    assert TestUser.__name__.lower() in panel.panels
    assert isinstance(panel.panels['testuser'], TestUserPanel)


@pytest.mark.asyncio
async def test_panel_config():
    """Test panel configuration."""
    config = PanelConfig(
        title="Test Panel",
        theme="dark",
        auth_required=False,
        items_per_page=50
    )

    panel = ControlPanel(config)

    assert panel.config.title == "Test Panel"
    assert panel.config.theme == "dark"
    assert panel.config.auth_required is False
    assert panel.config.items_per_page == 50


@pytest.mark.asyncio
async def test_panel_field_detection():
    """Test automatic field detection."""
    panel = TestUserPanel(TestUser)

    assert 'name' in panel.fields
    assert 'email' in panel.fields
    assert 'id' in panel.fields  # From base Model

    name_field = panel.fields['name']
    assert name_field.display_name == "Name"
    assert name_field.required is True  # String fields are typically required
    assert name_field.searchable is True
    assert name_field.filterable is True


@pytest.mark.asyncio
async def test_panel_list_data():
    """Test list data generation."""
    panel = TestUserPanel(TestUser)

    # Mock request
    request = MagicMock()
    request.query_params = {}

    # Mock queryset methods
    mock_queryset = AsyncMock()
    mock_queryset.all.return_value = []
    mock_queryset.count.return_value = 0
    mock_queryset.order_by.return_value = mock_queryset
    mock_queryset.paginate.return_value = MagicMock(
        items=[],
        total=0,
        page=1,
        per_page=25,
        has_next=False,
        has_prev=False,
        total_pages=1,
    )

    panel.get_queryset = AsyncMock(return_value=mock_queryset)

    data = await panel.get_list_data(request)

    assert 'items' in data
    assert 'total' in data
    assert 'page' in data
    assert data['page'] == 1
    assert data['per_page'] == 25  # Default


@pytest.mark.asyncio
async def test_panel_detail_data():
    """Test detail data generation."""
    panel = TestUserPanel(TestUser)

    # Mock request
    request = MagicMock()

    # Mock the model query
    mock_user = TestUser(id=uuid.uuid4(), name="Test User", email="test@example.com")

    mock_queryset = AsyncMock()
    mock_queryset.filter = MagicMock(return_value=mock_queryset)
    mock_queryset.first.return_value = mock_user

    # Temporarily replace the model's query method
    original_query = TestUser.query
    TestUser.query = MagicMock(return_value=mock_queryset)

    try:
        data = await panel.get_detail_data(request, str(mock_user.id))

        assert 'object' in data
        assert 'fields' in data
        assert data['object'] == mock_user
        assert isinstance(data['fields'], dict)

    finally:
        # Restore original method
        TestUser.query = original_query


@pytest.mark.asyncio
async def test_panel_routes():
    """Test panel route generation."""
    panel = ControlPanel()
    routes = panel.get_routes()

    assert len(routes) == 3  # dashboard, list, detail

    route_names = [route.name for route in routes]
    assert 'panel_dashboard' in route_names
    assert 'panel_list' in route_names
    assert 'panel_detail' in route_names


@pytest.mark.asyncio
async def test_dashboard_view():
    """Test dashboard view rendering."""
    panel = ControlPanel()

    # Mock request
    request = MagicMock()

    response = await panel.dashboard_view(request)

    assert isinstance(response, HTMLResponse)
    # In a real test, we'd check the HTML content
    # For now, just verify it returns a response