"""
Health Check Endpoints for MultinotesAI.

This module provides:
- Liveness and readiness probes
- Component health checks
- Dependency status monitoring
- Health aggregation

Usage in urls.py:
    from backend.health_checks import health_router
    urlpatterns += [path('health/', include(health_router.urls))]
"""

import time
import socket
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from django.conf import settings
from django.db import connection, connections
from django.core.cache import cache
from django.http import JsonResponse
from django.views import View
from django.urls import path

logger = logging.getLogger(__name__)


# =============================================================================
# Health Status Types
# =============================================================================

class HealthStatus(Enum):
    """Health check status values."""
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'
    UNKNOWN = 'unknown'


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: HealthStatus
    message: str = ''
    latency_ms: float = 0
    details: Dict = field(default_factory=dict)
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class OverallHealth:
    """Aggregated health status."""
    status: HealthStatus
    version: str
    uptime_seconds: float
    components: List[ComponentHealth] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# Health Checkers
# =============================================================================

class HealthChecker:
    """
    Individual health check implementations.

    Each check returns a ComponentHealth object.
    """

    @staticmethod
    def check_database() -> ComponentHealth:
        """Check database connectivity and response time."""
        start = time.time()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()

            latency = (time.time() - start) * 1000

            # Check if latency is acceptable
            if latency > 1000:  # > 1 second
                return ComponentHealth(
                    name='database',
                    status=HealthStatus.DEGRADED,
                    message='Database responding slowly',
                    latency_ms=round(latency, 2),
                    details={'warning': 'High latency detected'}
                )

            return ComponentHealth(
                name='database',
                status=HealthStatus.HEALTHY,
                message='Database connection OK',
                latency_ms=round(latency, 2)
            )

        except Exception as e:
            return ComponentHealth(
                name='database',
                status=HealthStatus.UNHEALTHY,
                message=f'Database connection failed: {str(e)}',
                latency_ms=(time.time() - start) * 1000
            )

    @staticmethod
    def check_cache() -> ComponentHealth:
        """Check cache (Redis) connectivity."""
        start = time.time()
        try:
            # Test read/write
            test_key = '__health_check_test__'
            test_value = str(time.time())

            cache.set(test_key, test_value, 10)
            retrieved = cache.get(test_key)
            cache.delete(test_key)

            latency = (time.time() - start) * 1000

            if retrieved != test_value:
                return ComponentHealth(
                    name='cache',
                    status=HealthStatus.DEGRADED,
                    message='Cache read/write inconsistency',
                    latency_ms=round(latency, 2)
                )

            return ComponentHealth(
                name='cache',
                status=HealthStatus.HEALTHY,
                message='Cache connection OK',
                latency_ms=round(latency, 2)
            )

        except Exception as e:
            return ComponentHealth(
                name='cache',
                status=HealthStatus.UNHEALTHY,
                message=f'Cache connection failed: {str(e)}',
                latency_ms=(time.time() - start) * 1000
            )

    @staticmethod
    def check_storage() -> ComponentHealth:
        """Check file storage accessibility."""
        start = time.time()
        try:
            import os
            from django.conf import settings

            media_root = getattr(settings, 'MEDIA_ROOT', '/tmp')

            # Check if directory exists and is writable
            if os.path.exists(media_root):
                test_file = os.path.join(media_root, '__health_check_test__')
                try:
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    writable = True
                except Exception:
                    writable = False
            else:
                writable = False

            latency = (time.time() - start) * 1000

            if not writable:
                return ComponentHealth(
                    name='storage',
                    status=HealthStatus.DEGRADED,
                    message='Storage not writable',
                    latency_ms=round(latency, 2)
                )

            return ComponentHealth(
                name='storage',
                status=HealthStatus.HEALTHY,
                message='Storage accessible',
                latency_ms=round(latency, 2)
            )

        except Exception as e:
            return ComponentHealth(
                name='storage',
                status=HealthStatus.UNHEALTHY,
                message=f'Storage check failed: {str(e)}',
                latency_ms=(time.time() - start) * 1000
            )

    @staticmethod
    def check_external_api(name: str, url: str, timeout: int = 5) -> ComponentHealth:
        """Check external API connectivity."""
        start = time.time()
        try:
            import requests

            response = requests.head(url, timeout=timeout)
            latency = (time.time() - start) * 1000

            if response.status_code < 400:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message=f'{name} reachable',
                    latency_ms=round(latency, 2),
                    details={'status_code': response.status_code}
                )
            else:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.DEGRADED,
                    message=f'{name} returned error status',
                    latency_ms=round(latency, 2),
                    details={'status_code': response.status_code}
                )

        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f'{name} unreachable: {str(e)}',
                latency_ms=(time.time() - start) * 1000
            )

    @staticmethod
    def check_celery() -> ComponentHealth:
        """Check Celery worker availability."""
        start = time.time()
        try:
            from celery import current_app

            # Get active workers
            inspect = current_app.control.inspect()
            active = inspect.active()

            latency = (time.time() - start) * 1000

            if active is None:
                return ComponentHealth(
                    name='celery',
                    status=HealthStatus.UNHEALTHY,
                    message='No Celery workers responding',
                    latency_ms=round(latency, 2)
                )

            worker_count = len(active)
            if worker_count == 0:
                return ComponentHealth(
                    name='celery',
                    status=HealthStatus.UNHEALTHY,
                    message='No active Celery workers',
                    latency_ms=round(latency, 2)
                )

            return ComponentHealth(
                name='celery',
                status=HealthStatus.HEALTHY,
                message=f'{worker_count} Celery worker(s) active',
                latency_ms=round(latency, 2),
                details={'workers': worker_count}
            )

        except Exception as e:
            return ComponentHealth(
                name='celery',
                status=HealthStatus.UNKNOWN,
                message=f'Celery check skipped: {str(e)}',
                latency_ms=(time.time() - start) * 1000
            )

    @staticmethod
    def check_memory() -> ComponentHealth:
        """Check system memory usage."""
        start = time.time()
        try:
            import psutil

            memory = psutil.virtual_memory()
            latency = (time.time() - start) * 1000

            usage_percent = memory.percent

            if usage_percent > 95:
                return ComponentHealth(
                    name='memory',
                    status=HealthStatus.UNHEALTHY,
                    message=f'Critical memory usage: {usage_percent}%',
                    latency_ms=round(latency, 2),
                    details={
                        'total_gb': round(memory.total / (1024**3), 2),
                        'available_gb': round(memory.available / (1024**3), 2),
                        'usage_percent': usage_percent
                    }
                )
            elif usage_percent > 85:
                return ComponentHealth(
                    name='memory',
                    status=HealthStatus.DEGRADED,
                    message=f'High memory usage: {usage_percent}%',
                    latency_ms=round(latency, 2),
                    details={'usage_percent': usage_percent}
                )

            return ComponentHealth(
                name='memory',
                status=HealthStatus.HEALTHY,
                message=f'Memory usage: {usage_percent}%',
                latency_ms=round(latency, 2),
                details={'usage_percent': usage_percent}
            )

        except ImportError:
            return ComponentHealth(
                name='memory',
                status=HealthStatus.UNKNOWN,
                message='psutil not available',
                latency_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ComponentHealth(
                name='memory',
                status=HealthStatus.UNKNOWN,
                message=f'Memory check failed: {str(e)}',
                latency_ms=(time.time() - start) * 1000
            )

    @staticmethod
    def check_disk() -> ComponentHealth:
        """Check disk space usage."""
        start = time.time()
        try:
            import psutil

            disk = psutil.disk_usage('/')
            latency = (time.time() - start) * 1000

            usage_percent = disk.percent

            if usage_percent > 95:
                return ComponentHealth(
                    name='disk',
                    status=HealthStatus.UNHEALTHY,
                    message=f'Critical disk usage: {usage_percent}%',
                    latency_ms=round(latency, 2),
                    details={
                        'total_gb': round(disk.total / (1024**3), 2),
                        'free_gb': round(disk.free / (1024**3), 2),
                        'usage_percent': usage_percent
                    }
                )
            elif usage_percent > 85:
                return ComponentHealth(
                    name='disk',
                    status=HealthStatus.DEGRADED,
                    message=f'High disk usage: {usage_percent}%',
                    latency_ms=round(latency, 2),
                    details={'usage_percent': usage_percent}
                )

            return ComponentHealth(
                name='disk',
                status=HealthStatus.HEALTHY,
                message=f'Disk usage: {usage_percent}%',
                latency_ms=round(latency, 2),
                details={'usage_percent': usage_percent}
            )

        except ImportError:
            return ComponentHealth(
                name='disk',
                status=HealthStatus.UNKNOWN,
                message='psutil not available',
                latency_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ComponentHealth(
                name='disk',
                status=HealthStatus.UNKNOWN,
                message=f'Disk check failed: {str(e)}',
                latency_ms=(time.time() - start) * 1000
            )


# =============================================================================
# Health Check Service
# =============================================================================

class HealthCheckService:
    """
    Service for managing and running health checks.

    Usage:
        service = HealthCheckService()
        health = service.check_all()
        liveness = service.check_liveness()
        readiness = service.check_readiness()
    """

    # Application start time for uptime calculation
    _start_time = datetime.now()

    def __init__(self):
        self.checker = HealthChecker()
        self.version = getattr(settings, 'APP_VERSION', '2.0.0')

    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds()

    def check_liveness(self) -> Dict:
        """
        Kubernetes liveness probe.

        Returns true if the application process is running.
        """
        return {
            'status': 'ok',
            'timestamp': datetime.now().isoformat()
        }

    def check_readiness(self) -> Dict:
        """
        Kubernetes readiness probe.

        Returns true if the application can serve traffic.
        """
        # Check critical dependencies
        db_health = self.checker.check_database()
        cache_health = self.checker.check_cache()

        # Ready if database is healthy
        is_ready = db_health.status == HealthStatus.HEALTHY

        return {
            'ready': is_ready,
            'status': 'ready' if is_ready else 'not_ready',
            'checks': {
                'database': db_health.status.value,
                'cache': cache_health.status.value,
            },
            'timestamp': datetime.now().isoformat()
        }

    def check_all(self, include_details: bool = True) -> OverallHealth:
        """
        Run all health checks and return aggregated status.

        Args:
            include_details: Include detailed component information

        Returns:
            OverallHealth with all check results
        """
        components = []

        # Core checks
        components.append(self.checker.check_database())
        components.append(self.checker.check_cache())
        components.append(self.checker.check_storage())

        # System checks
        components.append(self.checker.check_memory())
        components.append(self.checker.check_disk())

        # Optional checks
        try:
            components.append(self.checker.check_celery())
        except Exception:
            pass

        # Determine overall status
        statuses = [c.status for c in components]

        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return OverallHealth(
            status=overall_status,
            version=self.version,
            uptime_seconds=self.get_uptime(),
            components=components if include_details else [],
            timestamp=datetime.now().isoformat()
        )

    def check_specific(self, component_name: str) -> Optional[ComponentHealth]:
        """Check a specific component by name."""
        check_methods = {
            'database': self.checker.check_database,
            'cache': self.checker.check_cache,
            'storage': self.checker.check_storage,
            'celery': self.checker.check_celery,
            'memory': self.checker.check_memory,
            'disk': self.checker.check_disk,
        }

        if component_name in check_methods:
            return check_methods[component_name]()
        return None


# =============================================================================
# Health Check Views
# =============================================================================

health_service = HealthCheckService()


class LivenessView(View):
    """Kubernetes liveness probe endpoint."""

    def get(self, request):
        result = health_service.check_liveness()
        return JsonResponse(result, status=200)


class ReadinessView(View):
    """Kubernetes readiness probe endpoint."""

    def get(self, request):
        result = health_service.check_readiness()
        status_code = 200 if result.get('ready') else 503
        return JsonResponse(result, status=status_code)


class HealthView(View):
    """Comprehensive health check endpoint."""

    def get(self, request):
        include_details = request.GET.get('details', 'true').lower() == 'true'
        health = health_service.check_all(include_details=include_details)

        # Convert to dict
        result = {
            'status': health.status.value,
            'version': health.version,
            'uptime_seconds': round(health.uptime_seconds, 2),
            'timestamp': health.timestamp,
        }

        if include_details:
            result['components'] = [
                {
                    'name': c.name,
                    'status': c.status.value,
                    'message': c.message,
                    'latency_ms': c.latency_ms,
                    'details': c.details,
                    'checked_at': c.checked_at,
                }
                for c in health.components
            ]

        # Return appropriate status code
        if health.status == HealthStatus.UNHEALTHY:
            status_code = 503
        elif health.status == HealthStatus.DEGRADED:
            status_code = 200  # Still serving traffic
        else:
            status_code = 200

        return JsonResponse(result, status=status_code)


class ComponentHealthView(View):
    """Individual component health check endpoint."""

    def get(self, request, component):
        health = health_service.check_specific(component)

        if health is None:
            return JsonResponse(
                {'error': f'Unknown component: {component}'},
                status=404
            )

        result = {
            'name': health.name,
            'status': health.status.value,
            'message': health.message,
            'latency_ms': health.latency_ms,
            'details': health.details,
            'checked_at': health.checked_at,
        }

        status_code = 200 if health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED] else 503
        return JsonResponse(result, status=status_code)


# =============================================================================
# URL Configuration
# =============================================================================

# Use this in your urls.py:
# from backend.health_checks import health_urlpatterns
# urlpatterns += health_urlpatterns

health_urlpatterns = [
    path('live/', LivenessView.as_view(), name='health-live'),
    path('ready/', ReadinessView.as_view(), name='health-ready'),
    path('', HealthView.as_view(), name='health'),
    path('<str:component>/', ComponentHealthView.as_view(), name='health-component'),
]


# =============================================================================
# Health Check Middleware
# =============================================================================

class HealthCheckMiddleware:
    """
    Middleware to handle health check requests at specific paths.

    This allows health checks to bypass authentication and other middleware.
    """

    HEALTH_PATHS = {
        '/health/live/',
        '/health/ready/',
        '/health/',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Fast path for health checks
        if request.path in self.HEALTH_PATHS:
            if request.path == '/health/live/':
                return JsonResponse(health_service.check_liveness())
            elif request.path == '/health/ready/':
                result = health_service.check_readiness()
                status = 200 if result.get('ready') else 503
                return JsonResponse(result, status=status)
            elif request.path == '/health/':
                health = health_service.check_all(include_details=False)
                return JsonResponse({
                    'status': health.status.value,
                    'version': health.version,
                })

        return self.get_response(request)
