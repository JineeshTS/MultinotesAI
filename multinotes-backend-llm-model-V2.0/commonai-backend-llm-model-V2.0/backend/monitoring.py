"""
Monitoring and Metrics Configuration for MultinotesAI.

This module provides:
- Prometheus metrics configuration
- Application performance monitoring
- Custom metrics collection
- Health check endpoints
"""

import time
import logging
from functools import wraps
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import connection

logger = logging.getLogger(__name__)


# =============================================================================
# Metrics Registry
# =============================================================================

class MetricsRegistry:
    """
    Simple metrics registry for application monitoring.

    For production, integrate with Prometheus using django-prometheus
    or similar libraries.
    """

    def __init__(self):
        self._counters = {}
        self._gauges = {}
        self._histograms = {}
        self._prefix = 'multinotesai_'

    def counter(self, name: str, description: str = '', labels: Dict = None):
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        if key not in self._counters:
            self._counters[key] = {
                'value': 0,
                'description': description,
                'labels': labels or {}
            }
        self._counters[key]['value'] += 1
        self._counters[key]['last_updated'] = datetime.now().isoformat()

    def gauge(self, name: str, value: float, description: str = '', labels: Dict = None):
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        self._gauges[key] = {
            'value': value,
            'description': description,
            'labels': labels or {},
            'last_updated': datetime.now().isoformat()
        }

    def histogram(self, name: str, value: float, description: str = '', labels: Dict = None):
        """Record a histogram observation."""
        key = self._make_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = {
                'values': [],
                'description': description,
                'labels': labels or {},
                'count': 0,
                'sum': 0,
            }
        self._histograms[key]['values'].append(value)
        self._histograms[key]['count'] += 1
        self._histograms[key]['sum'] += value
        # Keep only last 1000 values to prevent memory issues
        if len(self._histograms[key]['values']) > 1000:
            self._histograms[key]['values'] = self._histograms[key]['values'][-1000:]

    def _make_key(self, name: str, labels: Dict = None) -> str:
        """Generate a unique key for a metric."""
        key = f"{self._prefix}{name}"
        if labels:
            label_str = ','.join(f'{k}={v}' for k, v in sorted(labels.items()))
            key = f"{key}{{{label_str}}}"
        return key

    def get_all_metrics(self) -> Dict:
        """Get all metrics for export."""
        return {
            'counters': self._counters,
            'gauges': self._gauges,
            'histograms': {
                k: {
                    **v,
                    'avg': v['sum'] / v['count'] if v['count'] > 0 else 0,
                    'min': min(v['values']) if v['values'] else 0,
                    'max': max(v['values']) if v['values'] else 0,
                }
                for k, v in self._histograms.items()
            }
        }


# Global metrics registry
metrics = MetricsRegistry()


# =============================================================================
# Prometheus Configuration
# =============================================================================

