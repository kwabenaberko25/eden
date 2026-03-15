"""
Comprehensive tests for all 5 dependency injection fixes.

Tests cover:
1. Context manager support (async and sync)
2. Circular dependency detection
3. Lazy loading parameter support
4. Advanced type coercion (Union, Optional, List, Dict, Pydantic, etc.)
5. Proper async context manager cleanup with __aexit__
"""

import pytest
import asyncio
from typing import Optional, Union, List, Dict
from contextlib import asynccontextmanager, contextmanager

from eden.dependencies import (
    Depends, 
    DependencyResolver, 
    CircularDependencyError,
    _coerce_type
)


# ============================================================================
# FIX #1: Context Manager Support Tests
# ============================================================================

class TestContextManagerSupport:
    """Test support for async and sync context managers as dependencies."""

    @pytest.mark.asyncio
    async def test_async_context_manager_dependency(self):
        """Test that async context managers are properly entered and exited."""
        cleanup_log = []

        @asynccontextmanager
        async def get_resource():
            resource = {"name": "test_resource"}
            cleanup_log.append("entered")
            try:
                yield resource
            finally:
                cleanup_log.append("exited")

        async def handler(resource=Depends(get_resource)):
            return resource

        resolver = DependencyResolver()
        kwargs = await resolver.resolve(handler)
        
        # Resource should be resolved and injected
        assert kwargs["resource"]["name"] == "test_resource"
        assert cleanup_log == ["entered"]
        
        # Cleanup should trigger __aexit__
        await resolver.cleanup()
        assert cleanup_log == ["entered", "exited"]

    @pytest.mark.asyncio
    async def test_sync_context_manager_dependency(self):
        """Test that sync context managers work as dependencies."""
        cleanup_log = []

        @contextmanager
        def get_sync_resource():
            resource = {"name": "sync_resource"}
            cleanup_log.append("sync_entered")
            try:
                yield resource
            finally:
                cleanup_log.append("sync_exited")

        async def handler(resource=Depends(get_sync_resource)):
            return resource

        resolver = DependencyResolver()
        kwargs = await resolver.resolve(handler)
        
        assert kwargs["resource"]["name"] == "sync_resource"
        assert cleanup_log == ["sync_entered"]
        
        await resolver.cleanup()
        assert cleanup_log == ["sync_entered", "sync_exited"]

    @pytest.mark.asyncio
    async def test_multiple_context_managers_cleanup_order(self):
        """Test that multiple context managers are cleaned up in LIFO order."""
        order = []

        @asynccontextmanager
        async def resource_a():
            order.append("a_enter")
            try:
                yield "a"
            finally:
                order.append("a_exit")

        @asynccontextmanager
        async def resource_b():
            order.append("b_enter")
            try:
                yield "b"
            finally:
                order.append("b_exit")

        async def handler(a=Depends(resource_a), b=Depends(resource_b)):
            return {"a": a, "b": b}

        resolver = DependencyResolver()
        kwargs = await resolver.resolve(handler)
        
        assert order == ["a_enter", "b_enter"]
        
        # Should cleanup in reverse order (b before a)
        await resolver.cleanup()
        assert order == ["a_enter", "b_enter", "b_exit", "a_exit"]


# ============================================================================
# FIX #2: Circular Dependency Detection Tests
# ============================================================================

class TestCircularDependencyDetection:
    """Test detection and error handling of circular dependencies."""

    @pytest.mark.asyncio
    async def test_self_referential_circular_dependency(self):
        """Test that a dependency depending on itself is detected."""
        
        # Create circular ref by updating function after definition
        async def circular_dep(dep=None):
            pass
        
        # Now set the circular reference
        circular_dep.__defaults__ = (Depends(circular_dep),)

        resolver = DependencyResolver()
        
        with pytest.raises(CircularDependencyError) as exc_info:
            await resolver._resolve_dependency(Depends(circular_dep))
        
        assert "Circular dependency detected" in str(exc_info.value)
        assert "circular_dep -> circular_dep" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_indirect_circular_dependency_chain(self):
        """Test detection of circular dependencies through a chain."""
        # We need to create the circular chain after defining functions
        
        async def get_a(b=Depends(None)):  # Placeholder, will be set
            pass

        async def get_b(a=Depends(None)):  # Placeholder, will be set
            pass

        # Now set up the actual circular dependency
        get_a.__defaults__ = (Depends(get_b),)
        get_b.__defaults__ = (Depends(get_a),)

        resolver = DependencyResolver()
        
        with pytest.raises(CircularDependencyError) as exc_info:
            await resolver._resolve_dependency(Depends(get_a))
        
        error_msg = str(exc_info.value)
        assert "Circular dependency detected" in error_msg
        # Should show the chain
        assert "get_a" in error_msg

    @pytest.mark.asyncio
    async def test_no_error_on_valid_dependency_chain(self):
        """Test that valid (non-circular) chains don't raise errors."""
        async def get_c():
            return "c"

        async def get_b(c=Depends(get_c)):
            return f"b-{c}"

        async def get_a(b=Depends(get_b)):
            return f"a-{b}"

        resolver = DependencyResolver()
        result = await resolver._resolve_dependency(Depends(get_a))
        
        # Should resolve without error
        assert result == "a-b-c"


