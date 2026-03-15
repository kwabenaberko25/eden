"""
Eden — S3 Storage Backend

Async S3 storage using aioboto3 with progress tracking and presigned URLs.

Requires: `uv add aioboto3` or `pip install aioboto3`

Usage:
    from eden.storage_backends.s3 import S3StorageBackend

    s3 = S3StorageBackend(
        bucket_name="my-bucket",
        aws_access_key_id="...",
        aws_secret_access_key="...",
        region_name="us-east-1"
    )
    app.storage.register("s3", s3, default=True)
    
    # Save file
    key = await storage.get("s3").save(upload_file)
    
    # Get URL
    url = storage.get("s3").url(key)
    
    # Save with progress tracking
    async def on_progress(bytes_written, total_bytes):
        if total_bytes:
            print(f"{bytes_written}/{total_bytes} bytes")
    
    key = await storage.get("s3").save(upload_file, progress=on_progress)
"""

import logging
import mimetypes
import os
import uuid
from typing import Optional

from starlette.datastructures import UploadFile

from eden.storage import StorageBackend, ProgressCallback

logger = logging.getLogger(__name__)


class S3StorageBackend(StorageBackend):
    """
    AWS S3 storage backend with progress tracking.
    
    Features:
    - Async uploads using aioboto3
    - Progress callback for large files
    - Presigned URLs for private objects
    - Public/private ACL support
    - Custom MIME type detection
    
    Example:
        backend = S3StorageBackend(
            bucket_name="media-bucket",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name="us-west-2",
            public=True
        )
        
        # Save with progress
        key = await backend.save(
            file,
            folder="avatars",
            progress=lambda written, total: print(f"{written}/{total}")
        )
        
        url = backend.url(key)
        await backend.delete(key)
    """

    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str = "us-east-1",
        endpoint_url: str | None = None,
        base_url: str | None = None,
        public: bool = True,
    ):
        try:
            import aioboto3
        except ImportError:
            raise ImportError(
                "aioboto3 is required for S3StorageBackend. "
                "Install it with: uv add aioboto3"
            )

        self.bucket_name = bucket_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        self.base_url = base_url or f"https://{bucket_name}.s3.{region_name}.amazonaws.com/"
        self.public = public
        self._session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )

    async def save(
        self,
        content: UploadFile | bytes,
        name: str | None = None,
        folder: str = "",
        progress: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Save file to S3 with optional progress tracking.
        
        Args:
            content: File content (UploadFile or bytes)
            name: Custom filename (generated if None)
            folder: S3 folder/prefix
            progress: Optional callback for upload progress
        
        Returns:
            S3 object key
        
        Raises:
            IOError: If S3 upload fails
        
        Implementation Notes:
            - Files are uploaded with unique names to prevent collisions
            - MIME type is auto-detected from filename
            - Public/private ACL is set based on backend config
            - Progress callback is called after each chunk (for bytes only)
        """
        if name is None:
            if isinstance(content, UploadFile):
                name = content.filename or str(uuid.uuid4())
            else:
                name = str(uuid.uuid4())

        # Ensure unique name while preserving original name for traceability
        base_name, ext = os.path.splitext(name)
        unique_name = f"{base_name}_{uuid.uuid4().hex[:8]}{ext}"
        key = os.path.join(folder, unique_name).replace("\\", "/")

        # Detect MIME type
        content_type, _ = mimetypes.guess_type(name)
        if not content_type:
            content_type = "application/octet-stream"

        # Prepare S3 put_object arguments
        extra_args = {"ContentType": content_type}
        if self.public:
            extra_args["ACL"] = "public-read"

        try:
            async with self._session.client("s3", endpoint_url=self.endpoint_url) as s3:
                if isinstance(content, UploadFile):
                    # Read entire file then upload (UploadFile doesn't support chunked progress)
                    file_data = await content.read()
                    total_bytes = len(file_data)
                    
                    await s3.put_object(
                        Bucket=self.bucket_name,
                        Key=key,
                        Body=file_data,
                        **extra_args
                    )
                    
                    # Report completion
                    if progress:
                        await progress(total_bytes, total_bytes)
                else:
                    # For bytes, report progress
                    total_bytes = len(content)
                    await s3.put_object(
                        Bucket=self.bucket_name,
                        Key=key,
                        Body=content,
                        **extra_args
                    )
                    
                    if progress:
                        await progress(total_bytes, total_bytes)
            
            logger.info(f"Uploaded S3 object: {key} ({total_bytes} bytes)")
            return key
        
        except Exception as e:
            logger.error(f"S3 upload failed for {key}: {e}")
            raise IOError(f"Failed to upload to S3: {str(e)}") from e

    async def delete(self, name: str):
        """
        Delete object from S3.
        
        Args:
            name: S3 object key to delete
        
        Raises:
            IOError: If deletion fails
        """
        try:
            async with self._session.client("s3", endpoint_url=self.endpoint_url) as s3:
                await s3.delete_object(Bucket=self.bucket_name, Key=name)
            logger.info(f"Deleted S3 object: {name}")
        except Exception as e:
            logger.error(f"S3 delete failed for {name}: {e}")
            raise IOError(f"Failed to delete from S3: {str(e)}") from e

    def url(self, name: str) -> str:
        """
        Get public URL for S3 object.
        
        Args:
            name: S3 object key
        
        Returns:
            HTTPS URL to object
        """
        if self.base_url.endswith("/"):
            return f"{self.base_url}{name}"
        return f"{self.base_url}/{name}"

    async def get_presigned_url(self, name: str, expires_in: int = 3600) -> str:
        """
        Generate a pre-signed URL for a private S3 object.
        
        Presigned URLs allow temporary access to private (non-public) objects
        without AWS credentials. Useful for serving protected downloads.
        
        Args:
            name: S3 object key
            expires_in: URL validity in seconds (default 1 hour)
        
        Returns:
            Presigned HTTPS URL
        
        Raises:
            IOError: If presigned URL generation fails
        
        Example:
            # Generate 30-minute private download link
            private_url = await s3.get_presigned_url(
                "confidential/contract.pdf",
                expires_in=1800
            )
            return {"download_url": private_url}
        """
        try:
            async with self._session.client("s3", endpoint_url=self.endpoint_url) as s3:
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": name},
                    ExpiresIn=expires_in,
                )
            logger.debug(f"Generated presigned URL for {name} ({expires_in}s)")
            return url
        except Exception as e:
            logger.error(f"Presigned URL generation failed for {name}: {e}")
            raise IOError(f"Failed to generate presigned URL: {str(e)}") from e
