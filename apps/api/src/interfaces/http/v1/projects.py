from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.application.files import use_cases as file_use_cases
from src.application.projects import use_cases as project_use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.domain.shared.storage_port import StorageProvider
from src.infrastructure.db.models import User
from src.interfaces.http.dependencies import get_current_user, get_db, get_storage, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import (
    CreateProjectRequest,
    CreateVersionRequest,
    DownloadUrlResponse,
    FileAssetResponse,
    ProjectResponse,
    ProjectVersionResponse,
    RequestUploadRequest,
    RequestUploadResponse,
    UpdateProjectRequest,
)

router = APIRouter(prefix="/organizations/{organization_id}/projects", tags=["projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def create_project(
    organization_id: UUID,
    payload: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    try:
        project = project_use_cases.create_project(
            db,
            organization_id=organization_id,
            name=payload.name,
            description=payload.description,
            created_by=current_user.id,
            customer_id=payload.customer_id,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ProjectResponse.model_validate(project)


@router.get(
    "",
    response_model=list[ProjectResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_projects(organization_id: UUID, db: Session = Depends(get_db)) -> list[ProjectResponse]:
    projects = project_use_cases.list_projects(db, organization_id=organization_id)
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_project(
    organization_id: UUID, project_id: UUID, db: Session = Depends(get_db)
) -> ProjectResponse:
    try:
        project = project_use_cases.get_project(
            db, organization_id=organization_id, project_id=project_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ProjectResponse.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def update_project(
    organization_id: UUID,
    project_id: UUID,
    payload: UpdateProjectRequest,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    try:
        project = project_use_cases.update_project(
            db,
            organization_id=organization_id,
            project_id=project_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ProjectResponse.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_org_role(Role.MANAGER))],
)
def delete_project(organization_id: UUID, project_id: UUID, db: Session = Depends(get_db)) -> None:
    try:
        project_use_cases.delete_project(db, organization_id=organization_id, project_id=project_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc


@router.get(
    "/{project_id}/versions",
    response_model=list[ProjectVersionResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_versions(
    organization_id: UUID, project_id: UUID, db: Session = Depends(get_db)
) -> list[ProjectVersionResponse]:
    try:
        versions = project_use_cases.list_versions(
            db, organization_id=organization_id, project_id=project_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return [ProjectVersionResponse.model_validate(v) for v in versions]


@router.post(
    "/{project_id}/versions",
    response_model=ProjectVersionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def create_version(
    organization_id: UUID,
    project_id: UUID,
    payload: CreateVersionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectVersionResponse:
    try:
        version = project_use_cases.create_version(
            db,
            organization_id=organization_id,
            project_id=project_id,
            file_id=payload.file_id,
            label=payload.label,
            created_by=current_user.id,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ProjectVersionResponse.model_validate(version)


@router.post(
    "/{project_id}/versions/{version_id}/activate",
    response_model=ProjectResponse,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def activate_version(
    organization_id: UUID, project_id: UUID, version_id: UUID, db: Session = Depends(get_db)
) -> ProjectResponse:
    try:
        project = project_use_cases.activate_version(
            db, organization_id=organization_id, project_id=project_id, version_id=version_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ProjectResponse.model_validate(project)


@router.get(
    "/{project_id}/versions/{version_id}/files",
    response_model=list[FileAssetResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_version_files(
    organization_id: UUID, project_id: UUID, version_id: UUID, db: Session = Depends(get_db)
) -> list[FileAssetResponse]:
    try:
        files = project_use_cases.list_version_files(
            db, organization_id=organization_id, project_id=project_id, version_id=version_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return [FileAssetResponse.model_validate(f) for f in files]


@router.post(
    "/{project_id}/files/upload-url",
    response_model=RequestUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def request_upload(
    organization_id: UUID,
    project_id: UUID,
    payload: RequestUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage),
) -> RequestUploadResponse:
    try:
        project_use_cases.get_project(db, organization_id=organization_id, project_id=project_id)
        file_asset, upload_url = file_use_cases.request_upload(
            db,
            storage,
            organization_id=organization_id,
            project_id=project_id,
            filename=payload.filename,
            mime_type=payload.mime_type,
            kind=payload.kind,
            uploaded_by=current_user.id,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return RequestUploadResponse(
        file_id=file_asset.id, upload_url=upload_url, storage_key=file_asset.storage_key
    )


@router.post(
    "/{project_id}/files/{file_id}/confirm",
    response_model=FileAssetResponse,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def confirm_upload(
    organization_id: UUID,
    project_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage),
) -> FileAssetResponse:
    try:
        file_asset = file_use_cases.confirm_upload(
            db, storage, organization_id=organization_id, file_id=file_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return FileAssetResponse.model_validate(file_asset)


@router.get(
    "/{project_id}/files/{file_id}/download-url",
    response_model=DownloadUrlResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_download_url(
    organization_id: UUID,
    project_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage),
) -> DownloadUrlResponse:
    try:
        url = file_use_cases.get_download_url(
            db, storage, organization_id=organization_id, file_id=file_id
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return DownloadUrlResponse(download_url=url)
