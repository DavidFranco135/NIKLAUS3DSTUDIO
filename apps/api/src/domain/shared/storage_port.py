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

    def put_object(self, *, key: str, data: bytes, content_type: str) -> None:
        """Server-side write, used by workers that hold bytes in memory (e.g. AI

        generation output) — as opposed to `upload_url`, which hands the client
        a presigned URL to PUT bytes directly for a human-driven upload.
        """
        ...

    def get_object(self, *, key: str) -> bytes:
        """Server-side read — used by workers that need the actual bytes (e.g.

        an ImageTo3DProvider reading the source image), as opposed to
        `download_url`, which hands a human a presigned URL instead.
        """
        ...
