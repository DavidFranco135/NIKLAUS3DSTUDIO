from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.application.auth.use_cases import get_user_organizations
from src.domain.auth.roles import Role
from src.infrastructure.db.models import User
from src.interfaces.http.dependencies import get_current_user, get_db
from src.interfaces.http.v1.schemas import (
    MembershipResponse,
    MeResponse,
    OrganizationResponse,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    memberships = [
        MembershipResponse(organization=OrganizationResponse.model_validate(org), role=Role(role))
        for org, role in get_user_organizations(db, user_id=current_user.id)
    ]
    return MeResponse(user=UserResponse.model_validate(current_user), organizations=memberships)
