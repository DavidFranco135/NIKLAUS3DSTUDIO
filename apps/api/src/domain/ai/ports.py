from dataclasses import dataclass
from typing import Any, Protocol

from src.domain.ai.spec import StructuredSpecification


@dataclass(frozen=True)
class ProviderHealth:
    healthy: bool
    detail: str | None = None


@dataclass(frozen=True)
class GenerationResult:
    file_bytes: bytes
    mime_type: str
    kind: str
    metadata: dict[str, Any]


class AIProvider(Protocol):
    name: str

    def health_check(self) -> ProviderHealth: ...


class CADProvider(AIProvider, Protocol):
    def create_parametric_model(self, spec: StructuredSpecification) -> GenerationResult: ...


class TextTo3DProvider(AIProvider, Protocol):
    def generate_from_text(self, spec: StructuredSpecification) -> GenerationResult: ...


@dataclass(frozen=True)
class ImageInput:
    file_bytes: bytes
    mime_type: str


class ImageTo3DProvider(AIProvider, Protocol):
    def generate_from_image(
        self, image: ImageInput, spec: StructuredSpecification
    ) -> GenerationResult: ...


@dataclass(frozen=True)
class MeshRef:
    """References an existing mesh file (a `FileAsset`), carrying its bytes

    directly — same pattern as `ImageInput`: the caller (application layer)
    already fetched them via `StorageProvider.get_object()`, so the provider
    itself never needs its own storage dependency.
    """

    storage_key: str
    mime_type: str
    kind: str
    file_bytes: bytes


@dataclass(frozen=True)
class RepairOptions:
    fill_holes: bool = True
    remove_degenerate_faces: bool = True
    fix_normals: bool = True


@dataclass(frozen=True)
class OptimizeOptions:
    target_triangle_count: int | None = None
    simplify: bool = True


@dataclass(frozen=True)
class MeshResult:
    file_bytes: bytes
    mime_type: str
    kind: str
    metadata: dict[str, Any]


class MeshRepairProvider(AIProvider, Protocol):
    def repair_mesh(self, mesh: MeshRef, options: RepairOptions) -> MeshResult: ...

    def optimize_mesh(self, mesh: MeshRef, options: OptimizeOptions) -> MeshResult: ...


@dataclass(frozen=True)
class TextureSpec:
    prompt: str | None = None
    color_hint: str | None = None
    resolution_px: int = 512


@dataclass(frozen=True)
class TextureResult:
    file_bytes: bytes
    mime_type: str
    metadata: dict[str, Any]


class TextureProvider(AIProvider, Protocol):
    def generate_texture(self, mesh: MeshRef, spec: TextureSpec) -> TextureResult: ...


class LLMProvider(Protocol):
    """NLU step: free text -> StructuredSpecification. Output is untrusted data,

    validated by the pydantic schema before anything else touches it — never a
    channel for the model to trigger actions directly.
    """

    def extract_specification(self, prompt: str) -> StructuredSpecification: ...
