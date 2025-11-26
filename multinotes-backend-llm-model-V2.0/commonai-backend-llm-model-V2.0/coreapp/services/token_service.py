"""
Token Usage Prediction Service for MultinotesAI.

This module provides:
- Token usage estimation
- Cost prediction
- Usage forecasting
- Budget management
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncDate, TruncHour
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Token Configuration
# =============================================================================

@dataclass
class ModelPricing:
    """Pricing information for AI models."""
    model_id: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    currency: str = 'USD'


MODEL_PRICING = {
    'gpt-4': ModelPricing('gpt-4', 0.03, 0.06),
    'gpt-4-turbo': ModelPricing('gpt-4-turbo', 0.01, 0.03),
    'gpt-3.5-turbo': ModelPricing('gpt-3.5-turbo', 0.0005, 0.0015),
    'claude-3-opus': ModelPricing('claude-3-opus', 0.015, 0.075),
    'claude-3-sonnet': ModelPricing('claude-3-sonnet', 0.003, 0.015),
    'claude-3-haiku': ModelPricing('claude-3-haiku', 0.00025, 0.00125),
    'gemini-pro': ModelPricing('gemini-pro', 0.0005, 0.0015),
}


# =============================================================================
# Token Estimation
# =============================================================================

class TokenEstimator:
    """
    Estimate token counts for text.

    Uses approximation rules since actual tokenization
    varies by model. For accurate counts, use the model's
    actual tokenizer.
    """

    # Average characters per token (varies by language and content)
    CHARS_PER_TOKEN = 4

    # Adjustment factors by content type
    CONTENT_FACTORS = {
        'code': 0.9,  # Code tends to have more tokens per char
        'prose': 1.0,  # Normal text
        'technical': 0.95,  # Technical content
        'conversation': 1.05,  # Conversational tends to be efficient
    }

    def estimate_tokens(
        self,
        text: str,
        content_type: str = 'prose'
    ) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to estimate
            content_type: Type of content

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Base estimation
        char_count = len(text)
        base_tokens = char_count / self.CHARS_PER_TOKEN

        # Apply content type factor
        factor = self.CONTENT_FACTORS.get(content_type, 1.0)
        adjusted_tokens = base_tokens / factor

        # Account for whitespace and structure
        word_count = len(text.split())
        newline_count = text.count('\n')

        # Adjust for structure
        structure_tokens = (newline_count * 0.5) + (word_count * 0.1)

        return int(adjusted_tokens + structure_tokens)

    def estimate_response_tokens(
        self,
        prompt_tokens: int,
        task_type: str = 'general'
    ) -> int:
        """
        Estimate response token count based on prompt.

        Args:
            prompt_tokens: Number of prompt tokens
            task_type: Type of task

        Returns:
            Estimated response tokens
        """
        # Response length ratios by task type
        ratios = {
            'summarization': 0.3,
            'translation': 1.0,
            'code_generation': 1.5,
            'explanation': 1.2,
            'creative_writing': 2.0,
            'chat': 0.8,
            'general': 1.0,
        }

        ratio = ratios.get(task_type, 1.0)
        estimated = int(prompt_tokens * ratio)

        # Apply reasonable bounds
        min_tokens = 50
        max_tokens = 4000

        return max(min_tokens, min(estimated, max_tokens))


# =============================================================================
# Token Usage Service
# =============================================================================

class TokenUsageService:
    """
    Service for tracking and predicting token usage.

    Usage:
        service = TokenUsageService()
        estimate = service.estimate_cost(prompt_text, model='gpt-4')
        forecast = service.forecast_usage(user, days=30)
    """

    def __init__(self):
        self.estimator = TokenEstimator()
        self.pricing = MODEL_PRICING

    # -------------------------------------------------------------------------
    # Cost Estimation
    # -------------------------------------------------------------------------

    def estimate_cost(
        self,
        prompt: str,
        model: str = 'gpt-3.5-turbo',
        expected_output_tokens: int = None,
        content_type: str = 'prose'
    ) -> Dict:
        """
        Estimate cost for a generation.

        Args:
            prompt: Input prompt text
            model: Model to use
            expected_output_tokens: Expected output tokens (or auto-estimate)
            content_type: Type of content

        Returns:
            Cost estimation dict
        """
        # Get model pricing
        pricing = self.pricing.get(model)
        if not pricing:
            return {'error': f'Unknown model: {model}'}

        # Estimate input tokens
        input_tokens = self.estimator.estimate_tokens(prompt, content_type)

        # Estimate output tokens
        if expected_output_tokens is None:
            expected_output_tokens = self.estimator.estimate_response_tokens(
                input_tokens,
                task_type=self._detect_task_type(prompt)
            )

        # Calculate costs
        input_cost = (input_tokens / 1000) * pricing.input_cost_per_1k
        output_cost = (expected_output_tokens / 1000) * pricing.output_cost_per_1k
        total_cost = input_cost + output_cost

        return {
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': expected_output_tokens,
            'total_tokens': input_tokens + expected_output_tokens,
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(total_cost, 6),
            'currency': pricing.currency,
        }

    def compare_models(
        self,
        prompt: str,
        models: List[str] = None
    ) -> List[Dict]:
        """
        Compare costs across different models.

        Args:
            prompt: Input prompt
            models: Models to compare (default: all)

        Returns:
            List of cost estimates sorted by cost
        """
        models = models or list(self.pricing.keys())

        estimates = []
        for model in models:
            estimate = self.estimate_cost(prompt, model)
            if 'error' not in estimate:
                estimates.append(estimate)

        # Sort by total cost
        estimates.sort(key=lambda x: x['total_cost'])

        return estimates

    def _detect_task_type(self, prompt: str) -> str:
        """Detect task type from prompt."""
        prompt_lower = prompt.lower()

        if any(w in prompt_lower for w in ['summarize', 'summary', 'tldr']):
            return 'summarization'
        if any(w in prompt_lower for w in ['translate', 'translation']):
            return 'translation'
        if any(w in prompt_lower for w in ['code', 'function', 'class', 'program']):
            return 'code_generation'
        if any(w in prompt_lower for w in ['explain', 'what is', 'how does']):
            return 'explanation'
        if any(w in prompt_lower for w in ['write', 'create', 'story', 'essay']):
            return 'creative_writing'

        return 'general'

    # -------------------------------------------------------------------------
    # Usage Tracking
    # -------------------------------------------------------------------------

    def get_user_usage(
        self,
        user,
        days: int = 30
    ) -> Dict:
        """
        Get user's token usage statistics.

        Args:
            user: User
            days: Number of days to analyze

        Returns:
            Usage statistics dict
        """
        try:
            from coreapp.models_analytics import UserAnalytics

            since = timezone.now().date() - timedelta(days=days)

            analytics = UserAnalytics.objects.filter(
                user=user,
                date__gte=since
            )

            total_tokens = analytics.aggregate(
                total=Sum('ai_tokens_used')
            )['total'] or 0

            daily_usage = list(analytics.values('date').annotate(
                tokens=Sum('ai_tokens_used'),
                generations=Sum('ai_text_generations')
            ).order_by('date'))

            # Calculate averages
            total_days = max(len(daily_usage), 1)
            avg_daily = total_tokens / total_days

            return {
                'total_tokens': total_tokens,
                'period_days': days,
                'daily_average': round(avg_daily, 0),
                'daily_usage': [
                    {
                        'date': d['date'].isoformat(),
                        'tokens': d['tokens'] or 0,
                        'generations': d['generations'] or 0,
                    }
                    for d in daily_usage
                ],
            }

        except Exception as e:
            logger.error(f"Error getting user usage: {e}")
            return {}

    # -------------------------------------------------------------------------
    # Usage Forecasting
    # -------------------------------------------------------------------------

    def forecast_usage(
        self,
        user,
        days: int = 30
    ) -> Dict:
        """
        Forecast token usage for upcoming period.

        Args:
            user: User
            days: Days to forecast

        Returns:
            Forecast dict
        """
        # Get historical usage
        historical = self.get_user_usage(user, days=30)

        if not historical or not historical.get('daily_usage'):
            return {
                'forecast': 0,
                'confidence': 'low',
                'message': 'Insufficient data for forecast'
            }

        daily_usage = historical['daily_usage']

        # Simple forecasting based on trend
        if len(daily_usage) < 7:
            # Not enough data, use average
            avg_daily = historical.get('daily_average', 0)
            forecast = avg_daily * days

            return {
                'forecast': int(forecast),
                'daily_forecast': int(avg_daily),
                'confidence': 'low',
                'method': 'average',
            }

        # Calculate trend using last 7 vs previous 7 days
        recent = daily_usage[-7:]
        previous = daily_usage[-14:-7] if len(daily_usage) >= 14 else daily_usage[:-7]

        recent_avg = sum(d['tokens'] for d in recent) / len(recent)
        previous_avg = sum(d['tokens'] for d in previous) / max(len(previous), 1)

        # Calculate growth rate
        if previous_avg > 0:
            growth_rate = (recent_avg - previous_avg) / previous_avg
        else:
            growth_rate = 0

        # Project forward with dampened growth
        daily_forecast = recent_avg * (1 + growth_rate * 0.5)  # Dampen growth
        forecast = daily_forecast * days

        # Determine confidence
        if len(daily_usage) >= 14:
            confidence = 'high'
        elif len(daily_usage) >= 7:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'forecast': int(forecast),
            'daily_forecast': int(daily_forecast),
            'growth_rate': round(growth_rate * 100, 1),
            'confidence': confidence,
            'method': 'trend',
            'based_on_days': len(daily_usage),
        }

    # -------------------------------------------------------------------------
    # Budget Management
    # -------------------------------------------------------------------------

    def check_budget(
        self,
        user,
        estimated_tokens: int,
        model: str = 'gpt-3.5-turbo'
    ) -> Dict:
        """
        Check if user has budget for operation.

        Args:
            user: User
            estimated_tokens: Estimated tokens needed
            model: Model to use

        Returns:
            Budget check result
        """
        try:
            from planandsubscription.models import Subscription

            # Get active subscription
            subscription = Subscription.objects.filter(
                user=user,
                status='active',
                is_delete=False
            ).first()

            if not subscription:
                return {
                    'allowed': False,
                    'reason': 'No active subscription',
                }

            current_balance = subscription.balance_token or 0

            # Check if enough tokens
            if current_balance < estimated_tokens:
                return {
                    'allowed': False,
                    'reason': 'Insufficient tokens',
                    'current_balance': current_balance,
                    'needed': estimated_tokens,
                    'shortfall': estimated_tokens - current_balance,
                }

            # Calculate remaining after operation
            remaining = current_balance - estimated_tokens

            return {
                'allowed': True,
                'current_balance': current_balance,
                'estimated_usage': estimated_tokens,
                'remaining_after': remaining,
                'usage_percentage': round(
                    (estimated_tokens / max(current_balance, 1)) * 100, 1
                ),
            }

        except Exception as e:
            logger.error(f"Error checking budget: {e}")
            return {'allowed': False, 'reason': str(e)}

    def get_budget_status(self, user) -> Dict:
        """
        Get current budget status for user.

        Args:
            user: User

        Returns:
            Budget status dict
        """
        try:
            from planandsubscription.models import Subscription

            subscription = Subscription.objects.filter(
                user=user,
                status='active',
                is_delete=False
            ).select_related('plan').first()

            if not subscription:
                return {
                    'has_subscription': False,
                    'balance': 0,
                }

            plan = subscription.plan
            balance = subscription.balance_token or 0
            total = plan.token_limit if plan else 0

            return {
                'has_subscription': True,
                'plan_name': plan.name if plan else 'Unknown',
                'balance': balance,
                'total_allocation': total,
                'used': total - balance,
                'usage_percentage': round(
                    ((total - balance) / max(total, 1)) * 100, 1
                ),
                'low_balance': balance < (total * 0.2),  # < 20% remaining
            }

        except Exception as e:
            logger.error(f"Error getting budget status: {e}")
            return {'has_subscription': False, 'error': str(e)}

    # -------------------------------------------------------------------------
    # Optimization Suggestions
    # -------------------------------------------------------------------------

    def get_optimization_tips(
        self,
        user,
        current_model: str = None
    ) -> List[Dict]:
        """
        Get token optimization tips for user.

        Args:
            user: User
            current_model: Currently used model

        Returns:
            List of optimization tips
        """
        tips = []

        # Get usage patterns
        usage = self.get_user_usage(user, days=7)

        if usage.get('daily_average', 0) > 1000:
            tips.append({
                'type': 'model_switch',
                'title': 'Consider a faster model',
                'description': 'For simple tasks, GPT-3.5 Turbo is 10x cheaper than GPT-4',
                'potential_savings': '60-80%',
            })

        # Check if using expensive model
        if current_model in ['gpt-4', 'claude-3-opus']:
            tips.append({
                'type': 'model_selection',
                'title': 'Use appropriate model for task',
                'description': 'Use premium models only for complex reasoning tasks',
                'potential_savings': '50%',
            })

        # General tips
        tips.append({
            'type': 'prompt_optimization',
            'title': 'Optimize your prompts',
            'description': 'Clear, concise prompts use fewer tokens and get better results',
            'potential_savings': '20-30%',
        })

        tips.append({
            'type': 'caching',
            'title': 'Reuse similar responses',
            'description': 'Save and reuse AI responses for similar queries',
            'potential_savings': '10-20%',
        })

        return tips


# =============================================================================
# Singleton Instance
# =============================================================================

token_estimator = TokenEstimator()
token_usage_service = TokenUsageService()
