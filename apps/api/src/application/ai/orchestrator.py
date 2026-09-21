import time
from uuid import UUID

from sqlalchemy.orm import Session

from src.domain.ai.spec import StructuredSpecification, TaskType
from src.domain.shared.file_hash import sha256_hex
from src.domain.shared.storage_port import StorageProvider
from src.infrastructure.ai_providers.registry import get_providers_for_task
from src.infrastructure.db.repositories import (
    AIJobAttemptRepository,
    AIJobRepository,
    FileAssetRepository,
    ProjectRepository,
    ProjectVersionRepository,
)

_EXTENSION_BY_KIND = {
    "model_stl": ".stl",
    "model_obj": ".obj",
    "model_glb": ".glb",
    "model_3mf": ".3mf",
}

_VERSION_SOURCE_TYPE_BY_TASK = {
    TaskType.PARAMETRIC_CAD: "parametric_cad",
    TaskType.TEXT_TO_GENERATIVE_3D: "text_generative",
}


def _run_provider(task_type: TaskType, provider, spec: StructuredSpecification):
    if task_type == TaskType.PARAMETRIC_CAD:
        return provider.create_parametric_model(spec)
    return provider.generate_from_text(spec)


def execute_job(
    db: Session, storage: StorageProvider, *, organization_id: UUID, job_id: UUID
) -> None:
    """Runs the full AI job pipeline: dispatch to providers (with fallback),

    persist the result as a FileAsset (+ new ProjectVersion when the job is
    tied to a project), and update the job's status. Called from the Celery
    task — kept as a plain function so it can also be called directly (and
    synchronously) from tests without a broker.
    """
    job_repo = AIJobRepository(db)
    attempt_repo = AIJobAttemptRepository(db)

    job = job_repo.get(organization_id, job_id)
    if job is None:
        return

    job_repo.mark_processing(job)
    db.commit()

    task_type = TaskType(job.task_type)
    spec = StructuredSpecification.model_validate(job.input_spec["spec"])
    providers = get_providers_for_task(task_type)

    result = None
    last_error: Exception | None = None
    for attempt_number, provider in enumerate(providers, start=1):
        started_at = time.monotonic()
        try:
            result = _run_provider(task_type, provider, spec)
        except Exception as exc:  # noqa: BLE001 — any provider failure triggers fallback
            duration_ms = int((time.monotonic() - started_at) * 1000)
            attempt_repo.create(
                ai_job_id=job.id,
                provider_name=provider.name,
                attempt_number=attempt_number,
                status="FAILED",
                error_detail=str(exc),
                duration_ms=duration_ms,
            )
            db.commit()
            last_error = exc
            continue

        duration_ms = int((time.monotonic() - started_at) * 1000)
        attempt_repo.create(
            ai_job_id=job.id,
            provider_name=provider.name,
            attempt_number=attempt_number,
            status="SUCCEEDED",
            error_detail=None,
            duration_ms=duration_ms,
        )
        db.commit()
        break

    if result is None:
        job_repo.mark_failed(
            job, error_message=str(last_error) if last_error else "Todos os providers falharam"
        )
        db.commit()
        return

    try:
        extension = _EXTENSION_BY_KIND.get(result.kind, "")
        storage_key = f"org/{organization_id}/ai-jobs/{job.id}{extension}"
        storage.put_object(key=storage_key, data=result.file_bytes, content_type=result.mime_type)

        file_asset = FileAssetRepository(db).create_uploaded(
            organization_id=organization_id,
            project_id=job.project_id,
            kind=result.kind,
            storage_key=storage_key,
            mime_type=result.mime_type,
            size_bytes=len(result.file_bytes),
            sha256_hash=sha256_hex(result.file_bytes),
            uploaded_by=job.requested_by,
        )

        result_version_id = None
        if job.project_id is not None:
            project = ProjectRepository(db).get(organization_id, job.project_id)
            if project is not None:
                version_repo = ProjectVersionRepository(db)
                version = version_repo.create(
                    project_id=project.id,
                    version_number=version_repo.next_version_number(project.id),
                    label=f"Gerado por IA ({job.task_type})",
                    source_type=_VERSION_SOURCE_TYPE_BY_TASK[task_type],
                    created_by=job.requested_by,
                )
                FileAssetRepository(db).attach_to_version(
                    file_asset, project_version_id=version.id
                )
                project.active_version_id = version.id
                result_version_id = version.id
    except Exception as exc:  # noqa: BLE001 — a real provider succeeded; don't crash the
        # worker/request over a storage/DB hiccup while persisting its result.
        db.rollback()
        job = job_repo.get(organization_id, job_id)
        if job is not None:
            job_repo.mark_failed(job, error_message=f"Falha ao salvar o resultado: {exc}")
            db.commit()
        return

    job_repo.mark_completed(
        job, result_file_id=file_asset.id, result_project_version_id=result_version_id
    )
    db.commit()
