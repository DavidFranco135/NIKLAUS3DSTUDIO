from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.db.models import Organization, OrgMember, RefreshToken, User


def _as_aware_utc(value: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip even for DateTime(timezone=True); Postgres keeps it."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def create(self, *, email: str, password_hash: str, full_name: str | None) -> User:
        user = User(email=email, password_hash=password_hash, full_name=full_name)
        self.session.add(user)
        self.session.flush()
        return user


class OrganizationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, organization_id: UUID) -> Organization | None:
        return self.session.get(Organization, organization_id)

    def slug_exists(self, slug: str) -> bool:
        stmt = select(Organization).where(Organization.slug == slug)
        return self.session.scalar(stmt) is not None

    def create(self, *, name: str, slug: str) -> Organization:
        organization = Organization(name=name, slug=slug)
        self.session.add(organization)
        self.session.flush()
        return organization

    def list_for_user(self, user_id: UUID) -> list[Organization]:
        return list(
            self.session.scalars(
                select(Organization)
                .join(OrgMember, OrgMember.organization_id == Organization.id)
                .where(OrgMember.user_id == user_id)
                .order_by(Organization.created_at)
            )
        )


class OrgMemberRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, organization_id: UUID, user_id: UUID) -> OrgMember | None:
        return self.session.scalar(
            select(OrgMember).where(
                OrgMember.organization_id == organization_id,
                OrgMember.user_id == user_id,
            )
        )

    def list_for_org(self, organization_id: UUID) -> list[OrgMember]:
        return list(
            self.session.scalars(
                select(OrgMember)
                .where(OrgMember.organization_id == organization_id)
                .order_by(OrgMember.created_at)
            )
        )

    def count_owners(self, organization_id: UUID) -> int:
        return len(
            [
                m
                for m in self.list_for_org(organization_id)
                if m.role == "OWNER"
            ]
        )

    def create(
        self, *, organization_id: UUID, user_id: UUID, role: str, invited_by: UUID | None = None
    ) -> OrgMember:
        member = OrgMember(
            organization_id=organization_id, user_id=user_id, role=role, invited_by=invited_by
        )
        self.session.add(member)
        self.session.flush()
        return member

    def delete(self, member: OrgMember) -> None:
        self.session.delete(member)
        self.session.flush()


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, user_id: UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.session.add(token)
        self.session.flush()
        return token

    def get_valid_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        token = self.session.scalar(stmt)
        if token is None or token.revoked_at is not None:
            return None
        if _as_aware_utc(token.expires_at) < datetime.now(UTC):
            return None
        return token

    def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        self.session.flush()
