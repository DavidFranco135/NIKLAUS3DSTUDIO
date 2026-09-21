from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.application.organizations import use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.infrastructure.db.models import OrgMember, User
from src.infrastructure.db.repositories import OrganizationRepository, UserRepository
from src.interfaces.http.dependencies import get_current_user, get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import (
    AddMemberRequest,
    CreateOrganizationRequest,
    OrganizationResponse,
    OrgMemberResponse,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _to_member_response(db: Session, member: OrgMember) -> OrgMemberResponse:
    user = UserRepository(db).get_by_id(member.user_id)
    assert user is not None
    return OrgMemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=Role(member.role),
        created_at=member.created_at,
    )


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: CreateOrganizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationResponse:
    organization = use_cases.create_organization(
        db, owner_user_id=current_user.id, name=payload.name
    )
    return OrganizationResponse.model_validate(organization)


@router.get("", response_model=list[OrganizationResponse])
def list_my_organizations(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[OrganizationResponse]:
    organizations = OrganizationRepository(db).list_for_user(current_user.id)
    return [OrganizationResponse.model_validate(org) for org in organizations]


@router.get(
    "/{organization_id}/members",
    response_model=list[OrgMemberResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_members(organization_id: UUID, db: Session = Depends(get_db)) -> list[OrgMemberResponse]:
    members = use_cases.list_members(db, organization_id=organization_id)
    return [_to_member_response(db, member) for member in members]


@router.post(
    "/{organization_id}/members",
    response_model=OrgMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    organization_id: UUID,
    payload: AddMemberRequest,
    db: Session = Depends(get_db),
    acting_member: OrgMember = Depends(require_org_role(Role.ADMIN)),
) -> OrgMemberResponse:
    try:
        member = use_cases.add_member(
            db,
            organization_id=organization_id,
            email=payload.email,
            role=payload.role,
            invited_by=acting_member.user_id,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return _to_member_response(db, member)


@router.delete(
    "/{organization_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_org_role(Role.ADMIN))],
)
def remove_member(organization_id: UUID, user_id: UUID, db: Session = Depends(get_db)) -> None:
    try:
        use_cases.remove_member(db, organization_id=organization_id, target_user_id=user_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
