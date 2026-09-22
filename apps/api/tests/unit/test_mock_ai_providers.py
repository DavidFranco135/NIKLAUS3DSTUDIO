from src.domain.ai.ports import ImageInput, MeshRef, OptimizeOptions, RepairOptions, TextureSpec
from src.domain.ai.spec import StructuredSpecification
from src.infrastructure.ai_providers.mocks.mock_image_to_3d import MockImageTo3DProvider
from src.infrastructure.ai_providers.mocks.mock_mesh_repair import MockMeshRepairProvider
from src.infrastructure.ai_providers.mocks.mock_texture import MockTextureProvider


def test_mock_image_to_3d_ignores_image_and_returns_placeholder_stl():
    provider = MockImageTo3DProvider()
    image = ImageInput(file_bytes=b"not-a-real-image", mime_type="image/png")

    result = provider.generate_from_image(image, StructuredSpecification())

    assert result.kind == "model_stl"
    assert result.file_bytes.startswith(b"solid")
    assert result.metadata["placeholder"] is True


def test_mock_mesh_repair_is_a_labeled_noop():
    provider = MockMeshRepairProvider()
    mesh = MeshRef(
        storage_key="org/x/some.stl", mime_type="model/stl", kind="model_stl", file_bytes=b""
    )

    repaired = provider.repair_mesh(mesh, RepairOptions())
    optimized = provider.optimize_mesh(mesh, OptimizeOptions())

    assert repaired.metadata["placeholder"] is True
    assert repaired.metadata["source_storage_key"] == mesh.storage_key
    assert optimized.metadata["placeholder"] is True


def test_mock_texture_returns_valid_png():
    provider = MockTextureProvider()
    mesh = MeshRef(
        storage_key="org/x/some.stl", mime_type="model/stl", kind="model_stl", file_bytes=b""
    )

    result = provider.generate_texture(mesh, TextureSpec(prompt="wood grain"))

    assert result.mime_type == "image/png"
    assert result.file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert result.metadata["requested_prompt"] == "wood grain"
