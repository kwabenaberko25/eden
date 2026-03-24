
"""
Eden — S3 Storage Backend

Provides async file storage via AWS S3 (or S3-compatible services like MinIO).
Uses aioboto3 for native async performance.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
import mimetypes
from contextlib import asynccontextmanager
from typing import Any, Optional, TYPE_CHECKING

from . import StorageBackend, ProgressCallback, FileUploadValidator

try:
    import aioboto3
    from botocore.config import Config as BotoConfig
except ImportError:
    aioboto3 = None  # type: ignore[assignment]
    BotoConfig = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)


class S3StorageBackend(StorageBackend):
    """
    S3-compatible storage backend for Eden using aioboto3.

    Supports AWS S3, MinIO, DigitalOcean Spaces, and any
    S3-compatible service.
    """

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
        public_url: str | None = None,
        default_acl: str = "private",
    ) -> None:
        if aioboto3 is None:
            raise ImportError(
                "aioboto3 is required for S3 storage. Install it: pip install aioboto3"
            )

        self.bucket = bucket
        self.region = region
        self.default_acl = default_acl
        self.public_url = public_url
        self.endpoint_url = endpoint_url

        self._session = aioboto3.Session(
            aws_access_key_id=access_key or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=secret_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=region,
        )
        self._client_config = BotoConfig(signature_version="s3v4") if BotoConfig else None

    def _get_client_kwargs(self) -> dict[str, Any]:
        return {
            "service_name": "s3",
            "region_name": self.region,
            "endpoint_url": self.endpoint_url,
            "config": self._client_config,
        }

    async def save(
        self,
        content: UploadFile | bytes,
        name: str | None = None,
        folder: str = "",
        progress: Optional[ProgressCallback] = None,
        validator: Optional[FileUploadValidator] = None,
    ) -> str:
        """
        Save file to S3, optionally validating and reporting progress.
        
        Returns the object key (path).
        """
        # 1. Validate using the shared validator logic (which now handles bytes)
        if validator:
            await validator.validate(content, name=name)

        # 2. Determine filename
        from starlette.datastructures import UploadFile
        if name is None:
            if isinstance(content, UploadFile):
                name = content.filename or str(uuid.uuid4())
            else:
                name = str(uuid.uuid4())

        # 3. Ensure unique path to prevent collisions
        base_name, ext = os.path.splitext(name)
        unique_name = f"{base_name}_{uuid.uuid4().hex[:8]}{ext}"
        path = os.path.join(folder, unique_name).replace("\\", "/")

        # 4. Detect ContentType
        content_type, _ = mimetypes.guess_type(name)
        if not content_type:
            content_type = "application/octet-stream"

        # 5. Prepare body
        if isinstance(content, UploadFile):
            body = await content.read()
            # We don't need to seek back here as we've read it all into memory 
            # for the S3 put_object call.
        else:
            body = content

        total_bytes = len(body)
        if progress:
            await progress(0, total_bytes)

        # 6. Upload
        async with self._session.client(**self._get_client_kwargs()) as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=path,
                Body=body,
                ContentType=content_type,
                ACL=self.default_acl,
            )
            
            if progress:
                await progress(total_bytes, total_bytes)

        logger.info(f"Uploaded S3 object: {path} ({total_bytes} bytes)")
        return path

    async def delete(self, name: str) -> None:
        """Delete a file from S3."""
        async with self._session.client(**self._get_client_kwargs()) as s3:
            await s3.delete_object(Bucket=self.bucket, Key=name)
            logger.debug(f"Deleted S3 object: {name}")

    def url(self, name: str) -> str:
        """Get the public URL for a file."""
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{name}"

        # Standard AWS S3 URL format
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{name}"

    async def exists(self, name: str) -> bool:
        """Check if a file exists in S3."""
        try:
            async with self._session.client(**self._get_client_kwargs()) as s3:
                await s3.head_object(Bucket=self.bucket, Key=name)
                return True
        except Exception:
            return False

    async def presigned_url(self, name: str, expires_in: int = 3600) -> str:
        """Generate a pre-signed URL for temporary access."""
        async with self._session.client(**self._get_client_kwargs()) as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": name},
                ExpiresIn=expires_in,
            )

    def open(self, name: str) -> Any:
        """
        Open a file for reading from S3 via an async context manager.
        Returns the StreamingBody object from botocore.
        """
        return S3FileContext(self._session, self.bucket, name, self._get_client_kwargs())

    def mount(self, app: Any, name: str = "s3") -> None:
        """Mount this storage backend onto an Eden app."""
        from eden.storage import storage as eden_storage
        eden_storage.register(name, self)
        app.s3 = self


class S3FileContext:
    """Helper to provide an async context manager for S3 file streaming."""
    def __init__(self, session: Any, bucket: str, key: str, client_kwargs: dict[str, Any]):
        self.session = session
        self.bucket = bucket
        self.key = key
        self.client_kwargs = client_kwargs
        self._client = None
        self._response = None

    async def __aenter__(self):
        # We need to manage the client lifecycle manually to keep it open for the stream
        self._client = await self.session.client(**self.client_kwargs).__aenter__()
        try:
            self._response = await self._client.get_object(Bucket=self.bucket, Key=self.key)
            return self._response["Body"]
        except Exception as e:
            # If get_object fails, ensure we close the client
            await self._client.__aexit__(None, None, None)
            raise e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
