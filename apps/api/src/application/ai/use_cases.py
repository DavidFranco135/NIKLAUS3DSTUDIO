import hashlib
import json
from uuid import UUID

from sqlalchemy.orm import Session

from src.domain.ai.classifier import classify_task
from src.domain.ai.spec import TaskType
from src.domain.shared.exceptions import AIJobNotFoundError
from src.infrastructure.ai_providers.registry import get_llm_provider
from src.infrastructure.db.models import AIJob, AIJobAttempt
from src.infrastructure.db.repositories import AIJobAttemptRepository, AIJobRepository
from src.infrastructure.queue.tasks import process_ai_job

_QUEUE_BY_TASK_TYPE = {
    TaskType.PARAMETRIC_CAD: "ai.cad",
    TaskType.TEXT_TO_GENERATIVE_3D: "ai.generate",
}


def _idempotency_key(*, prompt: str, project_id: UUID | None) -> str:
    payload = json.dumps(
        {"prompt": prompt.strip().lower(), "project_id": str(project_id) if project_id else None},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def create_ai_job(
    db: Session, *, organization_id: UUID, project_id: UUID | None, prompt: str, requested_by: UUID
) -> tuple[AIJob, bool]:
    """Returns (job, created). `created=False` means an equivalent job was

    already in flight (or done) for this prompt+project — the idempotency key
    from ARCHITECTURE.md section 15, so re-submitting the same request from a
    flaky client doesn't spawn duplicate work.
    """
    idempotency_key = _idempotency_key(prompt=prompt, project_id=project_id)
    job_repo = AIJobRepository(db)

    existing = job_repo.get_active_by_idempotency_key(organization_id, idempotency_key)
    if existing is not None:
        return existing, False

    spec = get_llm_provider().extract_specification(prompt)
    task_type = classify_task(spec)

    job = job_repo.create(
        organization_id=organization_id,
        project_id=project_id,
        requested_by=requested_by,
        task_type=task_type.value,
        input_spec={"prompt": prompt, "spec": spec.model_dump()},
        queue_name=_QUEUE_BY_TASK_TYPE[task_type],
        idempotency_key=idempotency_key,
    )
    db.commit()

    job_id = job.id
    process_ai_job.delay(str(organization_id), str(job_id))
    # In eager mode (tests, and dev without a broker) the task above already ran
    # synchronously against a *different* DB session and committed its changes.
    # This session's identity map still holds the pre-task object, so it needs
    # to be expired or callers reading `job` right after this call see stale data.
    db.expire_all()
    return job_repo.get(organization_id, job_id), True


def get_job(db: Session, *, organization_id: UUID, job_id: UUID) -> AIJob:
    job = AIJobRepository(db).get(organization_id, job_id)
    if job is None:
        raise AIJobNotFoundError(str(job_id))
    return job


def list_jobs(db: Session, *, organization_id: UUID, project_id: UUID | None) -> list[AIJob]:
    return AIJobRepository(db).list_for_org(organization_id, project_id=project_id)


def list_job_attempts(db: Session, *, ai_job_id: UUID) -> list[AIJobAttempt]:
    return AIJobAttemptRepository(db).list_for_job(ai_job_id)
