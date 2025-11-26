"""
Celery Tasks for MultinotesAI.

This package contains all background tasks including:
- Analytics collection and processing
- Email notifications
- Scheduled maintenance
"""

from .analytics_tasks import (
    collect_daily_metrics,
    calculate_user_engagement_scores,
    calculate_revenue_analytics,
    track_conversion_funnels,
    run_daily_analytics,
    cleanup_old_analytics,
)

__all__ = [
    'collect_daily_metrics',
    'calculate_user_engagement_scores',
    'calculate_revenue_analytics',
    'track_conversion_funnels',
    'run_daily_analytics',
    'cleanup_old_analytics',
]
