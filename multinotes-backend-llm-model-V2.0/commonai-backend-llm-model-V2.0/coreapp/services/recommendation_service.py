"""
Model Recommendation Engine for MultinotesAI.

This module provides:
- Smart model recommendations based on task type
- Model performance tracking
- Cost/quality optimization
- User preference learning
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from django.db import models
from django.db.models import Avg, Count, Sum
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Task Types
# =============================================================================

class TaskType(Enum):
    """Types of AI tasks for recommendation."""

    # Writing tasks
    CREATIVE_WRITING = 'creative_writing'
    TECHNICAL_WRITING = 'technical_writing'
    COPYWRITING = 'copywriting'
    EMAIL_WRITING = 'email_writing'
    BLOG_POST = 'blog_post'

    # Analysis tasks
    CODE_ANALYSIS = 'code_analysis'
    DATA_ANALYSIS = 'data_analysis'
    SENTIMENT_ANALYSIS = 'sentiment_analysis'
    TEXT_SUMMARIZATION = 'text_summarization'

    # Code tasks
    CODE_GENERATION = 'code_generation'
    CODE_REVIEW = 'code_review'
    CODE_EXPLANATION = 'code_explanation'
    BUG_FIXING = 'bug_fixing'

    # Conversation tasks
    CHAT = 'chat'
    Q_AND_A = 'q_and_a'
    BRAINSTORMING = 'brainstorming'
    ROLE_PLAY = 'role_play'

    # Other
    TRANSLATION = 'translation'
    GENERAL = 'general'


# =============================================================================
# Model Profiles
# =============================================================================

@dataclass
class ModelProfile:
    """Profile for an AI model with strengths and capabilities."""
    model_id: str
    name: str
    provider: str
    cost_per_1k_tokens: float
    speed_rating: float  # 1-10
    quality_rating: float  # 1-10
    context_window: int
    strengths: List[TaskType]
    weaknesses: List[TaskType]
    best_for: List[str]


# Default model profiles
MODEL_PROFILES = {
    'gpt-4': ModelProfile(
        model_id='gpt-4',
        name='GPT-4',
        provider='openai',
        cost_per_1k_tokens=0.03,
        speed_rating=6,
        quality_rating=9.5,
        context_window=8192,
        strengths=[
            TaskType.CODE_GENERATION, TaskType.CODE_REVIEW,
            TaskType.TECHNICAL_WRITING, TaskType.DATA_ANALYSIS
        ],
        weaknesses=[],
        best_for=['Complex reasoning', 'Code generation', 'Technical tasks']
    ),
    'gpt-3.5-turbo': ModelProfile(
        model_id='gpt-3.5-turbo',
        name='GPT-3.5 Turbo',
        provider='openai',
        cost_per_1k_tokens=0.002,
        speed_rating=9,
        quality_rating=7.5,
        context_window=4096,
        strengths=[
            TaskType.CHAT, TaskType.EMAIL_WRITING,
            TaskType.Q_AND_A, TaskType.GENERAL
        ],
        weaknesses=[TaskType.CODE_GENERATION],
        best_for=['Quick responses', 'Simple tasks', 'Chat']
    ),
    'claude-3-opus': ModelProfile(
        model_id='claude-3-opus',
        name='Claude 3 Opus',
        provider='anthropic',
        cost_per_1k_tokens=0.015,
        speed_rating=7,
        quality_rating=9.5,
        context_window=200000,
        strengths=[
            TaskType.CREATIVE_WRITING, TaskType.TEXT_SUMMARIZATION,
            TaskType.CODE_ANALYSIS, TaskType.TECHNICAL_WRITING
        ],
        weaknesses=[],
        best_for=['Long documents', 'Analysis', 'Creative writing']
    ),
    'claude-3-sonnet': ModelProfile(
        model_id='claude-3-sonnet',
        name='Claude 3 Sonnet',
        provider='anthropic',
        cost_per_1k_tokens=0.003,
        speed_rating=8,
        quality_rating=8.5,
        context_window=200000,
        strengths=[
            TaskType.CREATIVE_WRITING, TaskType.CHAT,
            TaskType.BRAINSTORMING
        ],
        weaknesses=[],
        best_for=['Balanced quality/speed', 'General tasks']
    ),
    'gemini-pro': ModelProfile(
        model_id='gemini-pro',
        name='Gemini Pro',
        provider='google',
        cost_per_1k_tokens=0.001,
        speed_rating=8,
        quality_rating=8,
        context_window=32000,
        strengths=[
            TaskType.Q_AND_A, TaskType.TRANSLATION,
            TaskType.DATA_ANALYSIS
        ],
        weaknesses=[TaskType.CODE_GENERATION],
        best_for=['Multimodal', 'Research', 'Q&A']
    ),
}


# =============================================================================
# Model Performance Model
# =============================================================================

class ModelPerformance(models.Model):
    """Track model performance for recommendations."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='model_performance'
    )
    model_id = models.CharField(max_length=100)
    task_type = models.CharField(max_length=50)

    # Aggregated metrics
    total_uses = models.IntegerField(default=0)
    total_rating = models.IntegerField(default=0)
    avg_response_time = models.FloatField(default=0)
    avg_tokens_used = models.IntegerField(default=0)

    # Timestamps
    last_used = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'model_performance'
        unique_together = ['user', 'model_id', 'task_type']
        indexes = [
            models.Index(fields=['user', 'task_type']),
            models.Index(fields=['model_id', '-total_uses']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.model_id} - {self.task_type}"

    @property
    def average_rating(self) -> float:
        if self.total_uses == 0:
            return 0
        return self.total_rating / self.total_uses


# =============================================================================
# Recommendation Engine
# =============================================================================

class ModelRecommendationEngine:
    """
    Smart model recommendation engine.

    Usage:
        engine = ModelRecommendationEngine()
        recommendations = engine.get_recommendations(
            user=user,
            task_type=TaskType.CODE_GENERATION,
            prompt_length=500,
            priority='quality'
        )
    """

    def __init__(self):
        self.profiles = MODEL_PROFILES
        self.cache_timeout = 300  # 5 minutes

    def get_recommendations(
        self,
        user=None,
        task_type: TaskType = None,
        prompt_length: int = 0,
        priority: str = 'balanced',  # 'quality', 'speed', 'cost', 'balanced'
        limit: int = 3
    ) -> List[Dict]:
        """
        Get model recommendations.

        Args:
            user: User for personalized recommendations
            task_type: Type of task
            prompt_length: Estimated prompt length in tokens
            priority: Optimization priority
            limit: Max recommendations

        Returns:
            List of recommended models with scores
        """
        # Get available models
        available_models = self._get_available_models()

        if not available_models:
            return []

        # Score each model
        scored_models = []
        for model_id in available_models:
            profile = self.profiles.get(model_id)
            if not profile:
                continue

            score = self._calculate_score(
                profile=profile,
                user=user,
                task_type=task_type,
                prompt_length=prompt_length,
                priority=priority
            )

            scored_models.append({
                'model_id': model_id,
                'name': profile.name,
                'provider': profile.provider,
                'score': score,
                'cost_per_1k': profile.cost_per_1k_tokens,
                'speed_rating': profile.speed_rating,
                'quality_rating': profile.quality_rating,
                'best_for': profile.best_for,
                'reasons': self._get_recommendation_reasons(
                    profile, task_type, priority
                ),
            })

        # Sort by score and return top N
        scored_models.sort(key=lambda x: x['score'], reverse=True)
        return scored_models[:limit]

    def _get_available_models(self) -> List[str]:
        """Get list of available models from database."""
        try:
            from coreapp.models import LLMModel

            return list(LLMModel.objects.filter(
                is_delete=False,
                is_connected=True
            ).values_list('model_id', flat=True))
        except Exception:
            return list(self.profiles.keys())

    def _calculate_score(
        self,
        profile: ModelProfile,
        user=None,
        task_type: TaskType = None,
        prompt_length: int = 0,
        priority: str = 'balanced'
    ) -> float:
        """Calculate recommendation score for a model."""
        score = 0.0

        # Base scores from profile
        quality_score = profile.quality_rating * 10
        speed_score = profile.speed_rating * 10
        cost_score = max(0, 100 - (profile.cost_per_1k_tokens * 1000))

        # Apply priority weights
        weights = {
            'quality': {'quality': 0.6, 'speed': 0.2, 'cost': 0.2},
            'speed': {'quality': 0.2, 'speed': 0.6, 'cost': 0.2},
            'cost': {'quality': 0.2, 'speed': 0.2, 'cost': 0.6},
            'balanced': {'quality': 0.4, 'speed': 0.3, 'cost': 0.3},
        }

        w = weights.get(priority, weights['balanced'])
        score = (
            quality_score * w['quality'] +
            speed_score * w['speed'] +
            cost_score * w['cost']
        )

        # Task type bonus
        if task_type:
            if task_type in profile.strengths:
                score += 15
            if task_type in profile.weaknesses:
                score -= 20

        # Context window check
        if prompt_length > 0:
            if prompt_length > profile.context_window:
                score -= 50  # Model can't handle this prompt
            elif prompt_length > profile.context_window * 0.8:
                score -= 10  # Close to limit

        # User history bonus
        if user:
            user_score = self._get_user_preference_score(
                user, profile.model_id, task_type
            )
            score += user_score * 0.2

        return max(0, score)

    def _get_user_preference_score(
        self,
        user,
        model_id: str,
        task_type: TaskType = None
    ) -> float:
        """Get user's preference score for a model."""
        try:
            filters = {'user': user, 'model_id': model_id}
            if task_type:
                filters['task_type'] = task_type.value

            perf = ModelPerformance.objects.filter(**filters).first()

            if perf and perf.total_uses > 0:
                # Scale average rating (1-5) to score (0-50)
                return perf.average_rating * 10
            return 0

        except Exception:
            return 0

    def _get_recommendation_reasons(
        self,
        profile: ModelProfile,
        task_type: TaskType = None,
        priority: str = 'balanced'
    ) -> List[str]:
        """Get human-readable reasons for recommendation."""
        reasons = []

        if priority == 'quality':
            if profile.quality_rating >= 9:
                reasons.append("Highest quality output")
        elif priority == 'speed':
            if profile.speed_rating >= 8:
                reasons.append("Fast response times")
        elif priority == 'cost':
            if profile.cost_per_1k_tokens < 0.005:
                reasons.append("Most cost-effective option")

        if task_type and task_type in profile.strengths:
            reasons.append(f"Excellent for {task_type.value.replace('_', ' ')}")

        if profile.context_window >= 100000:
            reasons.append("Handles very long documents")

        if not reasons:
            reasons.append("Good all-around performance")

        return reasons[:3]

    # -------------------------------------------------------------------------
    # Performance Tracking
    # -------------------------------------------------------------------------

    def record_usage(
        self,
        user,
        model_id: str,
        task_type: str,
        rating: int = None,
        response_time: float = None,
        tokens_used: int = None
    ):
        """
        Record model usage for future recommendations.

        Args:
            user: User
            model_id: Model used
            task_type: Type of task
            rating: User rating (1-5)
            response_time: Response time in seconds
            tokens_used: Tokens used
        """
        try:
            perf, created = ModelPerformance.objects.get_or_create(
                user=user,
                model_id=model_id,
                task_type=task_type,
                defaults={
                    'total_uses': 0,
                    'total_rating': 0,
                    'avg_response_time': 0,
                    'avg_tokens_used': 0,
                }
            )

            perf.total_uses += 1

            if rating:
                perf.total_rating += rating

            if response_time:
                # Running average
                perf.avg_response_time = (
                    (perf.avg_response_time * (perf.total_uses - 1) + response_time)
                    / perf.total_uses
                )

            if tokens_used:
                perf.avg_tokens_used = (
                    (perf.avg_tokens_used * (perf.total_uses - 1) + tokens_used)
                    / perf.total_uses
                )

            perf.save()

        except Exception as e:
            logger.error(f"Error recording model usage: {e}")

    def get_user_model_stats(self, user) -> Dict:
        """Get user's model usage statistics."""
        try:
            stats = ModelPerformance.objects.filter(user=user).values(
                'model_id'
            ).annotate(
                uses=Sum('total_uses'),
                avg_rating=Avg('total_rating') / Avg('total_uses')
            ).order_by('-uses')

            return {
                'by_model': list(stats),
                'total_generations': sum(s['uses'] for s in stats),
                'favorite_model': stats[0]['model_id'] if stats else None,
            }
        except Exception:
            return {}

    # -------------------------------------------------------------------------
    # Task Detection
    # -------------------------------------------------------------------------

    def detect_task_type(self, prompt: str) -> TaskType:
        """
        Detect task type from prompt text.

        Args:
            prompt: User's prompt

        Returns:
            Detected TaskType
        """
        prompt_lower = prompt.lower()

        # Code-related keywords
        code_keywords = ['code', 'function', 'class', 'bug', 'error', 'debug',
                        'python', 'javascript', 'java', 'sql', 'api']
        if any(kw in prompt_lower for kw in code_keywords):
            if 'review' in prompt_lower:
                return TaskType.CODE_REVIEW
            if 'explain' in prompt_lower:
                return TaskType.CODE_EXPLANATION
            if 'fix' in prompt_lower or 'bug' in prompt_lower:
                return TaskType.BUG_FIXING
            return TaskType.CODE_GENERATION

        # Writing keywords
        if 'blog' in prompt_lower or 'article' in prompt_lower:
            return TaskType.BLOG_POST
        if 'email' in prompt_lower:
            return TaskType.EMAIL_WRITING
        if 'story' in prompt_lower or 'creative' in prompt_lower:
            return TaskType.CREATIVE_WRITING
        if 'copy' in prompt_lower or 'ad' in prompt_lower or 'marketing' in prompt_lower:
            return TaskType.COPYWRITING

        # Analysis keywords
        if 'summarize' in prompt_lower or 'summary' in prompt_lower:
            return TaskType.TEXT_SUMMARIZATION
        if 'analyze' in prompt_lower or 'analysis' in prompt_lower:
            return TaskType.DATA_ANALYSIS
        if 'sentiment' in prompt_lower:
            return TaskType.SENTIMENT_ANALYSIS

        # Other
        if 'translate' in prompt_lower:
            return TaskType.TRANSLATION
        if 'brainstorm' in prompt_lower or 'ideas' in prompt_lower:
            return TaskType.BRAINSTORMING

        return TaskType.GENERAL

    # -------------------------------------------------------------------------
    # Cost Estimation
    # -------------------------------------------------------------------------

    def estimate_cost(
        self,
        model_id: str,
        prompt_tokens: int,
        estimated_completion_tokens: int = None
    ) -> Dict:
        """
        Estimate cost for a generation.

        Args:
            model_id: Model to use
            prompt_tokens: Number of prompt tokens
            estimated_completion_tokens: Estimated completion tokens

        Returns:
            Cost estimation dict
        """
        profile = self.profiles.get(model_id)
        if not profile:
            return {'error': 'Unknown model'}

        if estimated_completion_tokens is None:
            # Estimate based on prompt length
            estimated_completion_tokens = min(prompt_tokens * 2, 2000)

        total_tokens = prompt_tokens + estimated_completion_tokens
        cost = (total_tokens / 1000) * profile.cost_per_1k_tokens

        return {
            'model_id': model_id,
            'prompt_tokens': prompt_tokens,
            'estimated_completion_tokens': estimated_completion_tokens,
            'total_tokens': total_tokens,
            'estimated_cost_usd': round(cost, 6),
            'cost_per_1k_tokens': profile.cost_per_1k_tokens,
        }


# =============================================================================
# Singleton Instance
# =============================================================================

recommendation_engine = ModelRecommendationEngine()
