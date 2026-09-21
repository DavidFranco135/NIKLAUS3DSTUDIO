from src.domain.shared.exceptions import StorageUnavailableError
from src.domain.shared.storage_port import ObjectStat


class FakeStorageProvider:
    """In-memory StorageProvider for tests: no network, no real S3/MinIO needed.

    `upload_url` returns a fake URL that also marks the object as "uploaded" so
    tests can call `confirm` right away without a client actually PUTing bytes.
    """

    def __init__(self) -> None:
        self._objects: dict[str, ObjectStat] = {}

    def upload_url(self, *, key: str, content_type: str, expires_in: int) -> str:
        self._objects[key] = ObjectStat(size_bytes=1234, content_type=content_type)
        return f"https://fake-storage.test/{key}?upload=1"

    def download_url(self, *, key: str, expires_in: int) -> str:
        return f"https://fake-storage.test/{key}?download=1"

    def stat(self, *, key: str) -> ObjectStat | None:
        return self._objects.get(key)


class UnavailableStorageProvider:
    """Simulates the object storage being unreachable (e.g. MinIO down)."""

    def upload_url(self, *, key: str, content_type: str, expires_in: int) -> str:
        return f"https://fake-storage.test/{key}?upload=1"

    def download_url(self, *, key: str, expires_in: int) -> str:
        return f"https://fake-storage.test/{key}?download=1"

    def stat(self, *, key: str) -> ObjectStat | None:
        raise StorageUnavailableError(f"Could not connect to storage for key {key}")
