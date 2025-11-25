"""
Analytics API Views for MultinotesAI.

This module provides:
- User analytics endpoints
- Product metrics endpoints
- Dashboard data endpoints
- Admin analytics endpoints

All endpoints require authentication.
Admin endpoints require staff permissions.
"""

import logging
from datetime import datetime, timedelta

from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Sum, Avg

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

logger = logging.getLogger(__name__)


# =============================================================================
# User Analytics Views
# =============================================================================

class UserAnalyticsView(APIView):
    """
    User's own analytics data.

    GET /api/analytics/user/
    Returns user's usage statistics and analytics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get analytics for the authenticated user."""
        try:
            user = request.user
            days = int(request.query_params.get('days', 30))

            analytics = self._get_user_analytics(user, days)

            return Response({
                'success': True,
                'data': analytics,
            })

        except Exception as e:
            logger.error(f"Error fetching user analytics: {e}")
            return Response({
                'success': False,
                'error': {'message': 'Failed to fetch analytics'}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_user_analytics(self, user, days: int) -> dict:
        """Compile user analytics data."""
        from coreapp.models import ContentGen, Prompt, LLM_Tokens
        from coreapp.models_analytics import UserAnalytics

        since = timezone.now().date() - timedelta(days=days)

        # Usage statistics
        usage = UserAnalytics.objects.filter(
            user=user,
            date__gte=since
        ).aggregate(
            total_sessions=Sum('sessions'),
            total_generations=Sum('ai_text_generations'),
            total_tokens=Sum('ai_tokens_used'),
            avg_session_duration=Avg('avg_session_duration'),
        )

        # Content stats
        content_created = ContentGen.objects.filter(
            user=user,
            created_at__date__gte=since,
            is_delete=False
        ).count()

        prompts_sent = Prompt.objects.filter(
            user=user,
            created_at__date__gte=since,
            is_delete=False
        ).count()

        # Daily breakdown
        daily_usage = UserAnalytics.objects.filter(
            user=user,
            date__gte=since
        ).values('date').annotate(
            sessions=Sum('sessions'),
            tokens=Sum('ai_tokens_used'),
            generations=Sum('ai_text_generations'),
        ).order_by('date')

        # Token usage by model
        token_by_model = LLM_Tokens.objects.filter(
            user=user,
            created_at__date__gte=since,
            is_delete=False
        ).values('llm__name').annotate(
            total=Sum('token_used')
        )

        return {
            'period_days': days,
            'usage': {
                'total_sessions': usage['total_sessions'] or 0,
                'total_generations': usage['total_generations'] or 0,
                'total_tokens_used': usage['total_tokens'] or 0,
                'avg_session_minutes': round((usage['avg_session_duration'] or 0) / 60, 1),
            },
            'content': {
                'items_created': content_created,
                'prompts_sent': prompts_sent,
            },
            'daily_breakdown': [
                {
                    'date': d['date'].isoformat(),
                    'sessions': d['sessions'] or 0,
                    'tokens': d['tokens'] or 0,
                    'generations': d['generations'] or 0,
                }
                for d in daily_usage
            ],
            'token_by_model': {
                t['llm__name']: t['total'] or 0
                for t in token_by_model
            },
        }


class UserEngagementView(APIView):
    """
    User engagement score and details.

    GET /api/analytics/engagement/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get engagement score for authenticated user."""
        try:
            from coreapp.services.retention_service import retention_calculator

            user = request.user
            engagement = retention_calculator.calculate_engagement_score(user)

            return Response({
                'success': True,
                'data': {
                    'score': engagement.score,
                    'level': engagement.level,
                    'factors': engagement.factors,
                    'recommendations': self._get_recommendations(engagement),
                }
            })

        except Exception as e:
            logger.error(f"Error fetching engagement: {e}")
            return Response({
                'success': False,
                'error': {'message': 'Failed to fetch engagement data'}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_recommendations(self, engagement) -> list:
        """Get personalized recommendations based on engagement."""
        recommendations = []

        if engagement.factors.get('recency', 0) < 50:
            recommendations.append({
                'type': 'activity',
                'message': 'Try using the app more frequently to get the most value',
            })

        if engagement.factors.get('depth', 0) < 30:
            recommendations.append({
                'type': 'exploration',
                'message': 'Explore different AI models to find the best fit for your needs',
            })

        if engagement.factors.get('content', 0) < 30:
            recommendations.append({
                'type': 'content',
                'message': 'Save your best generations to build your content library',
            })

        return recommendations


# =============================================================================
# Dashboard Analytics Views (Admin)
# =============================================================================

class DashboardAnalyticsView(APIView):
    """
    Admin dashboard analytics.

    GET /api/analytics/dashboard/
    Returns comprehensive dashboard data for admins.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get dashboard analytics data."""
        try:
            days = int(request.query_params.get('days', 30))

            # Check cache first
            cache_key = f'dashboard_analytics_{days}'
            cached = cache.get(cache_key)
            if cached:
                return Response({'success': True, 'data': cached})

            data = {
                'overview': self._get_overview_metrics(days),
                'user_metrics': self._get_user_metrics(days),
                'revenue_metrics': self._get_revenue_metrics(days),
                'content_metrics': self._get_content_metrics(days),
                'generated_at': timezone.now().isoformat(),
            }

            cache.set(cache_key, data, 300)  # 5 minute cache

            return Response({'success': True, 'data': data})

        except Exception as e:
            logger.error(f"Error fetching dashboard analytics: {e}")
            return Response({
                'success': False,
                'error': {'message': 'Failed to fetch dashboard data'}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_overview_metrics(self, days: int) -> dict:
        """Get high-level overview metrics."""
        from django.contrib.auth import get_user_model
        from planandsubscription.models import Subscription, Payment

        User = get_user_model()
        since = timezone.now().date() - timedelta(days=days)

        # Users
        total_users = User.objects.filter(is_active=True).count()
        new_users = User.objects.filter(date_joined__date__gte=since).count()

        # Subscriptions
        active_subs = Subscription.objects.filter(status='active').count()

        # Revenue
        revenue = Payment.objects.filter(
            created_at__date__gte=since,
            status='captured'
        ).aggregate(total=Sum('amount'))['total'] or 0

        return {
            'total_users': total_users,
            'new_users': new_users,
            'active_subscriptions': active_subs,
            'revenue': float(revenue),
        }

    def _get_user_metrics(self, days: int) -> dict:
        """Get user-related metrics."""
        from coreapp.models_analytics import UserAnalytics

        since = timezone.now().date() - timedelta(days=days)

        # DAU trend
        dau_trend = UserAnalytics.objects.filter(
            date__gte=since
        ).values('date').annotate(
            count=Count('user', distinct=True)
        ).order_by('date')

        return {
            'dau_trend': [
                {'date': d['date'].isoformat(), 'users': d['count']}
                for d in dau_trend
            ],
        }

    def _get_revenue_metrics(self, days: int) -> dict:
        """Get revenue metrics."""
        from planandsubscription.models import Payment

        since = timezone.now().date() - timedelta(days=days)

        # Daily revenue
        daily_revenue = Payment.objects.filter(
            created_at__date__gte=since,
            status='captured'
        ).values('created_at__date').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('created_at__date')

        return {
            'daily_revenue': [
                {
                    'date': d['created_at__date'].isoformat(),
                    'amount': float(d['total'] or 0),
                    'transactions': d['count'],
                }
                for d in daily_revenue
            ],
        }

    def _get_content_metrics(self, days: int) -> dict:
        """Get content generation metrics."""
        from coreapp.models import Prompt, LLM_Tokens

        since = timezone.now().date() - timedelta(days=days)

        # Daily generations
        daily_prompts = Prompt.objects.filter(
            created_at__date__gte=since,
            is_delete=False
        ).values('created_at__date').annotate(
            count=Count('id')
        ).order_by('created_at__date')

        # Token usage by model
        token_by_model = LLM_Tokens.objects.filter(
            created_at__date__gte=since,
            is_delete=False
        ).values('llm__name').annotate(
            total=Sum('token_used')
        )

        return {
            'daily_generations': [
                {'date': d['created_at__date'].isoformat(), 'count': d['count']}
                for d in daily_prompts
            ],
            'token_by_model': {
                t['llm__name']: t['total'] or 0
                for t in token_by_model
            },
        }


class ProductMetricsView(APIView):
    """
    Product metrics API.

    GET /api/analytics/metrics/
    GET /api/analytics/metrics/?date=2024-01-01
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get product metrics."""
        try:
            from coreapp.models_analytics import ProductMetrics

            date_str = request.query_params.get('date')
            days = int(request.query_params.get('days', 30))

            if date_str:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                metrics = ProductMetrics.objects.filter(date=target_date).first()

                if metrics:
                    return Response({
                        'success': True,
                        'data': self._serialize_metrics(metrics)
                    })
                else:
                    return Response({
                        'success': False,
                        'error': {'message': 'No metrics for this date'}
                    }, status=status.HTTP_404_NOT_FOUND)

            # Get range of metrics
            since = timezone.now().date() - timedelta(days=days)
            metrics_list = ProductMetrics.objects.filter(
                date__gte=since
            ).order_by('date')

            return Response({
                'success': True,
                'data': [self._serialize_metrics(m) for m in metrics_list]
            })

        except Exception as e:
            logger.error(f"Error fetching product metrics: {e}")
            return Response({
                'success': False,
                'error': {'message': 'Failed to fetch metrics'}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _serialize_metrics(self, metrics) -> dict:
        """Serialize ProductMetrics model."""
        return {
            'date': metrics.date.isoformat(),
            'users': {
                'new_signups': metrics.new_signups,
                'total_users': metrics.total_users,
                'dau': metrics.dau,
                'wau': metrics.wau,
                'mau': metrics.mau,
            },
            'content': {
                'generated': metrics.content_generated,
                'prompts': metrics.prompts_sent,
                'responses': metrics.responses_generated,
            },
            'ai': {
                'tokens_used': metrics.tokens_used,
                'api_calls': metrics.api_calls,
            },
            'subscriptions': {
                'active': metrics.active_subscriptions,
                'new': metrics.new_subscriptions,
                'cancellations': metrics.cancellations,
            },
            'revenue': {
                'daily': float(metrics.daily_revenue),
                'mrr': float(metrics.mrr),
            },
        }


class RetentionAnalyticsView(APIView):
    """
    Retention analytics API.

    GET /api/analytics/retention/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get retention analytics."""
        try:
            from coreapp.services.retention_service import retention_service

            dashboard = retention_service.get_retention_dashboard()

            return Response({
                'success': True,
                'data': dashboard,
            })

        except Exception as e:
            logger.error(f"Error fetching retention analytics: {e}")
            return Response({
                'success': False,
                'error': {'message': 'Failed to fetch retention data'}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CohortAnalyticsView(APIView):
    """
    Cohort analysis API.

    GET /api/analytics/cohorts/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get cohort analysis data."""
        try:
            from coreapp.services.cohort_service import cohort_service

            cohort_type = request.query_params.get('type', 'acquisition')

            dashboard = cohort_service.get_cohort_dashboard()

            return Response({
                'success': True,
                'data': dashboard,
            })

        except Exception as e:
            logger.error(f"Error fetching cohort analytics: {e}")
            return Response({
                'success': False,
                'error': {'message': 'Failed to fetch cohort data'}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FunnelAnalyticsView(APIView):
    """
    Conversion funnel analytics API.

    GET /api/analytics/funnels/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get funnel analytics."""
        try:
            # Check cache first
            cached = cache.get('conversion_funnels')
            if cached:
                return Response({
                    'success': True,
                    'data': cached,
                })

            # Generate fresh data
            from coreapp.services.cohort_service import funnel_analyzer

            funnel_type = request.query_params.get('type', 'all')
            days = int(request.query_params.get('days', 30))

            funnels = {}

            if funnel_type in ['all', 'onboarding']:
                funnels['onboarding'] = funnel_analyzer.analyze_onboarding_funnel(days=days)

            if funnel_type in ['all', 'conversion']:
                funnels['conversion'] = funnel_analyzer.analyze_conversion_funnel(days=days)

            return Response({
                'success': True,
                'data': funnels,
            })

        except Exception as e:
            logger.error(f"Error fetching funnel analytics: {e}")
            return Response({
                'success': False,
                'error': {'message': 'Failed to fetch funnel data'}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RevenueAnalyticsView(APIView):
    """
    Revenue analytics API.

    GET /api/analytics/revenue/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get revenue analytics."""
        try:
            # Check cache
            cached = cache.get('revenue_analytics')
            if cached:
                return Response({
                    'success': True,
                    'data': cached,
                })

            # Calculate fresh
            from coreapp.tasks.analytics_tasks import calculate_revenue_analytics
            metrics = calculate_revenue_analytics()

            return Response({
                'success': True,
                'data': metrics,
            })

        except Exception as e:
            logger.error(f"Error fetching revenue analytics: {e}")
            return Response({
                'success': False,
                'error': {'message': 'Failed to fetch revenue data'}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# URL Patterns
# =============================================================================

# Add to urls.py:
"""
from coreapp.views.analytics_views import (
    UserAnalyticsView,
    UserEngagementView,
    DashboardAnalyticsView,
    ProductMetricsView,
    RetentionAnalyticsView,
    CohortAnalyticsView,
    FunnelAnalyticsView,
    RevenueAnalyticsView,
)

analytics_urlpatterns = [
    path('user/', UserAnalyticsView.as_view(), name='user-analytics'),
    path('engagement/', UserEngagementView.as_view(), name='user-engagement'),
    path('dashboard/', DashboardAnalyticsView.as_view(), name='dashboard-analytics'),
    path('metrics/', ProductMetricsView.as_view(), name='product-metrics'),
    path('retention/', RetentionAnalyticsView.as_view(), name='retention-analytics'),
    path('cohorts/', CohortAnalyticsView.as_view(), name='cohort-analytics'),
    path('funnels/', FunnelAnalyticsView.as_view(), name='funnel-analytics'),
    path('revenue/', RevenueAnalyticsView.as_view(), name='revenue-analytics'),
]
"""
