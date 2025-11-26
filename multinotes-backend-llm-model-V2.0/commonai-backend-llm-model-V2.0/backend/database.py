"""
Database configuration and connection pooling for MultinotesAI.

This module provides:
- Connection pooling configuration
- Database routers
- Query optimization helpers
- Database health monitoring
"""

import logging
from functools import wraps
from typing import Optional, List, Any
from contextlib import contextmanager

from django.db import connection, connections, transaction
from django.db.models import QuerySet
from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Connection Pooling Configuration
# =============================================================================

def get_database_config() -> dict:
    """
    Get database configuration with connection pooling settings.

    Add this to your Django settings.py DATABASES configuration.
    """
    return {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': settings.DB_NAME,
            'USER': settings.DB_USER,
            'PASSWORD': settings.DB_PASSWORD,
            'HOST': settings.DB_HOST,
            'PORT': settings.DB_PORT,
            'CONN_MAX_AGE': 600,  # Keep connections alive for 10 minutes
            'CONN_HEALTH_CHECKS': True,  # Django 4.1+
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'connect_timeout': 10,
                'read_timeout': 30,
                'write_timeout': 30,
            },
        }
    }


def get_pool_settings() -> dict:
    """
    Get connection pool settings for django-db-connection-pool (if used).

    Install: pip install django-db-connection-pool

    Example DATABASES config:
    DATABASES = {
        'default': {
            'ENGINE': 'dj_db_conn_pool.backends.mysql',
            'POOL_OPTIONS': get_pool_settings(),
            ...
        }
    }
    """
    return {
        'POOL_SIZE': getattr(settings, 'DB_POOL_SIZE', 10),
        'MAX_OVERFLOW': getattr(settings, 'DB_MAX_OVERFLOW', 10),
        'RECYCLE': getattr(settings, 'DB_POOL_RECYCLE', 3600),  # 1 hour
        'PRE_PING': True,  # Check connection before use
        'ECHO': getattr(settings, 'DEBUG', False),
    }


# =============================================================================
# Database Router
# =============================================================================

class DatabaseRouter:
    """
    Database router for read/write splitting and model-based routing.

    Add to settings.py:
    DATABASE_ROUTERS = ['backend.database.DatabaseRouter']
    """

    # Models that should use a specific database
    read_replica_apps = ['analytics', 'reports']
    write_only_apps = ['auth', 'sessions']

    def db_for_read(self, model, **hints) -> str:
        """Determine database for read operations."""
        app_label = model._meta.app_label

        # Use read replica for analytics if configured
        if app_label in self.read_replica_apps:
            if 'replica' in settings.DATABASES:
                return 'replica'

        return 'default'

    def db_for_write(self, model, **hints) -> str:
        """Determine database for write operations."""
        return 'default'

    def allow_relation(self, obj1, obj2, **hints) -> bool:
        """Allow relations between models in the same database."""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints) -> bool:
        """Allow migrations on default database."""
        return db == 'default'


# =============================================================================
# Query Optimization Helpers
# =============================================================================

class QueryOptimizer:
    """Helpers for optimizing database queries."""

    @staticmethod
    def bulk_create_chunked(
        model,
        objects: List,
        chunk_size: int = 1000,
        ignore_conflicts: bool = False
    ) -> List:
        """
        Create objects in batches to avoid memory issues.

        Args:
            model: Django model class
            objects: List of model instances
            chunk_size: Number of objects per batch
            ignore_conflicts: Whether to ignore duplicate key conflicts

        Returns:
            List of created objects
        """
        created = []
        for i in range(0, len(objects), chunk_size):
            chunk = objects[i:i + chunk_size]
            result = model.objects.bulk_create(
                chunk,
                ignore_conflicts=ignore_conflicts
            )
            created.extend(result)

        logger.debug(f"Bulk created {len(created)} {model.__name__} objects")
        return created

    @staticmethod
    def bulk_update_chunked(
        model,
        objects: List,
        fields: List[str],
        chunk_size: int = 1000
    ) -> int:
        """
        Update objects in batches.

        Args:
            model: Django model class
            objects: List of model instances
            fields: List of fields to update
            chunk_size: Number of objects per batch

        Returns:
            Total number of updated objects
        """
        updated = 0
        for i in range(0, len(objects), chunk_size):
            chunk = objects[i:i + chunk_size]
            model.objects.bulk_update(chunk, fields)
            updated += len(chunk)

        logger.debug(f"Bulk updated {updated} {model.__name__} objects")
        return updated

    @staticmethod
    def prefetch_all(queryset: QuerySet, *related) -> QuerySet:
        """
        Apply both select_related and prefetch_related optimally.

        Args:
            queryset: Base queryset
            *related: Related fields to prefetch

        Returns:
            Optimized queryset
        """
        for field in related:
            if '__' in field or hasattr(queryset.model, field):
                # Check if it's a ForeignKey or OneToOne (use select_related)
                try:
                    field_obj = queryset.model._meta.get_field(field.split('__')[0])
                    if field_obj.many_to_one or field_obj.one_to_one:
                        queryset = queryset.select_related(field)
                    else:
                        queryset = queryset.prefetch_related(field)
                except Exception:
                    queryset = queryset.prefetch_related(field)

        return queryset

    @staticmethod
    def exists_subquery(queryset: QuerySet) -> bool:
        """
        Check if queryset has results efficiently.

        More efficient than .count() > 0 or bool(queryset).
        """
        return queryset.exists()

    @staticmethod
    def iterator_chunk(queryset: QuerySet, chunk_size: int = 2000):
        """
        Iterate over large querysets efficiently.

        Args:
            queryset: QuerySet to iterate
            chunk_size: Number of rows per chunk

        Yields:
            Model instances
        """
        return queryset.iterator(chunk_size=chunk_size)


