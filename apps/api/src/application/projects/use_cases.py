from uuid import UUID

from sqlalchemy.orm import Session

from src.application.billing.use_cases import KEY_MAX_PROJECTS, enforce_numeric_limit
from src.application.customers.use_cases import get_customer
from src.domain.shared.exceptions import (
    FileAssetNotFoundError,
    FileNotUploadedError,
    ProjectNotFoundError,
    ProjectVersionNotFoundError,
)
from src.infrastructure.db.models import FileAsset, Project, ProjectVersion
from src.infrastructure.db.repositories import (
    FileAssetRepository,
    ProjectRepository,
    ProjectVersionRepository,
)


def create_project(
    db: Session,
    *,
    organization_id: UUID,
    name: str,
    description: str | None,
    created_by: UUID,
    customer_id: UUID | None = None,
) -> Project:
    if customer_id is not None:
        get_customer(db, organization_id=organization_id, customer_id=customer_id)

    current_count = len(ProjectRepository(db).list_for_org(organization_id))
    enforce_numeric_limit(
        db, organization_id=organization_id, key=KEY_MAX_PROJECTS, current_usage=current_count
    )

    project = ProjectRepository(db).create(
        organization_id=organization_id,
        name=name,
        description=description,
        created_by=created_by,
        customer_id=customer_id,
    )
    db.commit()
    return project


def list_projects(db: Session, *, organization_id: UUID) -> list[Project]:
    return ProjectRepository(db).list_for_org(organization_id)


def get_project(db: Session, *, organization_id: UUID, project_id: UUID) -> Project:
    project = ProjectRepository(db).get(organization_id, project_id)
    if project is None:
        raise ProjectNotFoundError(str(project_id))
    return project


def update_project(
    db: Session,
    *,
    organization_id: UUID,
    project_id: UUID,
    name: str | None,
    description: str | None,
    status: str | None,
) -> Project:
    project = get_project(db, organization_id=organization_id, project_id=project_id)
    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    if status is not None:
        project.status = status
    db.commit()
    return project


def delete_project(db: Session, *, organization_id: UUID, project_id: UUID) -> None:
    project = get_project(db, organization_id=organization_id, project_id=project_id)
    ProjectRepository(db).soft_delete(project)
    db.commit()


def list_versions(db: Session, *, organization_id: UUID, project_id: UUID) -> list[ProjectVersion]:
    get_project(db, organization_id=organization_id, project_id=project_id)
    return ProjectVersionRepository(db).list_for_project(project_id)


def create_version(
    db: Session,
    *,
    organization_id: UUID,
    project_id: UUID,
    file_id: UUID,
    label: str | None,
    created_by: UUID,
) -> ProjectVersion:
    project = get_project(db, organization_id=organization_id, project_id=project_id)

    file_repo = FileAssetRepository(db)
    file_asset = file_repo.get(organization_id, file_id)
    if file_asset is None or file_asset.project_id != project.id:
        raise FileAssetNotFoundError(str(file_id))
    if file_asset.status != "uploaded":
        raise FileNotUploadedError(file_asset.storage_key)

    version_repo = ProjectVersionRepository(db)
    version = version_repo.create(
        project_id=project.id,
        version_number=version_repo.next_version_number(project.id),
        label=label,
        source_type="manual_upload",
        created_by=created_by,
    )
    file_repo.attach_to_version(file_asset, project_version_id=version.id)
    project.active_version_id = version.id
    db.commit()
    return version


def list_version_files(
    db: Session, *, organization_id: UUID, project_id: UUID, version_id: UUID
) -> list[FileAsset]:
    get_project(db, organization_id=organization_id, project_id=project_id)
    version = ProjectVersionRepository(db).get(project_id, version_id)
    if version is None:
        raise ProjectVersionNotFoundError(str(version_id))
    return FileAssetRepository(db).list_for_version(version_id)


def activate_version(
    db: Session, *, organization_id: UUID, project_id: UUID, version_id: UUID
) -> Project:
    project = get_project(db, organization_id=organization_id, project_id=project_id)
    version = ProjectVersionRepository(db).get(project_id, version_id)
    if version is None:
        raise ProjectVersionNotFoundError(str(version_id))

    project.active_version_id = version.id
    db.commit()
    return project
