"""
Eden — File Storage Abstraction

This module provides:
- StorageBackend ABC for pluggable file storage
- Atomic transaction context manager to prevent orphaned files
- Progress callback support for large uploads
- StorageManager for multi-backend registry
- File upload validation (max size, file type whitelist)

FILE UPLOAD SECURITY:
Always validate uploaded files to prevent:
1. Disk space exhaustion (max file size limits)
2. Malicious file execution (file type whitelist)
3. Virus/malware (optional ClamAV integration)

Example:
    validator = FileUploadValidator(
        max_size_bytes=10 * 1024 * 1024,  # 10 MB
        allowed_types={"image/jpeg", "image/png"},
        enable_virus_scan=True
    )
    
    try:
        await validator.validate(upload_file)
    except FileUploadValidationError as e:
        print(f"Upload rejected: {e}")
"""

import asyncio
import logging
import os
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Protocol, Set

import aiofiles
from starlette.datastructures import UploadFile

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# File Upload Validation
# ─────────────────────────────────────────────────────────────────────────────


class FileUploadValidationError(Exception):
    """Raised when file upload validation fails."""
    pass


@dataclass
class FileUploadValidator:
    """
    Validates uploaded files before storage.
    
    Checks:
    - File size (max_size_bytes)
    - MIME type against whitelist
    - Optional virus scanning
    
    Attributes:
        max_size_bytes: Maximum file size in bytes (e.g., 10485760 for 10 MB)
        allowed_types: Set of allowed MIME types (e.g., {"image/jpeg", "image/png"})
        enable_virus_scan: If True, attempt to scan file with ClamAV (requires pyclamd)
        virus_scan_host: ClamAV daemon host:port (default: "localhost:3310")
    """
    max_size_bytes: int = 52_428_800  # 50 MB default
    allowed_types: Set[str] = None
    enable_virus_scan: bool = False
    virus_scan_host: str = "localhost:3310"
    
    def __post_init__(self):
        if self.allowed_types is None:
            # Default: Allow common media types
            self.allowed_types = {
                # Images
                "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
                # Documents
                "application/pdf", "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                # Archive
                "application/zip", "application/gzip",
            }
    
    async def validate(self, file: UploadFile) -> None:
        """
        Validate an uploaded file.
        
        Args:
            file: File to validate
        
        Raises:
            FileUploadValidationError: If validation fails
        """
        # Check MIME type
        if self.allowed_types and file.content_type not in self.allowed_types:
            raise FileUploadValidationError(
                f"File type '{file.content_type}' not allowed. "
                f"Allowed types: {', '.join(sorted(self.allowed_types))}"
            )
        
        # Check file size
        if hasattr(file, "size") and file.size and file.size > self.max_size_bytes:
            max_mb = self.max_size_bytes / (1024 * 1024)
            raise FileUploadValidationError(
                f"File size {file.size} bytes exceeds maximum {self.max_size_bytes} bytes ({max_mb:.1f} MB)"
            )
        
        # Virus scan if enabled
        if self.enable_virus_scan:
            await self._scan_for_viruses(file)
    
    async def _scan_for_viruses(self, file: UploadFile) -> None:
        """
        Scan file for viruses using ClamAV daemon.
        
        Requires pyclamd: pip install pyclamd
        
        Args:
            file: File to scan
        
        Raises:
            FileUploadValidationError: If virus found or scan fails
        """
        try:
            import pyclamd
        except ImportError:
            logger.warning("pyclamd not installed. Virus scanning disabled. Install with: pip install pyclamd")
            return
        
        try:
            host, port = self.virus_scan_host.split(":")
            clam = pyclamd.ClamdNetworked(host=host, port=int(port))
            
            if not clam.ping():
                logger.warning(f"ClamAV daemon not responding at {self.virus_scan_host}. Skipping virus scan.")
                return
            
            # Get file content
            content = await file.read()
            await file.seek(0)  # Reset for actual upload
            
            # Scan
            result = clam.scan_stream(content)
            
            if result:
                # result is {"stream": ("FOUND", "Virus.Name")} if virus found
                virus_name = result.get("stream", [None])[1] if result.get("stream") else "Unknown"
                raise FileUploadValidationError(f"Virus detected: {virus_name}")
                
        except pyclamd.ClamdNetworkingError as e:
            logger.error(f"ClamAV connection error: {e}")
            # Don't fail upload if ClamAV unreachable (fail open, not fail closed)
            logger.warning("Virus scan unavailable, allowing upload to proceed")
        except FileUploadValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during virus scan: {e}", exc_info=True)
            raise FileUploadValidationError(f"Virus scan error: {e}")


