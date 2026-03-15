import pytest
from click.testing import CliRunner
from eden import Eden, Router, FileField, Service
from eden.middleware import limiter, rate_limit
from eden.auth.providers import JWTProvider
from eden.admin import TabularInline

def test_exports():
    assert FileField is not None
    assert Service is not None
    assert JWTProvider is not None
    assert TabularInline is not None

def test_include_router_prefix():
    app = Eden()
    router = Router()
    @router.get("/foo")
    async def foo(): return "bar"
    
    app.include_router(router, prefix="/api")
    
    # Check if the path was updated
    assert router.routes[0].path == "/api/foo"

def test_router_add_middleware():
    router = Router()
    class DummyMiddleware: pass
    router.add_middleware(DummyMiddleware)
    assert DummyMiddleware in router.middleware
    
    @router.get("/bar")
    async def bar(): return "baz"
    
    assert DummyMiddleware in router.routes[0].middleware

def test_limiter_decorator():
    @limiter("10/minute")
    async def limited_view(): pass
    
    # Check if we can call it (it should return the wrapper)
    assert limited_view is not None

def test_cli_aliases():
    from eden.cli.main import cli
    runner = CliRunner()
    
    # Test forge alias
    result = runner.invoke(cli, ["forge", "--help"])
    assert result.exit_code == 0
    assert "Generate" in result.output
    
    # Test generate alias
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "Generate" in result.output
    
    # Test run --app-path alias
    # We can't easily run it fully without an app, but we can check if it parses
    result = runner.invoke(cli, ["run", "--app-path", "app:app", "--help"])
    assert result.exit_code == 0
    
    # Test db apply alias
    from eden.cli.db import db
    result = runner.invoke(db, ["apply", "--help"])
    assert result.exit_code == 0
    assert "Apply pending migrations" in result.output

if __name__ == "__main__":
    pytest.main([__file__])
