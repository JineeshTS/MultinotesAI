"""
Health check endpoints for MultinotesAI.

This module provides:
- Basic health check
- Detailed system status
- Dependency health checks
- Readiness and liveness probes
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any

from django.conf import settings
from django.db import connection
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


# =============================================================================
# Health Check Results
# =============================================================================

class HealthStatus:
    """Health status constants."""
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'


class HealthCheckResult:
    """Result of a health check."""

    def __init__(
        self,
        name: str,
        status: str,
        response_time_ms: float = 0,
        details: Dict = None,
        error: str = None
    ):
        self.name = name
        self.status = status
        self.response_time_ms = response_time_ms
        self.details = details or {}
        self.error = error

    def to_dict(self) -> Dict:
        result = {
            'name': self.name,
            'status': self.status,
            'response_time_ms': round(self.response_time_ms, 2),
        }
        if self.details:
            result['details'] = self.details
        if self.error:
            result['error'] = self.error
        return result


# =============================================================================
# Health Checks
# =============================================================================

def check_database() -> HealthCheckResult:
    """Check database connectivity."""
    start = time.time()
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()

        response_time = (time.time() - start) * 1000

        return HealthCheckResult(
            name='database',
            status=HealthStatus.HEALTHY,
            response_time_ms=response_time,
            details={'engine': connection.vendor}
        )
    except Exception as e:
        return HealthCheckResult(
            name='database',
            status=HealthStatus.UNHEALTHY,
            response_time_ms=(time.time() - start) * 1000,
            error=str(e)
        )


def check_cache() -> HealthCheckResult:
    """Check Redis/cache connectivity."""
    start = time.time()
    try:
        # Test set and get
        test_key = 'health_check_test'
        test_value = 'ok'

        cache.set(test_key, test_value, timeout=10)
        result = cache.get(test_key)
        cache.delete(test_key)

        response_time = (time.time() - start) * 1000

        if result == test_value:
            return HealthCheckResult(
                name='cache',
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
            )
        else:
            return HealthCheckResult(
                name='cache',
                status=HealthStatus.DEGRADED,
                response_time_ms=response_time,
                error='Cache read/write mismatch'
            )
    except Exception as e:
        return HealthCheckResult(
            name='cache',
            status=HealthStatus.UNHEALTHY,
            response_time_ms=(time.time() - start) * 1000,
            error=str(e)
        )


def check_celery() -> HealthCheckResult:
    """Check Celery worker connectivity."""
    start = time.time()
    try:
        from celery import current_app

        # Ping workers
        inspect = current_app.control.inspect()
        active_workers = inspect.active_queues()

        response_time = (time.time() - start) * 1000

        if active_workers:
            worker_count = len(active_workers)
            return HealthCheckResult(
                name='celery',
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={'workers': worker_count}
            )
        else:
            return HealthCheckResult(
                name='celery',
                status=HealthStatus.DEGRADED,
                response_time_ms=response_time,
                error='No active workers found'
            )
    except Exception as e:
        return HealthCheckResult(
            name='celery',
            status=HealthStatus.UNHEALTHY,
            response_time_ms=(time.time() - start) * 1000,
            error=str(e)
        )


def check_storage() -> HealthCheckResult:
    """Check file storage availability."""
    import os
    start = time.time()

    try:
        media_root = settings.MEDIA_ROOT
        static_root = settings.STATIC_ROOT

        # Check media directory
        media_writable = os.access(media_root, os.W_OK) if os.path.exists(media_root) else False

        response_time = (time.time() - start) * 1000

        if media_writable:
            return HealthCheckResult(
                name='storage',
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    'media_path': media_root,
                    'writable': media_writable,
                }
            )
        else:
            return HealthCheckResult(
                name='storage',
                status=HealthStatus.DEGRADED,
                response_time_ms=response_time,
                error='Media directory not writable'
            )
    except Exception as e:
        return HealthCheckResult(
            name='storage',
            status=HealthStatus.UNHEALTHY,
            response_time_ms=(time.time() - start) * 1000,
            error=str(e)
        )


def check_external_services() -> HealthCheckResult:
    """Check external service connectivity (AI providers, etc.)."""
    import requests
    start = time.time()

    try:
        # Check if we can reach OpenAI API (basic connectivity)
        response = requests.get(
            'https://api.openai.com/v1/models',
            timeout=5,
            headers={'Authorization': f"Bearer {getattr(settings, 'OPENAI_API_KEY', 'test')}"}
        )

        response_time = (time.time() - start) * 1000

        # Any response means the service is reachable
        return HealthCheckResult(
            name='external_services',
            status=HealthStatus.HEALTHY if response.status_code < 500 else HealthStatus.DEGRADED,
            response_time_ms=response_time,
            details={'openai_status': response.status_code}
        )
    except requests.Timeout:
        return HealthCheckResult(
            name='external_services',
            status=HealthStatus.DEGRADED,
            response_time_ms=(time.time() - start) * 1000,
            error='External service timeout'
        )
    except Exception as e:
        return HealthCheckResult(
            name='external_services',
            status=HealthStatus.DEGRADED,
            response_time_ms=(time.time() - start) * 1000,
            error=str(e)
        )


# =============================================================================
# Health Check API Views
# =============================================================================

class BasicHealthCheckView(APIView):
    """
    Basic health check endpoint.

    Returns 200 if the application is running.
    Used for load balancer health checks.

    GET /health/
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
        })


