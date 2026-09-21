from src.infrastructure.ai_providers.mocks.stl_box import generate_box_stl


def test_generates_valid_ascii_stl_structure():
    stl_bytes = generate_box_stl(70, 35, 4, name="keychain")
    text = stl_bytes.decode("ascii")

    assert text.startswith("solid keychain")
    assert text.strip().endswith("endsolid keychain")
    assert text.count("facet normal") == 12
    assert text.count("endfacet") == 12
    assert text.count("vertex") == 36
