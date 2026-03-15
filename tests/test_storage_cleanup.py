"""Test suite for automatic file cleanup on model deletion (Layer 2).

Tests verify that:
1. FileReference.link() creates references correctly
2. FileReference.cleanup_by_model() deletes files and marks references as deleted
3. Model.delete() triggers automatic cleanup
4. Integration with storage backends (local, S3, Supabase)
5. Error handling during cleanup doesn't break deletion
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from eden.db import Model, FileReference, f, Mapped
from eden.storage import StorageManager
from sqlalchemy.ext.asyncio import AsyncSession as Session


# ============================================================================
# Fixture: Test Model
# ============================================================================

class TestUser(Model):
    """Minimal test model for file associations."""
    __tablename__ = "test_users"
    
    name: Mapped[str] = f(max_length=100)
    email: Mapped[str] = f(max_length=100)


class TestPost(Model):
    """Another test model for multi-model reference tests."""
    __tablename__ = "test_posts"
    
    title: Mapped[str] = f(max_length=100)
    user_id: Mapped[UUID] = f()


@pytest.fixture
def test_user():
    """Create a test user."""
    user = TestUser(name="Alice", email="alice@example.com")
    user.id = uuid4()
    return user


@pytest.fixture
def test_post(test_user):
    """Create a test post."""
    post = TestPost(title="My Post", user_id=test_user.id)
    post.id = uuid4()
    return post


# ============================================================================
# Tests: FileReference.link()
# ============================================================================

@pytest.mark.asyncio
async def test_file_reference_link_creates_reference(test_user):
    """FileReference.link() creates a new reference with correct fields."""
    file_path = "s3://bucket/users/123/avatar.jpg"
    storage_backend = "s3"
    
    # Mock the save() to avoid DB interaction
    with patch.object(FileReference, 'save', new_callable=AsyncMock) as mock_save:
        ref = await FileReference.link(
            model_class=TestUser,
            model_id=test_user.id,
            file_path=file_path,
            storage_backend=storage_backend
        )
    
    # Verify reference was created with correct fields
    assert ref is not None
    assert ref.model_class_name == "TestUser"
    assert ref.model_instance_id == test_user.id
    assert ref.file_path == file_path
    assert ref.storage_backend == storage_backend
    assert ref.deleted_at is None


@pytest.mark.asyncio
async def test_file_reference_link_default_backend(test_user):
    """FileReference.link() defaults to 'local' storage backend."""
    file_path = "/var/uploads/file.txt"
    
    with patch.object(FileReference, 'save', new_callable=AsyncMock):
        ref = await FileReference.link(
            model_class=TestUser,
            model_id=test_user.id,
            file_path=file_path
        )
    
    assert ref.storage_backend == "local"


@pytest.mark.asyncio
async def test_file_reference_link_saves_to_database(test_user):
    """FileReference.link() persists reference to database."""
    with patch.object(FileReference, 'save', new_callable=AsyncMock) as mock_save:
        await FileReference.link(
            model_class=TestUser,
            model_id=test_user.id,
            file_path="test.jpg",
            storage_backend="s3"
        )
    
    mock_save.assert_called_once()


# ============================================================================
# Tests: FileReference.cleanup_by_model()
# ============================================================================

@pytest.mark.asyncio
async def test_cleanup_by_model_delete_all_files(test_user):
    """cleanup_by_model() deletes all storage files for the model."""
    # Create mock references
    mock_refs = [
        MagicMock(spec=FileReference, file_path="s3://bucket/users/123/avatar.jpg", storage_backend="s3"),
        MagicMock(spec=FileReference, file_path="s3://bucket/users/123/cover.jpg", storage_backend="s3"),
    ]
    
    with patch.object(FileReference, 'filter', return_value=MagicMock()) as mock_filter:
        mock_query = MagicMock()
        mock_filter.return_value = mock_query
        mock_query.all = AsyncMock(return_value=mock_refs)
        
        # Mock storage backends
        with patch('eden.db.file_reference.storage') as mock_storage:
            mock_s3_backend = AsyncMock()
            mock_storage.get.return_value = mock_s3_backend
            
            await FileReference.cleanup_by_model(TestUser, test_user.id)
        
        # Verify filter was called with correct parameters
        mock_filter.assert_called_once()
        call_kwargs = mock_filter.call_args[1]
        assert call_kwargs['model_class_name'] == 'TestUser'
        assert call_kwargs['model_instance_id'] == test_user.id
        assert call_kwargs['deleted_at'] is None
        
        # Verify delete() was called for each file
        assert mock_s3_backend.delete.call_count == 2
        mock_s3_backend.delete.assert_any_call("s3://bucket/users/123/avatar.jpg")
        mock_s3_backend.delete.assert_any_call("s3://bucket/users/123/cover.jpg")


@pytest.mark.asyncio
async def test_cleanup_by_model_marks_deleted_at(test_user):
    """cleanup_by_model() sets deleted_at timestamp on FileReference."""
    mock_ref = MagicMock(spec=FileReference)
    mock_ref.file_path = "test.jpg"
    mock_ref.storage_backend = "local"
    mock_ref.save = AsyncMock()
    
    with patch.object(FileReference, 'filter', return_value=MagicMock()) as mock_filter:
        mock_query = MagicMock()
        mock_filter.return_value = mock_query
        mock_query.all = AsyncMock(return_value=[mock_ref])
        
        with patch('eden.db.file_reference.storage') as mock_storage:
            mock_backend = AsyncMock()
            mock_storage.get.return_value = mock_backend
            
            await FileReference.cleanup_by_model(TestUser, test_user.id)
    
    # Verify deleted_at was set and saved
    assert mock_ref.deleted_at is not None
    mock_ref.save.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_by_model_handles_storage_error(test_user):
    """cleanup_by_model() continues even if storage delete fails."""
    mock_ref1 = MagicMock(spec=FileReference, file_path="file1.jpg", storage_backend="s3")
    mock_ref1.save = AsyncMock()
    mock_ref2 = MagicMock(spec=FileReference, file_path="file2.jpg", storage_backend="s3")
    mock_ref2.save = AsyncMock()
    
    with patch.object(FileReference, 'filter', return_value=MagicMock()) as mock_filter:
        mock_query = MagicMock()
        mock_filter.return_value = mock_query
        mock_query.all = AsyncMock(return_value=[mock_ref1, mock_ref2])
        
        with patch('eden.db.file_reference.storage') as mock_storage:
            mock_backend = AsyncMock()
            # First call raises error, second succeeds
            mock_backend.delete.side_effect = [IOError("S3 error"), None]
            mock_storage.get.return_value = mock_backend
            
            # Should not raise
            await FileReference.cleanup_by_model(TestUser, test_user.id)
    
    # Both marked as deleted despite first error
    assert mock_ref1.deleted_at is not None
    assert mock_ref2.deleted_at is not None


@pytest.mark.asyncio
async def test_cleanup_by_model_no_refs_for_model():
    """cleanup_by_model() handles case where no references exist."""
    with patch.object(FileReference, 'filter', return_value=MagicMock()) as mock_filter:
        mock_query = MagicMock()
        mock_filter.return_value = mock_query
        mock_query.all = AsyncMock(return_value=[])  # No refs
        
        # Should not raise
        await FileReference.cleanup_by_model(TestUser, uuid4())


# ============================================================================
# Tests: Model.delete() Integration
# ============================================================================

@pytest.mark.asyncio
async def test_model_delete_triggers_file_cleanup(test_user):
    """Model.delete() automatically calls FileReference.cleanup_by_model()."""
    with patch.object(FileReference, 'cleanup_by_model', new_callable=AsyncMock) as mock_cleanup:
        with patch('eden.db.base.Session.execute', new_callable=AsyncMock):
            # Mock the actual DB delete
            with patch.object(test_user, 'hard_delete', new_callable=AsyncMock):
                await test_user.delete()
    
    # Verify cleanup was called
    mock_cleanup.assert_called_once()
    call_args = mock_cleanup.call_args[0]
    assert call_args[0] == TestUser  # model_class
    assert call_args[1] == test_user.id  # model_id


@pytest.mark.asyncio
async def test_model_delete_cleanup_before_deletion(test_user):
    """File cleanup happens BEFORE model is deleted from DB."""
    call_order = []
    
    async def mock_cleanup(*args, **kwargs):
        call_order.append("cleanup")
    
    async def mock_hard_delete(*args, **kwargs):
        call_order.append("hard_delete")
    
    with patch.object(FileReference, 'cleanup_by_model', side_effect=mock_cleanup):
        with patch.object(test_user, 'hard_delete', side_effect=mock_hard_delete):
            await test_user.delete()
    
    # Cleanup should happen first
    assert call_order == ["cleanup", "hard_delete"]


@pytest.mark.asyncio
async def test_model_delete_continues_if_cleanup_fails(test_user):
    """Model deletion continues even if file cleanup raises error."""
    with patch.object(FileReference, 'cleanup_by_model', new_callable=AsyncMock) as mock_cleanup:
        mock_cleanup.side_effect = IOError("Storage error")
        
        with patch.object(test_user, 'hard_delete', new_callable=AsyncMock) as mock_hard_delete:
            # Should not raise, should still delete model
            await test_user.delete()
    
    mock_hard_delete.assert_called_once()


# ============================================================================
# Tests: create_from_upload() Helper
# ============================================================================

@pytest.mark.asyncio
async def test_create_from_upload_convenience_method(test_user):
    """create_from_upload() is a convenience method for upload workflows."""
    file_path = "s3://bucket/users/123/avatar.jpg"
    storage_backend = "s3"
    
    with patch.object(FileReference, 'link', new_callable=AsyncMock) as mock_link:
        mock_ref = MagicMock(spec=FileReference)
        mock_link.return_value = mock_ref
        
        ref = await FileReference.create_from_upload(
            model_class=TestUser,
            model_id=test_user.id,
            file_path=file_path,
            storage_backend=storage_backend
        )
    
    mock_link.assert_called_once_with(
        model_class=TestUser,
        model_id=test_user.id,
        file_path=file_path,
        storage_backend=storage_backend
    )
    assert ref is mock_ref


# ============================================================================
# Tests: Multi-Model Scenarios
# ============================================================================

@pytest.mark.asyncio
async def test_cleanup_does_not_affect_other_models(test_user, test_post):
    """Cleanup for one model doesn't affect another model's files."""
    # User has files
    user_refs = [
        MagicMock(spec=FileReference, file_path="avatar.jpg", storage_backend="s3"),
    ]
    # Post has files
    post_refs = [
        MagicMock(spec=FileReference, file_path="image.jpg", storage_backend="s3"),
    ]
    
    with patch.object(FileReference, 'filter', return_value=MagicMock()) as mock_filter:
        mock_query = MagicMock()
        mock_filter.return_value = mock_query
        # Return user refs only
        mock_query.all = AsyncMock(return_value=user_refs)
        
        with patch('eden.db.file_reference.storage') as mock_storage:
            mock_backend = AsyncMock()
            mock_storage.get.return_value = mock_backend
            
            await FileReference.cleanup_by_model(TestUser, test_user.id)
    
    # Only user file should be deleted
    mock_backend.delete.assert_called_once_with("avatar.jpg")


@pytest.mark.asyncio
async def test_cleanup_different_storage_backends():
    """cleanup_by_model() handles files from different storage backends."""
    ref_s3 = MagicMock(spec=FileReference, file_path="s3://key", storage_backend="s3")
    ref_s3.save = AsyncMock()
    ref_local = MagicMock(spec=FileReference, file_path="/var/uploads/file", storage_backend="local")
    ref_local.save = AsyncMock()
    
    with patch.object(FileReference, 'filter', return_value=MagicMock()) as mock_filter:
        mock_query = MagicMock()
        mock_filter.return_value = mock_query
        mock_query.all = AsyncMock(return_value=[ref_s3, ref_local])
        
        with patch('eden.db.file_reference.storage') as mock_storage:
            mock_s3_backend = AsyncMock()
            mock_local_backend = AsyncMock()
            mock_storage.get.side_effect = lambda x: {
                "s3": mock_s3_backend,
                "local": mock_local_backend
            }[x]
            
            await FileReference.cleanup_by_model(TestUser, uuid4())
    
    # Both backends should be called
    mock_storage.get.assert_any_call("s3")
    mock_storage.get.assert_any_call("local")
    mock_s3_backend.delete.assert_called_once_with("s3://key")
    mock_local_backend.delete.assert_called_once_with("/var/uploads/file")


# ============================================================================
# Tests: Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_cleanup_with_unicode_paths(test_user):
    """cleanup_by_model() handles Unicode file paths correctly."""
    mock_ref = MagicMock(spec=FileReference)
    mock_ref.file_path = "s3://bucket/用户/ファイル.jpg"  # Chinese + Japanese
    mock_ref.storage_backend = "s3"
    mock_ref.save = AsyncMock()
    
    with patch.object(FileReference, 'filter', return_value=MagicMock()) as mock_filter:
        mock_query = MagicMock()
        mock_filter.return_value = mock_query
        mock_query.all = AsyncMock(return_value=[mock_ref])
        
        with patch('eden.db.file_reference.storage') as mock_storage:
            mock_backend = AsyncMock()
            mock_storage.get.return_value = mock_backend
            
            await FileReference.cleanup_by_model(TestUser, test_user.id)
    
    mock_backend.delete.assert_called_once_with("s3://bucket/用户/ファイル.jpg")


@pytest.mark.asyncio
async def test_cleanup_with_very_long_paths(test_user):
    """cleanup_by_model() handles very long file paths."""
    long_path = "s3://bucket/" + ("x" * 2000) + ".jpg"
    mock_ref = MagicMock(spec=FileReference)
    mock_ref.file_path = long_path
    mock_ref.storage_backend = "s3"
    mock_ref.save = AsyncMock()
    
    with patch.object(FileReference, 'filter', return_value=MagicMock()) as mock_filter:
        mock_query = MagicMock()
        mock_filter.return_value = mock_query
        mock_query.all = AsyncMock(return_value=[mock_ref])
        
        with patch('eden.db.file_reference.storage') as mock_storage:
            mock_backend = AsyncMock()
            mock_storage.get.return_value = mock_backend
            
            await FileReference.cleanup_by_model(TestUser, test_user.id)
    
    mock_backend.delete.assert_called_once_with(long_path)


@pytest.mark.asyncio
async def test_file_reference_query_only_active_references():
    """cleanup_by_model() only targets references with deleted_at=None."""
    # Create mock references - one already deleted
    active_ref = MagicMock(spec=FileReference, file_path="active.jpg", storage_backend="s3")
    active_ref.save = AsyncMock()
    already_deleted = MagicMock(spec=FileReference, file_path="deleted.jpg", storage_backend="s3")
    already_deleted.deleted_at = datetime.utcnow()
    
    with patch.object(FileReference, 'filter', return_value=MagicMock()) as mock_filter:
        mock_query = MagicMock()
        mock_filter.return_value = mock_query
        # Only active should be returned
        mock_query.all = AsyncMock(return_value=[active_ref])
        
        with patch('eden.db.file_reference.storage') as mock_storage:
            mock_backend = AsyncMock()
            mock_storage.get.return_value = mock_backend
            
            await FileReference.cleanup_by_model(TestUser, uuid4())
    
    # Verify filter excluded already deleted
    filter_call_kwargs = mock_filter.call_args[1]
    assert filter_call_kwargs['deleted_at'] is None
    
    # Only active file deleted
    mock_backend.delete.assert_called_once_with("active.jpg")