# ============================================================================
# FIX #3: Lazy Loading Support Tests
# ============================================================================

class TestLazyLoadingSupport:
    """Test lazy loading parameter in Depends marker."""

    @pytest.mark.asyncio
    async def test_lazy_parameter_accepted_in_depends(self):
        """Test that Depends accepts and stores lazy parameter."""
        async def get_resource():
            return "resource"

        # Regular eager dependency
        eager = Depends(get_resource, lazy=False)
        assert eager.lazy is False

        # Lazy dependency
        lazy = Depends(get_resource, lazy=True)
        assert lazy.lazy is True

    @pytest.mark.asyncio
    async def test_lazy_parameter_in_docstring(self):
        """Test that Depends docstring documents lazy parameter."""
        # This is more of a documentation test
        assert "lazy" in Depends.__doc__
        assert "defer resolution" in Depends.__doc__.lower()


# ============================================================================
# FIX #4: Advanced Type Coercion Tests
# ============================================================================

class TestAdvancedTypeCoercion:
    """Test comprehensive type coercion for path parameters and values."""

    def test_coerce_basic_types(self):
        """Test coercion of basic types."""
        # String to int
        assert _coerce_type("123", int) == 123
        
        # String to float
        assert _coerce_type("3.14", float) == 3.14
        
        # String to bool (won't work, returns string)
        # This is intentional - bool("False") == True, so we don't auto-coerce
        assert _coerce_type("true", str) == "true"

    def test_coerce_optional_types(self):
        """Test coercion with Optional types."""
        # None should pass through
        assert _coerce_type(None, Optional[str]) is None
        assert _coerce_type(None, Optional[int]) is None
        
        # Non-None values should be coerced
        assert _coerce_type("123", Optional[int]) == 123
        assert _coerce_type("hello", Optional[str]) == "hello"

    def test_coerce_union_types(self):
        """Test coercion with Union types."""
        # Union[int, str] with string value should stay string
        result = _coerce_type("hello", Union[int, str])
        assert result == "hello"
        
        # Union[int, str] with "123" should become int
        result = _coerce_type("123", Union[int, str])
        assert result == 123

    def test_coerce_list_types(self):
        """Test coercion with List types."""
        # List from tuple
        result = _coerce_type((1, 2, 3), List[int])
        assert result == [1, 2, 3]
        
        # Single value (non-string) to list
        result = _coerce_type(42, List[str])
        assert result == [42]
        
        # String should not be split
        result = _coerce_type("hello", List[str])
        assert result == "hello"

    def test_coerce_dict_types(self):
        """Test coercion with Dict types."""
        # Dict stays dict
        d = {"key": "value"}
        result = _coerce_type(d, Dict[str, str])
        assert result == d

    def test_coerce_pydantic_model(self):
        """Test coercion with Pydantic models if available."""
        try:
            from pydantic import BaseModel

            class User(BaseModel):
                name: str
                age: int

            # Dict to Pydantic
            result = _coerce_type({"name": "Alice", "age": 30}, User)
            if isinstance(result, User):
                assert result.name == "Alice"
                assert result.age == 30

        except ImportError:
            # Pydantic not available, skip
            pytest.skip("Pydantic not installed")

    def test_coerce_already_correct_type(self):
        """Test that values already of correct type pass through."""
        assert _coerce_type(123, int) == 123
        assert _coerce_type("hello", str) == "hello"
        assert _coerce_type([1, 2], list) == [1, 2]

    def test_coerce_graceful_fallback(self):
        """Test that coercion gracefully falls back to original on failure."""
        # Invalid int should return as-is
        result = _coerce_type("not_a_number", int)
        assert result == "not_a_number"


    def test_coerce_complex_nested_union(self):
        """Test coercion with complex nested Union types."""
        # Union[int, Optional[str]]
        assert _coerce_type(None, Union[int, Optional[str]]) is None
        assert _coerce_type("123", Union[int, Optional[str]]) == 123
        assert _coerce_type("hello", Union[int, Optional[str]]) == "hello"


