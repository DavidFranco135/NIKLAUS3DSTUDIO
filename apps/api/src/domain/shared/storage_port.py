from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ObjectStat:
    size_bytes: int
    content_type: str | None


class StorageProvider(Protocol):
    def upload_url(self, *, key: str, content_type: str, expires_in: int) -> str: ...

    def download_url(self, *, key: str, expires_in: int) -> str: ...

    def stat(self, *, key: str) -> ObjectStat | None: ...
