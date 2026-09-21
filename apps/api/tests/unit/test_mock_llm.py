from src.infrastructure.ai_providers.mocks.mock_llm import MockLLMProvider


def test_extracts_keychain_spec_from_example_prompt():
    provider = MockLLMProvider()
    spec = provider.extract_specification(
        "Crie um chaveiro de 70x35x4mm com o nome CARLOS, furo de 5 mm, formato STL."
    )

    assert spec.object_type == "keychain"
    assert spec.dimensions.width_mm == 70
    assert spec.dimensions.height_mm == 35
    assert spec.dimensions.thickness_mm == 4
    assert spec.text == "CARLOS"
    assert spec.hole_diameter_mm == 5
    assert spec.output_format == "model_stl"


def test_extraction_is_deterministic():
    provider = MockLLMProvider()
    prompt = "Uma placa de 100x50x3mm com o nome LOJA"
    assert provider.extract_specification(prompt) == provider.extract_specification(prompt)


def test_extracts_no_dimensions_from_vague_prompt():
    provider = MockLLMProvider()
    spec = provider.extract_specification("Quero uma estátua de um cachorro sentado")

    assert spec.object_type == "statue"
    assert spec.dimensions.width_mm is None
    assert not spec.dimensions.is_fully_specified()