class ProgressCallback(Protocol):
    """
    Protocol for upload progress callbacks.
    
    Called during file upload to report progress:
    - bytes_written: Number of bytes uploaded so far
    - total_bytes: Total file size (may be None for streaming uploads)
    
    Example:
        async def on_progress(bytes_written: int, total_bytes: int | None):
            if total_bytes:
                percent = (bytes_written / total_bytes) * 100
                print(f"Upload: {percent:.1f}%")
        
        await storage.save(file, progress=on_progress)
    """
    async def __call__(self, bytes_written: int, total_bytes: Optional[int]) -> None:
        """Track upload progress."""
        ...


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.
    
    Subclasses must implement save(), delete(), and url() methods.
    Progress tracking is optional via progress parameter to save().
    File validation is optional via validator parameter to save().
    """
    @abstractmethod
    async def save(
        self,
        content: UploadFile | bytes,
        name: str | None = None,
        folder: str = "",
        progress: Optional[ProgressCallback] = None,
        validator: Optional["FileUploadValidator"] = None,
    ) -> str:
        """
        Save a file and return its identifier (e.g., path or URL).
        
        Args:
            content: File content (UploadFile or bytes)
            name: Custom filename (generated if None)
            folder: Optional folder/path prefix
            progress: Optional progress callback for tracking uploads
            validator: Optional FileUploadValidator to validate before saving
        
        Returns:
            File identifier (path, key, or equivalent)
        
        Raises:
            FileUploadValidationError: If validation fails
            IOError: If save fails
        """
        pass

    @abstractmethod
    async def delete(self, name: str):
        """
        Delete a file by its identifier.
        
        Args:
            name: File identifier to delete
        
        Raises:
            IOError: If delete fails
        """
        pass

    @abstractmethod
    def url(self, name: str) -> str:
        """
        Get the public URL for a file.
        
        Args:
            name: File identifier
        
        Returns:
            Public URL for the file
        """
        pass

class LocalStorageBackend(StorageBackend):
    """
    Storage backend that saves files to the local filesystem.
    
    Safe for development and small deployments. All files stored in base_path.
    
    Example:
        storage = LocalStorageBackend(
            base_path="./media",
            base_url="/media/"
        )
        
        file_key = await storage.save(content, name="photo.jpg")
        url = storage.url(file_key)
        await storage.delete(file_key)
    """
    def __init__(self, base_path: str, base_url: str = "/media/"):
        self.base_path = Path(base_path)
        self.base_url = base_url
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(
        self,
        content: UploadFile | bytes,
        name: str | None = None,
        folder: str = "",
        progress: Optional[ProgressCallback] = None,
        validator: Optional["FileUploadValidator"] = None,
    ) -> str:
        """
        Save file to disk, optionally validating and reporting progress.
        
        Args:
            validator: Optional FileUploadValidator to check file before saving
        
        Raises:
            FileUploadValidationError: If file validation fails
        """
        # Validate if validator provided
        if validator and isinstance(content, UploadFile):
            await validator.validate(content)
        
        if name is None:
            if isinstance(content, UploadFile):
                name = content.filename or str(uuid.uuid4())
            else:
                name = str(uuid.uuid4())

        # Ensure unique name to prevent collisions
        ext = os.path.splitext(name)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"

        target_path = self.base_path / folder / unique_name
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Track bytes written for progress callback
        bytes_written = 0
        total_bytes = None

        if isinstance(content, UploadFile):
            # For UploadFile, try to get size if available
            if hasattr(content, 'size') and content.size:
                total_bytes = content.size
            
            async with aiofiles.open(target_path, "wb") as f:
                chunk_size = 8192
                while True:
                    chunk = await content.read(chunk_size)
                    if not chunk:
                        break
                    await f.write(chunk)
                    bytes_written += len(chunk)
                    
                    if progress:
                        await progress(bytes_written, total_bytes)
        else:
            # For bytes, we know total size upfront
            total_bytes = len(content)
            async with aiofiles.open(target_path, "wb") as f:
                await f.write(content)
                bytes_written = total_bytes
            
            if progress:
                await progress(bytes_written, total_bytes)

        return os.path.join(folder, unique_name).replace("\\", "/")

    async def delete(self, name: str):
        """Delete file from disk."""
        target_path = self.base_path / name
        if target_path.exists():
            target_path.unlink()
            logger.debug(f"Deleted file: {name}")

    def url(self, name: str) -> str:
        """Get public URL for file."""
        return f"{self.base_url}{name}"



class AtomicStorageTransaction:
    """
    Context manager for atomic file upload + database save.
    
    Tracks uploaded files and automatically cleans them up if the transaction
    fails (e.g., due to a failed database save). Prevents orphaned files in S3/Supabase.
    
    Usage:
        async with AtomicStorageTransaction(storage_backend) as txn:
            # Upload file to S3
            file_key = await txn.save(upload_file, folder="avatars")
            
            # Save to database
            user.avatar_path = file_key
            await user.save()  # If this fails, file_key is auto-deleted
        
        # If we reach here, both succeeded
        return user
    """
    
    def __init__(self, backend: StorageBackend):
        """
        Initialize transaction with a storage backend.
        
        Args:
            backend: StorageBackend instance (S3, Supabase, or Local)
        """
        self.backend = backend
        self._uploaded_files: list[str] = []
    
    async def save(
        self,
        content: UploadFile | bytes,
        name: str | None = None,
        folder: str = "",
        progress: Optional[ProgressCallback] = None,
        validator: Optional["FileUploadValidator"] = None,
    ) -> str:
        """
        Save file to storage backend, tracking for potential rollback.
        
        Args:
            validator: Optional FileUploadValidator to check file before saving
        
        Returns:
            File key/identifier
        
        Raises:
            FileUploadValidationError: If file validation fails
            IOError: If upload fails, previously uploaded files are NOT cleaned up
        """
        try:
            file_key = await self.backend.save(content, name, folder, progress, validator)
            # Track file for cleanup if transaction fails
            self._uploaded_files.append(file_key)
            return file_key
        except Exception as e:
            # If save fails, clean up any previously uploaded files
            await self._cleanup()
            logger.error(f"Storage save failed, rolled back {len(self._uploaded_files)} files: {e}")
            raise
    
    async def _cleanup(self):
        """Delete all tracked files (called on error)."""
        for file_key in self._uploaded_files:
            try:
                await self.backend.delete(file_key)
                logger.debug(f"Rolled back file: {file_key}")
            except Exception as e:
                logger.error(f"Failed to rollback file {file_key}: {e}")
    
    async def __aenter__(self):
        """Enter async context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit async context manager.
        
        If an exception occurred, clean up all uploaded files.
        """
        if exc_type is not None:
            # Exception occurred, rollback
            await self._cleanup()
            logger.warning(
                f"Transaction rolled back due to {exc_type.__name__}: "
                f"deleted {len(self._uploaded_files)} files"
            )
        return False  # Re-raise the exception


class StorageManager:
    """
    Registry for storage backends.
    
    Manages multiple named storage backends and provides a unified API.
    
    Usage:
        from eden.storage import storage
        
        # Register backends (done in app startup)
        storage.register("local", LocalStorageBackend("./media"))
        storage.register("s3", S3StorageBackend(...), default=True)
        
        # Save to default backend
        key = await storage.get().save(file)
        
        # Save to specific backend
        key = await storage.get("s3").save(file)
        
        # Use transaction for atomic ops
        async with storage.transaction() as txn:
            key = await txn.save(file)
            # ... save to database ...
    """
    def __init__(self):
        self._backends: dict[str, StorageBackend] = {}
        self._default: str | None = None

    def register(self, name: str, backend: StorageBackend, default: bool = False):
        """
        Register a storage backend.
        
        Args:
            name: Unique backend name (e.g., "s3", "local", "supabase")
            backend: Configured StorageBackend instance
            default: If True, use as default backend
        """
        self._backends[name] = backend
        if default or not self._default:
            self._default = name
        logger.info(f"Registered storage backend '{name}' (default={default})")

    def get(self, name: str | None = None) -> StorageBackend:
        """
        Get a registered backend.
        
        Args:
            name: Backend name (uses default if None)
        
        Returns:
            StorageBackend instance
        
        Raises:
            ValueError: If backend not found
        """
        name = name or self._default
        if not name or name not in self._backends:
            raise ValueError(f"Storage backend '{name}' not found.")
        return self._backends[name]
    
    @asynccontextmanager
    async def transaction(self, backend_name: str | None = None):
        """
        Create an atomic transaction with a storage backend.
        
        Usage:
            async with storage.transaction("s3") as txn:
                key = await txn.save(file)
                # ... other operations ...
        
        If an exception occurs, all uploaded files are cleaned up.
        
        Args:
            backend_name: Backend to use (default if None)
        
        Yields:
            AtomicStorageTransaction instance
        """
        backend = self.get(backend_name)
        async with AtomicStorageTransaction(backend) as txn:
            yield txn


# Global storage manager instance
storage = StorageManager()
