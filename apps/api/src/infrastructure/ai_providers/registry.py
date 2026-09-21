from src.domain.ai.ports import (
    CADProvider,
    ImageTo3DProvider,
    LLMProvider,
    MeshRepairProvider,
    TextTo3DProvider,
    TextureProvider,
)
from src.domain.ai.spec import TaskType
from src.infrastructure.ai_providers.mocks.mock_cad import MockBoxCADProvider
from src.infrastructure.ai_providers.mocks.mock_generative import (
    AlwaysFailingMockProvider,
    PlaceholderMockProvider,
)
from src.infrastructure.ai_providers.mocks.mock_image_to_3d import MockImageTo3DProvider
from src.infrastructure.ai_providers.mocks.mock_llm import MockLLMProvider
from src.infrastructure.ai_providers.mocks.mock_mesh_repair import MockMeshRepairProvider
from src.infrastructure.ai_providers.mocks.mock_texture import MockTextureProvider
from src.infrastructure.ai_providers.stubs.hunyuan3d import Hunyuan3DProvider
from src.infrastructure.ai_providers.stubs.spar3d import SPAR3DProvider
from src.infrastructure.ai_providers.stubs.stable_fast_3d import StableFast3DProvider
from src.infrastructure.ai_providers.stubs.trellis import TrellisProvider

# Fallback order = priority. The real-vendor stubs sit at the end of each list:
# reachable in principle (so the orchestrator's fallback mechanics already know
# about them), but never actually needed while a mock ahead of them keeps
# succeeding. Swapping a stub for a working adapter is the only change needed
# once GPU infra + a license check land (Fase 6+) — nothing here has to move.
_CAD_PROVIDERS: list[CADProvider] = [MockBoxCADProvider()]

_TEXT_TO_3D_PROVIDERS: list[TextTo3DProvider] = [
    AlwaysFailingMockProvider(),
    PlaceholderMockProvider(),
    Hunyuan3DProvider(),
]

_IMAGE_TO_3D_PROVIDERS: list[ImageTo3DProvider] = [
    MockImageTo3DProvider(),
    StableFast3DProvider(),
    TrellisProvider(),
    SPAR3DProvider(),
    Hunyuan3DProvider(),
]

_MESH_REPAIR_PROVIDER: MeshRepairProvider = MockMeshRepairProvider()
_TEXTURE_PROVIDER: TextureProvider = MockTextureProvider()
_LLM_PROVIDER: LLMProvider = MockLLMProvider()


def get_llm_provider() -> LLMProvider:
    return _LLM_PROVIDER


def get_mesh_repair_provider() -> MeshRepairProvider:
    return _MESH_REPAIR_PROVIDER


def get_texture_provider() -> TextureProvider:
    return _TEXTURE_PROVIDER


def get_providers_for_task(
    task_type: TaskType,
) -> list[CADProvider] | list[TextTo3DProvider] | list[ImageTo3DProvider]:
    if task_type == TaskType.PARAMETRIC_CAD:
        return _CAD_PROVIDERS
    if task_type == TaskType.TEXT_TO_GENERATIVE_3D:
        return _TEXT_TO_3D_PROVIDERS
    if task_type == TaskType.IMAGE_TO_3D:
        return _IMAGE_TO_3D_PROVIDERS
    raise ValueError(f"No providers registered for task type {task_type}")
