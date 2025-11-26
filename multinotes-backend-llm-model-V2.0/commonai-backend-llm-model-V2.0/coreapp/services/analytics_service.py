"""
Analytics Service for MultinotesAI.

This module provides:
- User activity tracking
- Usage analytics
- Business metrics
- Dashboard data aggregation
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict

from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDate, TruncHour, TruncMonth
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)
User = get_user_model()


# =============================================================================
# Analytics Service
# =============================================================================

class AnalyticsService:
    """
    Unified analytics service for tracking and reporting.

    Usage:
        service = AnalyticsService()
        stats = service.get_user_stats(user_id=123)
        dashboard = service.get_dashboard_metrics()
    """

    CACHE_PREFIX = 'analytics:'
    CACHE_TIMEOUT = 300  # 5 minutes

    def __init__(self):
        self.cache_enabled = getattr(settings, 'ANALYTICS_CACHE_ENABLED', True)

    # -------------------------------------------------------------------------
    # User Analytics
    # -------------------------------------------------------------------------

    def track_user_activity(
        self,
        user,
        activity_type: str,
        metadata: Dict = None
    ):
        """
        Track user activity.

        Args:
            user: User instance
            activity_type: Type of activity (login, note_created, etc.)
            metadata: Additional activity data
        """
        try:
            from coreapp.models_analytics import UserAnalytics

            today = timezone.now().date()

            analytics, created = UserAnalytics.objects.get_or_create(
                user=user,
                date=today,
                defaults={
                    'notes_created': 0,
                    'notes_edited': 0,
                    'ai_text_generations': 0,
                    'ai_image_generations': 0,
                    'ai_tokens_used': 0,
                    'files_uploaded': 0,
                    'storage_used_mb': 0,
                }
            )

            # Update based on activity type
            if activity_type == 'note_created':
                analytics.notes_created = F('notes_created') + 1
            elif activity_type == 'note_edited':
                analytics.notes_edited = F('notes_edited') + 1
            elif activity_type == 'ai_generation':
                analytics.ai_text_generations = F('ai_text_generations') + 1
                if metadata and 'tokens' in metadata:
                    analytics.ai_tokens_used = F('ai_tokens_used') + metadata['tokens']
            elif activity_type == 'file_upload':
                analytics.files_uploaded = F('files_uploaded') + 1

            analytics.save()

            # Invalidate cache
            self._invalidate_user_cache(user.id)

        except Exception as e:
            logger.error(f"Error tracking user activity: {e}")

    def get_user_stats(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict:
        """
        Get user statistics.

        Args:
            user_id: User ID
            days: Number of days to include

        Returns:
            User statistics dict
        """
        cache_key = f"{self.CACHE_PREFIX}user:{user_id}:stats:{days}"

        if self.cache_enabled:
            cached = cache.get(cache_key)
            if cached:
                return cached

        try:
            from coreapp.models_analytics import UserAnalytics
            from coreapp.models import ContentGen, Folder

            since = timezone.now().date() - timedelta(days=days)

            # Get analytics data
            analytics = UserAnalytics.objects.filter(
                user_id=user_id,
                date__gte=since
            ).aggregate(
                total_notes=Sum('notes_created'),
                total_edits=Sum('notes_edited'),
                total_ai_generations=Sum('ai_text_generations') + Sum('ai_image_generations'),
                total_tokens=Sum('ai_tokens_used'),
                total_files=Sum('files_uploaded'),
            )

            # Get content counts
            total_notes = ContentGen.objects.filter(
                user_id=user_id,
                is_delete=False
            ).count()

            total_folders = Folder.objects.filter(
                user_id=user_id,
                is_delete=False
            ).count()

            # Get daily breakdown
            daily_activity = list(UserAnalytics.objects.filter(
                user_id=user_id,
                date__gte=since
            ).values('date').annotate(
                notes=Sum('notes_created'),
                ai_uses=Sum('ai_text_generations') + Sum('ai_image_generations'),
            ).order_by('date'))

            stats = {
                'period_days': days,
                'totals': {
                    'notes_created': analytics['total_notes'] or 0,
                    'notes_edited': analytics['total_edits'] or 0,
                    'ai_generations': analytics['total_ai_generations'] or 0,
                    'tokens_used': analytics['total_tokens'] or 0,
                    'files_uploaded': analytics['total_files'] or 0,
                },
                'all_time': {
                    'total_notes': total_notes,
                    'total_folders': total_folders,
                },
                'daily': [
                    {
                        'date': d['date'].isoformat(),
                        'notes': d['notes'] or 0,
                        'ai_uses': d['ai_uses'] or 0,
                    }
                    for d in daily_activity
                ],
            }

            if self.cache_enabled:
                cache.set(cache_key, stats, self.CACHE_TIMEOUT)

            return stats

        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

    # -------------------------------------------------------------------------
    # Platform Analytics
    # -------------------------------------------------------------------------

    def get_dashboard_metrics(self) -> Dict:
        """
        Get admin dashboard metrics.

        Returns:
            Dashboard metrics dict
        """
        cache_key = f"{self.CACHE_PREFIX}dashboard:metrics"

        if self.cache_enabled:
            cached = cache.get(cache_key)
            if cached:
                return cached

        try:
            metrics = {
                'users': self._get_user_metrics(),
                'content': self._get_content_metrics(),
                'subscriptions': self._get_subscription_metrics(),
                'revenue': self._get_revenue_metrics(),
                'ai_usage': self._get_ai_usage_metrics(),
                'generated_at': timezone.now().isoformat(),
            }

            if self.cache_enabled:
                cache.set(cache_key, metrics, self.CACHE_TIMEOUT)

            return metrics

        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {e}")
            return {}

    def _get_user_metrics(self) -> Dict:
        """Get user-related metrics."""
        today = timezone.now().date()
        last_7_days = today - timedelta(days=7)
        last_30_days = today - timedelta(days=30)

        total_users = User.objects.filter(is_active=True).count()
        new_users_7d = User.objects.filter(date_joined__date__gte=last_7_days).count()
        new_users_30d = User.objects.filter(date_joined__date__gte=last_30_days).count()

        # User growth trend
        growth = list(User.objects.filter(
            date_joined__date__gte=last_30_days
        ).annotate(
            date=TruncDate('date_joined')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date'))

        return {
            'total': total_users,
            'new_7d': new_users_7d,
            'new_30d': new_users_30d,
            'growth_rate': round((new_users_7d / max(total_users - new_users_7d, 1)) * 100, 2),
            'daily_signups': [
                {'date': g['date'].isoformat(), 'count': g['count']}
                for g in growth
            ],
        }

    def _get_content_metrics(self) -> Dict:
        """Get content-related metrics."""
        from coreapp.models import ContentGen, Folder

        total_notes = ContentGen.objects.filter(is_delete=False).count()
        total_folders = Folder.objects.filter(is_delete=False).count()

        # Notes created in last 7 days
        last_7_days = timezone.now().date() - timedelta(days=7)
        new_notes_7d = ContentGen.objects.filter(
            created_at__date__gte=last_7_days,
            is_delete=False
        ).count()

        return {
            'total_notes': total_notes,
            'total_folders': total_folders,
            'new_notes_7d': new_notes_7d,
            'avg_notes_per_user': round(total_notes / max(User.objects.filter(is_active=True).count(), 1), 2),
        }

    def _get_subscription_metrics(self) -> Dict:
        """Get subscription-related metrics."""
        try:
            from planandsubscription.models import Subscription

            active_subs = Subscription.objects.filter(
                is_delete=False,
                status='active'
            ).count()

            total_subs = Subscription.objects.filter(is_delete=False).count()

            # By plan breakdown
            by_plan = list(Subscription.objects.filter(
                is_delete=False,
                status='active'
            ).values('plan__name').annotate(
                count=Count('id')
            ).order_by('-count'))

            return {
                'total': total_subs,
                'active': active_subs,
                'conversion_rate': round((active_subs / max(total_subs, 1)) * 100, 2),
                'by_plan': [
                    {'plan': p['plan__name'] or 'Unknown', 'count': p['count']}
                    for p in by_plan
                ],
            }
        except Exception:
            return {'total': 0, 'active': 0, 'by_plan': []}

    def _get_revenue_metrics(self) -> Dict:
        """Get revenue-related metrics."""
        try:
            from planandsubscription.models import Payment

            last_30_days = timezone.now().date() - timedelta(days=30)
            last_7_days = timezone.now().date() - timedelta(days=7)

            revenue_30d = Payment.objects.filter(
                created_at__date__gte=last_30_days,
                status='captured'
            ).aggregate(total=Sum('amount'))

            revenue_7d = Payment.objects.filter(
                created_at__date__gte=last_7_days,
                status='captured'
            ).aggregate(total=Sum('amount'))

            # Daily revenue trend
            daily_revenue = list(Payment.objects.filter(
                created_at__date__gte=last_30_days,
                status='captured'
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                amount=Sum('amount')
            ).order_by('date'))

            return {
                'total_30d': float(revenue_30d['total'] or 0) / 100,  # Convert from paisa
                'total_7d': float(revenue_7d['total'] or 0) / 100,
                'currency': 'INR',
                'daily_trend': [
                    {
                        'date': r['date'].isoformat(),
                        'amount': float(r['amount'] or 0) / 100
                    }
                    for r in daily_revenue
                ],
            }
        except Exception:
            return {'total_30d': 0, 'total_7d': 0, 'currency': 'INR', 'daily_trend': []}

    def _get_ai_usage_metrics(self) -> Dict:
        """Get AI usage metrics."""
        try:
            from coreapp.models_analytics import UserAnalytics

            last_30_days = timezone.now().date() - timedelta(days=30)

            stats = UserAnalytics.objects.filter(
                date__gte=last_30_days
            ).aggregate(
                total_text_gen=Sum('ai_text_generations'),
                total_image_gen=Sum('ai_image_generations'),
                total_tokens=Sum('ai_tokens_used'),
            )

            # Daily trend
            daily_usage = list(UserAnalytics.objects.filter(
                date__gte=last_30_days
            ).values('date').annotate(
                generations=Sum('ai_text_generations') + Sum('ai_image_generations'),
                tokens=Sum('ai_tokens_used')
            ).order_by('date'))

            return {
                'total_generations': (stats['total_text_gen'] or 0) + (stats['total_image_gen'] or 0),
                'text_generations': stats['total_text_gen'] or 0,
                'image_generations': stats['total_image_gen'] or 0,
                'total_tokens': stats['total_tokens'] or 0,
                'daily_trend': [
                    {
                        'date': u['date'].isoformat(),
                        'generations': u['generations'] or 0,
                        'tokens': u['tokens'] or 0
                    }
                    for u in daily_usage
                ],
            }
        except Exception:
            return {'total_generations': 0, 'total_tokens': 0, 'daily_trend': []}

    # -------------------------------------------------------------------------
    # Retention Analytics
    # -------------------------------------------------------------------------

    def get_retention_metrics(self, cohort_days: int = 30) -> Dict:
        """
        Calculate user retention metrics.

        Args:
            cohort_days: Days to include in cohort analysis

        Returns:
            Retention metrics dict
        """
        try:
            from coreapp.models_analytics import UserAnalytics

            cohorts = []
            today = timezone.now().date()

            # Analyze cohorts week by week
            for week in range(4):
                cohort_start = today - timedelta(days=(week + 1) * 7)
                cohort_end = today - timedelta(days=week * 7)

                # Users who signed up in this week
                cohort_users = set(User.objects.filter(
                    date_joined__date__gte=cohort_start,
                    date_joined__date__lt=cohort_end
                ).values_list('id', flat=True))

                if not cohort_users:
                    continue

                # Users active in subsequent weeks
                retention_data = {
                    'cohort_start': cohort_start.isoformat(),
                    'cohort_size': len(cohort_users),
                    'retention': []
                }

                for ret_week in range(4 - week):
                    ret_start = cohort_end + timedelta(days=ret_week * 7)
                    ret_end = ret_start + timedelta(days=7)

                    active_users = UserAnalytics.objects.filter(
                        user_id__in=cohort_users,
                        date__gte=ret_start,
                        date__lt=ret_end
                    ).values('user_id').distinct().count()

                    retention_rate = round((active_users / len(cohort_users)) * 100, 1)
                    retention_data['retention'].append({
                        'week': ret_week + 1,
                        'active': active_users,
                        'rate': retention_rate
                    })

                cohorts.append(retention_data)

            return {'cohorts': cohorts}

        except Exception as e:
            logger.error(f"Error calculating retention: {e}")
            return {'cohorts': []}

    # -------------------------------------------------------------------------
    # Export Analytics
    # -------------------------------------------------------------------------

    def export_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        metrics: List[str] = None
    ) -> List[Dict]:
        """
        Export analytics data for a date range.

        Args:
            start_date: Start of range
            end_date: End of range
            metrics: Specific metrics to include

        Returns:
            List of daily analytics records
        """
        try:
            from coreapp.models_analytics import UserAnalytics

            queryset = UserAnalytics.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).values('date').annotate(
                users=Count('user_id', distinct=True),
                notes_created=Sum('notes_created'),
                ai_generations=Sum('ai_text_generations') + Sum('ai_image_generations'),
                tokens_used=Sum('ai_tokens_used'),
            ).order_by('date')

            return list(queryset)

        except Exception as e:
            logger.error(f"Error exporting analytics: {e}")
            return []

    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------

    def _invalidate_user_cache(self, user_id: int):
        """Invalidate user-related cache entries."""
        patterns = [
            f"{self.CACHE_PREFIX}user:{user_id}:*",
        ]
        for pattern in patterns:
            try:
                cache.delete_pattern(pattern)
            except Exception:
                pass

    def clear_all_cache(self):
        """Clear all analytics cache."""
        try:
            cache.delete_pattern(f"{self.CACHE_PREFIX}*")
        except Exception:
            pass


# =============================================================================
# Singleton Instance
# =============================================================================

analytics_service = AnalyticsService()
