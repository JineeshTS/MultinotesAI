"""
Optimal Plan Recommender for MultinotesAI.

This module provides:
- Subscription plan recommendations based on usage
- Cost optimization suggestions
- Upgrade/downgrade recommendations
- Usage-to-plan matching

WBS Item: 4.4.6 - Implement optimal plan recommender
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from django.conf import settings
from django.db.models import Sum, Count, F, Avg
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Plan Configuration
# =============================================================================

# Default plan tiers (can be overridden from database)
DEFAULT_PLANS = {
    'free': {
        'name': 'Free',
        'price_monthly': Decimal('0'),
        'tokens_per_month': 10000,
        'storage_gb': 1,
        'models_access': ['basic'],
        'features': ['basic_generation', 'basic_export'],
        'priority': 1,
    },
    'starter': {
        'name': 'Starter',
        'price_monthly': Decimal('9.99'),
        'tokens_per_month': 100000,
        'storage_gb': 10,
        'models_access': ['basic', 'standard'],
        'features': ['basic_generation', 'basic_export', 'templates'],
        'priority': 2,
    },
    'professional': {
        'name': 'Professional',
        'price_monthly': Decimal('29.99'),
        'tokens_per_month': 500000,
        'storage_gb': 50,
        'models_access': ['basic', 'standard', 'advanced'],
        'features': ['basic_generation', 'basic_export', 'templates', 'api_access', 'priority_support'],
        'priority': 3,
    },
    'business': {
        'name': 'Business',
        'price_monthly': Decimal('99.99'),
        'tokens_per_month': 2000000,
        'storage_gb': 200,
        'models_access': ['basic', 'standard', 'advanced', 'premium'],
        'features': ['basic_generation', 'basic_export', 'templates', 'api_access', 'priority_support', 'team_features', 'analytics'],
        'priority': 4,
    },
    'enterprise': {
        'name': 'Enterprise',
        'price_monthly': Decimal('299.99'),
        'tokens_per_month': 10000000,
        'storage_gb': 1000,
        'models_access': ['all'],
        'features': ['all'],
        'priority': 5,
    },
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PlanRecommendation:
    """A plan recommendation."""
    plan_id: str
    plan_name: str
    reason: str
    confidence: float
    monthly_cost: Decimal
    estimated_savings: Optional[Decimal] = None
    features_gained: List[str] = None
    features_lost: List[str] = None

    def __post_init__(self):
        if self.features_gained is None:
            self.features_gained = []
        if self.features_lost is None:
            self.features_lost = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'plan_id': self.plan_id,
            'plan_name': self.plan_name,
            'reason': self.reason,
            'confidence': round(self.confidence, 2),
            'monthly_cost': float(self.monthly_cost),
            'estimated_savings': float(self.estimated_savings) if self.estimated_savings else None,
            'features_gained': self.features_gained,
            'features_lost': self.features_lost,
        }


@dataclass
class UsageAnalysis:
    """Analysis of user's usage for plan recommendation."""
    avg_monthly_tokens: int
    peak_monthly_tokens: int
    avg_daily_prompts: float
    storage_used_gb: float
    models_used: List[str]
    features_used: List[str]
    growth_rate: float  # Monthly growth rate
    usage_consistency: float  # 0-1, how consistent usage is

    def to_dict(self) -> Dict[str, Any]:
        return {
            'avg_monthly_tokens': self.avg_monthly_tokens,
            'peak_monthly_tokens': self.peak_monthly_tokens,
            'avg_daily_prompts': round(self.avg_daily_prompts, 2),
            'storage_used_gb': round(self.storage_used_gb, 2),
            'models_used': self.models_used,
            'features_used': self.features_used,
            'growth_rate': round(self.growth_rate, 3),
            'usage_consistency': round(self.usage_consistency, 2),
        }


# =============================================================================
# Plan Recommender
# =============================================================================

