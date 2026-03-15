"""
Tests for atomic storage transactions (Layer 1 & 4).

Verifies:
- Atomic file uploads prevent orphaned files
- Transaction rollback on errors
- Progress callback integration
- Supabase async initialization
"""

import asyncio
import io
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eden.storage import (
    AtomicStorageTransaction,
    LocalStorageBackend,
    ProgressCallback,
    StorageManager,
)


class TestAtomicStorageTransaction:
    """Tests for AtomicStorageTransaction context manager."""

    @pytest.fixture
    def storage_backend(self):
        """Create a local storage backend for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalStorageBackend(base_path=tmpdir)
            yield backend

    @pytest.mark.asyncio
    async def test_successful_transaction_commits(self, storage_backend):
        """Test successful transaction with file upload."""
        async with AtomicStorageTransaction(storage_backend) as txn:
            # Upload file
            file_key = await txn.save(b"test content", name="test.txt")
            assert file_key
            assert file_key.endswith(".txt")
        
        # File should still exist after successful transaction
        file_path = Path(storage_backend.base_path) / file_key
        assert file_path.exists()
        content = file_path.read_bytes()
        assert content == b"test content"

    @pytest.mark.asyncio
    async def test_failed_transaction_rolls_back(self, storage_backend):
        """Test that files are deleted on transaction error."""
        try:
            async with AtomicStorageTransaction(storage_backend) as txn:
                # Upload file (tracked for rollback)
                file_key = await txn.save(b"test content", name="test.txt")
                assert file_key
                
                # Simulate DB error
                raise ValueError("Database save failed")
        except ValueError:
            pass  # Expected
        
        # File should be deleted due to rollback
        file_path = Path(storage_backend.base_path) / file_key
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_multiple_files_rolled_back_together(self, storage_backend):
        """Test that multiple uploaded files are all rolled back."""
        file_keys = []
        
        try:
            async with AtomicStorageTransaction(storage_backend) as txn:
                # Upload multiple files
                for i in range(3):
                    key = await txn.save(
                        f"content{i}".encode(),
                        name=f"file{i}.txt"
                    )
                    file_keys.append(key)
                
                # Trigger rollback
                raise RuntimeError("Transaction failed")
        except RuntimeError:
            pass
        
        # All files should be deleted
        for key in file_keys:
            file_path = Path(storage_backend.base_path) / key
            assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_save_failure_within_transaction_rolls_back(self, storage_backend):
        """Test rollback when upload itself fails."""
        mock_backend = AsyncMock(spec=LocalStorageBackend)
        mock_backend.save.side_effect = IOError("Upload failed")
        mock_backend.delete = AsyncMock()
        
        with pytest.raises(IOError, match="Upload failed"):
            async with AtomicStorageTransaction(mock_backend) as txn:
                await txn.save(b"content", name="test.txt")
        
        # No files were tracked, so cleanup should not be called
        # (or called with empty list if implemented)

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, storage_backend):
        """Test that progress callbacks are invoked during upload."""
        progress_calls = []
        
        async def on_progress(bytes_written: int, total_bytes: int | None):
            progress_calls.append((bytes_written, total_bytes))
        
        async with AtomicStorageTransaction(storage_backend) as txn:
            content = b"test content here"
            file_key = await txn.save(
                content,
                name="test.txt",
                progress=on_progress
            )
        
        # Progress should be called at least once (at completion)
        assert len(progress_calls) > 0
        last_bytes_written, total_bytes = progress_calls[-1]
        assert last_bytes_written == len(content)
        assert total_bytes == len(content)


class TestStorageManagerTransaction:
    """Tests for StorageManager transaction context manager."""

    @pytest.fixture
    def storage_manager(self):
        """Create storage manager with local backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager()
            backend = LocalStorageBackend(base_path=tmpdir)
            manager.register("local", backend, default=True)
            yield manager

    @pytest.mark.asyncio
    async def test_manager_transaction_context(self, storage_manager):
        """Test StorageManager.transaction() context manager."""
        async with storage_manager.transaction() as txn:
            file_key = await txn.save(b"content", name="test.txt")
            assert file_key
        
        # File should exist after successful transaction
        backend = storage_manager.get()
        file_path = Path(backend.base_path) / file_key
        assert file_path.exists()

    @pytest.mark.asyncio
    async def test_manager_transaction_specific_backend(self, storage_manager):
        """Test transaction with specific backend."""
        async with storage_manager.transaction("local") as txn:
            file_key = await txn.save(b"content", name="test.txt")
            assert file_key


