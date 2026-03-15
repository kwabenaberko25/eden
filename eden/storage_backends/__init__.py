"""
Eden — Storage Backends

Pluggable storage backends: S3, Supabase, Local.

Exports:
- S3StorageBackend: AWS S3 storage with presigned URLs
- SupabaseStorageBackend: Supabase Storage with signed URLs
- LocalStorageBackend: Filesystem storage (in eden.storage)
- ProgressCallback: Protocol for upload progress tracking
- AtomicStorageTransaction: Context manager for atomic uploads (in eden.storage)
- StorageManager: Multi-backend registry (in eden.storage)
"""

from eden.storage_backends.s3 import S3StorageBackend
from eden.storage_backends.supabase import SupabaseStorageBackend

__all__ = [
    "S3StorageBackend",
    "SupabaseStorageBackend",
]