class PlanRecommender:
    """
    Recommend optimal subscription plans based on usage.

    Usage:
        recommender = PlanRecommender()
        recommendation = recommender.get_recommendation(user_id=123)
    """

    def __init__(self):
        self.plans = self._load_plans()

    def _load_plans(self) -> Dict[str, Dict]:
        """Load plans from database or use defaults."""
        try:
            from subscriptions.models import Plan

            db_plans = {}
            for plan in Plan.objects.filter(is_active=True):
                db_plans[plan.slug] = {
                    'name': plan.name,
                    'price_monthly': plan.price,
                    'tokens_per_month': plan.tokens_limit,
                    'storage_gb': plan.storage_limit / (1024 * 1024 * 1024),  # Convert to GB
                    'models_access': plan.allowed_models or ['basic'],
                    'features': plan.features or [],
                    'priority': plan.priority or 1,
                }

            if db_plans:
                return db_plans

        except Exception as e:
            logger.debug(f"Could not load plans from database: {e}")

        return DEFAULT_PLANS

    def get_recommendation(
        self,
        user_id: int,
        include_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Get plan recommendation for a user.

        Args:
            user_id: User ID
            include_analysis: Whether to include detailed analysis

        Returns:
            Dict with recommendation and optional analysis
        """
        # Analyze user's usage
        analysis = self._analyze_usage(user_id)

        # Get current plan
        current_plan = self._get_current_plan(user_id)

        # Generate recommendations
        recommendations = self._generate_recommendations(analysis, current_plan)

        result = {
            'current_plan': current_plan,
            'recommendations': [r.to_dict() for r in recommendations],
            'primary_recommendation': recommendations[0].to_dict() if recommendations else None,
        }

        if include_analysis:
            result['analysis'] = analysis.to_dict()

        return result

    def get_cost_analysis(
        self,
        user_id: int,
        months: int = 3
    ) -> Dict[str, Any]:
        """
        Get cost analysis comparing current plan to optimal.

        Args:
            user_id: User ID
            months: Months to project

        Returns:
            Cost analysis data
        """
        analysis = self._analyze_usage(user_id)
        current_plan = self._get_current_plan(user_id)
        current_plan_data = self.plans.get(current_plan, self.plans['free'])

        # Find optimal plan
        optimal_plan = self._find_optimal_plan(analysis)
        optimal_plan_data = self.plans.get(optimal_plan, self.plans['free'])

        current_monthly = current_plan_data['price_monthly']
        optimal_monthly = optimal_plan_data['price_monthly']

        monthly_savings = current_monthly - optimal_monthly
        projected_savings = monthly_savings * months

        # Check if current plan is sufficient
        is_sufficient = self._plan_meets_needs(current_plan_data, analysis)

        # Calculate utilization
        token_utilization = min(
            analysis.avg_monthly_tokens / max(current_plan_data['tokens_per_month'], 1),
            1.0
        )

        return {
            'current_plan': {
                'name': current_plan_data['name'],
                'monthly_cost': float(current_monthly),
                'tokens_included': current_plan_data['tokens_per_month'],
            },
            'optimal_plan': {
                'name': optimal_plan_data['name'],
                'monthly_cost': float(optimal_monthly),
                'tokens_included': optimal_plan_data['tokens_per_month'],
            },
            'analysis': {
                'is_current_sufficient': is_sufficient,
                'token_utilization': round(token_utilization * 100, 1),
                'monthly_savings': float(monthly_savings),
                'projected_savings_months': months,
                'projected_savings': float(projected_savings),
            },
            'recommendation': 'upgrade' if not is_sufficient else (
                'downgrade' if monthly_savings > 0 else 'keep'
            ),
        }

    def get_upgrade_benefits(
        self,
        user_id: int,
        target_plan: str
    ) -> Dict[str, Any]:
        """
        Get benefits of upgrading to a specific plan.

        Args:
            user_id: User ID
            target_plan: Target plan ID

        Returns:
            Benefits analysis
        """
        current_plan = self._get_current_plan(user_id)
        current_plan_data = self.plans.get(current_plan, self.plans['free'])
        target_plan_data = self.plans.get(target_plan)

        if not target_plan_data:
            return {'error': 'Invalid target plan'}

        # Calculate differences
        token_increase = target_plan_data['tokens_per_month'] - current_plan_data['tokens_per_month']
        storage_increase = target_plan_data['storage_gb'] - current_plan_data['storage_gb']
        price_increase = target_plan_data['price_monthly'] - current_plan_data['price_monthly']

        # Find new features
        current_features = set(current_plan_data.get('features', []))
        target_features = set(target_plan_data.get('features', []))
        new_features = list(target_features - current_features)

        # Find new models
        current_models = set(current_plan_data.get('models_access', []))
        target_models = set(target_plan_data.get('models_access', []))
        new_models = list(target_models - current_models)

        # Calculate value
        cost_per_token_current = (
            float(current_plan_data['price_monthly']) / max(current_plan_data['tokens_per_month'], 1)
        )
        cost_per_token_target = (
            float(target_plan_data['price_monthly']) / max(target_plan_data['tokens_per_month'], 1)
        )

        return {
            'current_plan': current_plan_data['name'],
            'target_plan': target_plan_data['name'],
            'benefits': {
                'additional_tokens': token_increase,
                'additional_storage_gb': storage_increase,
                'new_features': new_features,
                'new_models': new_models,
            },
            'cost': {
                'price_increase': float(price_increase),
                'cost_per_token_current': round(cost_per_token_current * 1000, 4),  # Per 1000 tokens
                'cost_per_token_target': round(cost_per_token_target * 1000, 4),
                'value_improvement': round(
                    (cost_per_token_current - cost_per_token_target) / max(cost_per_token_current, 0.0001) * 100, 1
                ),
            },
            'is_upgrade': target_plan_data['priority'] > current_plan_data['priority'],
        }

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    def _analyze_usage(self, user_id: int) -> UsageAnalysis:
        """Analyze user's usage patterns."""
        from coreapp.models import Prompt, PromptResponse, Document, LLM_Tokens

        now = timezone.now()
        three_months_ago = now - timedelta(days=90)
        one_month_ago = now - timedelta(days=30)

        # Get token usage
        token_data = LLM_Tokens.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=three_months_ago
        ).values('created_at__month').annotate(
            total=Sum(F('text_token_used') + F('file_token_used'))
        )

        monthly_tokens = [d['total'] or 0 for d in token_data]
        avg_monthly_tokens = int(sum(monthly_tokens) / max(len(monthly_tokens), 1))
        peak_monthly_tokens = max(monthly_tokens) if monthly_tokens else 0

        # Get daily prompts
        recent_prompts = Prompt.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=one_month_ago
        ).count()
        avg_daily_prompts = recent_prompts / 30

        # Get storage used
        storage_data = Document.objects.filter(
            user_id=user_id,
            is_delete=False
        ).aggregate(total_size=Sum('file_size'))
        storage_used_gb = (storage_data['total_size'] or 0) / (1024 * 1024 * 1024)

        # Get models used
        models_used = list(
            PromptResponse.objects.filter(
                prompt__user_id=user_id,
                is_delete=False,
                created_at__gte=three_months_ago
            ).values_list('llm__name', flat=True).distinct()
        )

        # Determine features used (simplified)
        features_used = ['basic_generation']
        if Document.objects.filter(user_id=user_id, is_delete=False).exists():
            features_used.append('document_storage')

        # Calculate growth rate
        if len(monthly_tokens) >= 2:
            first_month = monthly_tokens[0] or 1
            last_month = monthly_tokens[-1] or 0
            growth_rate = (last_month - first_month) / first_month
        else:
            growth_rate = 0

        # Calculate consistency
        if monthly_tokens and len(monthly_tokens) > 1:
            avg = sum(monthly_tokens) / len(monthly_tokens)
            variance = sum((x - avg) ** 2 for x in monthly_tokens) / len(monthly_tokens)
            std_dev = variance ** 0.5
            usage_consistency = max(0, 1 - (std_dev / max(avg, 1)))
        else:
            usage_consistency = 0.5

        return UsageAnalysis(
            avg_monthly_tokens=avg_monthly_tokens,
            peak_monthly_tokens=peak_monthly_tokens,
            avg_daily_prompts=avg_daily_prompts,
            storage_used_gb=storage_used_gb,
            models_used=models_used,
            features_used=features_used,
            growth_rate=growth_rate,
            usage_consistency=usage_consistency,
        )

    def _get_current_plan(self, user_id: int) -> str:
        """Get user's current plan."""
        try:
            from subscriptions.models import Subscription

            subscription = Subscription.objects.filter(
                user_id=user_id,
                status='active'
            ).select_related('plan').first()

            if subscription and subscription.plan:
                return subscription.plan.slug

        except Exception as e:
            logger.debug(f"Could not get current plan: {e}")

        return 'free'

    def _generate_recommendations(
        self,
        analysis: UsageAnalysis,
        current_plan: str
    ) -> List[PlanRecommendation]:
        """Generate plan recommendations."""
        recommendations = []
        current_plan_data = self.plans.get(current_plan, self.plans['free'])

        # Check each plan
        for plan_id, plan_data in self.plans.items():
            if plan_id == current_plan:
                continue

            recommendation = self._evaluate_plan(
                plan_id, plan_data, analysis, current_plan_data
            )
            if recommendation:
                recommendations.append(recommendation)

        # Sort by confidence
        recommendations.sort(key=lambda r: r.confidence, reverse=True)

        return recommendations

    def _evaluate_plan(
        self,
        plan_id: str,
        plan_data: Dict,
        analysis: UsageAnalysis,
        current_plan_data: Dict
    ) -> Optional[PlanRecommendation]:
        """Evaluate if a plan is a good recommendation."""
        confidence = 0.0
        reasons = []

        # Project future usage with growth
        projected_tokens = int(analysis.avg_monthly_tokens * (1 + max(analysis.growth_rate, 0)))

        # Check token sufficiency
        plan_tokens = plan_data['tokens_per_month']
        current_tokens = current_plan_data['tokens_per_month']

        # If user is near or over current limit
        if analysis.avg_monthly_tokens > current_tokens * 0.8:
            if plan_tokens > current_tokens:
                confidence += 0.3
                reasons.append('More tokens for growing usage')

        # If user is underutilizing
        if analysis.avg_monthly_tokens < current_tokens * 0.3:
            if plan_tokens < current_tokens and plan_tokens >= projected_tokens:
                confidence += 0.3
                reasons.append('Right-sized for actual usage')

        # Check if plan matches projected needs
        if plan_tokens >= projected_tokens and plan_tokens < projected_tokens * 3:
            confidence += 0.2
            reasons.append('Matches projected needs')

        # Check storage
        if analysis.storage_used_gb > current_plan_data['storage_gb'] * 0.8:
            if plan_data['storage_gb'] > current_plan_data['storage_gb']:
                confidence += 0.1
                reasons.append('More storage space')

        # Calculate savings
        savings = current_plan_data['price_monthly'] - plan_data['price_monthly']
        if savings > 0:
            confidence += 0.2
            reasons.append(f'Save ${float(savings):.2f}/month')

        # Only recommend if confidence is meaningful
        if confidence < 0.3:
            return None

        # Determine features gained/lost
        current_features = set(current_plan_data.get('features', []))
        new_features = set(plan_data.get('features', []))
        features_gained = list(new_features - current_features)
        features_lost = list(current_features - new_features)

        return PlanRecommendation(
            plan_id=plan_id,
            plan_name=plan_data['name'],
            reason='; '.join(reasons),
            confidence=min(confidence, 0.95),
            monthly_cost=plan_data['price_monthly'],
            estimated_savings=savings if savings > 0 else None,
            features_gained=features_gained,
            features_lost=features_lost,
        )

    def _find_optimal_plan(self, analysis: UsageAnalysis) -> str:
        """Find the optimal plan for given usage."""
        projected_tokens = int(analysis.avg_monthly_tokens * (1 + max(analysis.growth_rate, 0)))

        best_plan = 'free'
        best_score = float('inf')

        for plan_id, plan_data in self.plans.items():
            # Skip if insufficient tokens
            if plan_data['tokens_per_month'] < projected_tokens:
                continue

            # Skip if insufficient storage
            if plan_data['storage_gb'] < analysis.storage_used_gb * 1.2:
                continue

            # Score: prefer cheaper plans that meet needs
            score = float(plan_data['price_monthly'])

            # Penalize overprovisioning
            overprovision_ratio = plan_data['tokens_per_month'] / max(projected_tokens, 1)
            if overprovision_ratio > 3:
                score += 10 * (overprovision_ratio - 3)

            if score < best_score:
                best_score = score
                best_plan = plan_id

        return best_plan

    def _plan_meets_needs(self, plan_data: Dict, analysis: UsageAnalysis) -> bool:
        """Check if plan meets user's needs."""
        projected_tokens = int(analysis.avg_monthly_tokens * (1 + max(analysis.growth_rate, 0)))

        if plan_data['tokens_per_month'] < projected_tokens:
            return False

        if plan_data['storage_gb'] < analysis.storage_used_gb * 1.1:
            return False

        return True


# =============================================================================
# Singleton Instance
# =============================================================================

plan_recommender = PlanRecommender()
