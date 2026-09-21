from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.application.ai import use_cases
from src.domain.auth.roles import Role
from src.domain.shared.exceptions import DomainError
from src.infrastructure.db.models import User
from src.interfaces.http.dependencies import get_current_user, get_db, require_org_role
from src.interfaces.http.errors import as_http_exception
from src.interfaces.http.v1.schemas import AIJobResponse, CreateAIJobRequest

router = APIRouter(prefix="/organizations/{organization_id}/ai/jobs", tags=["ai"])


@router.post(
    "",
    response_model=AIJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_org_role(Role.OPERATOR))],
)
def create_job(
    organization_id: UUID,
    payload: CreateAIJobRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIJobResponse:
    try:
        job, _created = use_cases.create_ai_job(
            db,
            organization_id=organization_id,
            project_id=payload.project_id,
            prompt=payload.prompt,
            image_file_id=payload.image_file_id,
            requested_by=current_user.id,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return AIJobResponse.model_validate(job)


@router.get(
    "",
    response_model=list[AIJobResponse],
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def list_jobs(
    organization_id: UUID, project_id: UUID | None = None, db: Session = Depends(get_db)
) -> list[AIJobResponse]:
    jobs = use_cases.list_jobs(db, organization_id=organization_id, project_id=project_id)
    return [AIJobResponse.model_validate(job) for job in jobs]


@router.get(
    "/{job_id}",
    response_model=AIJobResponse,
    dependencies=[Depends(require_org_role(Role.VIEWER))],
)
def get_job(organization_id: UUID, job_id: UUID, db: Session = Depends(get_db)) -> AIJobResponse:
    try:
        job = use_cases.get_job(db, organization_id=organization_id, job_id=job_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return AIJobResponse.model_validate(job)
