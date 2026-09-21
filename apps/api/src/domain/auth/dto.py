from dataclasses import dataclass
from uuid import UUID

from src.domain.auth.roles import Role


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class MembershipView:
    organization_id: UUID
    organization_name: str
    role: Role


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID
    email: str
    full_name: str | None
