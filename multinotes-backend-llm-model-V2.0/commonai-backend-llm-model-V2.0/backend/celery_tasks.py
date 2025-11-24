"""
Celery task base classes and utilities for MultinotesAI.

This module provides:
- BaseTask with retry logic and error handling
- CallbackTask for tasks with success/failure callbacks
- Task decorators with exponential backoff
- Common task utilities
"""

from celery import Task, shared_task
from celery.exceptions import MaxRetriesExceededError, Reject
from django.core.mail import send_mail
from django.conf import settings
import logging
import traceback
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# =============================================================================
# Task Configuration
# =============================================================================

class TaskConfig:
    """Default task configuration values."""

    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 60  # seconds
    RETRY_BACKOFF = 2  # exponential backoff multiplier
    RETRY_BACKOFF_MAX = 3600  # max delay (1 hour)

    # Task timeouts
    SOFT_TIME_LIMIT = 300  # 5 minutes
    TIME_LIMIT = 600  # 10 minutes

    # Priority levels
    PRIORITY_HIGH = 0
    PRIORITY_NORMAL = 5
    PRIORITY_LOW = 9


# =============================================================================
# Base Task Classes
# =============================================================================

class BaseTask(Task):
    """
    Base task class with enhanced error handling and retry logic.

    Features:
    - Automatic retry with exponential backoff
    - Structured logging
    - Error notification
    - Task lifecycle hooks

    Usage:
        @shared_task(bind=True, base=BaseTask)
        def my_task(self, arg1, arg2):
            return process(arg1, arg2)
    """

    # Default settings
    autoretry_for = (Exception,)
    max_retries = TaskConfig.MAX_RETRIES
    default_retry_delay = TaskConfig.RETRY_DELAY
    retry_backoff = TaskConfig.RETRY_BACKOFF
    retry_backoff_max = TaskConfig.RETRY_BACKOFF_MAX
    retry_jitter = True

    # Timeout settings
    soft_time_limit = TaskConfig.SOFT_TIME_LIMIT
    time_limit = TaskConfig.TIME_LIMIT

    # Don't auto-acknowledge until complete
    acks_late = True
    reject_on_worker_lost = True

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        logger.warning(
            f"Task {self.name}[{task_id}] retry #{self.request.retries}: {exc}",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'retry_count': self.request.retries,
                'exception': str(exc),
            }
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails permanently."""
        logger.error(
            f"Task {self.name}[{task_id}] failed: {exc}",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'args': args,
                'kwargs': kwargs,
                'exception': str(exc),
                'traceback': traceback.format_exc(),
            }
        )
        self._notify_failure(exc, task_id, args, kwargs)
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(
            f"Task {self.name}[{task_id}] completed successfully",
            extra={
                'task_id': task_id,
                'task_name': self.name,
            }
        )
        super().on_success(retval, task_id, args, kwargs)

    def before_start(self, task_id, args, kwargs):
        """Called before task starts."""
        logger.info(
            f"Task {self.name}[{task_id}] starting",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'args': args,
                'kwargs': kwargs,
            }
        )

    def _notify_failure(self, exc, task_id, args, kwargs):
        """Send notification on critical task failure."""
        if not getattr(settings, 'TASK_FAILURE_NOTIFY', False):
            return

        try:
            admin_emails = getattr(settings, 'ADMIN_EMAILS', [])
            if admin_emails:
                send_mail(
                    subject=f"[MultinotesAI] Task Failed: {self.name}",
                    message=f"""
Task: {self.name}
Task ID: {task_id}
Error: {exc}

Arguments: {args}
Keyword Arguments: {kwargs}

Traceback:
{traceback.format_exc()}
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=True,
                )
        except Exception as e:
            logger.error(f"Failed to send task failure notification: {e}")


