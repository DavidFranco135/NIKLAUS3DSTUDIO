from src.domain.ai.ports import GenerationResult
from src.domain.ai.result_validation import validate_generation_result


def _stl_result(file_bytes: bytes) -> GenerationResult:
    return GenerationResult(
        file_bytes=file_bytes, mime_type="model/stl", kind="model_stl", metadata={}
    )


def test_empty_bytes_is_rejected():
    issues = validate_generation_result(_stl_result(b""))
    assert issues


def test_valid_ascii_stl_passes():
    issues = validate_generation_result(_stl_result(b"solid x\nendsolid x\n"))
    assert issues == []


def test_garbage_short_bytes_is_rejected():
    issues = validate_generation_result(_stl_result(b"not-a-mesh"))
    assert issues
