from uuid import UUID

from sqlalchemy.orm import Session

from src.application.organizations.slug import unique_org_slug
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import (
    CannotRemoveLastOwnerError,
    OrganizationNotFoundError,
    UserAlreadyMemberError,
    UserNotFoundError,
)
from src.infrastructure.db.models import Organization, OrgMember
from src.infrastructure.db.repositories import (
    OrganizationRepository,
    OrgMemberRepository,
    UserRepository,
)


def create_organization(db: Session, *, owner_user_id: UUID, name: str) -> Organization:
    organization = OrganizationRepository(db).create(name=name, slug=unique_org_slug(db, name))
    OrgMemberRepository(db).create(
        organization_id=organization.id, user_id=owner_user_id, role=Role.OWNER.value
    )
    db.commit()
    return organization


def list_members(db: Session, *, organization_id: UUID) -> list[OrgMember]:
    return OrgMemberRepository(db).list_for_org(organization_id)


def add_member(
    db: Session, *, organization_id: UUID, email: str, role: Role, invited_by: UUID
) -> OrgMember:
    if OrganizationRepository(db).get_by_id(organization_id) is None:
        raise OrganizationNotFoundError(str(organization_id))

    user = UserRepository(db).get_by_email(email)
    if user is None:
        raise UserNotFoundError(email)

    member_repo = OrgMemberRepository(db)
    if member_repo.get(organization_id, user.id) is not None:
        raise UserAlreadyMemberError(email)

    member = member_repo.create(
        organization_id=organization_id, user_id=user.id, role=role.value, invited_by=invited_by
    )
    db.commit()
    return member


def remove_member(db: Session, *, organization_id: UUID, target_user_id: UUID) -> None:
    member_repo = OrgMemberRepository(db)
    member = member_repo.get(organization_id, target_user_id)
    if member is None:
        raise UserNotFoundError(str(target_user_id))

    if member.role == Role.OWNER.value and member_repo.count_owners(organization_id) <= 1:
        raise CannotRemoveLastOwnerError()

    member_repo.delete(member)
    db.commit()