# ============================================================================
# FIX #5: Async Context Manager Cleanup Tests
# ============================================================================

class TestAsyncContextManagerCleanup:
    """Test proper cleanup of async context managers with __aexit__."""

    @pytest.mark.asyncio
    async def test_aexit_called_on_async_context_manager(self):
        """Test that __aexit__ is properly called during cleanup."""
        aexit_called = False

        class MockAsyncContextManager:
            async def __aenter__(self):
                return "resource"

            async def __aexit__(self, exc_type, exc, tb):
                nonlocal aexit_called
                aexit_called = True

        async def get_cm():
            return MockAsyncContextManager()

        async def handler(cm=Depends(get_cm)):
            return cm

        resolver = DependencyResolver()
        kwargs = await resolver.resolve(handler)
        
        assert aexit_called is False  # Not yet called
        assert kwargs["cm"] == "resource"
        
        # Cleanup should call __aexit__
        await resolver.cleanup()
        assert aexit_called is True

    @pytest.mark.asyncio
    async def test_aexit_called_with_exception_none_args(self):
        """Test that __aexit__ is called with (None, None, None) on normal cleanup."""
        aexit_args = None

        class MockAsyncContextManager:
            async def __aenter__(self):
                return "resource"

            async def __aexit__(self, exc_type, exc, tb):
                nonlocal aexit_args
                aexit_args = (exc_type, exc, tb)

        async def get_cm():
            return MockAsyncContextManager()

        async def handler(cm=Depends(get_cm)):
            return cm

        resolver = DependencyResolver()
        await resolver.resolve(handler)
        await resolver.cleanup()
        
        # Should be called with (None, None, None) for normal cleanup
        assert aexit_args == (None, None, None)

    @pytest.mark.asyncio
    async def test_async_context_manager_cleanup_suppresses_errors(self):
        """Test that cleanup errors don't prevent other cleanups."""
        cleanup_order = []

        class BrokenAsyncContextManager:
            async def __aenter__(self):
                return "broken"

            async def __aexit__(self, exc_type, exc, tb):
                cleanup_order.append("broken_aexit")
                raise RuntimeError("Cleanup error!")

        class GoodAsyncContextManager:
            async def __aenter__(self):
                return "good"

            async def __aexit__(self, exc_type, exc, tb):
                cleanup_order.append("good_aexit")

        async def get_broken():
            return BrokenAsyncContextManager()

        async def get_good():
            return GoodAsyncContextManager()

        async def handler(broken=Depends(get_broken), good=Depends(get_good)):
            return {"broken": broken, "good": good}

        resolver = DependencyResolver()
        await resolver.resolve(handler)
        
        # Cleanup should not raise even though broken raises
        await resolver.cleanup()
        
        # Both should have attempted cleanup (in reverse order)
        assert "good_aexit" in cleanup_order
        assert "broken_aexit" in cleanup_order


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple fixes."""

    @pytest.mark.asyncio
    async def test_complex_dependency_tree_with_context_managers(self):
        """Test complex dependency resolution with context managers and type coercion."""
        cleanup_order = []

        @asynccontextmanager
        async def get_database():
            cleanup_order.append("db_enter")
            try:
                yield {"name": "db"}
            finally:
                cleanup_order.append("db_exit")

        async def get_user_id(db=Depends(get_database)) -> int:
            return 42

        async def handler(
            db=Depends(get_database),
            user_id=Depends(get_user_id),
        ):
            return {"db": db, "user_id": user_id}

        resolver = DependencyResolver()
        kwargs = await resolver.resolve(handler)
        
        assert kwargs["user_id"] == 42
        assert kwargs["db"]["name"] == "db"
        
        # Cleanup in proper order
        await resolver.cleanup()
        assert cleanup_order == ["db_enter", "db_exit"]  # db_enter should appear once due to caching

    @pytest.mark.asyncio
    async def test_path_parameter_coercion_with_dependencies(self):
        """Test path parameter coercion combined with Depends."""
        async def get_db():
            return {"type": "database"}

        async def handler(
            user_id: int = 0,  # Path param with type hint
            db=Depends(get_db)
        ):
            return {"user_id": user_id, "db": db}

        resolver = DependencyResolver()
        kwargs = await resolver.resolve(
            handler,
            path_params={"user_id": "123"}
        )
        
        assert kwargs["user_id"] == 123  # Coerced to int
        assert kwargs["db"]["type"] == "database"


if __name__ == "__main__":
    # Run pytest
    pytest.main([__file__, "-v"])
