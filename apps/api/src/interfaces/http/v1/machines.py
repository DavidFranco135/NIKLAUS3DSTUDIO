from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.application.machines import use_cases as machine_use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.interfaces.http.dependencies import get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import (
    CreateMachineRequest,
    MachineResponse,
    UpdateMachineRequest,
)

router = APIRouter(prefix="/organizations/{organization_id}/machines", tags=["machines"])


@router.post(
    "",
    response_model=MachineResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def create_machine(
    organization_id: UUID, payload: CreateMachineRequest, db: Session = Depends(get_db)
) -> MachineResponse:
    machine = machine_use_cases.create_machine(
        db,
        organization_id=organization_id,
        name=payload.name,
        brand=payload.brand,
        model=payload.model,
        technology=payload.technology,
        build_volume_x_mm=payload.build_volume_x_mm,
        build_volume_y_mm=payload.build_volume_y_mm,
        build_volume_z_mm=payload.build_volume_z_mm,
        power_watts=payload.power_watts,
        cost_per_hour=payload.cost_per_hour,
        speed_profile=payload.speed_profile,
        compatible_materials=payload.compatible_materials,
    )
    return MachineResponse.model_validate(machine)


@router.get(
    "",
    response_model=list[MachineResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_machines(organization_id: UUID, db: Session = Depends(get_db)) -> list[MachineResponse]:
    machines = machine_use_cases.list_machines(db, organization_id=organization_id)
    return [MachineResponse.model_validate(m) for m in machines]


@router.get(
    "/{machine_id}",
    response_model=MachineResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_machine(
    organization_id: UUID, machine_id: UUID, db: Session = Depends(get_db)
) -> MachineResponse:
    try:
        machine = machine_use_cases.get_machine(
            db, organization_id=organization_id, machine_id=machine_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return MachineResponse.model_validate(machine)


@router.patch(
    "/{machine_id}",
    response_model=MachineResponse,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def update_machine(
    organization_id: UUID,
    machine_id: UUID,
    payload: UpdateMachineRequest,
    db: Session = Depends(get_db),
) -> MachineResponse:
    try:
        machine = machine_use_cases.update_machine(
            db,
            organization_id=organization_id,
            machine_id=machine_id,
            name=payload.name,
            brand=payload.brand,
            model=payload.model,
            cost_per_hour=payload.cost_per_hour,
            status=payload.status,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return MachineResponse.model_validate(machine)
