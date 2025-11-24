"""
Celery Beat schedule configuration for MultinotesAI.

This module defines periodic task schedules for:
- Daily analytics aggregation
- Token reset for subscriptions
- Cache cleanup
- Email notifications
- System maintenance tasks
"""

from celery.schedules import crontab
from datetime import timedelta


# =============================================================================
# Celery Beat Schedule
# =============================================================================

CELERY_BEAT_SCHEDULE = {
    # -------------------------------------------------------------------------
    # Analytics Tasks (Daily)
    # -------------------------------------------------------------------------
    'aggregate-daily-analytics': {
        'task': 'coreapp.tasks.aggregate_daily_analytics',
        'schedule': crontab(hour=1, minute=0),  # 1:00 AM daily
        'options': {'queue': 'analytics'},
    },

    'generate-usage-reports': {
        'task': 'coreapp.tasks.generate_usage_reports',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM daily
        'options': {'queue': 'analytics'},
    },

    'cleanup-old-analytics': {
        'task': 'coreapp.tasks.cleanup_old_analytics',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
        'options': {'queue': 'maintenance'},
    },

    # -------------------------------------------------------------------------
    # Subscription Tasks
    # -------------------------------------------------------------------------
    'reset-daily-tokens': {
        'task': 'planandsubscription.tasks.reset_daily_tokens',
        'schedule': crontab(hour=0, minute=5),  # 12:05 AM daily
        'options': {'queue': 'subscriptions'},
    },

    'check-subscription-expiry': {
        'task': 'planandsubscription.tasks.check_subscription_expiry',
        'schedule': crontab(hour=6, minute=0),  # 6:00 AM daily
        'options': {'queue': 'subscriptions'},
    },

    'process-recurring-payments': {
        'task': 'planandsubscription.tasks.process_recurring_payments',
        'schedule': crontab(hour=7, minute=0),  # 7:00 AM daily
        'options': {'queue': 'payments'},
    },

    'send-subscription-reminders': {
        'task': 'planandsubscription.tasks.send_subscription_reminders',
        'schedule': crontab(hour=10, minute=0),  # 10:00 AM daily
        'options': {'queue': 'notifications'},
    },

    # -------------------------------------------------------------------------
    # Cache Maintenance
    # -------------------------------------------------------------------------
    'cleanup-expired-cache': {
        'task': 'backend.tasks.cleanup_expired_cache',
        'schedule': timedelta(hours=6),  # Every 6 hours
        'options': {'queue': 'maintenance'},
    },

    'warm-cache': {
        'task': 'backend.tasks.warm_cache',
        'schedule': crontab(hour=5, minute=30),  # 5:30 AM daily
        'options': {'queue': 'maintenance'},
    },

    # -------------------------------------------------------------------------
    # Content Cleanup
    # -------------------------------------------------------------------------
    'cleanup-orphaned-files': {
        'task': 'coreapp.tasks.cleanup_orphaned_files',
        'schedule': crontab(hour=4, minute=0, day_of_week=6),  # Saturday 4 AM
        'options': {'queue': 'maintenance'},
    },

    'cleanup-expired-shares': {
        'task': 'coreapp.tasks.cleanup_expired_shares',
        'schedule': crontab(hour=3, minute=30),  # 3:30 AM daily
        'options': {'queue': 'maintenance'},
    },

    'recalculate-storage-usage': {
        'task': 'coreapp.tasks.recalculate_storage_usage',
        'schedule': crontab(hour=2, minute=30),  # 2:30 AM daily
        'options': {'queue': 'maintenance'},
    },

    # -------------------------------------------------------------------------
    # Email Tasks
    # -------------------------------------------------------------------------
    'send-daily-digest': {
        'task': 'notifications.tasks.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM daily
        'options': {'queue': 'notifications'},
    },

    'send-weekly-summary': {
        'task': 'notifications.tasks.send_weekly_summary',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Monday 9 AM
        'options': {'queue': 'notifications'},
    },

    'retry-failed-emails': {
        'task': 'notifications.tasks.retry_failed_emails',
        'schedule': timedelta(hours=1),  # Every hour
        'options': {'queue': 'notifications'},
    },

    # -------------------------------------------------------------------------
    # LLM Provider Tasks
    # -------------------------------------------------------------------------
    'check-llm-provider-status': {
        'task': 'coreapp.tasks.check_llm_provider_status',
        'schedule': timedelta(minutes=15),  # Every 15 minutes
        'options': {'queue': 'monitoring'},
    },

    'sync-llm-models': {
        'task': 'coreapp.tasks.sync_llm_models',
        'schedule': crontab(hour=4, minute=30),  # 4:30 AM daily
        'options': {'queue': 'default'},
    },

    # -------------------------------------------------------------------------
    # Database Maintenance
    # -------------------------------------------------------------------------
    'backup-database': {
        'task': 'backend.tasks.backup_database',
        'schedule': crontab(hour=1, minute=30),  # 1:30 AM daily
        'options': {'queue': 'maintenance'},
    },

    'vacuum-database': {
        'task': 'backend.tasks.vacuum_database',
        'schedule': crontab(hour=5, minute=0, day_of_week=0),  # Sunday 5 AM
        'options': {'queue': 'maintenance'},
    },

    # -------------------------------------------------------------------------
    # System Health
    # -------------------------------------------------------------------------
    'health-check': {
        'task': 'backend.tasks.system_health_check',
        'schedule': timedelta(minutes=5),  # Every 5 minutes
        'options': {'queue': 'monitoring', 'expires': 240},
    },

    'collect-metrics': {
        'task': 'backend.tasks.collect_system_metrics',
        'schedule': timedelta(minutes=1),  # Every minute
        'options': {'queue': 'monitoring', 'expires': 50},
    },

    # -------------------------------------------------------------------------
    # Security Tasks
    # -------------------------------------------------------------------------
    'cleanup-expired-sessions': {
        'task': 'backend.tasks.cleanup_expired_sessions',
        'schedule': crontab(hour=0, minute=30),  # 12:30 AM daily
        'options': {'queue': 'maintenance'},
    },

    'rotate-api-keys': {
        'task': 'backend.tasks.check_api_key_rotation',
        'schedule': crontab(hour=6, minute=30),  # 6:30 AM daily
        'options': {'queue': 'security'},
    },

    'audit-log-cleanup': {
        'task': 'backend.tasks.cleanup_audit_logs',
        'schedule': crontab(hour=4, minute=0, day_of_month=1),  # 1st of month 4 AM
        'options': {'queue': 'maintenance'},
    },

    # -------------------------------------------------------------------------
    # User Engagement
    # -------------------------------------------------------------------------
    'send-inactive-user-reminders': {
        'task': 'notifications.tasks.send_inactive_user_reminders',
        'schedule': crontab(hour=11, minute=0, day_of_week=3),  # Wednesday 11 AM
        'options': {'queue': 'notifications'},
    },

    'process-referral-rewards': {
        'task': 'planandsubscription.tasks.process_referral_rewards',
        'schedule': crontab(hour=12, minute=0),  # 12:00 PM daily
        'options': {'queue': 'subscriptions'},
    },
}


