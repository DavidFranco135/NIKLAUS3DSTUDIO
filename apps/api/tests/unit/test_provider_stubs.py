import pytest

from src.domain.ai.ports import ImageInput
from src.domain.ai.spec import StructuredSpecification
from src.domain.shared.exceptions import ProviderNotConfiguredError
from src.infrastructure.ai_providers.stubs.hunyuan3d import Hunyuan3DProvider
from src.infrastructure.ai_providers.stubs.spar3d import SPAR3DProvider
from src.infrastructure.ai_providers.stubs.stable_fast_3d import StableFast3DProvider
from src.infrastructure.ai_providers.stubs.trellis import TrellisProvider

_IMAGE = ImageInput(file_bytes=b"x", mime_type="image/png")
_SPEC = StructuredSpecification()


@pytest.mark.parametrize(
    "provider", [Hunyuan3DProvider(), TrellisProvider(), StableFast3DProvider(), SPAR3DProvider()]
)
def test_image_stub_reports_unhealthy_with_licensing_pointer(provider):
    health = provider.health_check()
    assert health.healthy is False
    assert "AI-LICENSES.md" in health.detail


@pytest.mark.parametrize(
    "provider", [Hunyuan3DProvider(), TrellisProvider(), StableFast3DProvider(), SPAR3DProvider()]
)
def test_image_stub_raises_not_configured_instead_of_pretending_to_work(provider):
    with pytest.raises(ProviderNotConfiguredError):
        provider.generate_from_image(_IMAGE, _SPEC)


def test_hunyuan3d_stub_also_raises_for_text_to_3d():
    with pytest.raises(ProviderNotConfiguredError):
        Hunyuan3DProvider().generate_from_text(_SPEC)
