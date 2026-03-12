from celery import Celery
from app.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    include=[
        "app.tasks.test",
        "app.tasks.pipeline",  # Added pipeline tasks
        "app.tasks.quality_gate",
        "app.tasks.vin_ocr",
        "app.tasks.damage_detection",
        "app.tasks.damage_hashing",
        "app.tasks.duplicate_detection",
        "app.tasks.damage_segmentation",
        "app.tasks.pii_redaction",
        "app.tasks.icve_calculation",
        "app.tasks.assignment"  # Added assignment tasks
    ],
    task_routes={
        "app.tasks.*": {"queue": "main-queue"},
        "app.tasks.ai.*": {"queue": "ai-queue"},
    },
)
