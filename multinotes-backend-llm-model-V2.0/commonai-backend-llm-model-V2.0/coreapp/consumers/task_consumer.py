"""
WebSocket Consumer for Task Notifications.

This module provides real-time task status updates via WebSocket.

WBS Items:
- 4.3.2: Add task success notifications via WebSocket
- 4.3.3: Add task failure notifications
- 4.3.4: Implement task progress tracking
"""

import json
import logging
from typing import Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class TaskNotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time task notifications.

    Clients connect to receive updates about their background tasks.

    Usage (JavaScript):
        const ws = new WebSocket('ws://localhost:8000/ws/tasks/');

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Task update:', data);
        };
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Join user-specific task group
        self.user_group = f'user_{self.user.id}_tasks'
        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )

        # Also join global tasks group for admin users
        if self.user.is_staff:
            await self.channel_layer.group_add(
                'tasks',
                self.channel_name
            )

        await self.accept()

        # Send connection confirmation
        await self.send_json({
            'type': 'connection.established',
            'message': 'Connected to task notifications',
            'user_id': self.user.id,
        })

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave groups
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(
                self.user_group,
                self.channel_name
            )

        if hasattr(self, 'user') and self.user and self.user.is_staff:
            await self.channel_layer.group_discard(
                'tasks',
                self.channel_name
            )

    async def receive_json(self, content):
        """
        Handle incoming WebSocket messages.

        Supported commands:
        - subscribe: Subscribe to specific task updates
        - unsubscribe: Unsubscribe from task updates
        - get_status: Get current status of a task
        """
        command = content.get('command')

        if command == 'subscribe':
            task_id = content.get('task_id')
            if task_id:
                await self.channel_layer.group_add(
                    f'task_{task_id}',
                    self.channel_name
                )
                await self.send_json({
                    'type': 'subscription.confirmed',
                    'task_id': task_id,
                })

        elif command == 'unsubscribe':
            task_id = content.get('task_id')
            if task_id:
                await self.channel_layer.group_discard(
                    f'task_{task_id}',
                    self.channel_name
                )
                await self.send_json({
                    'type': 'subscription.removed',
                    'task_id': task_id,
                })

        elif command == 'get_status':
            task_id = content.get('task_id')
            if task_id:
                status = await self.get_task_status(task_id)
                await self.send_json({
                    'type': 'task.status',
                    'task_id': task_id,
                    'status': status,
                })

        elif command == 'ping':
            await self.send_json({
                'type': 'pong',
                'timestamp': content.get('timestamp'),
            })

    async def task_update(self, event):
        """
        Handle task update message from channel layer.

        Called when a task sends an update notification.
        """
        await self.send_json({
            'type': 'task.update',
            'task_id': event.get('task_id'),
            'task_name': event.get('task_name'),
            'status': event.get('status'),
            'data': event.get('data'),
            'timestamp': event.get('timestamp'),
        })

    @database_sync_to_async
    def get_task_status(self, task_id: str) -> dict:
        """Get task status from Celery."""
        from celery.result import AsyncResult

        result = AsyncResult(task_id)

        status_data = {
            'status': result.status,
            'ready': result.ready(),
        }

        if result.ready():
            if result.successful():
                status_data['result'] = result.result
            else:
                status_data['error'] = str(result.result)

        if result.status == 'PROGRESS' and result.info:
            status_data['progress'] = result.info

        return status_data


class TaskAdminConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for admin task monitoring.

    Provides admin users with a stream of all task updates.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope.get('user')

        # Only allow staff/admin users
        if not self.user or not self.user.is_authenticated or not self.user.is_staff:
            await self.close(code=4003)
            return

        # Join global tasks group
        await self.channel_layer.group_add(
            'tasks',
            self.channel_name
        )

        await self.accept()

        await self.send_json({
            'type': 'connection.established',
            'message': 'Connected to task admin monitor',
        })

    async def disconnect(self, close_code):
        """Handle disconnection."""
        await self.channel_layer.group_discard(
            'tasks',
            self.channel_name
        )

    async def receive_json(self, content):
        """Handle incoming messages."""
        command = content.get('command')

        if command == 'get_active_tasks':
            tasks = await self.get_active_tasks()
            await self.send_json({
                'type': 'active.tasks',
                'tasks': tasks,
            })

        elif command == 'cancel_task':
            task_id = content.get('task_id')
            if task_id:
                success = await self.cancel_task(task_id)
                await self.send_json({
                    'type': 'task.cancelled',
                    'task_id': task_id,
                    'success': success,
                })

    async def task_update(self, event):
        """Forward task updates to admin."""
        await self.send_json(event)

    @database_sync_to_async
    def get_active_tasks(self) -> list:
        """Get list of active Celery tasks."""
        from celery import current_app

        try:
            inspect = current_app.control.inspect()
            active = inspect.active() or {}

            tasks = []
            for worker, task_list in active.items():
                for task in task_list:
                    tasks.append({
                        'worker': worker,
                        'task_id': task.get('id'),
                        'name': task.get('name'),
                        'args': task.get('args'),
                        'time_start': task.get('time_start'),
                    })

            return tasks
        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
            return []

    @database_sync_to_async
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        from celery.result import AsyncResult

        try:
            result = AsyncResult(task_id)
            result.revoke(terminate=True)
            return True
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
