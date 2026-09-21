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


class LLMProvider(Protocol):
    """NLU step: free text -> StructuredSpecification. Output is untrusted data,

    validated by the pydantic schema before anything else touches it — never a
    channel for the model to trigger actions directly.
    """

    def extract_specification(self, prompt: str) -> StructuredSpecification: ...
