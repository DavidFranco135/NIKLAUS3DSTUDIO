import pytest

from src.domain.ai.ports import MeshRef
from src.domain.shared.exceptions import ProviderNotConfiguredError
from src.domain.slicing.profiles import MaterialProfile, PrinterProfile
from src.infrastructure.slicers.orcaslicer.adapter import OrcaSlicerCLIProvider
from src.infrastructure.slicers.prusaslicer.adapter import PrusaSlicerCLIProvider
from src.infrastructure.slicers.registry import get_slicer_providers

_MESH = MeshRef(storage_key="k", mime_type="model/stl", kind="model_stl", file_bytes=b"x")
_PRINTER = PrinterProfile(
    name="Ender 3", bed_size_mm=(220, 220, 250), nozzle_diameter_mm=0.4, max_height_mm=250
)
_MATERIAL = MaterialProfile(
    name="PLA", filament_diameter_mm=1.75, density_g_cm3=1.24, cost_per_kg=90.0
)


@pytest.mark.parametrize("provider", [PrusaSlicerCLIProvider(), OrcaSlicerCLIProvider()])
def test_slicer_stub_reports_unhealthy_with_licensing_pointer(provider):
    health = provider.health_check()
    assert health.healthy is False
    assert "AI-LICENSES.md" in health.detail


@pytest.mark.parametrize("provider", [PrusaSlicerCLIProvider(), OrcaSlicerCLIProvider()])
def test_slicer_stub_raises_not_configured_instead_of_pretending_to_slice(provider):
    with pytest.raises(ProviderNotConfiguredError):
        provider.slice(_MESH, _PRINTER, _MATERIAL)


def test_registry_exposes_both_stubs_in_priority_order():
    providers = get_slicer_providers()
    assert [p.name for p in providers] == ["prusaslicer_cli", "orcaslicer_cli"]
