from src.domain.ai.spec import TaskType
from src.infrastructure.ai_providers import registry


def test_cad_providers_registered():
    providers = registry.get_providers_for_task(TaskType.PARAMETRIC_CAD)
    assert [p.name for p in providers] == ["build123d_cad"]


def test_text_to_3d_providers_include_mocks_before_real_vendor_stub():
    providers = registry.get_providers_for_task(TaskType.TEXT_TO_GENERATIVE_3D)
    names = [p.name for p in providers]
    assert names == ["mock_generative_unavailable", "mock_generative_placeholder", "hunyuan3d"]


def test_image_to_3d_providers_put_the_working_mock_first():
    providers = registry.get_providers_for_task(TaskType.IMAGE_TO_3D)
    names = [p.name for p in providers]
    assert names[0] == "mock_image_to_3d"
    assert set(names[1:]) == {"stable_fast_3d", "trellis", "spar3d", "hunyuan3d"}


def test_mesh_repair_is_real_but_texture_is_still_mock():
    assert registry.get_mesh_repair_provider().name == "trimesh_mesh_repair"
    assert registry.get_texture_provider().name == "mock_texture"
