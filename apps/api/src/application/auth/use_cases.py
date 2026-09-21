from uuid import UUID

from sqlalchemy.orm import Session

from src.application.organizations.slug import unique_org_slug
from src.domain.auth.dto import TokenPair
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    RefreshTokenInvalidError,
)
from src.domain.shared.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from src.infrastructure.db.models import Organization, User
from src.infrastructure.db.repositories import (
    OrganizationRepository,
    OrgMemberRepository,
    RefreshTokenRepository,
    UserRepository,
)


def _issue_token_pair(db: Session, user: User) -> TokenPair:
    refresh_plaintext, refresh_hash, expires_at = generate_refresh_token()
    RefreshTokenRepository(db).create(
        user_id=user.id, token_hash=refresh_hash, expires_at=expires_at
    )
    access_token = create_access_token(str(user.id))
    return TokenPair(access_token=access_token, refresh_token=refresh_plaintext)


def register(
    db: Session, *, organization_name: str, email: str, password: str, full_name: str | None
) -> tuple[User, Organization, TokenPair]:
    user_repo = UserRepository(db)
    if user_repo.get_by_email(email) is not None:
        raise EmailAlreadyRegisteredError(email)

    organization = OrganizationRepository(db).create(
        name=organization_name, slug=unique_org_slug(db, organization_name)
    )
    user = user_repo.create(email=email, password_hash=hash_password(password), full_name=full_name)
    OrgMemberRepository(db).create(
        organization_id=organization.id, user_id=user.id, role=Role.OWNER.value
    )

    tokens = _issue_token_pair(db, user)
    db.commit()
    return user, organization, tokens


def login(db: Session, *, email: str, password: str) -> tuple[User, TokenPair]:
    user = UserRepository(db).get_by_email(email)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    tokens = _issue_token_pair(db, user)
    db.commit()
    return user, tokens


def refresh_session(db: Session, *, refresh_token_plaintext: str) -> tuple[User, TokenPair]:
    token_repo = RefreshTokenRepository(db)
    token = token_repo.get_valid_by_hash(hash_refresh_token(refresh_token_plaintext))
    if token is None:
        raise RefreshTokenInvalidError()

    user = UserRepository(db).get_by_id(token.user_id)
    if user is None or not user.is_active:
        raise RefreshTokenInvalidError()

    token_repo.revoke(token)
    tokens = _issue_token_pair(db, user)
    db.commit()
    return user, tokens


def logout(db: Session, *, refresh_token_plaintext: str) -> None:
    token_repo = RefreshTokenRepository(db)
    token = token_repo.get_valid_by_hash(hash_refresh_token(refresh_token_plaintext))
    if token is not None:
        token_repo.revoke(token)
        db.commit()


def get_user_organizations(db: Session, *, user_id: UUID) -> list[tuple[Organization, str]]:
    member_repo = OrgMemberRepository(db)
    organizations = OrganizationRepository(db).list_for_user(user_id)
    result = []
    for org in organizations:
        member = member_repo.get(org.id, user_id)
        assert member is not None
        result.append((org, member.role))
    return result
