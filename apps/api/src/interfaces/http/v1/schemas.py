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


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(draft|in_progress|completed|archived)$")


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    status: str
    active_version_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectVersionResponse(BaseModel):
    id: UUID
    version_number: int
    label: str | None
    source_type: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateVersionRequest(BaseModel):
    file_id: UUID
    label: str | None = Field(default=None, max_length=200)


class RequestUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    kind: str


class RequestUploadResponse(BaseModel):
    file_id: UUID
    upload_url: str
    storage_key: str


class FileAssetResponse(BaseModel):
    id: UUID
    kind: str
    mime_type: str
    size_bytes: int | None
    status: str

    model_config = {"from_attributes": True}


class DownloadUrlResponse(BaseModel):
    download_url: str
