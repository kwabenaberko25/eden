
import pytest
import uuid
from unittest.mock import AsyncMock, patch
from eden.db import Model, f, Mapped
from eden.tenancy import OrganizationMixin
from eden.templating import EdenTemplates
from eden.db.reactive import broadcast_update, get_reactive_channels

# 1. Define a reactive organization model
class ReactiveDepartment(OrganizationMixin, Model):
    __tablename__ = "reactive_depts"
    __eden_reactive__ = True
    name: Mapped[str] = f()

@pytest.mark.asyncio
async def test_full_reactivity_integration_loop():
    """
    Verifies that a reactive organization model correctly resolves channels
    in templates and triggers broadcasts.
    """
    org_id = uuid.uuid4()
    dept = ReactiveDepartment(id=uuid.uuid4(), organization_id=org_id, name="Eng")
    
    # --- Step A: Template Channel Resolution ---
    # Simulate the helper used by @reactive directive
    from eden.templating.templates import get_sync_channel
    
    # We need to mock the context because OrganizationMixin looks for organization_id
    with patch("eden.context.get_organization_id", return_value=org_id):
        channel = get_sync_channel(dept)
        # Should be org-scoped because of OrganizationMixin
        assert f"org:{org_id}:reactive_depts" in channel or f"org:{org_id}:reactive_depts:{dept.id}" in channel
        
    # --- Step B: Broadcast Logic ---
    with patch("eden.websocket.connection_manager.broadcast", new_callable=AsyncMock) as mock_broadcast:
        # Simulate a model save trigger
        await broadcast_update(dept, event="updated")
        
        # Give the background task a moment to execute the mock
        import asyncio
        await asyncio.sleep(0.01)
        
        # Verify the broadcast reached the same channel identified in Step A
        assert mock_broadcast.called
        call_channels = [call.kwargs["channel"] for call in mock_broadcast.call_args_list]
        assert channel in call_channels

@pytest.mark.asyncio
async def test_reactive_directive_html_generation():
    """
    Verifies that the @reactive directive generates the expected HTMX/WS attributes.
    """
    templates = EdenTemplates(directory="tests/templates")
    org_id = uuid.uuid4()
    dept = ReactiveDepartment(id=uuid.uuid4(), organization_id=org_id, name="Design")
    
    template_str = """
    @reactive(dept)
    <div id="dept-{{ dept.id }}">{{ dept.name }}</div>
    @endreactive
    """
    
    # We need to manually preprocess for from_string calls to trigger Eden's @directives
    from eden.templating.extensions import EdenDirectivesExtension
    ext = EdenDirectivesExtension(templates.env)
    processed_source = ext.preprocess(template_str, "test.html")
    
    tmpl = templates.env.from_string(processed_source)
    
    class MockRequest:
        def __init__(self):
            self.url = "http://testserver/depts"
            self.state = type('state', (), {'eden_channels': set()})()

    with patch("eden.context.get_organization_id", return_value=org_id):
        html = tmpl.render(dept=dept, request=MockRequest())
        
        # Verify HTMX attributes
        assert 'hx-get="http://testserver/depts"' in html
        assert 'hx-trigger="updated:' in html
        assert 'hx-target="this"' in html
        assert 'hx-swap="outerHTML"' in html
        # Verify channel presence in the trigger
        assert f"org:{org_id}:reactive_depts" in html
