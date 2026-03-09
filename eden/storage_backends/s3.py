"""
Eden — S3 Storage Backend
"""

import mimetypes
import os
import uuid

from starlette.datastructures import UploadFile

from eden.storage import StorageBackend


class S3StorageBackend(StorageBackend):
    """
    Storage backend that saves files to AWS S3.

    Requires: `uv add aioboto3` or `pip install aioboto3`

    Usage:
        from eden.storage_backends.s3 import S3StorageBackend

        s3 = S3StorageBackend(
            bucket_name="my-bucket",
            aws_access_key_id="...",
            aws_secret_access_key="...",
            region_name="us-east-1"
        )
        app.storage.register("s3", s3)
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
        key = os.path.join(folder, unique_name).replace("\\", "/")

        content_type, _ = mimetypes.guess_type(name)
        if not content_type:
            content_type = "application/octet-stream"

        extra_args = {"ContentType": content_type}
        if self.public:
            extra_args["ACL"] = "public-read"

        async with self._session.client("s3", endpoint_url=self.endpoint_url) as s3:
            if isinstance(content, UploadFile):
                file_data = await content.read()
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=file_data,
                    **extra_args
                )
            else:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=content,
                    **extra_args
                )

        return key

    async def delete(self, name: str):
        async with self._session.client("s3", endpoint_url=self.endpoint_url) as s3:
            await s3.delete_object(Bucket=self.bucket_name, Key=name)

    def url(self, name: str) -> str:
        if self.base_url.endswith("/"):
            return f"{self.base_url}{name}"
        return f"{self.base_url}/{name}"

    async def get_presigned_url(self, name: str, expires_in: int = 3600) -> str:
        """
        Generate a pre-signed URL for a private S3 object.
        """
        async with self._session.client("s3", endpoint_url=self.endpoint_url) as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": name},
                ExpiresIn=expires_in,
            )
