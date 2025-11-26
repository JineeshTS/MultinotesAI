"""
Task Monitoring API Views for MultinotesAI.

This module provides REST API endpoints for:
- Task status queries
- Task management
- Task monitoring dashboard data

WBS Items:
- 4.3.6: Create task monitoring dashboard
- 4.3.8: Add task result storage
"""

import logging
from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from celery import current_app
from celery.result import AsyncResult

logger = logging.getLogger(__name__)


# =============================================================================
# Task Status View
# =============================================================================

class TaskStatusView(APIView):
    """
    Get status of a specific task.

    GET /api/tasks/<task_id>/status/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        """Get task status."""
        result = AsyncResult(task_id)

        response_data = {
            'task_id': task_id,
            'status': result.status,
            'ready': result.ready(),
        }

        if result.ready():
            if result.successful():
                response_data['successful'] = True
                response_data['result'] = result.result
            else:
                response_data['successful'] = False
                response_data['error'] = str(result.result)
        elif result.status == 'PROGRESS':
            response_data['progress'] = result.info

        return Response(response_data)


# =============================================================================
# Task Cancel View
# =============================================================================

class TaskCancelView(APIView):
    """
    Cancel a running task.

    POST /api/tasks/<task_id>/cancel/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        """Cancel a task."""
        try:
            result = AsyncResult(task_id)

            # Check if task is still pending/running
            if result.ready():
                return Response(
                    {'error': 'Task has already completed'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Revoke the task
            result.revoke(terminate=True)

            return Response({
                'task_id': task_id,
                'status': 'cancelled',
                'message': 'Task cancellation requested'
            })

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return Response(
                {'error': 'Failed to cancel task'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Task List View (Admin)
# =============================================================================

class ActiveTasksView(APIView):
    """
    Get list of active tasks across all workers.

    GET /api/admin/tasks/active/

    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get all active tasks."""
        try:
            inspect = current_app.control.inspect()

            # Get active tasks
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            scheduled = inspect.scheduled() or {}

            # Format active tasks
            active_tasks = []
            for worker, tasks in active.items():
                for task in tasks:
                    active_tasks.append({
                        'worker': worker,
                        'task_id': task.get('id'),
                        'name': task.get('name'),
                        'args': task.get('args'),
                        'kwargs': task.get('kwargs'),
                        'time_start': task.get('time_start'),
                        'status': 'active'
                    })

            # Format reserved (waiting) tasks
            reserved_tasks = []
            for worker, tasks in reserved.items():
                for task in tasks:
                    reserved_tasks.append({
                        'worker': worker,
                        'task_id': task.get('id'),
                        'name': task.get('name'),
                        'status': 'reserved'
                    })

            # Format scheduled tasks
            scheduled_tasks = []
            for worker, tasks in scheduled.items():
                for task in tasks:
                    scheduled_tasks.append({
                        'worker': worker,
                        'task_id': task.get('request', {}).get('id'),
                        'name': task.get('request', {}).get('name'),
                        'eta': task.get('eta'),
                        'status': 'scheduled'
                    })

            return Response({
                'active': active_tasks,
                'reserved': reserved_tasks,
                'scheduled': scheduled_tasks,
                'total_active': len(active_tasks),
                'total_reserved': len(reserved_tasks),
                'total_scheduled': len(scheduled_tasks),
            })

        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
            return Response(
                {'error': 'Failed to retrieve task information'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Worker Status View (Admin)
# =============================================================================

class WorkerStatusView(APIView):
    """
    Get status of Celery workers.

    GET /api/admin/tasks/workers/

    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get worker status."""
        try:
            inspect = current_app.control.inspect()

            # Get worker stats
            stats = inspect.stats() or {}
            ping = inspect.ping() or {}
            registered = inspect.registered() or {}

            workers = []
            for worker_name in stats.keys():
                worker_stats = stats.get(worker_name, {})
                worker_ping = ping.get(worker_name, {})
                worker_tasks = registered.get(worker_name, [])

                workers.append({
                    'name': worker_name,
                    'status': 'online' if worker_ping else 'offline',
                    'pool': worker_stats.get('pool', {}),
                    'broker': worker_stats.get('broker', {}),
                    'prefetch_count': worker_stats.get('prefetch_count'),
                    'concurrency': worker_stats.get('pool', {}).get('max-concurrency'),
                    'registered_tasks': len(worker_tasks),
                    'total_tasks': worker_stats.get('total', {}),
                })

            return Response({
                'workers': workers,
                'total_workers': len(workers),
                'online_workers': sum(1 for w in workers if w['status'] == 'online'),
            })

        except Exception as e:
            logger.error(f"Failed to get worker status: {e}")
            return Response(
                {'error': 'Failed to retrieve worker information'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Task Queue Stats View (Admin)
# =============================================================================

class QueueStatsView(APIView):
    """
    Get queue statistics.

    GET /api/admin/tasks/queues/

    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get queue statistics."""
        try:
            inspect = current_app.control.inspect()

            # Get queue information
            active_queues = inspect.active_queues() or {}

            queues = {}
            for worker, worker_queues in active_queues.items():
                for queue_info in worker_queues:
                    queue_name = queue_info.get('name')
                    if queue_name not in queues:
                        queues[queue_name] = {
                            'name': queue_name,
                            'workers': [],
                            'routing_key': queue_info.get('routing_key'),
                        }
                    queues[queue_name]['workers'].append(worker)

            return Response({
                'queues': list(queues.values()),
                'total_queues': len(queues),
            })

        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return Response(
                {'error': 'Failed to retrieve queue information'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Task Dashboard View (Admin)
# =============================================================================

class TaskDashboardView(APIView):
    """
    Get comprehensive task monitoring dashboard data.

    GET /api/admin/tasks/dashboard/

    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get dashboard data."""
        try:
            inspect = current_app.control.inspect()

            # Get all stats
            stats = inspect.stats() or {}
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            scheduled = inspect.scheduled() or {}

            # Calculate totals
            total_active = sum(len(tasks) for tasks in active.values())
            total_reserved = sum(len(tasks) for tasks in reserved.values())
            total_scheduled = sum(len(tasks) for tasks in scheduled.values())

            # Get worker info
            worker_count = len(stats)
            online_workers = len([w for w in inspect.ping() or {}])

            # Calculate task counts from stats
            total_processed = 0
            total_succeeded = 0
            total_failed = 0
            total_retried = 0

            for worker_name, worker_stats in stats.items():
                totals = worker_stats.get('total', {})
                for task_name, count in totals.items():
                    total_processed += count

            return Response({
                'summary': {
                    'workers': {
                        'total': worker_count,
                        'online': online_workers,
                        'offline': worker_count - online_workers,
                    },
                    'tasks': {
                        'active': total_active,
                        'reserved': total_reserved,
                        'scheduled': total_scheduled,
                        'total_in_queue': total_active + total_reserved + total_scheduled,
                    },
                    'processed': {
                        'total': total_processed,
                    },
                },
                'workers': [
                    {
                        'name': name,
                        'active_tasks': len(active.get(name, [])),
                        'reserved_tasks': len(reserved.get(name, [])),
                    }
                    for name in stats.keys()
                ],
                'recent_tasks': self._get_recent_active_tasks(active),
            })

        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return Response(
                {'error': 'Failed to retrieve dashboard information'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_recent_active_tasks(self, active, limit=10):
        """Get most recent active tasks."""
        tasks = []
        for worker, task_list in active.items():
            for task in task_list:
                tasks.append({
                    'worker': worker,
                    'task_id': task.get('id'),
                    'name': task.get('name'),
                    'time_start': task.get('time_start'),
                })

        # Sort by start time (most recent first)
        tasks.sort(key=lambda t: t.get('time_start', 0), reverse=True)
        return tasks[:limit]


# =============================================================================
# Registered Tasks View (Admin)
# =============================================================================

class RegisteredTasksView(APIView):
    """
    Get list of registered Celery tasks.

    GET /api/admin/tasks/registered/

    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get registered tasks."""
        try:
            inspect = current_app.control.inspect()
            registered = inspect.registered() or {}

            # Collect unique tasks
            all_tasks = set()
            for worker_tasks in registered.values():
                all_tasks.update(worker_tasks)

            return Response({
                'tasks': sorted(list(all_tasks)),
                'total': len(all_tasks),
            })

        except Exception as e:
            logger.error(f"Failed to get registered tasks: {e}")
            return Response(
                {'error': 'Failed to retrieve task list'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Purge Tasks View (Admin)
# =============================================================================

class PurgeTasksView(APIView):
    """
    Purge pending tasks from a queue.

    POST /api/admin/tasks/purge/
    {
        "queue": "celery"  # optional, defaults to all queues
    }

    Admin only. Use with caution!
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        """Purge tasks from queue."""
        queue_name = request.data.get('queue')

        try:
            if queue_name:
                # Purge specific queue
                count = current_app.control.purge(queue=queue_name)
            else:
                # Purge all queues
                count = current_app.control.purge()

            logger.warning(
                f"Admin {request.user.username} purged {count} tasks from queue {queue_name or 'all'}"
            )

            return Response({
                'purged': count,
                'queue': queue_name or 'all',
                'message': f'Purged {count} pending tasks'
            })

        except Exception as e:
            logger.error(f"Failed to purge tasks: {e}")
            return Response(
                {'error': 'Failed to purge tasks'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
