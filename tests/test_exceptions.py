"""
Tests for Eden exception handling — custom exceptions, global handlers,
and ValidationError serialization.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from eden import Eden, NotFound, BadRequest, Forbidden, Request
from eden.exceptions import ValidationError, EdenException
from eden.responses import JsonResponse


@pytest.fixture
def app() -> Eden:
    app = Eden(debug=False)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.get("/not-found")
    async def trigger_404():
        raise NotFound(detail="Item not found.")

    @app.get("/bad-request")
    async def trigger_400():
        raise BadRequest(detail="Missing required field: name")

    @app.get("/forbidden")
    async def trigger_403():
        raise Forbidden()

    @app.get("/validation")
    async def trigger_validation():
        raise ValidationError(
            errors=[
                {"field": "email", "message": "Invalid email format."},
                {"field": "age", "message": "Must be >= 18."},
            ],
            detail="Validation failed.",
        )

    @app.get("/custom-code")
    async def custom_code():
        raise EdenException(detail="Custom error", status_code=418)

    @app.get("/unhandled")
    async def unhandled():
        raise RuntimeError("Something broke!")

    return app


@pytest.fixture
async def client(app: Eden) -> AsyncClient:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


class TestExceptions:
    """Test exception handling and serialization."""

    async def test_not_found(self, client: AsyncClient):
        resp = await client.get("/not-found")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"] is True
        assert data["detail"] == "Item not found."

    async def test_bad_request(self, client: AsyncClient):
        resp = await client.get("/bad-request")
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] is True
        assert "Missing required field" in data["detail"]

    async def test_forbidden(self, client: AsyncClient):
        resp = await client.get("/forbidden")
        assert resp.status_code == 403

    async def test_validation_error(self, client: AsyncClient):
        resp = await client.get("/validation")
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"] is True
        assert data["detail"] == "Validation failed."
        assert len(data["extra"]["errors"]) == 2

    async def test_custom_status_code(self, client: AsyncClient):
        resp = await client.get("/custom-code")
        assert resp.status_code == 418
        data = resp.json()
        assert data["detail"] == "Custom error"

    async def test_unhandled_exception(self, client: AsyncClient):
        resp = await client.get("/unhandled")
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] is True


class TestCustomExceptionHandler:
    """Test app-level custom exception handlers."""

    async def test_custom_handler(self):
        app = Eden(debug=True)

        @app.get("/fail")
        async def fail():
            raise NotFound(detail="Gone!")

        @app.exception_handler(NotFound)
        async def handle_404(request: Request, exc: NotFound):
            return JsonResponse(
                content={"custom": True, "path": str(request.url.path)},
                status_code=404,
            )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get("/fail")
            assert resp.status_code == 404
            data = resp.json()
            assert data["custom"] is True
            assert data["path"] == "/fail"