# =============================================================================
# Queue Configuration
# =============================================================================

CELERY_TASK_QUEUES = {
    'default': {
        'exchange': 'default',
        'exchange_type': 'direct',
        'routing_key': 'default',
    },
    'analytics': {
        'exchange': 'analytics',
        'exchange_type': 'direct',
        'routing_key': 'analytics',
    },
    'notifications': {
        'exchange': 'notifications',
        'exchange_type': 'direct',
        'routing_key': 'notifications',
    },
    'subscriptions': {
        'exchange': 'subscriptions',
        'exchange_type': 'direct',
        'routing_key': 'subscriptions',
    },
    'payments': {
        'exchange': 'payments',
        'exchange_type': 'direct',
        'routing_key': 'payments',
    },
    'maintenance': {
        'exchange': 'maintenance',
        'exchange_type': 'direct',
        'routing_key': 'maintenance',
    },
    'monitoring': {
        'exchange': 'monitoring',
        'exchange_type': 'direct',
        'routing_key': 'monitoring',
    },
    'security': {
        'exchange': 'security',
        'exchange_type': 'direct',
        'routing_key': 'security',
    },
}


# =============================================================================
# Task Routing
# =============================================================================

CELERY_TASK_ROUTES = {
    'coreapp.tasks.aggregate_*': {'queue': 'analytics'},
    'coreapp.tasks.generate_*': {'queue': 'analytics'},
    'planandsubscription.tasks.*': {'queue': 'subscriptions'},
    'notifications.tasks.send_*': {'queue': 'notifications'},
    'backend.tasks.backup_*': {'queue': 'maintenance'},
    'backend.tasks.cleanup_*': {'queue': 'maintenance'},
    'backend.tasks.*_health_*': {'queue': 'monitoring'},
    'backend.tasks.*_metrics': {'queue': 'monitoring'},
}
