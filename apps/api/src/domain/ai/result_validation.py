from src.domain.ai.ports import GenerationResult

_STL_MARKERS = (b"solid", b"endsolid")


def validate_generation_result(result: GenerationResult) -> list[str]:
    """Basic structural sanity check on a provider's output — not a real

    printability assessment (that's the Printability Engine, Fase 9). Exists
    so the `VALIDATING` job status means something today, and so a future
    real provider that returns garbage bytes fails loudly instead of quietly
    becoming a broken project version.
    """
    issues: list[str] = []

    if not result.file_bytes:
        issues.append("Resultado vazio: o provider não retornou nenhum byte.")
        return issues

    if result.kind == "model_stl":
        head = result.file_bytes[:5]
        if head != b"solid" and head[:1] != b"\x00" and len(result.file_bytes) < 84:
            # Neither a plausible ASCII STL header nor long enough to be a binary
            # STL (binary STL: 80-byte header + 4-byte triangle count minimum).
            issues.append("Bytes não parecem um STL válido (nem ASCII nem binário).")

    return issues
