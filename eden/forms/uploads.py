from __future__ import annotations

"""
File upload data types and progress tracking protocol.

This module contains the data structures for handling file uploads
in Eden forms, including the UploadedFile wrapper and the
ProgressCallback protocol for tracking upload progress.
"""

import io
from dataclasses import dataclass
from typing import Callable, Awaitable


ProgressCallback = Callable[[int, int], Awaitable[None]]
"""
Protocol for upload progress callbacks.

The callback receives two arguments:
- bytes_written: int - Bytes uploaded so far
- total_bytes: int - Total bytes to upload

Example:
    async def progress(bytes_written, total_bytes):
        percentage = (bytes_written / total_bytes) * 100
        print(f"Upload: {percentage:.1f}%")

    await storage.save_with_progress(file, callback=progress)
"""


@dataclass
class UploadedFile:
    """
    Wrapper around a file uploaded through a multipart form.

    Attributes:
        filename:     Original filename from the client.
        content_type: MIME type (e.g. 'image/png').
        data:         Raw bytes of the uploaded file.
        size:         File size in bytes.

    Usage::

        form = await BaseForm.from_multipart(request)
        avatar: UploadedFile = form.files["avatar"]
        await storage.save(avatar.filename, avatar.data)
    """

    filename: str
    content_type: str
    data: bytes
    size: int

    def as_io(self) -> io.BytesIO:
        """Return the file data as an in-memory byte stream."""
        return io.BytesIO(self.data)

    @property
    def extension(self) -> str:
        """File extension including the leading dot, e.g. '.png'."""
        parts = self.filename.rsplit(".", 1)
        return f".{parts[-1].lower()}" if len(parts) == 2 else ""
