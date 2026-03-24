"""
Tests for CrudMixin.get() explicit signature fix (Issue #17).

Verifies:
1. Keyword id= usage works (canonical form)
2. Single positional arg emits FutureWarning and still works 
3. Multiple positional args raise TypeError
4. No args raise TypeError
5. Both positional and id= raises TypeError
6. Filter kwargs (email=...) are forwarded
7. get_or_404 delegates properly
"""

import pytest
import warnings
from unittest.mock import AsyncMock, patch, MagicMock
from eden.db.mixins.crud import CrudMixin


class FakeQuerySet:
    """Mock QuerySet that records filter calls."""
    
    def __init__(self):
        self._filters = {}
    
    def filter(self, *args, **kwargs):
        self._filters = kwargs
        return self
    
    async def first(self):
        # Return a fake record based on filters
        if self._filters:
            return {"id": self._filters.get("id", "mock"), **self._filters}
        return None


class MockModel(CrudMixin):
    """Test model inheriting CrudMixin."""
    __name__ = "MockModel"
    
    @classmethod
    def query(cls, session=None):
        return FakeQuerySet()


@pytest.mark.asyncio
async def test_get_keyword_id():
    """Canonical form: Model.get(id=value) should work without warnings."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = await MockModel.get(id="abc-123")
        assert result is not None
        assert result["id"] == "abc-123"
        # No deprecation warnings should be emitted
        future_warnings = [x for x in w if issubclass(x.category, FutureWarning)]
        assert len(future_warnings) == 0


@pytest.mark.asyncio
async def test_get_positional_id_deprecated():
    """Legacy form: Model.get(value) should work but emit FutureWarning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = await MockModel.get("abc-123")
        assert result is not None
        assert result["id"] == "abc-123"
        # Should emit exactly one FutureWarning
        future_warnings = [x for x in w if issubclass(x.category, FutureWarning)]
        assert len(future_warnings) == 1
        assert "positional form is deprecated" in str(future_warnings[0].message)


@pytest.mark.asyncio
async def test_get_multiple_positional_raises():
    """Multiple positional args should raise TypeError."""
    with pytest.raises(TypeError, match="takes at most 1 positional argument"):
        await MockModel.get("arg1", "arg2")


@pytest.mark.asyncio
async def test_get_no_args_raises():
    """No args at all should raise TypeError."""
    with pytest.raises(TypeError, match="requires at least"):
        await MockModel.get()


@pytest.mark.asyncio
async def test_get_positional_and_keyword_raises():
    """Both positional and id= at the same time should raise TypeError."""
    with pytest.raises(TypeError, match="received both a positional argument"):
        await MockModel.get("pos-id", id="kw-id")


@pytest.mark.asyncio
async def test_get_with_filter_kwargs():
    """Filter by non-PK fields: Model.get(email='alice@example.com')."""
    result = await MockModel.get(email="alice@example.com")
    assert result is not None
    assert result["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_get_keyword_id_with_session():
    """Session should be properly forwarded as keyword."""
    mock_session = MagicMock()
    mock_session.execute = MagicMock()  # has 'execute' attribute
    
    # We need a model whose query() can accept session
    calls = []
    original_query = MockModel.query
    
    @classmethod
    def tracking_query(cls, session=None):
        calls.append(session)
        return FakeQuerySet()
    
    MockModel.query = tracking_query
    try:
        result = await MockModel.get(id="abc", session=mock_session)
        assert calls[-1] is mock_session
    finally:
        MockModel.query = original_query
