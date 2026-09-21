import re

from src.domain.ai.ports import LLMProvider
from src.domain.ai.spec import Dimensions, StructuredSpecification

_DIMENSIONS_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*x\s*(\d+(?:[.,]\d+)?)\s*x\s*(\d+(?:[.,]\d+)?)\s*mm", re.IGNORECASE
)
_HOLE_RE = re.compile(r"furo\s+de\s+(\d+(?:[.,]\d+)?)\s*mm", re.IGNORECASE)
_QUOTED_TEXT_RE = re.compile(r'["“]([^"”]+)["”]')
_NAMED_TEXT_RE = re.compile(r"nome\s+([A-Za-zÀ-ÿ0-9]+)", re.IGNORECASE)

_OBJECT_KEYWORDS = {
    "chaveiro": "keychain",
    "placa": "plate",
    "letreiro": "sign",
    "caixa": "box",
    "estátua": "statue",
    "estatua": "statue",
}

_MATERIAL_KEYWORDS = ["pla", "petg", "abs", "resina", "tpu"]

_FORMAT_KEYWORDS = {
    "stl": "model_stl",
    "obj": "model_obj",
    "glb": "model_glb",
    "3mf": "model_3mf",
}


def _parse_float(value: str) -> float:
    return float(value.replace(",", "."))


class MockLLMProvider(LLMProvider):
    """Rule-based stand-in for the real NLU step (Fase 4 has no LLM integration yet).

    Deterministic on purpose: same prompt always yields the same spec, which
    keeps the orchestrator's classifier/fallback logic testable without
    depending on a live model.
    """

    name = "mock_llm"

    def extract_specification(self, prompt: str) -> StructuredSpecification:
        lowered = prompt.lower()

        dimensions = Dimensions()
        if match := _DIMENSIONS_RE.search(prompt):
            dimensions = Dimensions(
                width_mm=_parse_float(match.group(1)),
                height_mm=_parse_float(match.group(2)),
                thickness_mm=_parse_float(match.group(3)),
            )

        hole_diameter_mm = None
        if match := _HOLE_RE.search(prompt):
            hole_diameter_mm = _parse_float(match.group(1))

        text = None
        if match := _QUOTED_TEXT_RE.search(prompt):
            text = match.group(1).strip()
        elif match := _NAMED_TEXT_RE.search(prompt):
            text = match.group(1).strip()

        object_type = next(
            (value for keyword, value in _OBJECT_KEYWORDS.items() if keyword in lowered), None
        )
        material_hint = next(
            (word.upper() for word in _MATERIAL_KEYWORDS if word in lowered), None
        )
        output_format = next(
            (value for keyword, value in _FORMAT_KEYWORDS.items() if keyword in lowered),
            "model_stl",
        )

        return StructuredSpecification(
            object_type=object_type,
            dimensions=dimensions,
            text=text,
            hole_diameter_mm=hole_diameter_mm,
            material_hint=material_hint,
            output_format=output_format,
        )