class LivenessProbeView(APIView):
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the application process is alive.

    GET /health/live/
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            'status': 'alive',
            'timestamp': datetime.now().isoformat(),
        })


class ReadinessProbeView(APIView):
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if the application is ready to receive traffic.
    Checks database and cache connectivity.

    GET /health/ready/
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        db_check = check_database()
        cache_check = check_cache()

        is_ready = (
            db_check.status == HealthStatus.HEALTHY and
            cache_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        )

        status_code = 200 if is_ready else 503

        return Response({
            'status': 'ready' if is_ready else 'not_ready',
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'database': db_check.status,
                'cache': cache_check.status,
            }
        }, status=status_code)


class DetailedHealthCheckView(APIView):
    """
    Detailed health check endpoint.

    Returns comprehensive system status.
    Should be protected in production.

    GET /health/detailed/
    """
    permission_classes = [AllowAny]  # Consider restricting in production

    def get(self, request):
        start_time = time.time()

        # Run all health checks
        checks = [
            check_database(),
            check_cache(),
            check_storage(),
        ]

        # Optionally include celery and external services
        include_all = request.query_params.get('full', 'false').lower() == 'true'
        if include_all:
            checks.append(check_celery())
            checks.append(check_external_services())

        # Determine overall status
        statuses = [c.status for c in checks]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        total_time = (time.time() - start_time) * 1000

        response_data = {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'total_check_time_ms': round(total_time, 2),
            'version': getattr(settings, 'APP_VERSION', 'unknown'),
            'environment': getattr(settings, 'ENVIRONMENT', 'development'),
            'checks': [c.to_dict() for c in checks],
        }

        status_code = 200 if overall_status == HealthStatus.HEALTHY else 503

        return Response(response_data, status=status_code)


class SystemInfoView(APIView):
    """
    System information endpoint.

    Returns system metrics and configuration.
    Should be protected in production.

    GET /health/info/
    """
    permission_classes = [AllowAny]  # Consider restricting in production

    def get(self, request):
        import platform
        import sys
        import os

        return Response({
            'timestamp': datetime.now().isoformat(),
            'application': {
                'name': 'MultinotesAI',
                'version': getattr(settings, 'APP_VERSION', 'unknown'),
                'environment': getattr(settings, 'ENVIRONMENT', 'development'),
                'debug': settings.DEBUG,
            },
            'python': {
                'version': sys.version,
                'platform': platform.python_implementation(),
            },
            'system': {
                'platform': platform.platform(),
                'processor': platform.processor(),
            },
            'django': {
                'version': __import__('django').VERSION,
            },
        })


# =============================================================================
# URL Configuration
# =============================================================================

"""
Add to your urls.py:

from backend.health import (
    BasicHealthCheckView,
    LivenessProbeView,
    ReadinessProbeView,
    DetailedHealthCheckView,
    SystemInfoView,
)

urlpatterns = [
    path('health/', BasicHealthCheckView.as_view(), name='health'),
    path('health/live/', LivenessProbeView.as_view(), name='health-live'),
    path('health/ready/', ReadinessProbeView.as_view(), name='health-ready'),
    path('health/detailed/', DetailedHealthCheckView.as_view(), name='health-detailed'),
    path('health/info/', SystemInfoView.as_view(), name='health-info'),
]
"""
