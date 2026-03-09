"""
Eden — File Storage Abstraction
"""

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles
from starlette.datastructures import UploadFile


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.
    """
    @abstractmethod
    async def save(self, content: UploadFile | bytes, name: str | None = None, folder: str = "") -> str:
        """
        Save a file and return its identifier (e.g., path or URL).
        """
        pass

    @abstractmethod
    async def delete(self, name: str):
        """
        Delete a file by its identifier.
        """
        pass

    @abstractmethod
    def url(self, name: str) -> str:
        """
        Get the public URL for a file.
        """
        pass

class LocalStorageBackend(StorageBackend):
    """
    Storage backend that saves files to the local filesystem.
    """
    def __init__(self, base_path: str, base_url: str = "/media/"):
        self.base_path = Path(base_path)
        self.base_url = base_url
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, content: UploadFile | bytes, name: str | None = None, folder: str = "") -> str:
        if name is None:
            if isinstance(content, UploadFile):
                name = content.filename or str(uuid.uuid4())
            else:
                name = str(uuid.uuid4())

        # Ensure unique name
        ext = os.path.splitext(name)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"

        target_path = self.base_path / folder / unique_name
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, UploadFile):
            async with aiofiles.open(target_path, "wb") as f:
                while chunk := await content.read(8192):
                    await f.write(chunk)
        else:
            async with aiofiles.open(target_path, "wb") as f:
                await f.write(content)

        return os.path.join(folder, unique_name).replace("\\", "/")

    async def delete(self, name: str):
        target_path = self.base_path / name
        if target_path.exists():
            target_path.unlink()

    def url(self, name: str) -> str:
        return f"{self.base_url}{name}"

class StorageManager:
    """
    Registry for storage backends.
    """
    def __init__(self):
        self._backends: dict[str, StorageBackend] = {}
        self._default: str | None = None

    def register(self, name: str, backend: StorageBackend, default: bool = False):
        self._backends[name] = backend
        if default or not self._default:
            self._default = name

    def get(self, name: str | None = None) -> StorageBackend:
        name = name or self._default
        if not name or name not in self._backends:
            raise ValueError(f"Storage backend '{name}' not found.")
        return self._backends[name]

# Global instance
storage = StorageManager()
