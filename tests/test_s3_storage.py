"""
Eden — S3 Storage Backend Tests

Tests for S3StorageBackend using aioboto3 mocking.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from eden.storage_backends.s3 import S3StorageBackend


class TestS3StorageBackend:
    """Tests for S3StorageBackend."""

    @pytest.fixture
    def mock_aioboto3(self):
        with patch("aioboto3.Session") as mock_session:
            # Setup session
            session_instance = mock_session.return_value
            
            # Setup s3 client mock
            client_mock = AsyncMock()
            client_ctx = AsyncMock()
            client_ctx.__aenter__.return_value = client_mock
            
            session_instance.client.return_value = client_ctx
            
            yield client_mock

    @pytest.mark.asyncio
    async def test_save_bytes(self, mock_aioboto3):
        # We need to mock aioboto3 BEFORE instantiating the backend 
        # because the backend calls aioboto3.Session in __init__
        with patch("aioboto3.Session") as mock_session:
            # Setup session
            session_instance = mock_session.return_value
            client_mock = AsyncMock()
            client_ctx = AsyncMock()
            client_ctx.__aenter__.return_value = client_mock
            session_instance.client.return_value = client_ctx

            backend = S3StorageBackend(
                bucket_name="test-bucket",
                aws_access_key_id="key",
                aws_secret_access_key="secret",
                public=True
            )

            content = b"hello s3"
            filename = "test.txt"
            
            key = await backend.save(content, name=filename)
            
            assert "test" in key
            assert ".txt" in key
            client_mock.put_object.assert_called_once()
            args, kwargs = client_mock.put_object.call_args
            assert kwargs["Bucket"] == "test-bucket"
            assert kwargs["Body"] == content
            assert kwargs["ACL"] == "public-read"
            assert kwargs["ContentType"] == "text/plain"

    @pytest.mark.asyncio
    async def test_delete(self, mock_aioboto3):
        with patch("aioboto3.Session") as mock_session:
            # Setup session
            session_instance = mock_session.return_value
            client_mock = AsyncMock()
            client_ctx = AsyncMock()
            client_ctx.__aenter__.return_value = client_mock
            session_instance.client.return_value = client_ctx

            backend = S3StorageBackend(
                bucket_name="test-bucket",
                aws_access_key_id="key",
                aws_secret_access_key="secret"
            )

            await backend.delete("some/key.png")
            client_mock.delete_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="some/key.png"
            )

    def test_url(self):
        with patch("aioboto3.Session"):
            backend = S3StorageBackend(
                bucket_name="test-bucket",
                aws_access_key_id="key",
                aws_secret_access_key="secret",
                region_name="us-west-2"
            )
            
            url = backend.url("test.jpg")
            assert url == "https://test-bucket.s3.us-west-2.amazonaws.com/test.jpg"

    @pytest.mark.asyncio
    async def test_presigned_url(self, mock_aioboto3):
        with patch("aioboto3.Session") as mock_session:
            # Setup session
            session_instance = mock_session.return_value
            client_mock = AsyncMock()
            client_ctx = AsyncMock()
            client_ctx.__aenter__.return_value = client_mock
            session_instance.client.return_value = client_ctx
            
            client_mock.generate_presigned_url.return_value = "https://presigned-url.com"

            backend = S3StorageBackend(
                bucket_name="test-bucket",
                aws_access_key_id="key",
                aws_secret_access_key="secret"
            )

            url = await backend.get_presigned_url("private.pdf")
            assert url == "https://presigned-url.com"
            client_mock.generate_presigned_url.assert_called_once_with(
                "get_object",
                Params={"Bucket": "test-bucket", "Key": "private.pdf"},
                ExpiresIn=3600
            )
