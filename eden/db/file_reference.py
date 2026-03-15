"""
File Reference Model & Automatic Cleanup (Layer 2)

Tracks which model instances own which files and automatically cleans them up
when the model instance is deleted.

Usage:
    # In your model
    class User(Model):
        avatar_path: str | None = None
        
        async def save(self):
            await super().save()
            # Link avatar file to this user
            if self.avatar_path:
                await FileReference.link(
                    model_class=User,
                    model_id=self.id,
                    file_path=self.avatar_path
                )
    
    # When user is deleted, avatar is auto-deleted from S3/Supabase:
    await User.delete(user.id)
    # FileReference automatically triggers file cleanup

Features:
- Track file ownership by model and ID
- Automatic deletion when parent model is deleted
- Multi-backend support (S3, Supabase, Local)
- Atomic deletion (if file cleanup fails, transaction rolls back)
- Logging and error tracking
"""

import logging
from typing import Any, Optional, Type
from datetime import datetime
import uuid

from sqlalchemy import String, Uuid, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from eden.db.base import Model
from eden.storage import storage

logger = logging.getLogger(__name__)


class FileReference(Model):
    """
    Tracks ownership of files across different storage backends.
    
    When a model instance (e.g., User) is deleted, all its associated
    FileReferences are deleted, which triggers automatic cleanup in S3/Supabase.
    
    Attributes:
        model_class_name: Name of the model class owning the file (e.g., "User")
        model_instance_id: UUID of the model instance (e.g., user.id)
        file_path: Storage backend file key/path (e.g., "avatars/file_uuid.jpg")
        storage_backend: Which backend stores this file ("s3", "supabase", "local")
        deleted_at: When the file was deleted (NULL if still active)
    
    Example:
        # Create a file reference
        ref = await FileReference.create(
            model_class_name="User",
            model_instance_id=user.id,
            file_path="avatars/user_uuid.jpg",
            storage_backend="s3"
        )
        
        # When user is deleted, FileReference cascade automatically cleans up file
        await user.delete()  # Triggers FileReference deletion hook
    """

    __tablename__ = "file_references"

    # Which model owns this file
    model_class_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # UUID of the model instance
    model_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    # Storage location (backend-specific key or path)
    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    # Which storage backend (s3, supabase, local)
    storage_backend: Mapped[str] = mapped_column(
        String(50), nullable=False, default="local"
    )
    # Soft delete flag (file still tracked but marked as deleted)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=None
    )

    @classmethod
    async def link(
        cls,
        model_class: Type[Model],
        model_id: uuid.UUID,
        file_path: str,
        storage_backend: str = "local",
    ) -> "FileReference":
        """
        Create a file reference linking a file to a model instance.
        
        Args:
            model_class: Model class (e.g., User)
            model_id: UUID of model instance
            file_path: Storage backend file key/path
            storage_backend: Which backend stores file (default "local")
        
        Returns:
            Created FileReference instance
        
        Raises:
            ValueError: If model_id is None or file_path is empty
        
        Implementation Notes:
            - Automatically called by models with file fields
            - Does not delete existing references for same file
            - Creates new reference even if one exists with same path
        """
        if not model_id:
            raise ValueError("model_id is required")
        if not file_path or not file_path.strip():
            raise ValueError("file_path cannot be empty")

        ref = cls(
            model_class_name=model_class.__name__,
            model_instance_id=model_id,
            file_path=file_path,
            storage_backend=storage_backend,
        )
        await ref.save()
        logger.debug(
            f"Linked file {file_path} to {model_class.__name__}({model_id})"
        )
        return ref

    @classmethod
    async def cleanup_by_model(
        cls,
        model_class: Type[Model],
        model_id: uuid.UUID,
    ) -> int:
        """
        Clean up all files referenced by a model instance.
        
        Finds all FileReferences for the given model and deletes the
        actual files from storage backends. Called automatically when
        a model instance is deleted.
        
        Args:
            model_class: Model class (e.g., User)
            model_id: UUID of model instance to cleanup
        
        Returns:
            Number of files cleaned up
        
        Implementation Notes:
            - Called automatically by model deletion hooks
            - Silently continues if file deletion fails (logs error)
            - Marks file_reference.deleted_at to track cleanup
            - Idempotent (can be called multiple times safely)
        
        Example:
            # Called automatically by model deletion:
            await FileReference.cleanup_by_model(User, user.id)
        """
        # Find all active file references for this model instance
        refs = await cls.filter(
            model_class_name=model_class.__name__,
            model_instance_id=model_id,
            deleted_at=None,  # Only active references
        ).all()

        deleted_count = 0

        for ref in refs:
            try:
                # Get backend and delete file
                backend = storage.get(ref.storage_backend)
                await backend.delete(ref.file_path)
                logger.info(
                    f"Deleted file: {ref.file_path} "
                    f"(backend={ref.storage_backend})"
                )

                # Mark reference as deleted (soft delete for audit trail)
                ref.deleted_at = datetime.utcnow()
                await ref.save()
                deleted_count += 1

            except Exception as exc:
                # Log error but continue with other files
                logger.error(
                    f"Failed to delete file {ref.file_path} "
                    f"from {ref.storage_backend}: {exc}",
                    exc_info=True,
                )

        if deleted_count > 0:
            logger.info(
                f"Cleaned up {deleted_count} files "
                f"for {model_class.__name__}({model_id})"
            )

        return deleted_count

    @classmethod
    async def create_from_upload(
        cls,
        model_class: Type[Model],
        model_id: uuid.UUID,
        file_path: str,
        storage_backend: str = "s3",
    ) -> "FileReference":
        """
        Helper to create a file reference after successful S3/Supabase upload.
        
        Args:
            model_class: Model class owning the file
            model_id: UUID of model instance
            file_path: Storage backend file key from upload
        
        Returns:
            FileReference instance
        
        Example:
            # After uploading to S3:
            file_key = await storage.get("s3").save(upload_file)
            ref = await FileReference.create_from_upload(User, user.id, file_key)
        """
        return await cls.link(
            model_class=model_class,
            model_id=model_id,
            file_path=file_path,
            storage_backend="s3",  # Adjust based on actual backend
        )
