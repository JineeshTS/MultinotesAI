"""
Admin Dashboard API endpoints for MultinotesAI.

This module provides:
- User management endpoints
- Subscription management
- System statistics
- Content moderation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

logger = logging.getLogger(__name__)
User = get_user_model()


# =============================================================================
# Admin Permission Classes
# =============================================================================

class IsSuperAdmin(IsAdminUser):
    """Permission class for superadmin only endpoints."""

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )


# =============================================================================
# Dashboard Statistics
# =============================================================================

class DashboardStatsView(APIView):
    """
    Get dashboard statistics.

    GET /api/admin/dashboard/stats/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Date ranges
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        last_7_days = today - timedelta(days=7)

        # User statistics
        total_users = User.objects.filter(is_active=True).count()
        new_users_30d = User.objects.filter(
            date_joined__date__gte=last_30_days
        ).count()
        new_users_7d = User.objects.filter(
            date_joined__date__gte=last_7_days
        ).count()
        active_users_today = self._get_active_users_today()

        # Subscription statistics
        subscription_stats = self._get_subscription_stats()

        # Content statistics
        content_stats = self._get_content_stats()

        # AI usage statistics
        ai_stats = self._get_ai_usage_stats(last_30_days)

        # Revenue statistics
        revenue_stats = self._get_revenue_stats(last_30_days)

        return Response({
            'users': {
                'total': total_users,
                'new_30d': new_users_30d,
                'new_7d': new_users_7d,
                'active_today': active_users_today,
            },
            'subscriptions': subscription_stats,
            'content': content_stats,
            'ai_usage': ai_stats,
            'revenue': revenue_stats,
            'generated_at': timezone.now().isoformat(),
        })

    def _get_active_users_today(self) -> int:
        """Get count of users active today."""
        try:
            from coreapp.models_analytics import UserAnalytics
            today = timezone.now().date()
            return UserAnalytics.objects.filter(date=today).count()
        except Exception:
            return 0

    def _get_subscription_stats(self) -> Dict:
        """Get subscription statistics."""
        try:
            from planandsubscription.models import Subscription

            total = Subscription.objects.filter(is_delete=False).count()
            active = Subscription.objects.filter(
                is_delete=False,
                status='active'
            ).count()

            by_plan = Subscription.objects.filter(
                is_delete=False,
                status='active'
            ).values('plan__name').annotate(
                count=Count('id')
            ).order_by('-count')

            return {
                'total': total,
                'active': active,
                'by_plan': list(by_plan),
            }
        except Exception:
            return {'total': 0, 'active': 0, 'by_plan': []}

    def _get_content_stats(self) -> Dict:
        """Get content statistics."""
        try:
            from coreapp.models import ContentGen, Folder

            total_notes = ContentGen.objects.filter(is_delete=False).count()
            total_folders = Folder.objects.filter(is_delete=False).count()

            return {
                'total_notes': total_notes,
                'total_folders': total_folders,
            }
        except Exception:
            return {'total_notes': 0, 'total_folders': 0}

    def _get_ai_usage_stats(self, since_date) -> Dict:
        """Get AI usage statistics."""
        try:
            from coreapp.models_analytics import UserAnalytics

            stats = UserAnalytics.objects.filter(
                date__gte=since_date
            ).aggregate(
                total_generations=Sum('ai_text_generations') + Sum('ai_image_generations'),
                total_tokens=Sum('ai_tokens_used'),
            )

            return {
                'total_generations': stats['total_generations'] or 0,
                'total_tokens': stats['total_tokens'] or 0,
            }
        except Exception:
            return {'total_generations': 0, 'total_tokens': 0}

    def _get_revenue_stats(self, since_date) -> Dict:
        """Get revenue statistics."""
        try:
            from planandsubscription.models import Payment

            revenue = Payment.objects.filter(
                created_at__date__gte=since_date,
                status='captured'
            ).aggregate(
                total=Sum('amount')
            )

            return {
                'total_30d': float(revenue['total'] or 0) / 100,  # Convert from paisa
                'currency': 'INR',
            }
        except Exception:
            return {'total_30d': 0, 'currency': 'INR'}


