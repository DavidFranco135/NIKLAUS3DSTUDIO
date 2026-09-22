import pytest

from src.domain.mesh.operations import load_mesh
from src.infrastructure.ai_providers.mocks.stl_box import generate_box_stl


def test_generates_valid_ascii_stl_structure():
    stl_bytes = generate_box_stl(70, 35, 4, name="keychain")
    text = stl_bytes.decode("ascii")

    assert text.startswith("solid keychain")
    assert text.strip().endswith("endsolid keychain")
    assert text.count("facet normal") == 12
    assert text.count("endfacet") == 12
    assert text.count("vertex") == 36


def test_winding_order_gives_positive_volume_not_inside_out():
    # Regression test: the original triangle winding produced a watertight,
    # internally-consistent mesh that was nonetheless uniformly inside-out
    # (negative signed volume) — caught by Fase 8's real mesh validation.
    stl_bytes = generate_box_stl(70, 35, 4)
    mesh = load_mesh(stl_bytes, "model_stl")

    assert mesh.is_watertight
    assert mesh.volume == pytest.approx(70 * 35 * 4)