PROMETHEUS_METRICS_CONFIG = {
    # HTTP metrics
    'http_requests_total': {
        'type': 'counter',
        'description': 'Total HTTP requests',
        'labels': ['method', 'endpoint', 'status'],
    },
    'http_request_duration_seconds': {
        'type': 'histogram',
        'description': 'HTTP request duration in seconds',
        'labels': ['method', 'endpoint'],
        'buckets': [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    },

    # Database metrics
    'db_query_duration_seconds': {
        'type': 'histogram',
        'description': 'Database query duration in seconds',
        'labels': ['operation'],
        'buckets': [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    },
    'db_connections_active': {
        'type': 'gauge',
        'description': 'Number of active database connections',
    },

    # Cache metrics
    'cache_hits_total': {
        'type': 'counter',
        'description': 'Total cache hits',
        'labels': ['cache'],
    },
    'cache_misses_total': {
        'type': 'counter',
        'description': 'Total cache misses',
        'labels': ['cache'],
    },

    # AI metrics
    'ai_generation_requests_total': {
        'type': 'counter',
        'description': 'Total AI generation requests',
        'labels': ['model', 'status'],
    },
    'ai_generation_duration_seconds': {
        'type': 'histogram',
        'description': 'AI generation duration in seconds',
        'labels': ['model'],
        'buckets': [0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    },
    'ai_tokens_used_total': {
        'type': 'counter',
        'description': 'Total AI tokens used',
        'labels': ['model', 'type'],
    },

    # User metrics
    'active_users': {
        'type': 'gauge',
        'description': 'Number of active users',
    },
    'user_registrations_total': {
        'type': 'counter',
        'description': 'Total user registrations',
    },

    # Business metrics
    'subscriptions_active': {
        'type': 'gauge',
        'description': 'Number of active subscriptions',
        'labels': ['plan'],
    },
    'revenue_total': {
        'type': 'counter',
        'description': 'Total revenue in smallest currency unit',
        'labels': ['currency', 'plan'],
    },
}


# =============================================================================
# Monitoring Decorators
# =============================================================================

def track_time(metric_name: str, labels: Dict = None):
    """
    Decorator to track execution time of functions.

    Usage:
        @track_time('ai_generation_duration_seconds', {'model': 'gpt-4'})
        def generate_content():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metrics.histogram(metric_name, duration, labels=labels)
        return wrapper
    return decorator


def count_calls(metric_name: str, labels: Dict = None):
    """
    Decorator to count function calls.

    Usage:
        @count_calls('api_calls_total', {'endpoint': 'generate'})
        def generate_content():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            metrics.counter(metric_name, labels=labels)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# System Metrics Collector
# =============================================================================

class SystemMetricsCollector:
    """Collect system-level metrics."""

    @staticmethod
    def collect_all() -> Dict:
        """Collect all system metrics."""
        return {
            'database': SystemMetricsCollector.collect_database_metrics(),
            'cache': SystemMetricsCollector.collect_cache_metrics(),
            'application': SystemMetricsCollector.collect_application_metrics(),
        }

    @staticmethod
    def collect_database_metrics() -> Dict:
        """Collect database metrics."""
        try:
            with connection.cursor() as cursor:
                # Get connection count (MySQL)
                cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                threads = cursor.fetchone()

                cursor.execute("SHOW STATUS LIKE 'Questions'")
                questions = cursor.fetchone()

                cursor.execute("SHOW STATUS LIKE 'Slow_queries'")
                slow_queries = cursor.fetchone()

                return {
                    'connections': int(threads[1]) if threads else 0,
                    'total_queries': int(questions[1]) if questions else 0,
                    'slow_queries': int(slow_queries[1]) if slow_queries else 0,
                    'status': 'healthy',
                }
        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")
            return {'status': 'error', 'error': str(e)}

    @staticmethod
    def collect_cache_metrics() -> Dict:
        """Collect cache metrics."""
        try:
            # Test cache connectivity
            test_key = '_metrics_test'
            cache.set(test_key, True, 10)
            cache_working = cache.get(test_key) is True
            cache.delete(test_key)

            return {
                'status': 'healthy' if cache_working else 'degraded',
                'connected': cache_working,
            }
        except Exception as e:
            logger.error(f"Failed to collect cache metrics: {e}")
            return {'status': 'error', 'error': str(e)}

    @staticmethod
    def collect_application_metrics() -> Dict:
        """Collect application-level metrics."""
        try:
            from django.contrib.auth import get_user_model
            from coreapp.models import ContentGen

            User = get_user_model()

            today = datetime.now().date()
            last_24h = datetime.now() - timedelta(hours=24)

            return {
                'total_users': User.objects.filter(is_active=True).count(),
                'users_registered_24h': User.objects.filter(
                    date_joined__gte=last_24h
                ).count(),
                'total_content': ContentGen.objects.filter(is_delete=False).count(),
                'content_created_24h': ContentGen.objects.filter(
                    created_at__gte=last_24h,
                    is_delete=False
                ).count(),
            }
        except Exception as e:
            logger.error(f"Failed to collect application metrics: {e}")
            return {'status': 'error', 'error': str(e)}


# =============================================================================
# Alerting Configuration
# =============================================================================

class AlertConfig:
    """Alert configuration for monitoring."""

    # Alert thresholds
    THRESHOLDS = {
        'response_time_p99_seconds': 5.0,
        'error_rate_percent': 1.0,
        'database_connections_percent': 80,
        'memory_usage_percent': 85,
        'disk_usage_percent': 90,
        'ai_generation_error_rate_percent': 5.0,
    }

    # Alert channels
    CHANNELS = {
        'email': {
            'enabled': True,
            'recipients': ['alerts@multinotesai.com'],
        },
        'slack': {
            'enabled': False,
            'webhook_url': '',
        },
        'pagerduty': {
            'enabled': False,
            'service_key': '',
        },
    }


class AlertManager:
    """Manage and trigger alerts."""

    def __init__(self):
        self.config = AlertConfig

    def check_threshold(self, metric_name: str, value: float) -> bool:
        """Check if a metric exceeds its threshold."""
        threshold = self.config.THRESHOLDS.get(metric_name)
        if threshold is None:
            return False
        return value > threshold

    def trigger_alert(
        self,
        name: str,
        message: str,
        severity: str = 'warning',
        details: Dict = None
    ):
        """Trigger an alert."""
        alert = {
            'name': name,
            'message': message,
            'severity': severity,
            'details': details or {},
            'timestamp': datetime.now().isoformat(),
        }

        # Log alert
        log_level = logging.CRITICAL if severity == 'critical' else logging.WARNING
        logger.log(log_level, f"ALERT [{severity}]: {name} - {message}")

        # Send to configured channels
        if self.config.CHANNELS['email']['enabled']:
            self._send_email_alert(alert)

        if self.config.CHANNELS['slack']['enabled']:
            self._send_slack_alert(alert)

    def _send_email_alert(self, alert: Dict):
        """Send alert via email."""
        try:
            from django.core.mail import send_mail

            send_mail(
                subject=f"[{alert['severity'].upper()}] {alert['name']}",
                message=f"{alert['message']}\n\nDetails: {alert['details']}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=self.config.CHANNELS['email']['recipients'],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    def _send_slack_alert(self, alert: Dict):
        """Send alert via Slack webhook."""
        try:
            import requests

            webhook_url = self.config.CHANNELS['slack']['webhook_url']
            if not webhook_url:
                return

            color = '#ff0000' if alert['severity'] == 'critical' else '#ffcc00'

            payload = {
                'attachments': [{
                    'color': color,
                    'title': f"[{alert['severity'].upper()}] {alert['name']}",
                    'text': alert['message'],
                    'fields': [
                        {'title': k, 'value': str(v), 'short': True}
                        for k, v in (alert.get('details') or {}).items()
                    ],
                    'ts': datetime.now().timestamp(),
                }]
            }

            requests.post(webhook_url, json=payload, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")


# =============================================================================
# Dashboard Data Provider
# =============================================================================

class DashboardDataProvider:
    """Provide data for monitoring dashboards."""

    def __init__(self):
        self.metrics_collector = SystemMetricsCollector()
        self.cache_timeout = 60  # 1 minute

    def get_dashboard_data(self) -> Dict:
        """Get all dashboard data."""
        cache_key = 'monitoring:dashboard:data'
        cached = cache.get(cache_key)

        if cached:
            return cached

        data = {
            'system': self.metrics_collector.collect_all(),
            'custom_metrics': metrics.get_all_metrics(),
            'health': self._get_health_summary(),
            'generated_at': datetime.now().isoformat(),
        }

        cache.set(cache_key, data, self.cache_timeout)
        return data

    def _get_health_summary(self) -> Dict:
        """Get overall health summary."""
        system_metrics = self.metrics_collector.collect_all()

        # Determine overall status
        statuses = [
            system_metrics['database'].get('status', 'unknown'),
            system_metrics['cache'].get('status', 'unknown'),
        ]

        if 'error' in statuses:
            overall = 'unhealthy'
        elif 'degraded' in statuses:
            overall = 'degraded'
        else:
            overall = 'healthy'

        return {
            'overall': overall,
            'database': system_metrics['database'].get('status', 'unknown'),
            'cache': system_metrics['cache'].get('status', 'unknown'),
        }


# =============================================================================
# Grafana Dashboard Configuration
# =============================================================================

GRAFANA_DASHBOARD_CONFIG = {
    'title': 'MultinotesAI Monitoring',
    'panels': [
        {
            'title': 'Request Rate',
            'type': 'graph',
            'datasource': 'prometheus',
            'query': 'rate(multinotesai_http_requests_total[5m])',
        },
        {
            'title': 'Response Time (P99)',
            'type': 'graph',
            'datasource': 'prometheus',
            'query': 'histogram_quantile(0.99, rate(multinotesai_http_request_duration_seconds_bucket[5m]))',
        },
        {
            'title': 'Error Rate',
            'type': 'graph',
            'datasource': 'prometheus',
            'query': 'rate(multinotesai_http_requests_total{status=~"5.."}[5m]) / rate(multinotesai_http_requests_total[5m])',
        },
        {
            'title': 'AI Generation Rate',
            'type': 'graph',
            'datasource': 'prometheus',
            'query': 'rate(multinotesai_ai_generation_requests_total[5m])',
        },
        {
            'title': 'Database Connections',
            'type': 'gauge',
            'datasource': 'prometheus',
            'query': 'multinotesai_db_connections_active',
        },
        {
            'title': 'Active Users',
            'type': 'stat',
            'datasource': 'prometheus',
            'query': 'multinotesai_active_users',
        },
    ],
}


# =============================================================================
# Singleton Instances
# =============================================================================

alert_manager = AlertManager()
dashboard_provider = DashboardDataProvider()
