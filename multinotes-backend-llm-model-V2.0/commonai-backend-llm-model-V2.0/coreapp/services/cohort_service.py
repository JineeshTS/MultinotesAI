"""
Cohort Analysis Service for MultinotesAI.

This module provides:
- User cohort segmentation
- Cohort comparison analytics
- Behavioral cohort analysis
- Revenue cohort tracking
- Conversion funnel analysis

"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from django.db.models import Count, Avg, Sum, Q, F, Min, Max
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Data Types
# =============================================================================

class CohortType(Enum):
    """Types of cohort segmentation."""
    ACQUISITION = 'acquisition'  # By signup date
    BEHAVIORAL = 'behavioral'  # By actions taken
    SUBSCRIPTION = 'subscription'  # By plan type
    REVENUE = 'revenue'  # By spending
    ENGAGEMENT = 'engagement'  # By activity level


class CohortGranularity(Enum):
    """Time granularity for cohort analysis."""
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'


@dataclass
class CohortDefinition:
    """Definition of a cohort."""
    cohort_id: str
    name: str
    cohort_type: CohortType
    start_date: date
    end_date: date
    size: int
    criteria: Dict = field(default_factory=dict)


@dataclass
class CohortMetrics:
    """Metrics for a cohort at a specific period."""
    cohort_id: str
    period: int  # Periods since cohort start
    active_users: int
    retention_rate: float
    revenue: float = 0
    avg_sessions: float = 0
    avg_tokens_used: float = 0
    conversion_rate: float = 0


@dataclass
class CohortComparison:
    """Comparison between cohorts."""
    cohort_a: str
    cohort_b: str
    metric: str
    cohort_a_value: float
    cohort_b_value: float
    difference: float
    percent_change: float
    statistically_significant: bool = False


# =============================================================================
# Cohort Builder
# =============================================================================

class CohortBuilder:
    """
    Build and define user cohorts.

    Usage:
        builder = CohortBuilder()
        cohort = builder.by_acquisition(month='2024-01')
        cohort = builder.by_subscription_plan('Pro')
        cohort = builder.by_behavior('completed_onboarding')
    """

    def __init__(self):
        self.cache_timeout = 3600

    def by_acquisition(
        self,
        start_date: date = None,
        end_date: date = None,
        granularity: CohortGranularity = CohortGranularity.MONTHLY
    ) -> List[CohortDefinition]:
        """
        Create cohorts based on user acquisition date.

        Args:
            start_date: Cohort period start
            end_date: Cohort period end
            granularity: Time granularity

        Returns:
            List of cohort definitions
        """
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            if end_date is None:
                end_date = timezone.now().date()
            if start_date is None:
                start_date = end_date - timedelta(days=180)  # 6 months

            # Set truncation function based on granularity
            if granularity == CohortGranularity.MONTHLY:
                trunc_func = TruncMonth
            elif granularity == CohortGranularity.WEEKLY:
                trunc_func = TruncWeek
            else:
                trunc_func = TruncDate

            # Group users by period
            user_cohorts = User.objects.filter(
                date_joined__date__gte=start_date,
                date_joined__date__lte=end_date,
                is_active=True
            ).annotate(
                cohort_period=trunc_func('date_joined')
            ).values('cohort_period').annotate(
                size=Count('id')
            ).order_by('cohort_period')

            cohorts = []
            for cohort_data in user_cohorts:
                cohort_date = cohort_data['cohort_period']
                if hasattr(cohort_date, 'date'):
                    cohort_date = cohort_date.date()

                # Calculate end date based on granularity
                if granularity == CohortGranularity.MONTHLY:
                    cohort_end = cohort_date.replace(day=28) + timedelta(days=4)
                    cohort_end = cohort_end.replace(day=1) - timedelta(days=1)
                elif granularity == CohortGranularity.WEEKLY:
                    cohort_end = cohort_date + timedelta(days=6)
                else:
                    cohort_end = cohort_date

                cohorts.append(CohortDefinition(
                    cohort_id=f"acq_{cohort_date.strftime('%Y%m%d')}",
                    name=f"Acquired {cohort_date.strftime('%Y-%m')}",
                    cohort_type=CohortType.ACQUISITION,
                    start_date=cohort_date,
                    end_date=cohort_end,
                    size=cohort_data['size'],
                    criteria={'acquisition_period': cohort_date.isoformat()}
                ))

            return cohorts

        except Exception as e:
            logger.error(f"Error creating acquisition cohorts: {e}")
            return []

    def by_subscription_plan(
        self,
        plan_name: str = None,
        include_free: bool = True
    ) -> List[CohortDefinition]:
        """
        Create cohorts based on subscription plan.

        Args:
            plan_name: Specific plan to filter (or None for all)
            include_free: Include users without subscriptions

        Returns:
            List of cohort definitions
        """
        try:
            from planandsubscription.models import Subscription, Plan

            # Get all plans
            plans = Plan.objects.filter(is_delete=False)
            if plan_name:
                plans = plans.filter(name__icontains=plan_name)

            cohorts = []

            for plan in plans:
                subscriber_count = Subscription.objects.filter(
                    plan=plan,
                    status='active',
                    is_delete=False
                ).values('user_id').distinct().count()

                cohorts.append(CohortDefinition(
                    cohort_id=f"plan_{plan.id}",
                    name=f"{plan.name} Subscribers",
                    cohort_type=CohortType.SUBSCRIPTION,
                    start_date=timezone.now().date() - timedelta(days=365),
                    end_date=timezone.now().date(),
                    size=subscriber_count,
                    criteria={'plan_id': plan.id, 'plan_name': plan.name}
                ))

            if include_free:
                # Users without active subscription
                from django.contrib.auth import get_user_model
                User = get_user_model()

                users_with_sub = Subscription.objects.filter(
                    status='active',
                    is_delete=False
                ).values_list('user_id', flat=True)

                free_users = User.objects.filter(
                    is_active=True
                ).exclude(id__in=users_with_sub).count()

                cohorts.append(CohortDefinition(
                    cohort_id="plan_free",
                    name="Free Users",
                    cohort_type=CohortType.SUBSCRIPTION,
                    start_date=timezone.now().date() - timedelta(days=365),
                    end_date=timezone.now().date(),
                    size=free_users,
                    criteria={'plan': 'free'}
                ))

            return cohorts

        except Exception as e:
            logger.error(f"Error creating subscription cohorts: {e}")
            return []

    def by_behavior(
        self,
        behavior: str,
        start_date: date = None,
        end_date: date = None
    ) -> CohortDefinition:
        """
        Create a cohort based on specific behavior.

        Args:
            behavior: Behavior identifier
            start_date: Period start
            end_date: Period end

        Returns:
            CohortDefinition for behavioral cohort
        """
        try:
            from django.contrib.auth import get_user_model
            from coreapp.models import ContentGen
            from coreapp.models_analytics import UserAnalytics

            User = get_user_model()

            if end_date is None:
                end_date = timezone.now().date()
            if start_date is None:
                start_date = end_date - timedelta(days=30)

            user_ids = set()

            # Define behavior criteria
            if behavior == 'completed_onboarding':
                try:
                    from coreapp.models_onboarding import UserOnboarding
                    user_ids = set(
                        UserOnboarding.objects.filter(
                            is_completed=True
                        ).values_list('user_id', flat=True)
                    )
                except Exception:
                    pass

            elif behavior == 'power_users':
                # Users with high activity
                user_ids = set(
                    UserAnalytics.objects.filter(
                        date__gte=start_date,
                        date__lte=end_date
                    ).values('user_id').annotate(
                        total_sessions=Sum('sessions')
                    ).filter(
                        total_sessions__gte=20
                    ).values_list('user_id', flat=True)
                )

            elif behavior == 'content_creators':
                # Users who created content
                user_ids = set(
                    ContentGen.objects.filter(
                        created_at__date__gte=start_date,
                        created_at__date__lte=end_date,
                        is_delete=False
                    ).values_list('user_id', flat=True).distinct()
                )

            elif behavior == 'paid_converters':
                # Users who converted to paid
                from planandsubscription.models import Subscription, Plan

                paid_plans = Plan.objects.filter(price__gt=0).values_list('id', flat=True)
                user_ids = set(
                    Subscription.objects.filter(
                        plan_id__in=paid_plans,
                        start_date__gte=start_date,
                        start_date__lte=end_date
                    ).values_list('user_id', flat=True).distinct()
                )

            elif behavior == 'churned':
                # Users who haven't been active recently
                active_users = set(
                    UserAnalytics.objects.filter(
                        date__gte=end_date - timedelta(days=14)
                    ).values_list('user_id', flat=True).distinct()
                )
                all_users = set(
                    User.objects.filter(is_active=True).values_list('id', flat=True)
                )
                user_ids = all_users - active_users

            return CohortDefinition(
                cohort_id=f"behavior_{behavior}",
                name=f"Behavior: {behavior.replace('_', ' ').title()}",
                cohort_type=CohortType.BEHAVIORAL,
                start_date=start_date,
                end_date=end_date,
                size=len(user_ids),
                criteria={'behavior': behavior, 'user_ids': list(user_ids)[:1000]}
            )

        except Exception as e:
            logger.error(f"Error creating behavioral cohort: {e}")
            return CohortDefinition(
                cohort_id=f"behavior_{behavior}",
                name=f"Behavior: {behavior}",
                cohort_type=CohortType.BEHAVIORAL,
                start_date=start_date or timezone.now().date(),
                end_date=end_date or timezone.now().date(),
                size=0,
                criteria={'behavior': behavior, 'error': str(e)}
            )

    def by_engagement_level(self) -> List[CohortDefinition]:
        """
        Create cohorts based on engagement level.

        Returns:
            List of engagement-based cohorts
        """
        try:
            from coreapp.models_analytics import UserAnalytics

            last_30_days = timezone.now().date() - timedelta(days=30)

            # Get user activity levels
            user_activity = UserAnalytics.objects.filter(
                date__gte=last_30_days
            ).values('user_id').annotate(
                total_sessions=Sum('sessions'),
                active_days=Count('date', distinct=True)
            )

            # Segment users
            high_engagement = []
            medium_engagement = []
            low_engagement = []

            for ua in user_activity:
                if ua['active_days'] >= 20 or ua['total_sessions'] >= 30:
                    high_engagement.append(ua['user_id'])
                elif ua['active_days'] >= 10 or ua['total_sessions'] >= 15:
                    medium_engagement.append(ua['user_id'])
                else:
                    low_engagement.append(ua['user_id'])

            cohorts = [
                CohortDefinition(
                    cohort_id="engagement_high",
                    name="High Engagement",
                    cohort_type=CohortType.ENGAGEMENT,
                    start_date=last_30_days,
                    end_date=timezone.now().date(),
                    size=len(high_engagement),
                    criteria={'level': 'high', 'threshold': '20+ days or 30+ sessions'}
                ),
                CohortDefinition(
                    cohort_id="engagement_medium",
                    name="Medium Engagement",
                    cohort_type=CohortType.ENGAGEMENT,
                    start_date=last_30_days,
                    end_date=timezone.now().date(),
                    size=len(medium_engagement),
                    criteria={'level': 'medium', 'threshold': '10-19 days or 15-29 sessions'}
                ),
                CohortDefinition(
                    cohort_id="engagement_low",
                    name="Low Engagement",
                    cohort_type=CohortType.ENGAGEMENT,
                    start_date=last_30_days,
                    end_date=timezone.now().date(),
                    size=len(low_engagement),
                    criteria={'level': 'low', 'threshold': '<10 days and <15 sessions'}
                ),
            ]

            return cohorts

        except Exception as e:
            logger.error(f"Error creating engagement cohorts: {e}")
            return []


# =============================================================================
# Cohort Analyzer
# =============================================================================

class CohortAnalyzer:
    """
    Analyze cohort behavior and metrics.

    Usage:
        analyzer = CohortAnalyzer()
        metrics = analyzer.get_cohort_metrics(cohort, periods=12)
        comparison = analyzer.compare_cohorts(cohort_a, cohort_b)
    """

    def __init__(self):
        self.cache_timeout = 1800  # 30 minutes

    def get_cohort_metrics(
        self,
        cohort: CohortDefinition,
        periods: int = 12,
        granularity: CohortGranularity = CohortGranularity.MONTHLY
    ) -> List[CohortMetrics]:
        """
        Get metrics for a cohort over time.

        Args:
            cohort: Cohort to analyze
            periods: Number of periods to analyze
            granularity: Time granularity

        Returns:
            List of metrics for each period
        """
        cache_key = f'cohort:metrics:{cohort.cohort_id}:{periods}:{granularity.value}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            from coreapp.models_analytics import UserAnalytics
            from planandsubscription.models import Payment

            # Get user IDs for this cohort
            user_ids = self._get_cohort_user_ids(cohort)

            if not user_ids:
                return []

            # Determine period length
            if granularity == CohortGranularity.MONTHLY:
                period_days = 30
            elif granularity == CohortGranularity.WEEKLY:
                period_days = 7
            else:
                period_days = 1

            metrics_list = []

            for period in range(periods):
                period_start = cohort.start_date + timedelta(days=period * period_days)
                period_end = period_start + timedelta(days=period_days)

                if period_start > timezone.now().date():
                    break

                # Get active users in this period
                active_users = UserAnalytics.objects.filter(
                    user_id__in=user_ids,
                    date__gte=period_start,
                    date__lt=period_end
                ).values('user_id').distinct().count()

                # Calculate retention rate
                retention_rate = (active_users / cohort.size * 100) if cohort.size > 0 else 0

                # Get average metrics
                period_analytics = UserAnalytics.objects.filter(
                    user_id__in=user_ids,
                    date__gte=period_start,
                    date__lt=period_end
                ).aggregate(
                    avg_sessions=Avg('sessions'),
                    avg_tokens=Avg('ai_tokens_used')
                )

                # Get revenue for this period
                try:
                    revenue = Payment.objects.filter(
                        user_id__in=user_ids,
                        created_at__date__gte=period_start,
                        created_at__date__lt=period_end,
                        status='captured'
                    ).aggregate(total=Sum('amount'))['total'] or 0
                except Exception:
                    revenue = 0

                metrics_list.append(CohortMetrics(
                    cohort_id=cohort.cohort_id,
                    period=period,
                    active_users=active_users,
                    retention_rate=round(retention_rate, 2),
                    revenue=float(revenue),
                    avg_sessions=round(period_analytics['avg_sessions'] or 0, 2),
                    avg_tokens_used=round(period_analytics['avg_tokens'] or 0, 2)
                ))

            cache.set(cache_key, metrics_list, self.cache_timeout)
            return metrics_list

        except Exception as e:
            logger.error(f"Error getting cohort metrics: {e}")
            return []

    def _get_cohort_user_ids(self, cohort: CohortDefinition) -> List[int]:
        """Get user IDs belonging to a cohort."""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            if cohort.cohort_type == CohortType.ACQUISITION:
                return list(
                    User.objects.filter(
                        date_joined__date__gte=cohort.start_date,
                        date_joined__date__lte=cohort.end_date,
                        is_active=True
                    ).values_list('id', flat=True)
                )

            elif cohort.cohort_type == CohortType.SUBSCRIPTION:
                from planandsubscription.models import Subscription

                plan_id = cohort.criteria.get('plan_id')
                if plan_id:
                    return list(
                        Subscription.objects.filter(
                            plan_id=plan_id,
                            status='active'
                        ).values_list('user_id', flat=True).distinct()
                    )
                elif cohort.criteria.get('plan') == 'free':
                    users_with_sub = Subscription.objects.filter(
                        status='active'
                    ).values_list('user_id', flat=True)
                    return list(
                        User.objects.filter(
                            is_active=True
                        ).exclude(id__in=users_with_sub).values_list('id', flat=True)
                    )

            elif cohort.cohort_type == CohortType.BEHAVIORAL:
                return cohort.criteria.get('user_ids', [])

            return []

        except Exception as e:
            logger.error(f"Error getting cohort user IDs: {e}")
            return []

    def compare_cohorts(
        self,
        cohort_a: CohortDefinition,
        cohort_b: CohortDefinition,
        metrics: List[str] = None
    ) -> List[CohortComparison]:
        """
        Compare two cohorts across multiple metrics.

        Args:
            cohort_a: First cohort
            cohort_b: Second cohort
            metrics: Metrics to compare

        Returns:
            List of comparison results
        """
        if metrics is None:
            metrics = ['retention_rate', 'avg_sessions', 'avg_tokens_used', 'revenue']

        try:
            metrics_a = self.get_cohort_metrics(cohort_a, periods=3)
            metrics_b = self.get_cohort_metrics(cohort_b, periods=3)

            if not metrics_a or not metrics_b:
                return []

            # Use last period for comparison
            latest_a = metrics_a[-1]
            latest_b = metrics_b[-1]

            comparisons = []

            for metric in metrics:
                value_a = getattr(latest_a, metric, 0)
                value_b = getattr(latest_b, metric, 0)

                difference = value_a - value_b
                percent_change = ((value_a - value_b) / value_b * 100) if value_b != 0 else 0

                comparisons.append(CohortComparison(
                    cohort_a=cohort_a.cohort_id,
                    cohort_b=cohort_b.cohort_id,
                    metric=metric,
                    cohort_a_value=value_a,
                    cohort_b_value=value_b,
                    difference=round(difference, 2),
                    percent_change=round(percent_change, 2)
                ))

            return comparisons

        except Exception as e:
            logger.error(f"Error comparing cohorts: {e}")
            return []


# =============================================================================
# Funnel Analyzer
# =============================================================================

class FunnelAnalyzer:
    """
    Analyze conversion funnels for cohorts.

    Usage:
        analyzer = FunnelAnalyzer()
        funnel = analyzer.analyze_onboarding_funnel(cohort)
        funnel = analyzer.analyze_conversion_funnel(cohort)
    """

    def analyze_onboarding_funnel(
        self,
        cohort: CohortDefinition = None,
        days: int = 30
    ) -> Dict:
        """
        Analyze onboarding funnel completion.

        Args:
            cohort: Specific cohort (or all users)
            days: Days to analyze

        Returns:
            Funnel analysis results
        """
        try:
            from django.contrib.auth import get_user_model
            from coreapp.models import ContentGen
            from coreapp.models_analytics import UserAnalytics

            User = get_user_model()

            since = timezone.now() - timedelta(days=days)

            # Get users to analyze
            if cohort:
                analyzer = CohortAnalyzer()
                user_ids = analyzer._get_cohort_user_ids(cohort)
                users = User.objects.filter(id__in=user_ids)
            else:
                users = User.objects.filter(
                    date_joined__gte=since,
                    is_active=True
                )

            total_signups = users.count()

            if total_signups == 0:
                return {'error': 'No users to analyze'}

            # Funnel steps
            steps = []

            # Step 1: Signup
            steps.append({
                'step': 1,
                'name': 'Signup',
                'count': total_signups,
                'rate': 100.0
            })

            # Step 2: First session
            first_session = UserAnalytics.objects.filter(
                user__in=users
            ).values('user_id').distinct().count()

            steps.append({
                'step': 2,
                'name': 'First Session',
                'count': first_session,
                'rate': round(first_session / total_signups * 100, 2)
            })

            # Step 3: First content creation
            first_content = ContentGen.objects.filter(
                user__in=users,
                is_delete=False
            ).values('user_id').distinct().count()

            steps.append({
                'step': 3,
                'name': 'First Content Created',
                'count': first_content,
                'rate': round(first_content / total_signups * 100, 2)
            })

            # Step 4: Second day return
            second_day_users = UserAnalytics.objects.filter(
                user__in=users
            ).values('user_id').annotate(
                active_days=Count('date', distinct=True)
            ).filter(active_days__gte=2).count()

            steps.append({
                'step': 4,
                'name': 'Day 2 Return',
                'count': second_day_users,
                'rate': round(second_day_users / total_signups * 100, 2)
            })

            # Step 5: Week 1 retention
            week1_users = UserAnalytics.objects.filter(
                user__in=users
            ).values('user_id').annotate(
                active_days=Count('date', distinct=True)
            ).filter(active_days__gte=3).count()

            steps.append({
                'step': 5,
                'name': 'Week 1 Active (3+ days)',
                'count': week1_users,
                'rate': round(week1_users / total_signups * 100, 2)
            })

            return {
                'period_days': days,
                'total_signups': total_signups,
                'steps': steps,
                'overall_conversion': steps[-1]['rate'],
                'biggest_dropoff': self._find_biggest_dropoff(steps),
            }

        except Exception as e:
            logger.error(f"Error analyzing onboarding funnel: {e}")
            return {'error': str(e)}

    def analyze_conversion_funnel(
        self,
        cohort: CohortDefinition = None,
        days: int = 30
    ) -> Dict:
        """
        Analyze free-to-paid conversion funnel.

        Args:
            cohort: Specific cohort (or all users)
            days: Days to analyze

        Returns:
            Conversion funnel analysis
        """
        try:
            from django.contrib.auth import get_user_model
            from planandsubscription.models import Subscription, Plan, Payment

            User = get_user_model()

            since = timezone.now() - timedelta(days=days)

            # Get users to analyze
            if cohort:
                analyzer = CohortAnalyzer()
                user_ids = analyzer._get_cohort_user_ids(cohort)
                users = User.objects.filter(id__in=user_ids)
            else:
                users = User.objects.filter(
                    date_joined__gte=since,
                    is_active=True
                )

            total_users = users.count()

            if total_users == 0:
                return {'error': 'No users to analyze'}

            steps = []

            # Step 1: All users
            steps.append({
                'step': 1,
                'name': 'Total Users',
                'count': total_users,
                'rate': 100.0
            })

            # Step 2: Viewed pricing
            # This would require tracking - estimate as active users
            from coreapp.models_analytics import UserAnalytics
            active_users = UserAnalytics.objects.filter(
                user__in=users
            ).values('user_id').distinct().count()

            steps.append({
                'step': 2,
                'name': 'Active Users',
                'count': active_users,
                'rate': round(active_users / total_users * 100, 2)
            })

            # Step 3: Started checkout (created payment intent)
            checkout_started = Payment.objects.filter(
                user__in=users
            ).values('user_id').distinct().count()

            steps.append({
                'step': 3,
                'name': 'Started Checkout',
                'count': checkout_started,
                'rate': round(checkout_started / total_users * 100, 2)
            })

            # Step 4: Completed payment
            paid_users = Payment.objects.filter(
                user__in=users,
                status='captured'
            ).values('user_id').distinct().count()

            steps.append({
                'step': 4,
                'name': 'Completed Payment',
                'count': paid_users,
                'rate': round(paid_users / total_users * 100, 2)
            })

            # Step 5: Active subscribers
            active_subs = Subscription.objects.filter(
                user__in=users,
                status='active'
            ).values('user_id').distinct().count()

            steps.append({
                'step': 5,
                'name': 'Active Subscription',
                'count': active_subs,
                'rate': round(active_subs / total_users * 100, 2)
            })

            return {
                'period_days': days,
                'total_users': total_users,
                'steps': steps,
                'overall_conversion': steps[-1]['rate'],
                'biggest_dropoff': self._find_biggest_dropoff(steps),
            }

        except Exception as e:
            logger.error(f"Error analyzing conversion funnel: {e}")
            return {'error': str(e)}

    def _find_biggest_dropoff(self, steps: List[Dict]) -> Dict:
        """Find the step with the biggest dropoff."""
        if len(steps) < 2:
            return {}

        biggest_dropoff = {'step': 0, 'dropoff': 0}

        for i in range(1, len(steps)):
            dropoff = steps[i-1]['rate'] - steps[i]['rate']
            if dropoff > biggest_dropoff['dropoff']:
                biggest_dropoff = {
                    'from_step': steps[i-1]['name'],
                    'to_step': steps[i]['name'],
                    'dropoff': round(dropoff, 2),
                    'step_number': i
                }

        return biggest_dropoff


# =============================================================================
# Cohort Service
# =============================================================================

class CohortService:
    """
    High-level service for cohort analysis.

    Usage:
        service = CohortService()
        dashboard = service.get_cohort_dashboard()
        report = service.generate_cohort_report()
    """

    def __init__(self):
        self.builder = CohortBuilder()
        self.analyzer = CohortAnalyzer()
        self.funnel = FunnelAnalyzer()

    def get_cohort_dashboard(self) -> Dict:
        """
        Get comprehensive cohort dashboard data.

        Returns:
            Dashboard data with all cohort analytics
        """
        cache_key = 'cohort:dashboard'
        cached = cache.get(cache_key)
        if cached:
            return cached

        data = {
            'acquisition_cohorts': self._get_acquisition_summary(),
            'subscription_cohorts': self._get_subscription_summary(),
            'engagement_cohorts': self._get_engagement_summary(),
            'funnel_analysis': self.funnel.analyze_conversion_funnel(days=30),
            'generated_at': timezone.now().isoformat(),
        }

        cache.set(cache_key, data, 1800)  # 30 minutes
        return data

    def _get_acquisition_summary(self) -> Dict:
        """Get acquisition cohort summary."""
        cohorts = self.builder.by_acquisition(
            granularity=CohortGranularity.MONTHLY
        )[-6:]  # Last 6 months

        return {
            'cohorts': [
                {
                    'id': c.cohort_id,
                    'name': c.name,
                    'size': c.size,
                    'start_date': c.start_date.isoformat()
                }
                for c in cohorts
            ],
            'total_users': sum(c.size for c in cohorts)
        }

    def _get_subscription_summary(self) -> Dict:
        """Get subscription cohort summary."""
        cohorts = self.builder.by_subscription_plan()

        return {
            'cohorts': [
                {
                    'id': c.cohort_id,
                    'name': c.name,
                    'size': c.size,
                    'plan': c.criteria.get('plan_name', 'Free')
                }
                for c in cohorts
            ],
            'paid_users': sum(c.size for c in cohorts if c.criteria.get('plan_name'))
        }

    def _get_engagement_summary(self) -> Dict:
        """Get engagement cohort summary."""
        cohorts = self.builder.by_engagement_level()

        return {
            'cohorts': [
                {
                    'id': c.cohort_id,
                    'name': c.name,
                    'size': c.size,
                    'level': c.criteria.get('level')
                }
                for c in cohorts
            ]
        }

    def generate_cohort_report(
        self,
        cohort_type: CohortType = CohortType.ACQUISITION,
        periods: int = 6
    ) -> Dict:
        """
        Generate a detailed cohort report.

        Args:
            cohort_type: Type of cohort analysis
            periods: Number of periods to include

        Returns:
            Detailed cohort report
        """
        if cohort_type == CohortType.ACQUISITION:
            cohorts = self.builder.by_acquisition(
                granularity=CohortGranularity.MONTHLY
            )[-periods:]
        elif cohort_type == CohortType.SUBSCRIPTION:
            cohorts = self.builder.by_subscription_plan()
        elif cohort_type == CohortType.ENGAGEMENT:
            cohorts = self.builder.by_engagement_level()
        else:
            cohorts = []

        report_data = []

        for cohort in cohorts:
            metrics = self.analyzer.get_cohort_metrics(cohort, periods=6)

            report_data.append({
                'cohort': {
                    'id': cohort.cohort_id,
                    'name': cohort.name,
                    'size': cohort.size,
                    'type': cohort.cohort_type.value,
                },
                'metrics': [
                    {
                        'period': m.period,
                        'active_users': m.active_users,
                        'retention_rate': m.retention_rate,
                        'revenue': m.revenue,
                    }
                    for m in metrics
                ]
            })

        return {
            'report_type': cohort_type.value,
            'periods_analyzed': periods,
            'cohorts': report_data,
            'generated_at': timezone.now().isoformat(),
        }


# =============================================================================
# Singleton Instances
# =============================================================================

cohort_builder = CohortBuilder()
cohort_analyzer = CohortAnalyzer()
funnel_analyzer = FunnelAnalyzer()
cohort_service = CohortService()
