from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.domain.auth.roles import Role


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    full_name: str | None = Field(default=None, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None

    model_config = {"from_attributes": True}


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str

    model_config = {"from_attributes": True}


class MembershipResponse(BaseModel):
    organization: OrganizationResponse
    role: Role


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MeResponse(BaseModel):
    user: UserResponse
    organizations: list[MembershipResponse]


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class OrgMemberResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str | None
    role: Role
    created_at: datetime


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: Role
