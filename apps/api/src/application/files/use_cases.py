from pathlib import PurePosixPath
from uuid import UUID

from sqlalchemy.orm import Session

from src.application.billing.use_cases import KEY_MAX_STORAGE_MB, enforce_numeric_limit
from src.domain.shared.exceptions import (
    FileAssetNotFoundError,
    FileNotUploadedError,
    UnsupportedFileKindError,
)
from src.domain.shared.file_kinds import ALLOWED_FILE_KINDS
from src.domain.shared.storage_port import StorageProvider
from src.infrastructure.db.models import FileAsset
from src.infrastructure.db.repositories import FileAssetRepository

UPLOAD_URL_EXPIRES_IN = 900
DOWNLOAD_URL_EXPIRES_IN = 300


def _storage_key(
    *, organization_id: UUID, project_id: UUID | None, file_id: UUID, filename: str
) -> str:
    suffix = PurePosixPath(filename).suffix or ""
    project_segment = str(project_id) if project_id is not None else "unscoped"
    return f"org/{organization_id}/project/{project_segment}/{file_id}{suffix}"


def request_upload(
    db: Session,
    storage: StorageProvider,
    *,
    organization_id: UUID,
    project_id: UUID | None,
    filename: str,
    mime_type: str,
    kind: str,
    uploaded_by: UUID,
) -> tuple[FileAsset, str]:
    if kind not in ALLOWED_FILE_KINDS:
        raise UnsupportedFileKindError(kind)

    repo = FileAssetRepository(db)
    file_asset = repo.create(
        organization_id=organization_id,
        project_id=project_id,
        kind=kind,
        storage_key="pending",
        mime_type=mime_type,
        uploaded_by=uploaded_by,
    )
    storage_key = _storage_key(
        organization_id=organization_id,
        project_id=project_id,
        file_id=file_asset.id,
        filename=filename,
    )
    file_asset.storage_key = storage_key
    db.flush()

    upload_url = storage.upload_url(
        key=storage_key, content_type=mime_type, expires_in=UPLOAD_URL_EXPIRES_IN
    )
    db.commit()
    return file_asset, upload_url


def confirm_upload(
    db: Session, storage: StorageProvider, *, organization_id: UUID, file_id: UUID
) -> FileAsset:
    repo = FileAssetRepository(db)
    file_asset = repo.get(organization_id, file_id)
    if file_asset is None:
        raise FileAssetNotFoundError(str(file_id))

    stat = storage.stat(key=file_asset.storage_key)
    if stat is None:
        raise FileNotUploadedError(file_asset.storage_key)

    # O arquivo já foi enviado ao storage neste ponto (URL pré-assinada, sem
    # como bloquear antes) — o limite é aplicado aqui, antes de marcar como
    # "uploaded": se ultrapassar a cota, o arquivo fica "pending" para
    # sempre, nunca soma no total (`sum_size_bytes_for_org` só conta
    # status="uploaded"), e nunca fica utilizável pela plataforma.
    projected_bytes = repo.sum_size_bytes_for_org(organization_id) + stat.size_bytes
    enforce_numeric_limit(
        db,
        organization_id=organization_id,
        key=KEY_MAX_STORAGE_MB,
        current_usage=projected_bytes / (1024 * 1024),
    )

    repo.mark_uploaded(
        file_asset, size_bytes=stat.size_bytes, mime_type=stat.content_type or file_asset.mime_type
    )
    db.commit()
    return file_asset


def get_download_url(
    db: Session, storage: StorageProvider, *, organization_id: UUID, file_id: UUID
) -> str:
    file_asset = FileAssetRepository(db).get(organization_id, file_id)
    if file_asset is None:
        raise FileAssetNotFoundError(str(file_id))
    if file_asset.status != "uploaded":
        raise FileNotUploadedError(file_asset.storage_key)

    return storage.download_url(key=file_asset.storage_key, expires_in=DOWNLOAD_URL_EXPIRES_IN)