# =============================================================================
# User Management
# =============================================================================

class AdminUserListView(APIView):
    """
    List and search users.

    GET /api/admin/users/
    Query params: search, status, page, page_size
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        search = request.query_params.get('search', '')
        user_status = request.query_params.get('status', 'all')
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)

        queryset = User.objects.all()

        # Filter by search
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        # Filter by status
        if user_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif user_status == 'inactive':
            queryset = queryset.filter(is_active=False)

        # Paginate
        total = queryset.count()
        offset = (page - 1) * page_size
        users = queryset.order_by('-date_joined')[offset:offset + page_size]

        # Serialize
        user_data = []
        for user in users:
            user_data.append({
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
            })

        return Response({
            'users': user_data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size,
        })


class AdminUserDetailView(APIView):
    """
    Get/update user details.

    GET /api/admin/users/<id>/
    PATCH /api/admin/users/<id>/
    """
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get subscription info
        subscription_info = self._get_user_subscription(user)

        # Get usage stats
        usage_stats = self._get_user_usage_stats(user)

        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
            },
            'subscription': subscription_info,
            'usage': usage_stats,
        })

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Allowed fields to update
        allowed_fields = ['is_active', 'is_staff', 'first_name', 'last_name']

        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])

        user.save()

        logger.info(f"Admin {request.user.email} updated user {user.email}")

        return Response({'message': 'User updated successfully'})

    def _get_user_subscription(self, user) -> Dict:
        """Get user's subscription info."""
        try:
            from planandsubscription.models import Subscription

            subscription = Subscription.objects.filter(
                user=user,
                is_delete=False,
                status='active'
            ).select_related('plan').first()

            if subscription:
                return {
                    'plan': subscription.plan.name if subscription.plan else 'N/A',
                    'status': subscription.status,
                    'balance_tokens': subscription.balanceToken,
                    'file_tokens': subscription.fileToken,
                    'expires_at': subscription.end_date.isoformat() if subscription.end_date else None,
                }
        except Exception:
            pass
        return None

    def _get_user_usage_stats(self, user) -> Dict:
        """Get user's usage statistics."""
        try:
            from coreapp.models_analytics import UserAnalytics
            from datetime import timedelta

            last_30_days = timezone.now().date() - timedelta(days=30)

            stats = UserAnalytics.objects.filter(
                user=user,
                date__gte=last_30_days
            ).aggregate(
                notes_created=Sum('notes_created'),
                ai_generations=Sum('ai_text_generations') + Sum('ai_image_generations'),
                tokens_used=Sum('ai_tokens_used'),
            )

            return {
                'notes_created_30d': stats['notes_created'] or 0,
                'ai_generations_30d': stats['ai_generations'] or 0,
                'tokens_used_30d': stats['tokens_used'] or 0,
            }
        except Exception:
            return {}


# =============================================================================
# Subscription Management
# =============================================================================