class CallbackTask(BaseTask):
    """
    Task with success/failure callback support.

    Usage:
        @shared_task(bind=True, base=CallbackTask)
        def my_task(self, arg1, on_success=None, on_failure=None):
            result = process(arg1)
            return result

        # The on_success/on_failure callbacks will be called automatically
    """

    def on_success(self, retval, task_id, args, kwargs):
        """Execute success callback if provided."""
        super().on_success(retval, task_id, args, kwargs)

        callback = kwargs.get('on_success')
        if callback and callable(callback):
            try:
                callback(retval, task_id)
            except Exception as e:
                logger.error(f"Success callback failed: {e}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Execute failure callback if provided."""
        super().on_failure(exc, task_id, args, kwargs, einfo)

        callback = kwargs.get('on_failure')
        if callback and callable(callback):
            try:
                callback(exc, task_id)
            except Exception as e:
                logger.error(f"Failure callback failed: {e}")


class LongRunningTask(BaseTask):
    """
    Task class for long-running operations with extended timeouts.

    Usage:
        @shared_task(bind=True, base=LongRunningTask)
        def process_large_file(self, file_id):
            # This can run for up to 30 minutes
            return process(file_id)
    """

    soft_time_limit = 1800  # 30 minutes
    time_limit = 2100  # 35 minutes
    max_retries = 2


class CriticalTask(BaseTask):
    """
    Task class for critical operations that must complete.

    Features higher retry counts and longer backoffs.
    """

    max_retries = 5
    default_retry_delay = 120
    retry_backoff_max = 7200  # 2 hours


# =============================================================================
# Task Decorators
# =============================================================================

def with_retry(max_retries=3, delay=60, backoff=2, exceptions=(Exception,)):
    """
    Decorator to add retry logic to any function.

    Usage:
        @with_retry(max_retries=3, delay=30)
        def call_external_api():
            return api.call()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}"
                        )
                        import time
                        time.sleep(current_delay)
                        current_delay = min(current_delay * backoff, 3600)
                    else:
                        logger.error(
                            f"All retries exhausted for {func.__name__}: {e}"
                        )
                        raise last_exception
            raise last_exception
        return wrapper
    return decorator


def async_task(queue='default', priority=TaskConfig.PRIORITY_NORMAL):
    """
    Decorator to easily create async tasks.

    Usage:
        @async_task(queue='emails', priority=TaskConfig.PRIORITY_HIGH)
        def send_welcome_email(user_id):
            # Send email
            pass

        # Call asynchronously
        send_welcome_email.delay(user_id=123)
    """
    def decorator(func):
        return shared_task(
            bind=True,
            base=BaseTask,
            queue=queue,
            priority=priority,
            name=f"multinotesai.{func.__name__}"
        )(func)
    return decorator


# =============================================================================
# Task Utilities
# =============================================================================

class TaskResult:
    """Wrapper for task results with metadata."""

    def __init__(self, success: bool, data=None, error: str = None):
        self.success = success
        self.data = data
        self.error = error
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'timestamp': self.timestamp.isoformat(),
        }


def get_task_eta(delay_seconds: int = 0, delay_minutes: int = 0,
                 delay_hours: int = 0) -> datetime:
    """
    Calculate ETA for delayed task execution.

    Usage:
        my_task.apply_async(eta=get_task_eta(delay_minutes=30))
    """
    total_seconds = delay_seconds + (delay_minutes * 60) + (delay_hours * 3600)
    return datetime.now() + timedelta(seconds=total_seconds)


def schedule_task(task, args=None, kwargs=None, countdown=None, eta=None,
                  queue=None, priority=None):
    """
    Schedule a task with specified parameters.

    Usage:
        schedule_task(
            send_email_task,
            args=[user_id],
            countdown=300,  # 5 minutes
            priority=TaskConfig.PRIORITY_HIGH
        )
    """
    options = {}
    if countdown:
        options['countdown'] = countdown
    if eta:
        options['eta'] = eta
    if queue:
        options['queue'] = queue
    if priority is not None:
        options['priority'] = priority

    return task.apply_async(args=args, kwargs=kwargs, **options)


# =============================================================================
# Common Task Patterns
# =============================================================================

class ChunkedTask(BaseTask):
    """
    Task that processes items in chunks.

    Usage:
        @shared_task(bind=True, base=ChunkedTask)
        def process_users(self, user_ids, chunk_size=100):
            return self.process_in_chunks(
                user_ids,
                chunk_size,
                process_single_user
            )
    """

    def process_in_chunks(self, items, chunk_size, processor):
        """Process items in chunks."""
        results = []
        total = len(items)

        for i in range(0, total, chunk_size):
            chunk = items[i:i + chunk_size]
            logger.info(f"Processing chunk {i // chunk_size + 1} of {(total + chunk_size - 1) // chunk_size}")

            for item in chunk:
                try:
                    result = processor(item)
                    results.append({'item': item, 'success': True, 'result': result})
                except Exception as e:
                    results.append({'item': item, 'success': False, 'error': str(e)})
                    logger.error(f"Failed to process item {item}: {e}")

        return {
            'total': total,
            'processed': len(results),
            'successful': sum(1 for r in results if r['success']),
            'failed': sum(1 for r in results if not r['success']),
            'results': results,
        }


# =============================================================================
# Task Registry
# =============================================================================

class TaskRegistry:
    """Registry to track and manage task configurations."""

    _tasks = {}

    @classmethod
    def register(cls, name, task_class, config=None):
        """Register a task with configuration."""
        cls._tasks[name] = {
            'task': task_class,
            'config': config or {},
        }

    @classmethod
    def get(cls, name):
        """Get registered task."""
        return cls._tasks.get(name)

    @classmethod
    def list_tasks(cls):
        """List all registered tasks."""
        return list(cls._tasks.keys())
