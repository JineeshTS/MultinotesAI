"""
Analytics tracking service for MultinotesAI.

This module provides:
- Event tracking
- User behavior analytics
- Feature usage tracking
- Metrics collection
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

from django.db import transaction
from django.db.models import Sum, Count, Avg, F
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Event Types
# =============================================================================

class EventType:
    """Event type constants for tracking."""

    # Content events
    NOTE_CREATED = 'note_created'
    NOTE_EDITED = 'note_edited'
    NOTE_DELETED = 'note_deleted'
    NOTE_VIEWED = 'note_viewed'
    FOLDER_CREATED = 'folder_created'
    FOLDER_DELETED = 'folder_deleted'

    # AI events
    AI_TEXT_GENERATED = 'ai_text_generated'
    AI_IMAGE_GENERATED = 'ai_image_generated'
    AI_STREAM_STARTED = 'ai_stream_started'
    AI_STREAM_COMPLETED = 'ai_stream_completed'

    # User events
    USER_LOGIN = 'user_login'
    USER_LOGOUT = 'user_logout'
    USER_REGISTERED = 'user_registered'
    SESSION_STARTED = 'session_started'
    SESSION_ENDED = 'session_ended'

    # Sharing events
    CONTENT_SHARED = 'content_shared'
    SHARE_VIEWED = 'share_viewed'

    # Subscription events
    SUBSCRIPTION_CREATED = 'subscription_created'
    SUBSCRIPTION_RENEWED = 'subscription_renewed'
    SUBSCRIPTION_CANCELLED = 'subscription_cancelled'
    SUBSCRIPTION_UPGRADED = 'subscription_upgraded'

    # File events
    FILE_UPLOADED = 'file_uploaded'
    FILE_DOWNLOADED = 'file_downloaded'
    FILE_DELETED = 'file_deleted'

    # Feature events
    FEATURE_USED = 'feature_used'
    EXPORT_GENERATED = 'export_generated'


# =============================================================================
# Analytics Tracker
# =============================================================================

class AnalyticsTracker:
    """
    Track user analytics and events.

    Usage:
        tracker = AnalyticsTracker()
        tracker.track_event(user, EventType.NOTE_CREATED)
        tracker.track_ai_usage(user, tokens=500, model='gpt-4')
    """

    def __init__(self):
        self.enabled = getattr(settings, 'ANALYTICS_ENABLED', True)

    def track_event(
        self,
        user,
        event_type: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Track a user event.

        Args:
            user: User instance
            event_type: Type of event from EventType class
            metadata: Additional event metadata

        Returns:
            bool: Success status
        """
        if not self.enabled or not user or not user.is_authenticated:
            return False

        try:
            from .models_analytics import UserAnalytics

            analytics = UserAnalytics.get_or_create_today(user)

            # Update relevant counters based on event type
            event_handlers = {
                EventType.NOTE_CREATED: lambda: self._increment(analytics, 'notes_created'),
                EventType.NOTE_EDITED: lambda: self._increment(analytics, 'notes_edited'),
                EventType.NOTE_DELETED: lambda: self._increment(analytics, 'notes_deleted'),
                EventType.FOLDER_CREATED: lambda: self._increment(analytics, 'folders_created'),
                EventType.AI_TEXT_GENERATED: lambda: self._increment(analytics, 'ai_text_generations'),
                EventType.AI_IMAGE_GENERATED: lambda: self._increment(analytics, 'ai_image_generations'),
                EventType.CONTENT_SHARED: lambda: self._increment(analytics, 'content_shared'),
                EventType.SHARE_VIEWED: lambda: self._increment(analytics, 'shared_views_received'),
                EventType.FILE_UPLOADED: lambda: self._increment(analytics, 'files_uploaded'),
                EventType.SESSION_STARTED: lambda: self._increment(analytics, 'sessions_count'),
            }

            handler = event_handlers.get(event_type)
            if handler:
                handler()

            # Track feature usage
            if event_type == EventType.FEATURE_USED and metadata:
                feature_name = metadata.get('feature')
                if feature_name:
                    analytics.track_feature(feature_name)

            logger.debug(f"Tracked event {event_type} for user {user.id}")
            return True

        except Exception as e:
            logger.error(f"Error tracking event: {e}")
            return False

    def _increment(self, analytics, field: str, amount: int = 1):
        """Increment an analytics field."""
        current = getattr(analytics, field, 0) or 0
        setattr(analytics, field, current + amount)
        analytics.save(update_fields=[field, 'updated_at'])

    def track_ai_usage(
        self,
        user,
        tokens: int,
        model: str = '',
        is_streaming: bool = False
    ) -> bool:
        """
        Track AI token usage.

        Args:
            user: User instance
            tokens: Number of tokens used
            model: AI model name
            is_streaming: Whether this was a streaming request

        Returns:
            bool: Success status
        """
        if not self.enabled or not user or not user.is_authenticated:
            return False

        try:
            from .models_analytics import UserAnalytics

            analytics = UserAnalytics.get_or_create_today(user)

            analytics.ai_tokens_used = (analytics.ai_tokens_used or 0) + tokens
            if is_streaming:
                analytics.ai_requests_streamed = (analytics.ai_requests_streamed or 0) + 1

            analytics.save(update_fields=['ai_tokens_used', 'ai_requests_streamed', 'updated_at'])

            logger.debug(f"Tracked AI usage: {tokens} tokens for user {user.id}")
            return True

        except Exception as e:
            logger.error(f"Error tracking AI usage: {e}")
            return False

    def track_session(
        self,
        user,
        duration_seconds: int,
        pages_viewed: int = 0
    ) -> bool:
        """
        Track user session data.

        Args:
            user: User instance
            duration_seconds: Session duration in seconds
            pages_viewed: Number of pages viewed

        Returns:
            bool: Success status
        """
        if not self.enabled or not user or not user.is_authenticated:
            return False

        try:
            from .models_analytics import UserAnalytics

            analytics = UserAnalytics.get_or_create_today(user)

            analytics.total_session_duration = (analytics.total_session_duration or 0) + duration_seconds
            analytics.pages_viewed = (analytics.pages_viewed or 0) + pages_viewed

            analytics.save(update_fields=['total_session_duration', 'pages_viewed', 'updated_at'])

            return True

        except Exception as e:
            logger.error(f"Error tracking session: {e}")
            return False

    def track_api_call(
        self,
        user,
        endpoint: str,
        is_error: bool = False
    ) -> bool:
        """
        Track API call.

        Args:
            user: User instance
            endpoint: API endpoint called
            is_error: Whether the call resulted in an error

        Returns:
            bool: Success status
        """
        if not self.enabled or not user or not user.is_authenticated:
            return False

        try:
            from .models_analytics import UserAnalytics

            analytics = UserAnalytics.get_or_create_today(user)

            analytics.api_calls = (analytics.api_calls or 0) + 1
            if is_error:
                analytics.api_errors = (analytics.api_errors or 0) + 1

            analytics.save(update_fields=['api_calls', 'api_errors', 'updated_at'])

            return True

        except Exception as e:
            logger.error(f"Error tracking API call: {e}")
            return False

    def get_user_stats(self, user, days: int = 30) -> Dict[str, Any]:
        """
        Get aggregated stats for a user.

        Args:
            user: User instance
            days: Number of days to aggregate

        Returns:
            Dict with aggregated statistics
        """
        from .models_analytics import UserAnalytics

        start_date = timezone.now().date() - timedelta(days=days)

        stats = UserAnalytics.objects.filter(
            user=user,
            date__gte=start_date
        ).aggregate(
            total_notes_created=Sum('notes_created'),
            total_ai_generations=Sum('ai_text_generations') + Sum('ai_image_generations'),
            total_tokens_used=Sum('ai_tokens_used'),
            total_sessions=Sum('sessions_count'),
            total_session_time=Sum('total_session_duration'),
            total_api_calls=Sum('api_calls'),
            total_api_errors=Sum('api_errors'),
            avg_daily_notes=Avg('notes_created'),
        )

        return {
            'period_days': days,
            **{k: v or 0 for k, v in stats.items()}
        }


