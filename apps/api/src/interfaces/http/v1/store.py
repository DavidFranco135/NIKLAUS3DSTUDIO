from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from src.application.store import use_cases as store_use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.interfaces.http.dependencies import get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import (
    PublicStoreResponse,
    StoreAdminResponse,
    StoreSettings,
)

router = APIRouter(prefix="/organizations/{organization_id}/store", tags=["store"])
public_router = APIRouter(prefix="/public", tags=["public"])


@router.get(
    "",
    response_model=StoreAdminResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_store(organization_id: UUID, db: Session = Depends(get_db)) -> StoreAdminResponse:
    try:
        return store_use_cases.get_store_settings(db, organization_id=organization_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc


@router.put(
    "",
    response_model=StoreAdminResponse,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def save_store(
    organization_id: UUID, payload: StoreSettings, db: Session = Depends(get_db)
) -> StoreAdminResponse:
    try:
        return store_use_cases.save_store_settings(
            db, organization_id=organization_id, settings=payload
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc


@public_router.get("/stores/{slug}", response_model=PublicStoreResponse)
def get_public_store(
    slug: str, response: Response, db: Session = Depends(get_db)
) -> PublicStoreResponse:
    try:
        store = store_use_cases.get_public_store(db, slug=slug)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    response.headers["Cache-Control"] = "public, max-age=30"
    return store
