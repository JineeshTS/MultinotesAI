"""
User Retention Analytics Service for MultinotesAI.

This module provides:
- Retention rate calculation
- Cohort retention analysis
- Churn prediction
- User engagement scoring

"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from django.db.models import Count, Avg, Sum, Q, F
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RetentionMetrics:
    """Retention metrics for a period."""
    period_start: date
    period_end: date
    total_users: int
    active_users: int
    retained_users: int
    churned_users: int
    retention_rate: float
    churn_rate: float


@dataclass
class CohortData:
    """Data for a single cohort."""
    cohort_date: date
    cohort_size: int
    retention_by_period: Dict[int, float] = field(default_factory=dict)


@dataclass
class UserEngagementScore:
    """Engagement score for a user."""
    user_id: int
    score: float
    level: str  # 'high', 'medium', 'low', 'at_risk'
    factors: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# Retention Calculator
# =============================================================================

class RetentionCalculator:
    """
    Calculate user retention metrics.

    Usage:
        calculator = RetentionCalculator()
        metrics = calculator.calculate_retention(days=30)
        cohorts = calculator.analyze_cohorts(months=3)
    """

    # Retention period definitions (in days)
    PERIOD_DAILY = 1
    PERIOD_WEEKLY = 7
    PERIOD_MONTHLY = 30

    # Engagement thresholds
    HIGH_ENGAGEMENT_ACTIONS = 10
    MEDIUM_ENGAGEMENT_ACTIONS = 5
    LOW_ENGAGEMENT_ACTIONS = 1

    def __init__(self):
        self.cache_timeout = 3600  # 1 hour

    # -------------------------------------------------------------------------
    # Basic Retention Calculations
    # -------------------------------------------------------------------------

    def calculate_retention(
        self,
        start_date: date = None,
        end_date: date = None,
        days: int = 30
    ) -> RetentionMetrics:
        """
        Calculate retention metrics for a period.

        Args:
            start_date: Period start date
            end_date: Period end date
            days: Number of days (if dates not provided)

        Returns:
            RetentionMetrics with calculated values
        """
        try:
            from django.contrib.auth import get_user_model
            from coreapp.models_analytics import UserAnalytics

            User = get_user_model()

            # Set dates
            if end_date is None:
                end_date = timezone.now().date()
            if start_date is None:
                start_date = end_date - timedelta(days=days)

            # Users who existed at start of period
            total_users = User.objects.filter(
                date_joined__date__lt=start_date,
                is_active=True
            ).count()

            if total_users == 0:
                return RetentionMetrics(
                    period_start=start_date,
                    period_end=end_date,
                    total_users=0,
                    active_users=0,
                    retained_users=0,
                    churned_users=0,
                    retention_rate=0.0,
                    churn_rate=0.0
                )

            # Users who were active during the period
            active_user_ids = set(
                UserAnalytics.objects.filter(
                    date__range=[start_date, end_date],
                    user__date_joined__date__lt=start_date
                ).values_list('user_id', flat=True).distinct()
            )

            active_users = len(active_user_ids)
            retained_users = active_users
            churned_users = total_users - retained_users

            retention_rate = (retained_users / total_users) * 100
            churn_rate = (churned_users / total_users) * 100

            return RetentionMetrics(
                period_start=start_date,
                period_end=end_date,
                total_users=total_users,
                active_users=active_users,
                retained_users=retained_users,
                churned_users=churned_users,
                retention_rate=round(retention_rate, 2),
                churn_rate=round(churn_rate, 2)
            )

        except Exception as e:
            logger.error(f"Error calculating retention: {e}")
            return RetentionMetrics(
                period_start=start_date or timezone.now().date(),
                period_end=end_date or timezone.now().date(),
                total_users=0,
                active_users=0,
                retained_users=0,
                churned_users=0,
                retention_rate=0.0,
                churn_rate=0.0
            )

    def calculate_rolling_retention(
        self,
        days: int = 30,
        window_size: int = 7
    ) -> List[Dict]:
        """
        Calculate rolling retention over time.

        Args:
            days: Total days to analyze
            window_size: Size of rolling window

        Returns:
            List of retention data points
        """
        results = []
        end_date = timezone.now().date()

        for i in range(days - window_size + 1):
            window_end = end_date - timedelta(days=i)
            window_start = window_end - timedelta(days=window_size)

            metrics = self.calculate_retention(
                start_date=window_start,
                end_date=window_end
            )

            results.append({
                'date': window_end.isoformat(),
                'retention_rate': metrics.retention_rate,
                'active_users': metrics.active_users,
                'total_users': metrics.total_users,
            })

        results.reverse()  # Chronological order
        return results

    # -------------------------------------------------------------------------
    # Cohort Analysis
    # -------------------------------------------------------------------------

    def analyze_cohorts(
        self,
        months: int = 6,
        granularity: str = 'month'
    ) -> List[CohortData]:
        """
        Analyze user retention by signup cohort.

        Args:
            months: Number of months to analyze
            granularity: 'day', 'week', or 'month'

        Returns:
            List of CohortData objects
        """
        cache_key = f'retention:cohorts:{months}:{granularity}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            from django.contrib.auth import get_user_model
            from coreapp.models_analytics import UserAnalytics

            User = get_user_model()

            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=months * 30)

            # Get users grouped by signup period
            if granularity == 'month':
                trunc_func = TruncMonth
                periods = months
            elif granularity == 'week':
                trunc_func = TruncWeek
                periods = months * 4
            else:
                trunc_func = TruncDate
                periods = months * 30

            # Get signup cohorts
            cohort_users = User.objects.filter(
                date_joined__date__gte=start_date,
                is_active=True
            ).annotate(
                cohort=trunc_func('date_joined')
            ).values('cohort').annotate(
                size=Count('id')
            ).order_by('cohort')

            cohorts = []

            for cohort_info in cohort_users:
                cohort_date = cohort_info['cohort'].date() if hasattr(
                    cohort_info['cohort'], 'date'
                ) else cohort_info['cohort']

                cohort_size = cohort_info['size']

                # Calculate retention for each subsequent period
                retention_by_period = {}

                for period_num in range(periods):
                    period_start = cohort_date + timedelta(
                        days=period_num * (30 if granularity == 'month' else 7 if granularity == 'week' else 1)
                    )
                    period_end = period_start + timedelta(
                        days=30 if granularity == 'month' else 7 if granularity == 'week' else 1
                    )

                    if period_start > end_date:
                        break

                    # Count users from this cohort who were active in this period
                    active_count = UserAnalytics.objects.filter(
                        user__date_joined__date__gte=cohort_date,
                        user__date_joined__date__lt=cohort_date + timedelta(
                            days=30 if granularity == 'month' else 7 if granularity == 'week' else 1
                        ),
                        date__gte=period_start,
                        date__lt=period_end
                    ).values('user_id').distinct().count()

                    retention_rate = (active_count / cohort_size * 100) if cohort_size > 0 else 0
                    retention_by_period[period_num] = round(retention_rate, 2)

                cohorts.append(CohortData(
                    cohort_date=cohort_date,
                    cohort_size=cohort_size,
                    retention_by_period=retention_by_period
                ))

            cache.set(cache_key, cohorts, self.cache_timeout)
            return cohorts

        except Exception as e:
            logger.error(f"Error analyzing cohorts: {e}")
            return []

    def get_cohort_matrix(self, months: int = 6) -> Dict:
        """
        Generate a cohort retention matrix for visualization.

        Args:
            months: Number of months to include

        Returns:
            Matrix data suitable for heatmap visualization
        """
        cohorts = self.analyze_cohorts(months=months)

        if not cohorts:
            return {'cohorts': [], 'matrix': [], 'periods': []}

        # Build matrix
        matrix = []
        cohort_labels = []
        max_periods = max(len(c.retention_by_period) for c in cohorts) if cohorts else 0

        for cohort in cohorts:
            cohort_labels.append(cohort.cohort_date.strftime('%Y-%m'))
            row = [
                cohort.retention_by_period.get(i, None)
                for i in range(max_periods)
            ]
            matrix.append(row)

        period_labels = [f'Period {i}' for i in range(max_periods)]

        return {
            'cohorts': cohort_labels,
            'matrix': matrix,
            'periods': period_labels,
            'cohort_sizes': [c.cohort_size for c in cohorts],
        }

    # -------------------------------------------------------------------------
    # Engagement Scoring
    # -------------------------------------------------------------------------

    def calculate_engagement_score(self, user) -> UserEngagementScore:
        """
        Calculate engagement score for a user.

        Args:
            user: User object

        Returns:
            UserEngagementScore with score and breakdown
        """
        try:
            from coreapp.models_analytics import UserAnalytics
            from coreapp.models import ContentGen

            # Time windows
            last_7_days = timezone.now().date() - timedelta(days=7)
            last_30_days = timezone.now().date() - timedelta(days=30)

            # Get activity data
            recent_analytics = UserAnalytics.objects.filter(
                user=user,
                date__gte=last_7_days
            ).aggregate(
                total_sessions=Sum('sessions'),
                total_generations=Sum('ai_text_generations'),
                total_tokens=Sum('ai_tokens_used'),
                avg_session_duration=Avg('avg_session_duration')
            )

            monthly_analytics = UserAnalytics.objects.filter(
                user=user,
                date__gte=last_30_days
            ).aggregate(
                total_sessions=Sum('sessions'),
                active_days=Count('date', distinct=True)
            )

            # Content activity
            content_count = ContentGen.objects.filter(
                user=user,
                created_at__date__gte=last_30_days,
                is_delete=False
            ).count()

            # Calculate factor scores (0-100 scale)
            factors = {}

            # Recency factor - days since last activity
            last_activity = UserAnalytics.objects.filter(user=user).order_by('-date').first()
            if last_activity:
                days_since_active = (timezone.now().date() - last_activity.date).days
                factors['recency'] = max(0, 100 - (days_since_active * 10))
            else:
                factors['recency'] = 0

            # Frequency factor - sessions in last 7 days
            sessions = recent_analytics.get('total_sessions') or 0
            factors['frequency'] = min(100, sessions * 15)

            # Activity depth - generations per session
            generations = recent_analytics.get('total_generations') or 0
            if sessions > 0:
                factors['depth'] = min(100, (generations / sessions) * 20)
            else:
                factors['depth'] = 0

            # Consistency - active days in last 30 days
            active_days = monthly_analytics.get('active_days') or 0
            factors['consistency'] = min(100, (active_days / 30) * 100)

            # Content creation
            factors['content'] = min(100, content_count * 10)

            # Calculate weighted score
            weights = {
                'recency': 0.30,
                'frequency': 0.25,
                'depth': 0.20,
                'consistency': 0.15,
                'content': 0.10,
            }

            score = sum(factors[k] * weights[k] for k in factors)

            # Determine engagement level
            if score >= 70:
                level = 'high'
            elif score >= 40:
                level = 'medium'
            elif score >= 20:
                level = 'low'
            else:
                level = 'at_risk'

            return UserEngagementScore(
                user_id=user.id,
                score=round(score, 2),
                level=level,
                factors=factors
            )

        except Exception as e:
            logger.error(f"Error calculating engagement score: {e}")
            return UserEngagementScore(
                user_id=user.id,
                score=0,
                level='unknown',
                factors={}
            )

    # -------------------------------------------------------------------------
    # Churn Prediction
    # -------------------------------------------------------------------------

    def predict_churn_risk(self, user) -> Dict:
        """
        Predict churn risk for a user.

        Args:
            user: User object

        Returns:
            Churn risk assessment
        """
        try:
            engagement = self.calculate_engagement_score(user)

            # Risk indicators
            indicators = []
            risk_score = 0

            # Low engagement
            if engagement.level in ['low', 'at_risk']:
                indicators.append('Low engagement score')
                risk_score += 30

            # Recency check
            if engagement.factors.get('recency', 0) < 30:
                indicators.append('No recent activity')
                risk_score += 25

            # Declining frequency
            if engagement.factors.get('frequency', 0) < 20:
                indicators.append('Low session frequency')
                risk_score += 20

            # Low consistency
            if engagement.factors.get('consistency', 0) < 20:
                indicators.append('Inconsistent usage')
                risk_score += 15

            # Check subscription status
            try:
                from planandsubscription.models import Subscription

                subscription = Subscription.objects.filter(
                    user=user,
                    status='active'
                ).first()

                if subscription:
                    # Check if subscription is expiring soon
                    if subscription.end_date:
                        days_until_expiry = (subscription.end_date - timezone.now()).days
                        if days_until_expiry < 7:
                            indicators.append('Subscription expiring soon')
                            risk_score += 10
            except Exception:
                pass

            # Determine risk level
            if risk_score >= 70:
                risk_level = 'critical'
            elif risk_score >= 50:
                risk_level = 'high'
            elif risk_score >= 30:
                risk_level = 'medium'
            else:
                risk_level = 'low'

            return {
                'user_id': user.id,
                'risk_score': min(100, risk_score),
                'risk_level': risk_level,
                'indicators': indicators,
                'engagement_score': engagement.score,
                'recommendations': self._get_retention_recommendations(risk_level, indicators)
            }

        except Exception as e:
            logger.error(f"Error predicting churn risk: {e}")
            return {
                'user_id': user.id,
                'risk_score': 0,
                'risk_level': 'unknown',
                'indicators': [],
                'engagement_score': 0,
                'recommendations': []
            }

    def _get_retention_recommendations(
        self,
        risk_level: str,
        indicators: List[str]
    ) -> List[Dict]:
        """Generate retention recommendations based on risk indicators."""
        recommendations = []

        if 'No recent activity' in indicators:
            recommendations.append({
                'action': 'reactivation_email',
                'description': 'Send re-engagement email with personalized content',
                'priority': 'high'
            })

        if 'Low session frequency' in indicators:
            recommendations.append({
                'action': 'usage_tips',
                'description': 'Share tips and use cases to drive engagement',
                'priority': 'medium'
            })

        if 'Subscription expiring soon' in indicators:
            recommendations.append({
                'action': 'renewal_reminder',
                'description': 'Send renewal reminder with incentive offer',
                'priority': 'high'
            })

        if risk_level == 'critical':
            recommendations.append({
                'action': 'personal_outreach',
                'description': 'Personal outreach from success team',
                'priority': 'urgent'
            })

        return recommendations

    def get_at_risk_users(self, limit: int = 100) -> List[Dict]:
        """
        Get list of users at risk of churning.

        Args:
            limit: Maximum users to return

        Returns:
            List of at-risk users with risk details
        """
        try:
            from django.contrib.auth import get_user_model
            from coreapp.models_analytics import UserAnalytics

            User = get_user_model()

            # Find users with declining engagement
            # Users active in past but not recently
            past_active = UserAnalytics.objects.filter(
                date__gte=timezone.now().date() - timedelta(days=60),
                date__lt=timezone.now().date() - timedelta(days=14)
            ).values_list('user_id', flat=True).distinct()

            recently_active = UserAnalytics.objects.filter(
                date__gte=timezone.now().date() - timedelta(days=14)
            ).values_list('user_id', flat=True).distinct()

            # Users who were active but aren't anymore
            at_risk_ids = set(past_active) - set(recently_active)

            # Limit and analyze
            at_risk_users = []
            for user_id in list(at_risk_ids)[:limit]:
                try:
                    user = User.objects.get(id=user_id)
                    risk_data = self.predict_churn_risk(user)
                    risk_data['email'] = user.email
                    risk_data['username'] = user.username if hasattr(user, 'username') else None
                    at_risk_users.append(risk_data)
                except User.DoesNotExist:
                    continue

            # Sort by risk score
            at_risk_users.sort(key=lambda x: x['risk_score'], reverse=True)

            return at_risk_users

        except Exception as e:
            logger.error(f"Error getting at-risk users: {e}")
            return []


# =============================================================================
# Retention Analytics Service
# =============================================================================

class RetentionService:
    """
    High-level service for retention analytics.

    Usage:
        service = RetentionService()
        dashboard = service.get_retention_dashboard()
        report = service.generate_retention_report()
    """

    def __init__(self):
        self.calculator = RetentionCalculator()

    def get_retention_dashboard(self) -> Dict:
        """
        Get comprehensive retention dashboard data.

        Returns:
            Dashboard data with all retention metrics
        """
        cache_key = 'retention:dashboard'
        cached = cache.get(cache_key)
        if cached:
            return cached

        data = {
            'current_metrics': self._get_current_metrics(),
            'trends': self._get_trends(),
            'cohort_matrix': self.calculator.get_cohort_matrix(months=6),
            'at_risk_count': len(self.calculator.get_at_risk_users(limit=1000)),
            'generated_at': timezone.now().isoformat(),
        }

        cache.set(cache_key, data, 1800)  # 30 minutes
        return data

    def _get_current_metrics(self) -> Dict:
        """Get current retention metrics."""
        daily = self.calculator.calculate_retention(days=1)
        weekly = self.calculator.calculate_retention(days=7)
        monthly = self.calculator.calculate_retention(days=30)

        return {
            'daily': {
                'retention_rate': daily.retention_rate,
                'churn_rate': daily.churn_rate,
                'active_users': daily.active_users,
            },
            'weekly': {
                'retention_rate': weekly.retention_rate,
                'churn_rate': weekly.churn_rate,
                'active_users': weekly.active_users,
            },
            'monthly': {
                'retention_rate': monthly.retention_rate,
                'churn_rate': monthly.churn_rate,
                'active_users': monthly.active_users,
            },
        }

    def _get_trends(self) -> Dict:
        """Get retention trends over time."""
        return {
            'rolling_7d': self.calculator.calculate_rolling_retention(days=30, window_size=7),
            'rolling_30d': self.calculator.calculate_rolling_retention(days=90, window_size=30),
        }

    def generate_retention_report(self, period: str = 'monthly') -> Dict:
        """
        Generate a retention report.

        Args:
            period: 'daily', 'weekly', or 'monthly'

        Returns:
            Detailed retention report
        """
        days_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
        days = days_map.get(period, 30)

        metrics = self.calculator.calculate_retention(days=days)
        cohorts = self.calculator.analyze_cohorts(months=3)
        at_risk = self.calculator.get_at_risk_users(limit=50)

        # Calculate period-over-period change
        previous_metrics = self.calculator.calculate_retention(
            end_date=timezone.now().date() - timedelta(days=days),
            days=days
        )

        retention_change = metrics.retention_rate - previous_metrics.retention_rate

        return {
            'period': period,
            'period_start': metrics.period_start.isoformat(),
            'period_end': metrics.period_end.isoformat(),
            'metrics': {
                'total_users': metrics.total_users,
                'active_users': metrics.active_users,
                'retained_users': metrics.retained_users,
                'churned_users': metrics.churned_users,
                'retention_rate': metrics.retention_rate,
                'churn_rate': metrics.churn_rate,
            },
            'comparison': {
                'retention_change': round(retention_change, 2),
                'trend': 'up' if retention_change > 0 else 'down' if retention_change < 0 else 'stable',
            },
            'cohort_summary': {
                'total_cohorts': len(cohorts),
                'avg_retention_period_1': (
                    sum(c.retention_by_period.get(1, 0) for c in cohorts) / len(cohorts)
                    if cohorts else 0
                ),
            },
            'at_risk_users': {
                'count': len(at_risk),
                'critical': len([u for u in at_risk if u['risk_level'] == 'critical']),
                'high': len([u for u in at_risk if u['risk_level'] == 'high']),
            },
            'generated_at': timezone.now().isoformat(),
        }


# =============================================================================
# Singleton Instances
# =============================================================================

retention_calculator = RetentionCalculator()
retention_service = RetentionService()
