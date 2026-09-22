from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass(frozen=True)
class StoredObject:
    object_key: str
    size_bytes: int
    content_type: str | None


class StorageService(ABC):
    """Storage abstraction used by the business/API layer."""

    @abstractmethod
    def upload_file(
        self,
        *,
        file: BinaryIO,
        object_key: str,
        content_type: str | None = None,
    ) -> StoredObject:
        """Persist a file and return metadata about the stored object."""

    @abstractmethod
    def delete_file(self, *, object_key: str) -> None:
        """Delete a stored object by its storage key."""


class MockStorageService(StorageService):
    """In-memory storage used for local development and tests."""

    def __init__(self) -> None:
        self.objects: dict[str, StoredObject] = {}

    def upload_file(
        self,
        *,
        file: BinaryIO,
        object_key: str,
        content_type: str | None = None,
    ) -> StoredObject:
        file.seek(0)
        data = file.read()
        if not isinstance(data, bytes):
            data = bytes(data)

        stored = StoredObject(
            object_key=object_key,
            size_bytes=len(data),
            content_type=content_type,
        )
        self.objects[object_key] = stored
        return stored

    def delete_file(self, *, object_key: str) -> None:
        self.objects.pop(object_key, None)


_default_storage_service = MockStorageService()


def get_storage_service() -> StorageService:
    return _default_storage_service
