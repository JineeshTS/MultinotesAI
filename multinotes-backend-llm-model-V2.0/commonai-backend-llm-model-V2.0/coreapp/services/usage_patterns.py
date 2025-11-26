"""
Usage Pattern Analyzer for MultinotesAI.

This module provides:
- User behavior analysis
- Usage pattern detection
- Peak usage time identification
- Feature usage tracking
- Anomaly detection

WBS Item: 4.4.5 - Build usage pattern analyzer
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from django.conf import settings
from django.db.models import Count, Sum, Avg, F, Q
from django.db.models.functions import TruncHour, TruncDay, TruncWeek, ExtractHour, ExtractWeekDay
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class UsageMetric(Enum):
    """Types of usage metrics."""
    PROMPTS = 'prompts'
    TOKENS = 'tokens'
    DOCUMENTS = 'documents'
    SESSIONS = 'sessions'
    API_CALLS = 'api_calls'


class TimeGranularity(Enum):
    """Time granularity for analysis."""
    HOURLY = 'hourly'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class UsagePattern:
    """Represents a detected usage pattern."""
    pattern_type: str
    description: str
    confidence: float
    data: Dict[str, Any]
    recommendation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pattern_type': self.pattern_type,
            'description': self.description,
            'confidence': round(self.confidence, 2),
            'data': self.data,
            'recommendation': self.recommendation,
        }


@dataclass
class UsageSummary:
    """Summary of user usage."""
    total_prompts: int
    total_tokens: int
    total_documents: int
    avg_prompts_per_day: float
    avg_tokens_per_prompt: float
    most_active_hour: int
    most_active_day: int
    favorite_models: List[Dict[str, Any]]
    patterns: List[UsagePattern]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_prompts': self.total_prompts,
            'total_tokens': self.total_tokens,
            'total_documents': self.total_documents,
            'avg_prompts_per_day': round(self.avg_prompts_per_day, 2),
            'avg_tokens_per_prompt': round(self.avg_tokens_per_prompt, 2),
            'most_active_hour': self.most_active_hour,
            'most_active_day': self.most_active_day,
            'favorite_models': self.favorite_models,
            'patterns': [p.to_dict() for p in self.patterns],
        }


# =============================================================================
# Usage Pattern Analyzer
# =============================================================================

class UsagePatternAnalyzer:
    """
    Analyze user usage patterns.

    Usage:
        analyzer = UsagePatternAnalyzer()
        summary = analyzer.get_user_summary(user_id=123, days=30)
        patterns = analyzer.detect_patterns(user_id=123)
    """

    DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    def __init__(self):
        self.min_data_points = 5

    def get_user_summary(
        self,
        user_id: int,
        days: int = 30
    ) -> UsageSummary:
        """
        Get comprehensive usage summary for a user.

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            UsageSummary object
        """
        from coreapp.models import Prompt, PromptResponse, Document, LLM_Tokens

        cutoff_date = timezone.now() - timedelta(days=days)

        # Get prompt stats
        prompts = Prompt.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        )

        total_prompts = prompts.count()

        # Get token usage
        token_data = LLM_Tokens.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        ).aggregate(
            total=Sum(F('text_token_used') + F('file_token_used'))
        )
        total_tokens = token_data['total'] or 0

        # Get document count
        total_documents = Document.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        ).count()

        # Calculate averages
        avg_prompts_per_day = total_prompts / max(days, 1)
        avg_tokens_per_prompt = total_tokens / max(total_prompts, 1)

        # Get peak times
        most_active_hour = self._get_most_active_hour(user_id, cutoff_date)
        most_active_day = self._get_most_active_day(user_id, cutoff_date)

        # Get favorite models
        favorite_models = self._get_favorite_models(user_id, cutoff_date)

        # Detect patterns
        patterns = self.detect_patterns(user_id, days)

        return UsageSummary(
            total_prompts=total_prompts,
            total_tokens=total_tokens,
            total_documents=total_documents,
            avg_prompts_per_day=avg_prompts_per_day,
            avg_tokens_per_prompt=avg_tokens_per_prompt,
            most_active_hour=most_active_hour,
            most_active_day=most_active_day,
            favorite_models=favorite_models,
            patterns=patterns,
        )

    def detect_patterns(
        self,
        user_id: int,
        days: int = 30
    ) -> List[UsagePattern]:
        """
        Detect usage patterns for a user.

        Args:
            user_id: User ID
            days: Days to analyze

        Returns:
            List of detected patterns
        """
        patterns = []

        cutoff_date = timezone.now() - timedelta(days=days)

        # Detect time-based patterns
        time_patterns = self._detect_time_patterns(user_id, cutoff_date)
        patterns.extend(time_patterns)

        # Detect model preference patterns
        model_patterns = self._detect_model_patterns(user_id, cutoff_date)
        patterns.extend(model_patterns)

        # Detect usage trend patterns
        trend_patterns = self._detect_trend_patterns(user_id, cutoff_date)
        patterns.extend(trend_patterns)

        # Detect session patterns
        session_patterns = self._detect_session_patterns(user_id, cutoff_date)
        patterns.extend(session_patterns)

        return patterns

    def get_hourly_distribution(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[int, int]:
        """
        Get usage distribution by hour of day.

        Args:
            user_id: User ID
            days: Days to analyze

        Returns:
            Dict mapping hour (0-23) to usage count
        """
        from coreapp.models import Prompt

        cutoff_date = timezone.now() - timedelta(days=days)

        hourly_data = Prompt.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        ).annotate(
            hour=ExtractHour('created_at')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')

        # Fill in all hours
        distribution = {h: 0 for h in range(24)}
        for item in hourly_data:
            distribution[item['hour']] = item['count']

        return distribution

    def get_daily_distribution(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, int]:
        """
        Get usage distribution by day of week.

        Args:
            user_id: User ID
            days: Days to analyze

        Returns:
            Dict mapping day name to usage count
        """
        from coreapp.models import Prompt

        cutoff_date = timezone.now() - timedelta(days=days)

        daily_data = Prompt.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        ).annotate(
            day=ExtractWeekDay('created_at')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')

        # Fill in all days (Django weekday: 1=Sunday, 7=Saturday)
        distribution = {day: 0 for day in self.DAY_NAMES}
        day_mapping = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday',
                       5: 'Thursday', 6: 'Friday', 7: 'Saturday'}

        for item in daily_data:
            day_name = day_mapping.get(item['day'], 'Unknown')
            distribution[day_name] = item['count']

        return distribution

    def get_usage_timeline(
        self,
        user_id: int,
        days: int = 30,
        granularity: TimeGranularity = TimeGranularity.DAILY
    ) -> List[Dict[str, Any]]:
        """
        Get usage over time.

        Args:
            user_id: User ID
            days: Days to analyze
            granularity: Time granularity

        Returns:
            List of time-series data points
        """
        from coreapp.models import Prompt

        cutoff_date = timezone.now() - timedelta(days=days)

        trunc_func = {
            TimeGranularity.HOURLY: TruncHour,
            TimeGranularity.DAILY: TruncDay,
            TimeGranularity.WEEKLY: TruncWeek,
        }.get(granularity, TruncDay)

        timeline_data = Prompt.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        ).annotate(
            period=trunc_func('created_at')
        ).values('period').annotate(
            prompt_count=Count('id')
        ).order_by('period')

        return [
            {
                'period': item['period'].isoformat() if item['period'] else None,
                'prompts': item['prompt_count'],
            }
            for item in timeline_data
        ]

    def get_model_usage(
        self,
        user_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get model usage breakdown.

        Args:
            user_id: User ID
            days: Days to analyze

        Returns:
            List of model usage data
        """
        from coreapp.models import PromptResponse

        cutoff_date = timezone.now() - timedelta(days=days)

        model_data = PromptResponse.objects.filter(
            prompt__user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        ).values(
            'llm__name', 'llm__id'
        ).annotate(
            usage_count=Count('id'),
            total_tokens=Sum('tokens_used')
        ).order_by('-usage_count')

        return [
            {
                'model_id': item['llm__id'],
                'model_name': item['llm__name'],
                'usage_count': item['usage_count'],
                'total_tokens': item['total_tokens'] or 0,
            }
            for item in model_data
        ]

    def compare_to_average(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Compare user's usage to platform average.

        Args:
            user_id: User ID
            days: Days to analyze

        Returns:
            Comparison data
        """
        from coreapp.models import Prompt, LLM_Tokens
        from authentication.models import CustomUser

        cutoff_date = timezone.now() - timedelta(days=days)

        # Get user stats
        user_prompts = Prompt.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        ).count()

        user_tokens = LLM_Tokens.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        ).aggregate(
            total=Sum(F('text_token_used') + F('file_token_used'))
        )['total'] or 0

        # Get platform averages
        active_users = CustomUser.objects.filter(
            prompt_creator__created_at__gte=cutoff_date
        ).distinct().count()

        total_prompts = Prompt.objects.filter(
            is_delete=False,
            created_at__gte=cutoff_date
        ).count()

        total_tokens = LLM_Tokens.objects.filter(
            is_delete=False,
            created_at__gte=cutoff_date
        ).aggregate(
            total=Sum(F('text_token_used') + F('file_token_used'))
        )['total'] or 0

        avg_prompts = total_prompts / max(active_users, 1)
        avg_tokens = total_tokens / max(active_users, 1)

        return {
            'user': {
                'prompts': user_prompts,
                'tokens': user_tokens,
            },
            'platform_average': {
                'prompts': round(avg_prompts, 1),
                'tokens': round(avg_tokens, 1),
            },
            'comparison': {
                'prompts_vs_avg': round((user_prompts / max(avg_prompts, 1)) * 100 - 100, 1),
                'tokens_vs_avg': round((user_tokens / max(avg_tokens, 1)) * 100 - 100, 1),
            },
            'percentile': self._calculate_percentile(user_id, user_prompts, cutoff_date),
        }

    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------

    def _get_most_active_hour(self, user_id: int, cutoff_date: datetime) -> int:
        """Get user's most active hour."""
        distribution = self.get_hourly_distribution(user_id, 30)
        if not distribution:
            return 12  # Default to noon

        return max(distribution, key=distribution.get)

    def _get_most_active_day(self, user_id: int, cutoff_date: datetime) -> int:
        """Get user's most active day of week."""
        distribution = self.get_daily_distribution(user_id, 30)
        if not distribution:
            return 1  # Default to Monday

        most_active = max(distribution, key=distribution.get)
        return self.DAY_NAMES.index(most_active)

    def _get_favorite_models(
        self,
        user_id: int,
        cutoff_date: datetime,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Get user's favorite models."""
        model_usage = self.get_model_usage(user_id, 30)
        return model_usage[:limit]

    def _detect_time_patterns(
        self,
        user_id: int,
        cutoff_date: datetime
    ) -> List[UsagePattern]:
        """Detect time-based usage patterns."""
        patterns = []

        hourly = self.get_hourly_distribution(user_id, 30)
        daily = self.get_daily_distribution(user_id, 30)

        total_usage = sum(hourly.values())
        if total_usage < self.min_data_points:
            return patterns

        # Check for morning person pattern
        morning_usage = sum(hourly.get(h, 0) for h in range(5, 12))
        if morning_usage > total_usage * 0.5:
            patterns.append(UsagePattern(
                pattern_type='time_preference',
                description='Morning person - most activity between 5 AM and noon',
                confidence=morning_usage / total_usage,
                data={'morning_usage_percent': round(morning_usage / total_usage * 100, 1)},
                recommendation='Consider scheduling complex tasks in the morning'
            ))

        # Check for night owl pattern
        night_usage = sum(hourly.get(h, 0) for h in range(20, 24)) + sum(hourly.get(h, 0) for h in range(0, 5))
        if night_usage > total_usage * 0.4:
            patterns.append(UsagePattern(
                pattern_type='time_preference',
                description='Night owl - significant activity during late hours',
                confidence=night_usage / total_usage,
                data={'night_usage_percent': round(night_usage / total_usage * 100, 1)},
                recommendation='Consider scheduled generation for off-peak hours'
            ))

        # Check for weekend warrior pattern
        weekend_usage = daily.get('Saturday', 0) + daily.get('Sunday', 0)
        weekday_usage = sum(daily.get(day, 0) for day in self.DAY_NAMES[:5])
        if weekend_usage > weekday_usage * 0.5 and weekend_usage > 0:
            patterns.append(UsagePattern(
                pattern_type='time_preference',
                description='Weekend warrior - higher activity on weekends',
                confidence=0.7,
                data={
                    'weekend_usage': weekend_usage,
                    'weekday_usage': weekday_usage,
                }
            ))

        return patterns

    def _detect_model_patterns(
        self,
        user_id: int,
        cutoff_date: datetime
    ) -> List[UsagePattern]:
        """Detect model preference patterns."""
        patterns = []

        model_usage = self.get_model_usage(user_id, 30)

        if len(model_usage) < 2:
            return patterns

        total_usage = sum(m['usage_count'] for m in model_usage)
        if total_usage < self.min_data_points:
            return patterns

        # Check for strong model preference
        if model_usage:
            top_model = model_usage[0]
            top_usage = top_model['usage_count']
            top_percent = top_usage / total_usage

            if top_percent > 0.7:
                patterns.append(UsagePattern(
                    pattern_type='model_preference',
                    description=f'Strong preference for {top_model["model_name"]}',
                    confidence=top_percent,
                    data={
                        'preferred_model': top_model['model_name'],
                        'usage_percent': round(top_percent * 100, 1),
                    },
                    recommendation='Consider exploring other models for specific tasks'
                ))

            # Check for multi-model user
            if len(model_usage) >= 3:
                top3_usage = sum(m['usage_count'] for m in model_usage[:3])
                if top3_usage / total_usage > 0.9:
                    patterns.append(UsagePattern(
                        pattern_type='model_diversity',
                        description='Uses multiple models effectively',
                        confidence=0.8,
                        data={
                            'models_used': len(model_usage),
                            'top_models': [m['model_name'] for m in model_usage[:3]],
                        }
                    ))

        return patterns

    def _detect_trend_patterns(
        self,
        user_id: int,
        cutoff_date: datetime
    ) -> List[UsagePattern]:
        """Detect usage trend patterns."""
        patterns = []

        timeline = self.get_usage_timeline(user_id, 30)

        if len(timeline) < 7:
            return patterns

        # Calculate trend
        counts = [t['prompts'] for t in timeline]
        first_half_avg = sum(counts[:len(counts)//2]) / max(len(counts)//2, 1)
        second_half_avg = sum(counts[len(counts)//2:]) / max(len(counts) - len(counts)//2, 1)

        if first_half_avg > 0:
            growth = (second_half_avg - first_half_avg) / first_half_avg

            if growth > 0.3:
                patterns.append(UsagePattern(
                    pattern_type='usage_trend',
                    description='Increasing usage trend',
                    confidence=min(0.5 + growth / 2, 0.95),
                    data={
                        'growth_rate': round(growth * 100, 1),
                        'first_half_avg': round(first_half_avg, 1),
                        'second_half_avg': round(second_half_avg, 1),
                    },
                    recommendation='Consider upgrading to a higher tier for better value'
                ))
            elif growth < -0.3:
                patterns.append(UsagePattern(
                    pattern_type='usage_trend',
                    description='Decreasing usage trend',
                    confidence=min(0.5 + abs(growth) / 2, 0.95),
                    data={
                        'decline_rate': round(abs(growth) * 100, 1),
                    },
                    recommendation='Check if you need help with any features'
                ))

        return patterns

    def _detect_session_patterns(
        self,
        user_id: int,
        cutoff_date: datetime
    ) -> List[UsagePattern]:
        """Detect session-based patterns."""
        from coreapp.models import Prompt

        patterns = []

        prompts = Prompt.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        ).order_by('created_at').values_list('created_at', flat=True)

        if len(prompts) < self.min_data_points:
            return patterns

        # Calculate session lengths (group prompts within 30 min)
        sessions = []
        current_session = []

        for prompt_time in prompts:
            if current_session and (prompt_time - current_session[-1]).total_seconds() > 1800:
                sessions.append(current_session)
                current_session = [prompt_time]
            else:
                current_session.append(prompt_time)

        if current_session:
            sessions.append(current_session)

        if len(sessions) >= 3:
            # Calculate average session length
            session_lengths = [
                (s[-1] - s[0]).total_seconds() / 60 for s in sessions if len(s) > 1
            ]

            if session_lengths:
                avg_length = sum(session_lengths) / len(session_lengths)
                prompts_per_session = sum(len(s) for s in sessions) / len(sessions)

                if avg_length > 30:
                    patterns.append(UsagePattern(
                        pattern_type='session_behavior',
                        description='Deep work sessions - extended usage periods',
                        confidence=0.7,
                        data={
                            'avg_session_minutes': round(avg_length, 1),
                            'avg_prompts_per_session': round(prompts_per_session, 1),
                            'total_sessions': len(sessions),
                        }
                    ))
                elif avg_length < 5:
                    patterns.append(UsagePattern(
                        pattern_type='session_behavior',
                        description='Quick query sessions - short focused interactions',
                        confidence=0.7,
                        data={
                            'avg_session_minutes': round(avg_length, 1),
                            'avg_prompts_per_session': round(prompts_per_session, 1),
                        }
                    ))

        return patterns

    def _calculate_percentile(
        self,
        user_id: int,
        user_prompts: int,
        cutoff_date: datetime
    ) -> int:
        """Calculate user's percentile among all users."""
        from coreapp.models import Prompt

        # Get all users' prompt counts
        user_counts = Prompt.objects.filter(
            is_delete=False,
            created_at__gte=cutoff_date
        ).values('user').annotate(
            count=Count('id')
        ).order_by('count')

        if not user_counts:
            return 50

        counts = [u['count'] for u in user_counts]
        position = sum(1 for c in counts if c <= user_prompts)
        percentile = int((position / len(counts)) * 100)

        return min(percentile, 99)


# =============================================================================
# Singleton Instance
# =============================================================================

usage_analyzer = UsagePatternAnalyzer()
