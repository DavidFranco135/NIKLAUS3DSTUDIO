from uuid import UUID

from src.application.ai.orchestrator import execute_job
from src.infrastructure.db import session as db_session_module
from src.infrastructure.queue.celery_app import celery_app
from src.infrastructure.storage import s3_storage as storage_module


@celery_app.task(name="src.infrastructure.queue.tasks.process_ai_job")
def process_ai_job(organization_id: str, job_id: str) -> None:
    db = db_session_module.SessionLocal()
    try:
        storage = storage_module.get_storage_provider()
        execute_job(db, storage, organization_id=UUID(organization_id), job_id=UUID(job_id))
    finally:
        db.close()
