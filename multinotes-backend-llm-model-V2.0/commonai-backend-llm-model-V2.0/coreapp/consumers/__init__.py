"""
WebSocket Consumers for MultinotesAI.

This package contains WebSocket consumers for:
- Task notifications and progress tracking
- Real-time updates
"""

from .task_consumer import TaskNotificationConsumer, TaskAdminConsumer

__all__ = [
    'TaskNotificationConsumer',
    'TaskAdminConsumer',
]
