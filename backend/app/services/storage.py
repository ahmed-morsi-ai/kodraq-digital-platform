from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from app.core.config import settings


class FileTooLargeError(ValueError):
    """An upload exceeds the configured per-file limit."""


@dataclass(frozen=True)
class StoredObject:
    object_key: str
    size_bytes: int
    content_type: str | None


class StorageService(ABC):
    """Private object storage contract, suitable for local storage or an R2 adapter.

    Implementations enforce upload limits and remove partial uploads on failure.
    API code uses object keys and streams, never provider-specific file paths.
    """

    @abstractmethod
    def upload_file(
        self, *, file: BinaryIO, object_key: str, content_type: str | None = None
    ) -> StoredObject: ...

    @abstractmethod
    def open_file(self, *, object_key: str) -> BinaryIO:
        """Return a readable binary stream; the caller closes it."""

    @abstractmethod
    def delete_file(self, *, object_key: str) -> None: ...


class LocalStorageService(StorageService):
    def __init__(self, root: Path, *, max_file_bytes: int = 10 * 1024 * 1024):
        self.root = root.resolve()
        self.max_file_bytes = max_file_bytes

    def _path(self, object_key: str) -> Path:
        key = PurePosixPath(object_key)
        if (
            not object_key
            or key.is_absolute()
            or any(part in {".", "..", ""} for part in object_key.split("/"))
            or any(char in object_key for char in "\\:\x00")
        ):
            raise ValueError("Invalid storage key")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Storage key escapes the storage root")
        return path

    def upload_file(
        self, *, file: BinaryIO, object_key: str, content_type: str | None = None
    ) -> StoredObject:
        path = self._path(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        destination = path.open("xb")
        size = 0
        try:
            with destination:
                file.seek(0)
                while chunk := file.read(64 * 1024):
                    size += len(chunk)
                    if size > self.max_file_bytes:
                        raise FileTooLargeError("File exceeds the upload size limit")
                    destination.write(chunk)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return StoredObject(object_key, size, content_type)

    def open_file(self, *, object_key: str) -> BinaryIO:
        return self._path(object_key).open("rb")

    def delete_file(self, *, object_key: str) -> None:
        self._path(object_key).unlink(missing_ok=True)


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    return LocalStorageService(
        settings.STORAGE_LOCAL_ROOT,
        max_file_bytes=settings.SUBMISSION_MAX_FILE_BYTES,
    )