# =============================================================================
# Tracking Decorator
# =============================================================================

def track_event(event_type: str, metadata_func=None):
    """
    Decorator to track events on function calls.

    Usage:
        @track_event(EventType.NOTE_CREATED)
        def create_note(request, ...):
            ...

        @track_event(EventType.FEATURE_USED, lambda r, *a, **kw: {'feature': 'export'})
        def export_notes(request, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            result = func(request, *args, **kwargs)

            # Track event after successful execution
            try:
                user = getattr(request, 'user', None)
                if user and user.is_authenticated:
                    metadata = None
                    if metadata_func:
                        metadata = metadata_func(request, *args, **kwargs)

                    tracker = AnalyticsTracker()
                    tracker.track_event(user, event_type, metadata)
            except Exception as e:
                logger.error(f"Error in tracking decorator: {e}")

            return result
        return wrapper
    return decorator


# =============================================================================
# Metrics Aggregator
# =============================================================================

class MetricsAggregator:
    """
    Aggregate and compute metrics from analytics data.

    Usage:
        aggregator = MetricsAggregator()
        daily_stats = aggregator.get_daily_platform_stats()
    """

    def aggregate_daily_stats(self, date=None) -> Dict[str, Any]:
        """
        Aggregate platform-wide stats for a day.

        Args:
            date: Date to aggregate (default: today)

        Returns:
            Dict with aggregated statistics
        """
        from .models_analytics import UserAnalytics, DailyAggregation
        from django.contrib.auth import get_user_model

        User = get_user_model()
        target_date = date or timezone.now().date()

        # Get or create daily aggregation
        aggregation, created = DailyAggregation.objects.get_or_create(
            date=target_date
        )

        # Calculate metrics
        day_analytics = UserAnalytics.objects.filter(date=target_date)

        stats = day_analytics.aggregate(
            notes_created=Sum('notes_created'),
            ai_generations=Sum('ai_text_generations') + Sum('ai_image_generations'),
            total_tokens=Sum('ai_tokens_used'),
            total_sessions=Sum('sessions_count'),
            total_api_calls=Sum('api_calls'),
            total_api_errors=Sum('api_errors'),
        )

        # Active users (users with any activity)
        active_users = day_analytics.values('user').distinct().count()

        # New users
        new_users = User.objects.filter(
            date_joined__date=target_date
        ).count()

        # Total users
        total_users = User.objects.filter(is_active=True).count()

        # Update aggregation
        aggregation.total_users = total_users
        aggregation.new_users = new_users
        aggregation.active_users = active_users
        aggregation.notes_created = stats.get('notes_created') or 0
        aggregation.ai_generations = stats.get('ai_generations') or 0
        aggregation.total_tokens = stats.get('total_tokens') or 0

        # Calculate error rate
        total_calls = stats.get('total_api_calls') or 0
        total_errors = stats.get('total_api_errors') or 0
        aggregation.error_rate = (total_errors / total_calls * 100) if total_calls > 0 else 0

        aggregation.save()

        logger.info(f"Aggregated daily stats for {target_date}")

        return aggregation.__dict__

    def get_trend_data(self, days: int = 30) -> list:
        """
        Get trend data for the specified number of days.

        Args:
            days: Number of days to get trends for

        Returns:
            List of daily stats dicts
        """
        from .models_analytics import DailyAggregation

        start_date = timezone.now().date() - timedelta(days=days)

        return list(DailyAggregation.objects.filter(
            date__gte=start_date
        ).order_by('date').values(
            'date', 'total_users', 'new_users', 'active_users',
            'notes_created', 'ai_generations', 'total_tokens',
            'error_rate', 'avg_response_time_ms'
        ))


# =============================================================================
# Celery Tasks
# =============================================================================

def aggregate_daily_analytics_task():
    """
    Celery task to aggregate daily analytics.

    Should be scheduled to run at end of each day.
    """
    aggregator = MetricsAggregator()

    # Aggregate for yesterday (completed day)
    yesterday = timezone.now().date() - timedelta(days=1)
    aggregator.aggregate_daily_stats(yesterday)

    logger.info(f"Daily analytics aggregation completed for {yesterday}")


def cleanup_old_analytics_task(retention_days: int = 90):
    """
    Celery task to clean up old analytics data.

    Args:
        retention_days: Number of days to retain data
    """
    from .models_analytics import UserAnalytics, APIUsageLog

    cutoff_date = timezone.now().date() - timedelta(days=retention_days)

    # Delete old user analytics
    deleted_analytics = UserAnalytics.objects.filter(
        date__lt=cutoff_date
    ).delete()

    # Delete old API usage logs
    deleted_logs = APIUsageLog.objects.filter(
        created_at__date__lt=cutoff_date
    ).delete()

    logger.info(
        f"Analytics cleanup: deleted {deleted_analytics[0]} analytics records, "
        f"{deleted_logs[0]} API logs older than {cutoff_date}"
    )


# =============================================================================
# Singleton Instance
# =============================================================================

analytics_tracker = AnalyticsTracker()
metrics_aggregator = MetricsAggregator()