class AdminSubscriptionListView(APIView):
    """
    List subscriptions.

    GET /api/admin/subscriptions/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from planandsubscription.models import Subscription

        subscription_status = request.query_params.get('status', 'active')
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)

        queryset = Subscription.objects.filter(is_delete=False)

        if subscription_status != 'all':
            queryset = queryset.filter(status=subscription_status)

        total = queryset.count()
        offset = (page - 1) * page_size
        subscriptions = queryset.select_related(
            'user', 'plan'
        ).order_by('-created_at')[offset:offset + page_size]

        data = []
        for sub in subscriptions:
            data.append({
                'id': sub.id,
                'user_email': sub.user.email if sub.user else 'N/A',
                'plan': sub.plan.name if sub.plan else 'N/A',
                'status': sub.status,
                'balance_tokens': sub.balanceToken,
                'start_date': sub.start_date.isoformat() if sub.start_date else None,
                'end_date': sub.end_date.isoformat() if sub.end_date else None,
            })

        return Response({
            'subscriptions': data,
            'total': total,
            'page': page,
            'page_size': page_size,
        })


class AdminSubscriptionModifyView(APIView):
    """
    Modify a subscription (add tokens, extend, etc.)

    PATCH /api/admin/subscriptions/<id>/
    """
    permission_classes = [IsSuperAdmin]

    def patch(self, request, subscription_id):
        from planandsubscription.models import Subscription

        try:
            subscription = Subscription.objects.get(id=subscription_id, is_delete=False)
        except Subscription.DoesNotExist:
            return Response(
                {'error': 'Subscription not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Add tokens
        if 'add_tokens' in request.data:
            tokens = int(request.data['add_tokens'])
            subscription.balanceToken = (subscription.balanceToken or 0) + tokens
            logger.info(f"Admin added {tokens} tokens to subscription {subscription_id}")

        # Extend subscription
        if 'extend_days' in request.data:
            days = int(request.data['extend_days'])
            if subscription.end_date:
                subscription.end_date += timedelta(days=days)
            logger.info(f"Admin extended subscription {subscription_id} by {days} days")

        # Change status
        if 'status' in request.data:
            subscription.status = request.data['status']
            logger.info(f"Admin changed subscription {subscription_id} status to {request.data['status']}")

        subscription.save()

        return Response({'message': 'Subscription updated successfully'})


# =============================================================================
# System Health
# =============================================================================

class AdminSystemHealthView(APIView):
    """
    Get system health information.

    GET /api/admin/system/health/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from backend.health import (
            check_database,
            check_cache,
            check_storage,
            HealthStatus
        )

        checks = {
            'database': check_database().to_dict(),
            'cache': check_cache().to_dict(),
            'storage': check_storage().to_dict(),
        }

        # Determine overall status
        statuses = [c['status'] for c in checks.values()]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return Response({
            'status': overall,
            'checks': checks,
            'timestamp': timezone.now().isoformat(),
        })


# =============================================================================
# Analytics Charts
# =============================================================================

class AdminAnalyticsChartsView(APIView):
    """
    Get analytics data for charts.

    GET /api/admin/analytics/charts/
    Query params: period (7d, 30d, 90d)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        period = request.query_params.get('period', '30d')

        days_map = {'7d': 7, '30d': 30, '90d': 90}
        days = days_map.get(period, 30)

        start_date = timezone.now().date() - timedelta(days=days)

        # User growth
        user_growth = self._get_user_growth(start_date)

        # Revenue trend
        revenue_trend = self._get_revenue_trend(start_date)

        # AI usage trend
        ai_trend = self._get_ai_usage_trend(start_date)

        return Response({
            'user_growth': user_growth,
            'revenue_trend': revenue_trend,
            'ai_usage_trend': ai_trend,
            'period': period,
        })

    def _get_user_growth(self, start_date) -> list:
        """Get daily user signups."""
        data = User.objects.filter(
            date_joined__date__gte=start_date
        ).annotate(
            date=TruncDate('date_joined')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        return [{'date': d['date'].isoformat(), 'count': d['count']} for d in data]

    def _get_revenue_trend(self, start_date) -> list:
        """Get daily revenue."""
        try:
            from planandsubscription.models import Payment

            data = Payment.objects.filter(
                created_at__date__gte=start_date,
                status='captured'
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                amount=Sum('amount')
            ).order_by('date')

            return [
                {'date': d['date'].isoformat(), 'amount': float(d['amount'] or 0) / 100}
                for d in data
            ]
        except Exception:
            return []

    def _get_ai_usage_trend(self, start_date) -> list:
        """Get daily AI usage."""
        try:
            from coreapp.models_analytics import UserAnalytics

            data = UserAnalytics.objects.filter(
                date__gte=start_date
            ).values('date').annotate(
                generations=Sum('ai_text_generations') + Sum('ai_image_generations'),
                tokens=Sum('ai_tokens_used')
            ).order_by('date')

            return [
                {
                    'date': d['date'].isoformat(),
                    'generations': d['generations'] or 0,
                    'tokens': d['tokens'] or 0
                }
                for d in data
            ]
        except Exception:
            return []
