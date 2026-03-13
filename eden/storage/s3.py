"""
Eden — S3 Storage Backend

Provides async file storage via AWS S3 (or S3-compatible services like MinIO).

Usage:
    from eden.storage.s3 import S3StorageBackend

    s3 = S3StorageBackend(
        bucket="my-bucket",
        region="us-east-1",
        access_key="...",
        secret_key="...",
    )
    s3.mount(app)

    # In views:
    url = await app.storage.upload(file, path="avatars/user.jpg")
"""

from __future__ import annotations

import os
from typing import Any, BinaryIO

try:
    import boto3
    from botocore.config import Config as BotoConfig
except ImportError:
    boto3 = None  # type: ignore[assignment]
    BotoConfig = None  # type: ignore[assignment, misc]


class S3StorageBackend:
    """
    S3-compatible storage backend for Eden.

    Supports AWS S3, MinIO, DigitalOcean Spaces, and any
    S3-compatible service.

    Usage:
        s3 = S3StorageBackend(
            bucket="my-app-assets",
            region="us-east-1",
            access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        s3.mount(app)
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
        if boto3 is None:
            raise ImportError(
                "boto3 is required for S3 storage. Install it: pip install boto3"
            )

        self.bucket = bucket
        self.region = region
        self.default_acl = default_acl
        self.public_url = public_url

        self._client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=secret_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
            endpoint_url=endpoint_url,
            config=BotoConfig(signature_version="s3v4") if BotoConfig else None,
        )

    def upload(
        self,
        file: BinaryIO,
        path: str,
        content_type: str = "application/octet-stream",
        acl: str | None = None,
    ) -> str:
        """
        Upload a file to S3.

        Returns the URL of the uploaded file.
        """
        extra_args: dict[str, str] = {
            "ContentType": content_type,
            "ACL": acl or self.default_acl,
        }

        self._client.upload_fileobj(file, self.bucket, path, ExtraArgs=extra_args)

        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{path}"

        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{path}"

    def download(self, path: str, destination: BinaryIO) -> None:
        """Download a file from S3 to a file-like object."""
        self._client.download_fileobj(self.bucket, path, destination)

    def delete(self, path: str) -> None:
        """Delete a file from S3."""
        self._client.delete_object(Bucket=self.bucket, Key=path)

    def exists(self, path: str) -> bool:
        """Check if a file exists in S3."""
        try:
            self._client.head_object(Bucket=self.bucket, Key=path)
            return True
        except self._client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            # Log unexpected errors but return False for safety
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"S3 head_object failed for {path}: {e}")
            return False

    def presigned_url(self, path: str, expires_in: int = 3600) -> str:
        """
        Generate a pre-signed URL for temporary access.

        Args:
            path: The S3 object key.
            expires_in: URL expiration time in seconds (default: 1 hour).
        """
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": path},
            ExpiresIn=expires_in,
        )

    def list_files(self, prefix: str = "") -> list[dict[str, Any]]:
        """
        List files in the bucket with an optional prefix filter.

        Returns a list of dicts with 'key', 'size', and 'last_modified'.
        """
        response = self._client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        files = []
        for obj in response.get("Contents", []):
            files.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            })
        return files

    def mount(self, app: Any, name: str = "s3") -> None:
        """
        Mount this storage backend onto an Eden app.

        Registers it with Eden's storage system.
        """
        from eden.storage import storage as eden_storage
        eden_storage.register(name, self)
        app.s3 = self
