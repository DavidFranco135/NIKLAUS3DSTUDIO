"""The generic "pluggable provider" convention (`name` + `health_check`)

shared by every swappable engine in this codebase - billing providers
(mock today, Stripe later) and slicer providers (PrusaSlicer/OrcaSlicer),
so orchestration code can treat them uniformly regardless of what each
one actually does.
"""
from dataclasses import dataclass
from typing import Protocol

from src.domain.slicing.profiles import MaterialProfile, PrinterProfile
from src.domain.slicing.report import SliceResult


@dataclass(frozen=True)
class ProviderHealth:
    healthy: bool
    detail: str | None = None


@dataclass(frozen=True)
class MeshRef:
    """References an existing mesh file (a `FileAsset`), carrying its bytes

    directly - the caller (application layer) already fetched them via
    `StorageProvider.get_object()`, so the provider itself never needs its
    own storage dependency.
    """

    storage_key: str
    mime_type: str
    kind: str
    file_bytes: bytes


class SlicerProvider(Protocol):
    name: str

    def health_check(self) -> ProviderHealth: ...

    def slice(
        self, mesh: MeshRef, printer: PrinterProfile, material: MaterialProfile
    ) -> SliceResult: ...