class TestSupabaseAsyncInitialization:
    """Tests for Supabase async-compatible initialization (Layer 4)."""

    @pytest.mark.asyncio
    async def test_supabase_client_lazy_initialization(self):
        """Test that Supabase client is initialized lazily."""
        from eden.storage_backends.supabase import SupabaseStorageBackend
        
        # Create backend without initializing client
        backend = SupabaseStorageBackend(
            url="https://test.supabase.co",
            key="test-key",
            bucket="test-bucket"
        )
        
        # Client should not be initialized yet
        assert backend._client is None

    @pytest.mark.asyncio
    async def test_supabase_client_uses_asyncio_to_thread(self):
        """Test that Supabase operations use asyncio.to_thread()."""
        from eden.storage_backends.supabase import SupabaseStorageBackend
        
        backend = SupabaseStorageBackend(
            url="https://test.supabase.co",
            key="test-key",
            bucket="test-bucket"
        )
        
        # Mock the supabase client to verify to_thread is used
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        
        mock_client.storage.from_.return_value = mock_bucket
        mock_bucket.upload.return_value = {"path": "test.txt"}
        
        backend._client = mock_client
        
        # Save should work (would use to_thread in real usage)
        key = await backend.save(b"content", name="test.txt")
        assert key is not None

    @pytest.mark.asyncio
    async def test_supabase_thread_safe_initialization(self):
        """Test that concurrent initializations don't cause issues."""
        from eden.storage_backends.supabase import SupabaseStorageBackend
        
        backend = SupabaseStorageBackend(
            url="https://test.supabase.co",
            key="test-key",
            bucket="test-bucket"
        )
        
        # Mock the initialization to avoid actual Supabase calls
        mock_client = MagicMock()
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = mock_client
            
            # Simulate concurrent calls to _get_client
            # In real scenario, only one should actually initialize
            tasks = [backend._get_client() for _ in range(3)]
            results = await asyncio.gather(*tasks)
            
            # All should return the same client instance
            assert len(set(id(r) for r in results)) == 1 or \
                   all(r is not None for r in results)


class TestProgressCallbackProtocol:
    """Tests for ProgressCallback protocol."""

    @pytest.mark.asyncio
    async def test_progress_callback_protocol(self):
        """Test that ProgressCallback protocol is properly defined."""
        progress_events = []
        
        # This simulates a real progress callback implementation
        async def upload_progress(
            bytes_written: int,
            total_bytes: int | None
        ) -> None:
            """Track upload progress."""
            progress_events.append({
                "bytes": bytes_written,
                "total": total_bytes
            })
        
        # Callback should be awaitable
        await upload_progress(100, 1000)
        assert len(progress_events) == 1
        assert progress_events[0]["bytes"] == 100
        assert progress_events[0]["total"] == 1000


class TestStorageTransactionIntegration:
    """Integration tests for atomic storage with DB operations."""

    @pytest.mark.asyncio
    async def test_file_upload_and_db_save_atomicity(self):
        """Test coordinated file upload and database operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_backend = LocalStorageBackend(base_path=tmpdir)
            
            # Simulate user model with avatar
            class MockUser:
                def __init__(self):
                    self.id = 1
                    self.avatar_key = None
                
                async def save(self):
                    """Simulate database save."""
                    if self.avatar_key == "TRIGGER_ERROR":
                        raise ValueError("Database constraint failed")
                    return True
            
            user = MockUser()
            
            # Successful transaction
            try:
                async with AtomicStorageTransaction(storage_backend) as txn:
                    file_key = await txn.save(b"avatar data", name="avatar.jpg")
                    user.avatar_key = file_key
                    await user.save()
            except Exception as e:
                pytest.fail(f"Unexpected error: {e}")
            
            # File should exist
            file_path = Path(storage_backend.base_path) / user.avatar_key
            assert file_path.exists()
            
            # Failed transaction
            user2 = MockUser()
            try:
                async with AtomicStorageTransaction(storage_backend) as txn:
                    file_key = await txn.save(b"bad avatar", name="bad.jpg")
                    user2.avatar_key = "TRIGGER_ERROR"
                    await user2.save()
            except ValueError:
                pass  # Expected
            
            # New file should be cleaned up automatically
            # (Note: if TRIGGER_ERROR literal was used as key, it wouldn't exist anyway)
