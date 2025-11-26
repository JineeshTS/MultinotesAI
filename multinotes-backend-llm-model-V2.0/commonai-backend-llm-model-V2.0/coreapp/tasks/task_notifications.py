"""
Task Notification Service for MultinotesAI.

This module provides:
- WebSocket notifications for task progress
- Task success/failure notifications
- Real-time task status updates

WBS Items:
- 4.3.2: Add task success notifications via WebSocket
- 4.3.3: Add task failure notifications
- 4.3.4: Implement task progress tracking
"""

import json
import logging
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum

from django.conf import settings
from celery import current_task
from celery.signals import (
    task_prerun,
    task_postrun,
    task_failure,
    task_success,
    task_revoked,
    task_retry,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Task Status Enum
# =============================================================================

class TaskStatus(Enum):
    """Task execution status."""
    PENDING = 'pending'
    STARTED = 'started'
    PROGRESS = 'progress'
    SUCCESS = 'success'
    FAILURE = 'failure'
    RETRY = 'retry'
    REVOKED = 'revoked'


# =============================================================================
# Task Progress Tracker
# =============================================================================

class TaskProgressTracker:
    """
    Track and report task progress.

    Usage:
        @shared_task(bind=True)
        def long_running_task(self, items):
            tracker = TaskProgressTracker(self)
            tracker.start(total=len(items))

            for i, item in enumerate(items):
                process(item)
                tracker.update(current=i+1, message=f"Processing {item}")

            tracker.complete(result={'processed': len(items)})
    """

    def __init__(self, task_instance, user_id: Optional[int] = None):
        """
        Initialize tracker.

        Args:
            task_instance: The Celery task instance (self in bound task)
            user_id: Optional user ID for targeted notifications
        """
        self.task = task_instance
        self.user_id = user_id
        self.task_id = task_instance.request.id if task_instance.request else None
        self.task_name = task_instance.name
        self.total = 0
        self.current = 0
        self.started_at = None
        self.notifier = TaskNotificationService()

    def start(self, total: int = 100, message: str = 'Starting...'):
        """
        Mark task as started.

        Args:
            total: Total units of work
            message: Status message
        """
        self.total = total
        self.current = 0
        self.started_at = datetime.now()

        self._update_state(TaskStatus.STARTED, {
            'total': total,
            'current': 0,
            'percent': 0,
            'message': message,
            'started_at': self.started_at.isoformat(),
        })

    def update(
        self,
        current: Optional[int] = None,
        increment: int = 0,
        message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Update task progress.

        Args:
            current: Current progress (absolute)
            increment: Increment progress by this amount
            message: Status message
            metadata: Additional metadata
        """
        if current is not None:
            self.current = current
        else:
            self.current += increment

        percent = int((self.current / self.total) * 100) if self.total > 0 else 0

        state_data = {
            'total': self.total,
            'current': self.current,
            'percent': min(percent, 100),
            'message': message or f'Processing {self.current}/{self.total}',
        }

        if metadata:
            state_data['metadata'] = metadata

        # Add ETA calculation
        if self.started_at and self.current > 0:
            elapsed = (datetime.now() - self.started_at).total_seconds()
            rate = self.current / elapsed if elapsed > 0 else 0
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            state_data['eta_seconds'] = int(remaining)

        self._update_state(TaskStatus.PROGRESS, state_data)

    def complete(self, result: Any = None, message: str = 'Completed'):
        """
        Mark task as complete.

        Args:
            result: Task result
            message: Completion message
        """
        self.current = self.total

        elapsed = None
        if self.started_at:
            elapsed = (datetime.now() - self.started_at).total_seconds()

        self._update_state(TaskStatus.SUCCESS, {
            'total': self.total,
            'current': self.total,
            'percent': 100,
            'message': message,
            'result': result,
            'elapsed_seconds': elapsed,
        })

    def fail(self, error: str, exception: Optional[Exception] = None):
        """
        Mark task as failed.

        Args:
            error: Error message
            exception: Exception object
        """
        self._update_state(TaskStatus.FAILURE, {
            'total': self.total,
            'current': self.current,
            'percent': int((self.current / self.total) * 100) if self.total > 0 else 0,
            'error': error,
            'exception_type': type(exception).__name__ if exception else None,
        })

    def _update_state(self, status: TaskStatus, data: Dict):
        """Update task state and send notification."""
        # Update Celery task state
        if self.task and hasattr(self.task, 'update_state'):
            self.task.update_state(state=status.value.upper(), meta=data)

        # Send WebSocket notification
        self.notifier.notify_task_update(
            task_id=self.task_id,
            task_name=self.task_name,
            status=status,
            data=data,
            user_id=self.user_id
        )


# =============================================================================
# WebSocket Notification Service
# =============================================================================

class TaskNotificationService:
    """
    Send task notifications via WebSocket.

    Integrates with Django Channels for real-time updates.
    """

    def __init__(self):
        self.channel_layer = self._get_channel_layer()

    def _get_channel_layer(self):
        """Get Django Channels layer."""
        try:
            from channels.layers import get_channel_layer
            return get_channel_layer()
        except ImportError:
            logger.warning("Django Channels not installed. WebSocket notifications disabled.")
            return None

    async def _async_send(self, channel: str, message: Dict):
        """Send message to channel asynchronously."""
        if self.channel_layer:
            await self.channel_layer.group_send(channel, message)

    def _sync_send(self, channel: str, message: Dict):
        """Send message to channel synchronously."""
        if not self.channel_layer:
            return

        try:
            from asgiref.sync import async_to_sync
            async_to_sync(self.channel_layer.group_send)(channel, message)
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")

    def notify_task_update(
        self,
        task_id: str,
        task_name: str,
        status: TaskStatus,
        data: Dict,
        user_id: Optional[int] = None
    ):
        """
        Send task update notification.

        Args:
            task_id: Celery task ID
            task_name: Task name
            status: Task status
            data: Task data/metadata
            user_id: Target user (for user-specific notifications)
        """
        message = {
            'type': 'task.update',
            'task_id': task_id,
            'task_name': task_name,
            'status': status.value,
            'data': data,
            'timestamp': datetime.now().isoformat(),
        }

        # Send to user-specific channel if user_id provided
        if user_id:
            channel = f'user_{user_id}_tasks'
            self._sync_send(channel, message)

        # Also send to global task channel
        self._sync_send('tasks', message)

    def notify_task_success(
        self,
        task_id: str,
        task_name: str,
        result: Any,
        user_id: Optional[int] = None
    ):
        """Send task success notification."""
        self.notify_task_update(
            task_id=task_id,
            task_name=task_name,
            status=TaskStatus.SUCCESS,
            data={'result': result},
            user_id=user_id
        )

    def notify_task_failure(
        self,
        task_id: str,
        task_name: str,
        error: str,
        user_id: Optional[int] = None
    ):
        """Send task failure notification."""
        self.notify_task_update(
            task_id=task_id,
            task_name=task_name,
            status=TaskStatus.FAILURE,
            data={'error': error},
            user_id=user_id
        )


# =============================================================================
# Celery Signal Handlers
# =============================================================================

notification_service = TaskNotificationService()


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None,
                        kwargs=None, **kw):
    """Handle task pre-run signal."""
    user_id = kwargs.get('user_id') if kwargs else None

    notification_service.notify_task_update(
        task_id=task_id,
        task_name=sender.name if sender else 'unknown',
        status=TaskStatus.STARTED,
        data={'args': str(args), 'kwargs': str(kwargs)},
        user_id=user_id
    )


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Handle task success signal."""
    task_id = sender.request.id if sender and sender.request else None

    # Try to get user_id from task kwargs
    user_id = None
    if sender and sender.request:
        task_kwargs = sender.request.kwargs or {}
        user_id = task_kwargs.get('user_id')

    notification_service.notify_task_success(
        task_id=task_id,
        task_name=sender.name if sender else 'unknown',
        result=result,
        user_id=user_id
    )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None,
                         traceback=None, **kwargs):
    """Handle task failure signal."""
    user_id = None
    if sender and sender.request:
        task_kwargs = sender.request.kwargs or {}
        user_id = task_kwargs.get('user_id')

    notification_service.notify_task_failure(
        task_id=task_id,
        task_name=sender.name if sender else 'unknown',
        error=str(exception),
        user_id=user_id
    )


@task_retry.connect
def task_retry_handler(sender=None, reason=None, request=None, **kwargs):
    """Handle task retry signal."""
    task_id = request.id if request else None
    user_id = None
    if request:
        task_kwargs = request.kwargs or {}
        user_id = task_kwargs.get('user_id')

    notification_service.notify_task_update(
        task_id=task_id,
        task_name=sender.name if sender else 'unknown',
        status=TaskStatus.RETRY,
        data={'reason': str(reason)},
        user_id=user_id
    )


@task_revoked.connect
def task_revoked_handler(sender=None, request=None, terminated=None,
                         signum=None, **kwargs):
    """Handle task revoked signal."""
    task_id = request.id if request else None
    user_id = None
    if request:
        task_kwargs = request.kwargs or {}
        user_id = task_kwargs.get('user_id')

    notification_service.notify_task_update(
        task_id=task_id,
        task_name=sender.name if sender else 'unknown',
        status=TaskStatus.REVOKED,
        data={'terminated': terminated, 'signal': signum},
        user_id=user_id
    )


# =============================================================================
# Task Status API
# =============================================================================

class TaskStatusService:
    """
    Service for querying task status.

    Usage:
        status_service = TaskStatusService()
        status = status_service.get_task_status(task_id)
    """

    def get_task_status(self, task_id: str) -> Dict:
        """
        Get current status of a task.

        Args:
            task_id: Celery task ID

        Returns:
            Task status dictionary
        """
        from celery.result import AsyncResult

        result = AsyncResult(task_id)

        status_data = {
            'task_id': task_id,
            'status': result.status,
            'ready': result.ready(),
            'successful': result.successful() if result.ready() else None,
            'failed': result.failed() if result.ready() else None,
        }

        # Add result or error
        if result.ready():
            if result.successful():
                status_data['result'] = result.result
            else:
                status_data['error'] = str(result.result)

        # Add progress info if available
        if result.status == 'PROGRESS' and result.info:
            status_data['progress'] = result.info

        return status_data

    def get_user_tasks(self, user_id: int, status: Optional[str] = None) -> list:
        """
        Get tasks for a specific user.

        Note: This requires task results to be stored with user_id metadata.
        """
        # This would typically query a database or Redis for user-specific tasks
        # Implementation depends on your task result storage strategy
        return []

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancellation was sent
        """
        from celery.result import AsyncResult

        result = AsyncResult(task_id)
        result.revoke(terminate=True)
        return True


# =============================================================================
# Singleton Instances
# =============================================================================

task_status_service = TaskStatusService()
