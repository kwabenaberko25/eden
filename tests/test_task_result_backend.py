"""
Tests for TaskResultBackend (Issue #25).

Verifies:
1. Store and retrieve task results
2. Get all results with ordering
3. Cleanup expired results 
4. Dead-letter queue management
"""

import pytest
from datetime import datetime, timedelta
from eden.tasks import TaskResult, TaskResultBackend


class TestTaskResult:
    """Test TaskResult data class."""
    
    def test_to_dict(self):
        result = TaskResult(
            task_id="abc123",
            task_name="my_task",
            status="success",
            result={"key": "value"},
        )
        d = result.to_dict()
        assert d["task_id"] == "abc123"
        assert d["status"] == "success"
        assert d["result"] == {"key": "value"}
    
    def test_to_dict_serializes_datetime(self):
        now = datetime.now()
        result = TaskResult(
            task_id="abc123",
            task_name="my_task",
            status="success",
            created_at=now,
        )
        d = result.to_dict()
        assert isinstance(d["created_at"], str)
    
    def test_from_dict(self):
        data = {
            "task_id": "abc123",
            "task_name": "my_task",
            "status": "failed",
            "result": None,
            "error": "Something broke",
            "error_traceback": None,
            "retries": 3,
            "correlation_id": None,
            "created_at": "2024-01-01T00:00:00",
            "started_at": None,
            "completed_at": None,
            "ttl_seconds": 3600,
        }
        result = TaskResult.from_dict(data)
        assert result.task_id == "abc123"
        assert result.status == "failed"
        assert isinstance(result.created_at, datetime)


class TestTaskResultBackend:
    """Test in-memory task result storage."""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        backend = TaskResultBackend()
        result = TaskResult(
            task_id="t1",
            task_name="test_task",
            status="success",
            result=42,
        )
        await backend.store_result("t1", result)
        
        retrieved = await backend.get_result("t1")
        assert retrieved is not None
        assert retrieved.task_id == "t1"
        assert retrieved.result == 42
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self):
        backend = TaskResultBackend()
        result = await backend.get_result("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_results_ordered(self):
        backend = TaskResultBackend()
        
        r1 = TaskResult(task_id="t1", task_name="a", status="success",
                        created_at=datetime(2024, 1, 1))
        r2 = TaskResult(task_id="t2", task_name="b", status="success",
                        created_at=datetime(2024, 1, 2))
        r3 = TaskResult(task_id="t3", task_name="c", status="failed",
                        created_at=datetime(2024, 1, 3))
        
        await backend.store_result("t1", r1)
        await backend.store_result("t2", r2)
        await backend.store_result("t3", r3)
        
        results = await backend.get_all_results()
        assert len(results) == 3
        # Most recent first
        assert results[0].task_id == "t3"
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        backend = TaskResultBackend()
        
        # Expired result (completed 8 days ago with 7-day TTL)
        expired = TaskResult(
            task_id="old",
            task_name="old_task", 
            status="success",
            completed_at=datetime.now() - timedelta(days=8),
            ttl_seconds=604800,  # 7 days
        )
        
        # Fresh result
        fresh = TaskResult(
            task_id="new",
            task_name="new_task",
            status="success",
            completed_at=datetime.now(),
            ttl_seconds=604800,
        )
        
        await backend.store_result("old", expired)
        await backend.store_result("new", fresh)
        
        cleaned = await backend.cleanup_expired()
        assert cleaned == 1
        assert await backend.get_result("old") is None
        assert await backend.get_result("new") is not None
    
    @pytest.mark.asyncio
    async def test_dead_letter_queue(self):
        backend = TaskResultBackend()
        
        dead = TaskResult(
            task_id="d1",
            task_name="dead_task",
            status="dead_letter",
            error="Max retries exceeded",
        )
        
        await backend.store_result("d1", dead)
        
        dead_letters = await backend.get_dead_letter_tasks()
        assert len(dead_letters) == 1
        assert dead_letters[0].task_id == "d1"
    
    @pytest.mark.asyncio
    async def test_clear_dead_letter(self):
        backend = TaskResultBackend()
        
        dead = TaskResult(task_id="d1", task_name="t", status="dead_letter")
        await backend.store_result("d1", dead)
        
        count = await backend.clear_dead_letter()
        assert count == 1
        
        dead_letters = await backend.get_dead_letter_tasks()
        assert len(dead_letters) == 0
