from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.application.inventory import use_cases as inventory_use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.interfaces.http.dependencies import get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import CreateMaterialRequest, MaterialResponse

router = APIRouter(prefix="/organizations/{organization_id}/materials", tags=["materials"])


@router.post(
    "",
    response_model=MaterialResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def create_material(
    organization_id: UUID, payload: CreateMaterialRequest, db: Session = Depends(get_db)
) -> MaterialResponse:
    material = inventory_use_cases.create_material(
        db,
        organization_id=organization_id,
        name=payload.name,
        type=payload.type,
        color=payload.color,
        density_g_cm3=payload.density_g_cm3,
        cost_per_kg=payload.cost_per_kg,
        supplier=payload.supplier,
    )
    return MaterialResponse.model_validate(material)


@router.get(
    "",
    response_model=list[MaterialResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_materials(organization_id: UUID, db: Session = Depends(get_db)) -> list[MaterialResponse]:
    materials = inventory_use_cases.list_materials(db, organization_id=organization_id)
    return [MaterialResponse.model_validate(m) for m in materials]


@router.get(
    "/{material_id}",
    response_model=MaterialResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_material(
    organization_id: UUID, material_id: UUID, db: Session = Depends(get_db)
) -> MaterialResponse:
    try:
        material = inventory_use_cases.get_material(
            db, organization_id=organization_id, material_id=material_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return MaterialResponse.model_validate(material)
