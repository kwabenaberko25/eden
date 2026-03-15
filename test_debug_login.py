import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_debug_login_required():
    """Debug login_required with request.state.user = None."""
    from eden.auth.decorators import login_required

    @login_required
    async def protected_view(request):
        return {"message": "success"}

    # Mock request without user
    request = MagicMock()
    request.state = MagicMock()
    request.state.user = None
    request.headers = {}
    request.scope = {"type": "http"}
    
    print(f"request.state.user = {request.state.user}")
    print(f"hasattr(request, 'state') = {hasattr(request, 'state')}")
    print(f"hasattr(request.state, 'user') = {hasattr(request.state, 'user')}")
    
    user = None
    if hasattr(request, "state") and hasattr(request.state, "user"):
        user = request.state.user
        print(f"Got user from request.state: {user}")
    if not user:
        user = getattr(request, "user", None)
        print(f"Got user from getattr: {user}")
    
    print(f"Final user: {user}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_debug_login_required())