# =============================================================================
# Transaction Helpers
# =============================================================================

def atomic_with_retry(max_retries: int = 3, delay: float = 0.1):
    """
    Decorator for atomic transactions with retry on deadlock.

    Args:
        max_retries: Maximum retry attempts
        delay: Initial delay between retries (exponential backoff)

    Usage:
        @atomic_with_retry(max_retries=3)
        def update_tokens(user_id, amount):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            from django.db import OperationalError

            last_error = None
            for attempt in range(max_retries):
                try:
                    with transaction.atomic():
                        return func(*args, **kwargs)
                except OperationalError as e:
                    last_error = e
                    error_msg = str(e).lower()
                    if 'deadlock' in error_msg or 'lock wait timeout' in error_msg:
                        sleep_time = delay * (2 ** attempt)
                        logger.warning(
                            f"Database deadlock, retrying in {sleep_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(sleep_time)
                    else:
                        raise

            logger.error(f"Max retries exceeded for {func.__name__}")
            raise last_error

        return wrapper
    return decorator


@contextmanager
def disable_foreign_key_checks():
    """
    Temporarily disable foreign key checks for bulk operations.

    WARNING: Use with caution, only for controlled bulk imports.

    Usage:
        with disable_foreign_key_checks():
            Model.objects.bulk_create(objects)
    """
    cursor = connection.cursor()
    try:
        cursor.execute('SET FOREIGN_KEY_CHECKS=0')
        yield
    finally:
        cursor.execute('SET FOREIGN_KEY_CHECKS=1')
        cursor.close()


# =============================================================================
# Database Health Monitoring
# =============================================================================

class DatabaseHealthMonitor:
    """Monitor database health and performance."""

    @staticmethod
    def check_connection() -> dict:
        """Check database connection health."""
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()

            return {
                'status': 'healthy',
                'message': 'Database connection successful'
            }
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': str(e)
            }

    @staticmethod
    def get_connection_info() -> dict:
        """Get database connection information."""
        try:
            with connection.cursor() as cursor:
                # Get connection count (MySQL)
                cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                threads = cursor.fetchone()

                cursor.execute("SHOW STATUS LIKE 'Max_used_connections'")
                max_used = cursor.fetchone()

                cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
                max_connections = cursor.fetchone()

                return {
                    'active_connections': int(threads[1]) if threads else 0,
                    'max_used_connections': int(max_used[1]) if max_used else 0,
                    'max_connections': int(max_connections[1]) if max_connections else 0,
                }
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            return {}

    @staticmethod
    def get_slow_queries(threshold_seconds: float = 1.0) -> List[dict]:
        """Get recent slow queries (requires slow query log enabled)."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT query_time, lock_time, rows_examined, sql_text
                    FROM mysql.slow_log
                    WHERE start_time > NOW() - INTERVAL 1 HOUR
                    ORDER BY query_time DESC
                    LIMIT 10
                """)
                rows = cursor.fetchall()

                return [
                    {
                        'query_time': str(row[0]),
                        'lock_time': str(row[1]),
                        'rows_examined': row[2],
                        'sql': row[3][:500] if row[3] else ''
                    }
                    for row in rows
                ]
        except Exception:
            # Slow query log might not be enabled
            return []

    @staticmethod
    def get_table_sizes() -> List[dict]:
        """Get database table sizes."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        table_name,
                        ROUND((data_length + index_length) / 1024 / 1024, 2) AS size_mb,
                        table_rows
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                    ORDER BY (data_length + index_length) DESC
                    LIMIT 20
                """)
                rows = cursor.fetchall()

                return [
                    {
                        'table': row[0],
                        'size_mb': float(row[1]) if row[1] else 0,
                        'rows': row[2] or 0
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get table sizes: {e}")
            return []


# =============================================================================
# Query Logging
# =============================================================================

class QueryLogger:
    """Log and analyze database queries."""

    def __init__(self):
        self.queries = []
        self.enabled = False

    def enable(self):
        """Enable query logging."""
        self.enabled = True
        self.queries = []
        settings.DEBUG = True  # Required for query logging

    def disable(self):
        """Disable query logging and return collected queries."""
        self.enabled = False
        return self.get_queries()

    def get_queries(self) -> List[dict]:
        """Get logged queries."""
        return [
            {
                'sql': q['sql'],
                'time': q['time'],
            }
            for q in connection.queries
        ]

    def get_summary(self) -> dict:
        """Get query summary."""
        queries = self.get_queries()
        total_time = sum(float(q['time']) for q in queries)

        return {
            'total_queries': len(queries),
            'total_time_seconds': round(total_time, 4),
            'avg_time_seconds': round(total_time / len(queries), 4) if queries else 0,
            'queries': queries
        }

    @contextmanager
    def log_queries(self):
        """Context manager for query logging."""
        self.enable()
        try:
            yield self
        finally:
            self.disable()


# =============================================================================
# Utility Functions
# =============================================================================

def close_old_connections():
    """Close old database connections."""
    for conn in connections.all():
        conn.close_if_unusable_or_obsolete()


def reset_queries():
    """Reset the query log."""
    from django.db import reset_queries as django_reset_queries
    django_reset_queries()


def explain_query(queryset: QuerySet) -> str:
    """Get EXPLAIN output for a queryset."""
    sql, params = queryset.query.sql_with_params()
    with connection.cursor() as cursor:
        cursor.execute(f"EXPLAIN {sql}", params)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        result = []
        for row in rows:
            result.append(dict(zip(columns, row)))

        return result


# =============================================================================
# Singleton Instances
# =============================================================================

query_optimizer = QueryOptimizer()
db_health_monitor = DatabaseHealthMonitor()
query_logger = QueryLogger()
