import time
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task(name="app.tasks.test.test_celery")
def test_celery(word: str) -> str:
    logger.info(f"Test task received: {word}")
    time.sleep(1)
    return f"Test task completed: {word}"
