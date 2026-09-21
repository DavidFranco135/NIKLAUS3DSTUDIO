from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.domain.auth.roles import Role, role_at_least
from src.domain.shared.security import decode_access_token
from src.infrastructure.db.models import OrgMember, User
from src.infrastructure.db.repositories import OrgMemberRepository, UserRepository
from src.infrastructure.db.session import get_db


def get_current_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from None

    user = UserRepository(db).get_by_id(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return user


def require_org_role(minimum: Role):
    def dependency(
        organization_id: UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> OrgMember:
        member = OrgMemberRepository(db).get(organization_id, current_user.id)
        if member is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this organization")
        if not role_at_least(Role(member.role), minimum):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role for this action")
        return member

    return dependency
