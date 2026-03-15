"""
Eden — Supabase Storage Backend

Async-compatible Supabase Storage integration using asyncio.to_thread() for
blocking SDK calls.

Requires: `uv add supabase` or `pip install supabase`

Usage:
    from eden.storage_backends.supabase import SupabaseStorageBackend

    storage = SupabaseStorageBackend(
        url="https://your-project.supabase.co",
        key="your-service-role-key",
        bucket="uploads",
    )
    app.storage.register("supabase", storage, default=True)
    
    # Save file
    key = await storage.save(upload_file, folder="documents")
    
    # Get URL
    url = storage.url(key)
    
    # Get signed URL (private access)
    signed_url = await storage.get_signed_url(key, expires_in=3600)
"""

import asyncio
import logging
import mimetypes
import os
import uuid
from typing import Optional

from starlette.datastructures import UploadFile

from eden.storage import StorageBackend, ProgressCallback

logger = logging.getLogger(__name__)


class SupabaseStorageBackend(StorageBackend):
    """
    Supabase Storage backend with async-compatible initialization.
    
    Features:
    - Async file operations (uses asyncio.to_thread for blocking calls)
    - Progress tracking for uploads
    - Signed URLs for private objects
    - Public/private bucket support
    
    Why asyncio.to_thread()?
    ========================
    The Supabase Python SDK is synchronous, but we need async compatibility
    in an async framework. asyncio.to_thread() runs blocking SDK calls in a
    thread pool, keeping the event loop responsive.
    
    Example:
        backend = SupabaseStorageBackend(
            url=os.getenv("SUPABASE_URL"),
            key=os.getenv("SUPABASE_KEY"),
            bucket="media",
            public=True
        )
        
        # Save file
        key = await backend.save(file, folder="avatars")
        
        # Get signed URL for private file
        signed_url = await backend.get_signed_url(key, expires_in=1800)
        
        # Delete
        await backend.delete(key)
    """

    def __init__(
        self,
        url: str,
        key: str,
        bucket: str = "uploads",
        public: bool = True,
    ):
        """
        Initialize Supabase storage backend.
        
        Args:
            url: Supabase project URL (e.g., https://xxxxx.supabase.co)
            key: Service role key (for server-side access)
            bucket: Bucket name in Supabase Storage
            public: If True, files are publicly accessible
        
        Note:
            Client initialization is deferred (lazy-loaded) to avoid blocking
            the event loop during app startup.
        """
        try:
            import supabase
        except ImportError:
            raise ImportError(
                "supabase is required for SupabaseStorageBackend. "
                "Install it with: uv add supabase"
            )

        self.url = url.rstrip("/")
        self.key = key
        self.bucket = bucket
        self.public = public
        self._client = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self):
        """
        Lazily initialize and cache the Supabase client (thread-safe).
        
        Client initialization is deferred to avoid blocking at startup.
        First call initializes the client, subsequent calls return cached instance.
        
        Returns:
            Initialized Supabase client
        """
        if self._client is not None:
            return self._client

        async with self._client_lock:
            # Double-check pattern: another coroutine may have initialized it
            if self._client is not None:
                return self._client

            try:
                from supabase import create_client

                # Run blocking client creation in thread pool
                self._client = await asyncio.to_thread(
                    create_client, self.url, self.key
                )
                logger.info(f"Initialized Supabase client for bucket '{self.bucket}'")
                return self._client
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise IOError(f"Supabase initialization failed: {str(e)}") from e

    async def save(
        self,
        content: UploadFile | bytes,
        name: str | None = None,
        folder: str = "",
        progress: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Save file to Supabase Storage.
        
        Args:
            content: File content (UploadFile or bytes)
            name: Custom filename (generated if None)
            folder: Supabase folder/prefix
            progress: Optional callback for upload progress (reports at completion)
        
        Returns:
            Supabase file path (object key)
        
        Raises:
            IOError: If upload fails
        
        Implementation Notes:
            - Files uploaded with unique names to prevent collisions
            - MIME type auto-detected from filename
            - Blocking Supabase SDK calls run in thread pool (not event loop)
            - Progress callback called at end of upload (Supabase SDK limitation)
        """
        if name is None:
            if isinstance(content, UploadFile):
                name = content.filename or str(uuid.uuid4())
            else:
                name = str(uuid.uuid4())

        # Ensure unique name while preserving original name for traceability
        base_name, ext = os.path.splitext(name)
        unique_name = f"{base_name}_{uuid.uuid4().hex[:8]}{ext}"
        key = os.path.join(folder, unique_name).replace("\\", "/").lstrip("/")

        # Detect MIME type
        content_type, _ = mimetypes.guess_type(name)
        if not content_type:
            content_type = "application/octet-stream"

        try:
            client = await self._get_client()

            # Read file content
            if isinstance(content, UploadFile):
                file_data = await content.read()
            else:
                file_data = content

            total_bytes = len(file_data)

            # Run blocking upload in thread pool
            def _upload():
                return client.storage.from_(self.bucket).upload(
                    path=key,
                    file=file_data,
                    file_options={"content-type": content_type},
                )

            await asyncio.to_thread(_upload)

            # Report progress at completion
            if progress:
                await progress(total_bytes, total_bytes)

            logger.info(
                f"Uploaded Supabase object: {self.bucket}/{key} ({total_bytes} bytes)"
            )
            return key

        except Exception as e:
            logger.error(f"Supabase upload failed for {key}: {e}")
            raise IOError(f"Failed to upload to Supabase: {str(e)}") from e

    async def delete(self, name: str):
        """
        Delete object from Supabase Storage.
        
        Args:
            name: Supabase object path to delete
        
        Raises:
            IOError: If deletion fails
        """
        try:
            client = await self._get_client()

            # Run blocking delete in thread pool
            def _delete():
                return client.storage.from_(self.bucket).remove([name])

            await asyncio.to_thread(_delete)
            logger.info(f"Deleted Supabase object: {self.bucket}/{name}")
        except Exception as e:
            logger.error(f"Supabase delete failed for {name}: {e}")
            raise IOError(f"Failed to delete from Supabase: {str(e)}") from e

    def url(self, name: str) -> str:
        """
        Get public or private URL for Supabase object.
        
        Args:
            name: Supabase object path
        
        Returns:
            Supabase Storage URL (public or requires signed URL for private access)
        """
        if self.public:
            return f"{self.url}/storage/v1/object/public/{self.bucket}/{name}"
        return f"{self.url}/storage/v1/object/{self.bucket}/{name}"

    async def get_signed_url(self, name: str, expires_in: int = 3600) -> str:
        """
        Generate a signed URL for a private Supabase Storage object.
        
        Signed URLs provide temporary access to private objects without
        authentication. Useful for serving protected downloads.
        
        Args:
            name: Supabase object path
            expires_in: URL validity in seconds (default 1 hour)
        
        Returns:
            Signed HTTPS URL with embedded access token
        
        Raises:
            IOError: If signed URL generation fails
        
        Example:
            # Generate 30-minute private download
            signed_url = await backend.get_signed_url(
                "confidential/report.pdf",
                expires_in=1800
            )
            return {"download_url": signed_url}
        """
        try:
            client = await self._get_client()

            # Run blocking signed URL generation in thread pool
            def _create_signed_url():
                result = client.storage.from_(self.bucket).create_signed_url(
                    path=name,
                    expires_in=expires_in,
                )
                return result.get("signedURL", "")

            signed_url = await asyncio.to_thread(_create_signed_url)
            logger.debug(f"Generated signed URL for {name} ({expires_in}s)")
            return signed_url

        except Exception as e:
            logger.error(f"Signed URL generation failed for {name}: {e}")
            raise IOError(f"Failed to generate signed URL: {str(e)}") from e
