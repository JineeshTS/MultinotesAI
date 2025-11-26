"""
Analytics Celery Tasks for MultinotesAI.

This module provides:
- Daily metrics collection
- Product metrics aggregation
- User engagement scoring
- Revenue analytics
- Scheduled analytics jobs

Usage:
    from coreapp.tasks.analytics_tasks import collect_daily_metrics
    collect_daily_metrics.delay()
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, List

from celery import shared_task
from django.db.models import Count, Sum, Avg, F, Q
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Daily Metrics Collection
# =============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def collect_daily_metrics(self, target_date: str = None):
    """
    Collect and store daily metrics for analytics.

    Args:
        target_date: Date string (YYYY-MM-DD), defaults to yesterday

    This task should run daily via Celery beat.
    """
    try:
        if target_date:
            collection_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            collection_date = timezone.now().date() - timedelta(days=1)

        logger.info(f"Collecting daily metrics for {collection_date}")

        metrics = {}

        # User metrics
        metrics['users'] = collect_user_metrics(collection_date)

        # Content metrics
        metrics['content'] = collect_content_metrics(collection_date)

        # AI usage metrics
        metrics['ai_usage'] = collect_ai_usage_metrics(collection_date)

        # Subscription metrics
        metrics['subscriptions'] = collect_subscription_metrics(collection_date)

        # Revenue metrics
        metrics['revenue'] = collect_revenue_metrics(collection_date)

        # Store aggregated metrics
        store_product_metrics(collection_date, metrics)

        logger.info(f"Daily metrics collection complete for {collection_date}")

        return {
            'date': str(collection_date),
            'status': 'success',
            'metrics_collected': list(metrics.keys())
        }

    except Exception as e:
        logger.error(f"Daily metrics collection failed: {e}")
        raise self.retry(exc=e)


def collect_user_metrics(target_date: date) -> Dict:
    """Collect user-related metrics for a specific date."""
    try:
        from django.contrib.auth import get_user_model
        from coreapp.models_analytics import UserAnalytics

        User = get_user_model()

        # New signups
        new_users = User.objects.filter(
            date_joined__date=target_date,
            is_active=True
        ).count()

        # Total users
        total_users = User.objects.filter(
            date_joined__date__lte=target_date,
            is_active=True
        ).count()

        # Active users (DAU)
        dau = UserAnalytics.objects.filter(
            date=target_date
        ).values('user_id').distinct().count()

        # Weekly active users (WAU)
        week_start = target_date - timedelta(days=7)
        wau = UserAnalytics.objects.filter(
            date__gte=week_start,
            date__lte=target_date
        ).values('user_id').distinct().count()

        # Monthly active users (MAU)
        month_start = target_date - timedelta(days=30)
        mau = UserAnalytics.objects.filter(
            date__gte=month_start,
            date__lte=target_date
        ).values('user_id').distinct().count()

        return {
            'new_signups': new_users,
            'total_users': total_users,
            'dau': dau,
            'wau': wau,
            'mau': mau,
            'dau_mau_ratio': round(dau / mau * 100, 2) if mau > 0 else 0,
        }

    except Exception as e:
        logger.error(f"Error collecting user metrics: {e}")
        return {}


def collect_content_metrics(target_date: date) -> Dict:
    """Collect content-related metrics."""
    try:
        from coreapp.models import ContentGen, Prompt, PromptResponse, Folder

        # Content generated
        content_created = ContentGen.objects.filter(
            created_at__date=target_date,
            is_delete=False
        ).count()

        # Prompts sent
        prompts_sent = Prompt.objects.filter(
            created_at__date=target_date,
            is_delete=False
        ).count()

        # Responses generated
        responses_generated = PromptResponse.objects.filter(
            created_at__date=target_date,
            is_delete=False
        ).count()

        # Folders created
        folders_created = Folder.objects.filter(
            created_at__date=target_date,
            is_delete=False
        ).count()

        # Average prompts per user
        prompts_by_user = Prompt.objects.filter(
            created_at__date=target_date,
            is_delete=False
        ).values('user').annotate(count=Count('id'))

        avg_prompts_per_user = round(
            sum(p['count'] for p in prompts_by_user) / len(prompts_by_user), 2
        ) if prompts_by_user else 0

        return {
            'content_created': content_created,
            'prompts_sent': prompts_sent,
            'responses_generated': responses_generated,
            'folders_created': folders_created,
            'avg_prompts_per_user': avg_prompts_per_user,
        }

    except Exception as e:
        logger.error(f"Error collecting content metrics: {e}")
        return {}


def collect_ai_usage_metrics(target_date: date) -> Dict:
    """Collect AI usage metrics."""
    try:
        from coreapp.models import LLM_Tokens, LLM

        # Token usage by model
        token_usage = LLM_Tokens.objects.filter(
            created_at__date=target_date,
            is_delete=False
        ).values('llm__name').annotate(
            total_tokens=Sum('token_used'),
            request_count=Count('id'),
            unique_users=Count('user', distinct=True)
        )

        # Total tokens used
        total_tokens = sum(t['total_tokens'] or 0 for t in token_usage)

        # Total API calls
        total_calls = sum(t['request_count'] for t in token_usage)

        # Model breakdown
        model_breakdown = {
            t['llm__name']: {
                'tokens': t['total_tokens'] or 0,
                'calls': t['request_count'],
                'users': t['unique_users'],
            }
            for t in token_usage
        }

        # Average tokens per request
        avg_tokens_per_request = round(
            total_tokens / total_calls, 2
        ) if total_calls > 0 else 0

        return {
            'total_tokens': total_tokens,
            'total_calls': total_calls,
            'avg_tokens_per_request': avg_tokens_per_request,
            'model_breakdown': model_breakdown,
        }

    except Exception as e:
        logger.error(f"Error collecting AI usage metrics: {e}")
        return {}


def collect_subscription_metrics(target_date: date) -> Dict:
    """Collect subscription metrics."""
    try:
        from planandsubscription.models import Subscription, Plan

        # Active subscriptions by plan
        active_subs = Subscription.objects.filter(
            status='active',
            start_date__date__lte=target_date,
            is_delete=False
        ).values('plan__name').annotate(
            count=Count('id')
        )

        # New subscriptions
        new_subs = Subscription.objects.filter(
            start_date__date=target_date,
            is_delete=False
        ).count()

        # Cancelled subscriptions
        cancelled_subs = Subscription.objects.filter(
            end_date__date=target_date,
            status='cancelled',
            is_delete=False
        ).count()

        # Upgraded subscriptions
        # (Subscriptions where new subscription started same day as cancel)
        upgrades = 0  # Would need subscription change tracking

        # Plan distribution
        plan_distribution = {
            sub['plan__name']: sub['count']
            for sub in active_subs
        }

        # Total active
        total_active = sum(sub['count'] for sub in active_subs)

        return {
            'total_active': total_active,
            'new_subscriptions': new_subs,
            'cancellations': cancelled_subs,
            'upgrades': upgrades,
            'plan_distribution': plan_distribution,
        }

    except Exception as e:
        logger.error(f"Error collecting subscription metrics: {e}")
        return {}


def collect_revenue_metrics(target_date: date) -> Dict:
    """Collect revenue metrics."""
    try:
        from planandsubscription.models import Payment

        # Daily revenue
        payments = Payment.objects.filter(
            created_at__date=target_date,
            status='captured',
            is_delete=False
        )

        daily_revenue = payments.aggregate(total=Sum('amount'))['total'] or 0

        # Payment count
        payment_count = payments.count()

        # Average payment
        avg_payment = round(
            daily_revenue / payment_count, 2
        ) if payment_count > 0 else 0

        # Revenue by plan
        revenue_by_plan = payments.values(
            'subscription__plan__name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        )

        plan_revenue = {
            r['subscription__plan__name'] or 'Unknown': {
                'revenue': float(r['total'] or 0),
                'transactions': r['count'],
            }
            for r in revenue_by_plan
        }

        # MRR calculation (Monthly Recurring Revenue)
        month_payments = Payment.objects.filter(
            created_at__date__gte=target_date - timedelta(days=30),
            created_at__date__lte=target_date,
            status='captured',
            is_delete=False
        ).aggregate(total=Sum('amount'))

        mrr = float(month_payments['total'] or 0)

        return {
            'daily_revenue': float(daily_revenue),
            'payment_count': payment_count,
            'avg_payment': float(avg_payment),
            'mrr': mrr,
            'plan_revenue': plan_revenue,
        }

    except Exception as e:
        logger.error(f"Error collecting revenue metrics: {e}")
        return {}


def store_product_metrics(target_date: date, metrics: Dict):
    """Store aggregated product metrics."""
    try:
        from coreapp.models_analytics import ProductMetrics

        ProductMetrics.objects.update_or_create(
            date=target_date,
            defaults={
                # User metrics
                'new_signups': metrics.get('users', {}).get('new_signups', 0),
                'total_users': metrics.get('users', {}).get('total_users', 0),
                'dau': metrics.get('users', {}).get('dau', 0),
                'wau': metrics.get('users', {}).get('wau', 0),
                'mau': metrics.get('users', {}).get('mau', 0),

                # Content metrics
                'content_generated': metrics.get('content', {}).get('content_created', 0),
                'prompts_sent': metrics.get('content', {}).get('prompts_sent', 0),
                'responses_generated': metrics.get('content', {}).get('responses_generated', 0),

                # AI metrics
                'tokens_used': metrics.get('ai_usage', {}).get('total_tokens', 0),
                'api_calls': metrics.get('ai_usage', {}).get('total_calls', 0),

                # Subscription metrics
                'active_subscriptions': metrics.get('subscriptions', {}).get('total_active', 0),
                'new_subscriptions': metrics.get('subscriptions', {}).get('new_subscriptions', 0),
                'cancellations': metrics.get('subscriptions', {}).get('cancellations', 0),

                # Revenue metrics
                'daily_revenue': metrics.get('revenue', {}).get('daily_revenue', 0),
                'mrr': metrics.get('revenue', {}).get('mrr', 0),

                # JSON data for detailed breakdown
                'metadata': metrics,
            }
        )

        logger.info(f"Stored product metrics for {target_date}")

    except Exception as e:
        logger.error(f"Error storing product metrics: {e}")


# =============================================================================
# User Engagement Scoring Task
# =============================================================================

@shared_task(bind=True, max_retries=2)
def calculate_user_engagement_scores(self, batch_size: int = 100):
    """
    Calculate engagement scores for all active users.

    Should run daily after metrics collection.
    """
    try:
        from django.contrib.auth import get_user_model
        from coreapp.services.retention_service import retention_calculator

        User = get_user_model()

        # Get active users
        active_users = User.objects.filter(
            is_active=True
        ).order_by('id')

        total = active_users.count()
        processed = 0
        scores = []

        for user in active_users.iterator(chunk_size=batch_size):
            try:
                score = retention_calculator.calculate_engagement_score(user)
                scores.append({
                    'user_id': user.id,
                    'score': score.score,
                    'level': score.level,
                })
                processed += 1

            except Exception as e:
                logger.warning(f"Failed to calculate engagement for user {user.id}: {e}")

        # Store aggregated engagement data
        engagement_summary = {
            'high': len([s for s in scores if s['level'] == 'high']),
            'medium': len([s for s in scores if s['level'] == 'medium']),
            'low': len([s for s in scores if s['level'] == 'low']),
            'at_risk': len([s for s in scores if s['level'] == 'at_risk']),
        }

        cache.set('engagement_summary', engagement_summary, 86400)

        logger.info(f"Calculated engagement scores: {processed}/{total} users")

        return {
            'status': 'success',
            'processed': processed,
            'total': total,
            'summary': engagement_summary,
        }

    except Exception as e:
        logger.error(f"Engagement scoring failed: {e}")
        raise self.retry(exc=e)


# =============================================================================
# Revenue Analytics Task
# =============================================================================

@shared_task
def calculate_revenue_analytics():
    """
    Calculate comprehensive revenue analytics.

    Includes LTV, ARPU, churn rate, etc.
    """
    try:
        from django.contrib.auth import get_user_model
        from planandsubscription.models import Subscription, Payment

        User = get_user_model()

        today = timezone.now().date()

        # Calculate metrics
        metrics = {}

        # ARPU (Average Revenue Per User)
        total_revenue = Payment.objects.filter(
            status='captured',
            is_delete=False
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_users = User.objects.filter(is_active=True).count()
        metrics['arpu'] = round(total_revenue / total_users, 2) if total_users > 0 else 0

        # Monthly ARPU
        month_start = today - timedelta(days=30)
        monthly_revenue = Payment.objects.filter(
            created_at__date__gte=month_start,
            status='captured'
        ).aggregate(total=Sum('amount'))['total'] or 0

        paying_users = Subscription.objects.filter(
            status='active'
        ).values('user_id').distinct().count()

        metrics['monthly_arpu'] = round(
            monthly_revenue / paying_users, 2
        ) if paying_users > 0 else 0

        # Churn rate (last 30 days)
        churned = Subscription.objects.filter(
            end_date__date__gte=month_start,
            end_date__date__lte=today,
            status='cancelled'
        ).count()

        start_subscribers = Subscription.objects.filter(
            start_date__date__lt=month_start,
            status='active'
        ).count()

        metrics['churn_rate'] = round(
            churned / start_subscribers * 100, 2
        ) if start_subscribers > 0 else 0

        # Customer Lifetime Value (LTV)
        # Simplified: ARPU / Churn Rate
        if metrics['churn_rate'] > 0:
            metrics['ltv'] = round(
                metrics['monthly_arpu'] / (metrics['churn_rate'] / 100), 2
            )
        else:
            metrics['ltv'] = metrics['monthly_arpu'] * 12  # Assume 12 month lifetime

        # Revenue growth
        prev_month_revenue = Payment.objects.filter(
            created_at__date__gte=month_start - timedelta(days=30),
            created_at__date__lt=month_start,
            status='captured'
        ).aggregate(total=Sum('amount'))['total'] or 0

        if prev_month_revenue > 0:
            metrics['revenue_growth'] = round(
                (monthly_revenue - prev_month_revenue) / prev_month_revenue * 100, 2
            )
        else:
            metrics['revenue_growth'] = 0

        # Store in cache
        cache.set('revenue_analytics', metrics, 86400)

        logger.info(f"Revenue analytics calculated: {metrics}")

        return metrics

    except Exception as e:
        logger.error(f"Revenue analytics calculation failed: {e}")
        return {}


# =============================================================================
# Funnel Tracking Task
# =============================================================================

@shared_task
def track_conversion_funnels():
    """
    Track conversion funnel metrics.

    Funnels:
    - Signup → First Content → Upgrade
    - Visit → Signup → Active
    """
    try:
        from django.contrib.auth import get_user_model
        from coreapp.models import ContentGen
        from coreapp.models_analytics import UserAnalytics
        from planandsubscription.models import Subscription

        User = get_user_model()

        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)

        # Signup to Content Creation Funnel
        signups = User.objects.filter(
            date_joined__date__gte=last_30_days,
            is_active=True
        )
        signup_count = signups.count()

        content_creators = ContentGen.objects.filter(
            user__in=signups,
            is_delete=False
        ).values('user_id').distinct().count()

        # Conversion to paid
        paid_users = Subscription.objects.filter(
            user__in=signups,
            status='active',
            plan__price__gt=0
        ).values('user_id').distinct().count()

        signup_funnel = {
            'signups': signup_count,
            'created_content': content_creators,
            'converted_to_paid': paid_users,
            'content_rate': round(content_creators / signup_count * 100, 2) if signup_count > 0 else 0,
            'conversion_rate': round(paid_users / signup_count * 100, 2) if signup_count > 0 else 0,
        }

        # Free to Paid Funnel
        free_users = User.objects.filter(
            is_active=True
        ).exclude(
            id__in=Subscription.objects.filter(
                status='active',
                plan__price__gt=0
            ).values('user_id')
        ).count()

        active_free_users = UserAnalytics.objects.filter(
            date__gte=last_30_days,
            user__in=User.objects.exclude(
                id__in=Subscription.objects.filter(
                    status='active',
                    plan__price__gt=0
                ).values('user_id')
            )
        ).values('user_id').distinct().count()

        new_paid = Subscription.objects.filter(
            start_date__date__gte=last_30_days,
            status='active',
            plan__price__gt=0
        ).count()

        free_to_paid_funnel = {
            'free_users': free_users,
            'active_free': active_free_users,
            'converted': new_paid,
            'conversion_rate': round(new_paid / active_free_users * 100, 2) if active_free_users > 0 else 0,
        }

        funnels = {
            'signup_funnel': signup_funnel,
            'free_to_paid_funnel': free_to_paid_funnel,
            'calculated_at': timezone.now().isoformat(),
        }

        cache.set('conversion_funnels', funnels, 86400)

        logger.info(f"Funnel tracking complete: {funnels}")

        return funnels

    except Exception as e:
        logger.error(f"Funnel tracking failed: {e}")
        return {}


# =============================================================================
# Scheduled Tasks (Celery Beat)
# =============================================================================

@shared_task
def run_daily_analytics():
    """
    Run all daily analytics tasks.

    Schedule this via Celery beat at 1 AM daily.
    """
    logger.info("Starting daily analytics batch")

    results = {}

    # Collect yesterday's metrics
    results['metrics'] = collect_daily_metrics.delay().get(timeout=300)

    # Calculate engagement scores
    results['engagement'] = calculate_user_engagement_scores.delay().get(timeout=600)

    # Calculate revenue analytics
    results['revenue'] = calculate_revenue_analytics.delay().get(timeout=120)

    # Track funnels
    results['funnels'] = track_conversion_funnels.delay().get(timeout=120)

    logger.info(f"Daily analytics batch complete: {results}")

    return results


@shared_task
def cleanup_old_analytics(days_to_keep: int = 90):
    """
    Clean up old analytics data.

    Args:
        days_to_keep: Number of days of data to retain
    """
    try:
        from coreapp.models_analytics import UserAnalytics, ProductMetrics

        cutoff_date = timezone.now().date() - timedelta(days=days_to_keep)

        # Delete old user analytics
        deleted_user = UserAnalytics.objects.filter(
            date__lt=cutoff_date
        ).delete()

        logger.info(f"Deleted {deleted_user[0]} old UserAnalytics records")

        return {
            'status': 'success',
            'deleted_user_analytics': deleted_user[0],
            'cutoff_date': str(cutoff_date),
        }

    except Exception as e:
        logger.error(f"Analytics cleanup failed: {e}")
        return {'status': 'error', 'message': str(e)}
