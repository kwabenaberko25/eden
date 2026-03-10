"""
Eden — Supabase Storage Backend
"""

import mimetypes
import os
import uuid

from starlette.datastructures import UploadFile

from eden.storage import StorageBackend


class SupabaseStorageBackend(StorageBackend):
    """
    Storage backend that saves files to Supabase Storage.

    Requires: `uv add supabase` or `pip install supabase`

    Usage::

        from eden.storage_backends.supabase import SupabaseStorageBackend

        storage = SupabaseStorageBackend(
            url="https://your-project.supabase.co",
            key="your-service-role-key",
            bucket="uploads",
        )
        app.storage.register("supabase", storage)
    """

    def __init__(
        self,
        url: str,
        key: str,
        bucket: str = "uploads",
        public: bool = True,
    ):
        self.url = url.rstrip("/")
        self.key = key
        self.bucket = bucket
        self.public = public
        self._client = None

    def _get_client(self):
        """Lazily create the Supabase client."""
        if self._client is None:
            try:
                from supabase import create_client
            except ImportError:
                raise ImportError(
                    "supabase is required for SupabaseStorageBackend. "
                    "Install it with: uv add supabase"
                )
            self._client = create_client(self.url, self.key)
        return self._client

    async def save(
        self, content: UploadFile | bytes, name: str | None = None, folder: str = ""
    ) -> str:
        if name is None:
            if isinstance(content, UploadFile):
                name = content.filename or str(uuid.uuid4())
            else:
                name = str(uuid.uuid4())

        # Ensure unique name while preserving original name for traceability
        base_name, ext = os.path.splitext(name)
        unique_name = f"{base_name}_{uuid.uuid4().hex[:8]}{ext}"
        key = os.path.join(folder, unique_name).replace("\\", "/").lstrip("/")

        content_type, _ = mimetypes.guess_type(name)
        if not content_type:
            content_type = "application/octet-stream"

        client = self._get_client()

        if isinstance(content, UploadFile):
            file_data = await content.read()
        else:
            file_data = content

        # Upload to Supabase Storage
        client.storage.from_(self.bucket).upload(
            path=key,
            file=file_data,
            file_options={"content-type": content_type},
        )

        return key

    async def delete(self, name: str):
        client = self._get_client()
        client.storage.from_(self.bucket).remove([name])

    def url(self, name: str) -> str:
        if self.public:
            return (
                f"{self.url}/storage/v1/object/public/{self.bucket}/{name}"
            )
        return f"{self.url}/storage/v1/object/{self.bucket}/{name}"

    async def get_signed_url(self, name: str, expires_in: int = 3600) -> str:
        """
        Generate a signed URL for a private Supabase Storage object.
        """
        client = self._get_client()
        result = client.storage.from_(self.bucket).create_signed_url(
            path=name,
            expires_in=expires_in,
        )
        return result.get("signedURL", "")
