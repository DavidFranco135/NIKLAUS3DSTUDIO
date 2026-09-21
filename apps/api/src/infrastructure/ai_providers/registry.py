from src.domain.ai.ports import CADProvider, LLMProvider, TextTo3DProvider
from src.domain.ai.spec import TaskType
from src.infrastructure.ai_providers.mocks.mock_cad import MockBoxCADProvider
from src.infrastructure.ai_providers.mocks.mock_generative import (
    AlwaysFailingMockProvider,
    PlaceholderMockProvider,
)
from src.infrastructure.ai_providers.mocks.mock_llm import MockLLMProvider

_CAD_PROVIDERS: list[CADProvider] = [MockBoxCADProvider()]
_TEXT_TO_3D_PROVIDERS: list[TextTo3DProvider] = [
    AlwaysFailingMockProvider(),
    PlaceholderMockProvider(),
]

_LLM_PROVIDER: LLMProvider = MockLLMProvider()


def get_llm_provider() -> LLMProvider:
    return _LLM_PROVIDER


def get_providers_for_task(task_type: TaskType) -> list[CADProvider] | list[TextTo3DProvider]:
    if task_type == TaskType.PARAMETRIC_CAD:
        return _CAD_PROVIDERS
    if task_type == TaskType.TEXT_TO_GENERATIVE_3D:
        return _TEXT_TO_3D_PROVIDERS
    raise ValueError(f"No providers registered for task type {task_type}")
