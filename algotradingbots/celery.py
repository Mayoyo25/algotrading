# algotradingbots/celery.py
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algotradingbots.settings')

app = Celery('algotradingbots')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    result_backend='redis://localhost:6379/0',
    broker_url='redis://localhost:6379/0',
    task_always_eager=False,
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_eager_result=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50,
)

# Task routing (optional)
app.conf.task_routes = {
    'backtest.tasks.run_backtest_task': {'queue': 'backtest'},
    'backtest.tasks.download_market_data': {'queue': 'data'},
    'backtest.tasks.cleanup_old_jobs': {'queue': 'maintenance'},
}

# Periodic tasks
from celery.schedules import crontab

app.conf.beat_schedule = {
    'cleanup-old-jobs': {
        'task': 'backtest.tasks.cleanup_old_jobs',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Add to algotradingbots/__init__.py
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)