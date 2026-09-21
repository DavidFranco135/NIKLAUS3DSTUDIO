from celery import Celery

from src.config import get_settings

settings = get_settings()

celery_app = Celery("studio", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_routes = {
    "src.infrastructure.queue.tasks.process_ai_job": {"queue": "ai"},
}
celery_app.conf.task_always_eager = settings.celery_task_always_eager
celery_app.conf.task_eager_propagates = True
