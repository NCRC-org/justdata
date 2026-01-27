"""
Celery application for JustData background tasks.
"""

from celery import Celery
from core.config.settings import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "justdata",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "apps.branchsight.tasks",
        "apps.lendsight.tasks",
        "apps.bizsight.tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
    beat_schedule={
        "cleanup-old-reports": {
            "task": "shared.services.cleanup.cleanup_old_reports",
            "schedule": 86400.0,  # Daily
        },
        "update-data-sources": {
            "task": "shared.services.data_sync.sync_data_sources",
            "schedule": 3600.0,  # Hourly
        },
    }
)

# Task routing
celery_app.conf.task_routes = {
    "apps.branchsight.*": {"queue": "branchsight"},
    "apps.lendsight.*": {"queue": "lendsight"},
    "apps.bizsight.*": {"queue": "bizsight"},
    "shared.services.*": {"queue": "shared"},
}

if __name__ == "__main__":
    celery_app.start()
