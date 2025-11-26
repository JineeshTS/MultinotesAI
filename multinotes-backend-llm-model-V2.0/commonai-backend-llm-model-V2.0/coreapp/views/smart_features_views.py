"""
Smart Features API Views for MultinotesAI.

This module provides REST API endpoints for:
- Topic extraction
- Prompt suggestions
- Usage patterns
- Plan recommendations
- Token estimation
- Conversation compression

WBS Items:
- 4.4.3: Topic extraction
- 4.4.4: Prompt suggestions
- 4.4.5: Usage patterns
- 4.4.6: Plan recommendations
- 6.1.9: Token usage predictor
- 6.1.10: Conversation compression
"""

import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


# =============================================================================
# Topic Extraction Views
# =============================================================================

class TopicExtractionView(APIView):
    """
    Extract topics from text.

    POST /api/smart/topics/extract/
    {
        "text": "Your text here..."
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Extract topics from text."""
        from coreapp.services.topic_extraction import topic_extractor

        text = request.data.get('text', '')
        max_topics = request.data.get('max_topics', 10)

        if not text:
            return Response(
                {'error': 'Text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = topic_extractor.extract_topics(text, max_topics=max_topics)
            return Response(result.to_dict())

        except Exception as e:
            logger.exception("Topic extraction failed")
            return Response(
                {'error': 'Topic extraction failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConversationTopicsView(APIView):
    """
    Extract topics from a conversation.

    GET /api/smart/topics/conversation/<prompt_id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, prompt_id):
        """Get topics for a conversation."""
        from coreapp.services.topic_extraction import topic_analyzer

        try:
            result = topic_analyzer.analyze_conversation(prompt_id)
            return Response(result.to_dict())

        except Exception as e:
            logger.exception(f"Failed to get conversation topics for {prompt_id}")
            return Response(
                {'error': 'Failed to analyze conversation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserTopicsView(APIView):
    """
    Get aggregated topics for user.

    GET /api/smart/topics/user/?days=30
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's topic summary."""
        from coreapp.services.topic_extraction import topic_analyzer

        days = int(request.query_params.get('days', 30))

        try:
            result = topic_analyzer.get_user_topics(
                user_id=request.user.id,
                days=days
            )
            return Response(result)

        except Exception as e:
            logger.exception("Failed to get user topics")
            return Response(
                {'error': 'Failed to get topics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Prompt Suggestion Views
# =============================================================================

class PromptSuggestionsView(APIView):
    """
    Get prompt suggestions.

    GET /api/smart/suggestions/?category=coding&limit=10
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get prompt suggestions."""
        from coreapp.services.prompt_suggestions import prompt_generator

        category = request.query_params.get('category')
        context = request.query_params.get('context')
        limit = int(request.query_params.get('limit', 10))

        try:
            suggestions = prompt_generator.get_suggestions(
                user_id=request.user.id,
                category=category,
                context=context,
                limit=limit
            )

            return Response({
                'suggestions': [s.to_dict() for s in suggestions]
            })

        except Exception as e:
            logger.exception("Failed to get suggestions")
            return Response(
                {'error': 'Failed to get suggestions'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FollowUpSuggestionsView(APIView):
    """
    Get follow-up prompt suggestions.

    POST /api/smart/suggestions/followup/
    {
        "previous_response": "AI's previous response..."
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Get follow-up suggestions."""
        from coreapp.services.prompt_suggestions import prompt_generator

        previous_response = request.data.get('previous_response', '')
        limit = int(request.data.get('limit', 5))

        if not previous_response:
            return Response(
                {'error': 'Previous response is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            suggestions = prompt_generator.get_follow_ups(
                previous_response=previous_response,
                limit=limit
            )

            return Response({
                'suggestions': [s.to_dict() for s in suggestions]
            })

        except Exception as e:
            logger.exception("Failed to get follow-up suggestions")
            return Response(
                {'error': 'Failed to get follow-up suggestions'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StarterPromptsView(APIView):
    """
    Get starter prompts for new users.

    GET /api/smart/suggestions/starters/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get starter prompts."""
        from coreapp.services.prompt_suggestions import prompt_generator

        limit = int(request.query_params.get('limit', 6))

        try:
            starters = prompt_generator.get_starter_prompts(limit=limit)
            return Response({
                'prompts': [s.to_dict() for s in starters]
            })

        except Exception as e:
            logger.exception("Failed to get starter prompts")
            return Response(
                {'error': 'Failed to get starter prompts'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromptCategoriesView(APIView):
    """
    Get prompt categories.

    GET /api/smart/suggestions/categories/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get available categories."""
        from coreapp.services.prompt_suggestions import prompt_discovery

        categories = prompt_discovery.get_categories()
        return Response({'categories': categories})


# =============================================================================
# Usage Pattern Views
# =============================================================================

class UsageSummaryView(APIView):
    """
    Get user's usage summary.

    GET /api/smart/usage/summary/?days=30
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get usage summary."""
        from coreapp.services.usage_patterns import usage_analyzer

        days = int(request.query_params.get('days', 30))

        try:
            summary = usage_analyzer.get_user_summary(
                user_id=request.user.id,
                days=days
            )
            return Response(summary.to_dict())

        except Exception as e:
            logger.exception("Failed to get usage summary")
            return Response(
                {'error': 'Failed to get usage summary'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UsagePatternsView(APIView):
    """
    Get detected usage patterns.

    GET /api/smart/usage/patterns/?days=30
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get usage patterns."""
        from coreapp.services.usage_patterns import usage_analyzer

        days = int(request.query_params.get('days', 30))

        try:
            patterns = usage_analyzer.detect_patterns(
                user_id=request.user.id,
                days=days
            )

            return Response({
                'patterns': [p.to_dict() for p in patterns]
            })

        except Exception as e:
            logger.exception("Failed to detect patterns")
            return Response(
                {'error': 'Failed to detect patterns'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HourlyDistributionView(APIView):
    """
    Get hourly usage distribution.

    GET /api/smart/usage/hourly/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get hourly distribution."""
        from coreapp.services.usage_patterns import usage_analyzer

        days = int(request.query_params.get('days', 30))

        try:
            distribution = usage_analyzer.get_hourly_distribution(
                user_id=request.user.id,
                days=days
            )

            return Response({'hourly_distribution': distribution})

        except Exception as e:
            logger.exception("Failed to get hourly distribution")
            return Response(
                {'error': 'Failed to get distribution'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UsageTimelineView(APIView):
    """
    Get usage timeline.

    GET /api/smart/usage/timeline/?days=30&granularity=daily
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get usage timeline."""
        from coreapp.services.usage_patterns import usage_analyzer, TimeGranularity

        days = int(request.query_params.get('days', 30))
        granularity_str = request.query_params.get('granularity', 'daily')

        try:
            granularity = TimeGranularity(granularity_str)
        except ValueError:
            granularity = TimeGranularity.DAILY

        try:
            timeline = usage_analyzer.get_usage_timeline(
                user_id=request.user.id,
                days=days,
                granularity=granularity
            )

            return Response({'timeline': timeline})

        except Exception as e:
            logger.exception("Failed to get timeline")
            return Response(
                {'error': 'Failed to get timeline'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Plan Recommendation Views
# =============================================================================

class PlanRecommendationView(APIView):
    """
    Get plan recommendation.

    GET /api/smart/plans/recommendation/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get plan recommendation."""
        from coreapp.services.plan_recommender import plan_recommender

        include_analysis = request.query_params.get('include_analysis', 'true').lower() == 'true'

        try:
            recommendation = plan_recommender.get_recommendation(
                user_id=request.user.id,
                include_analysis=include_analysis
            )

            return Response(recommendation)

        except Exception as e:
            logger.exception("Failed to get recommendation")
            return Response(
                {'error': 'Failed to get recommendation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CostAnalysisView(APIView):
    """
    Get cost analysis.

    GET /api/smart/plans/cost-analysis/?months=3
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get cost analysis."""
        from coreapp.services.plan_recommender import plan_recommender

        months = int(request.query_params.get('months', 3))

        try:
            analysis = plan_recommender.get_cost_analysis(
                user_id=request.user.id,
                months=months
            )

            return Response(analysis)

        except Exception as e:
            logger.exception("Failed to get cost analysis")
            return Response(
                {'error': 'Failed to get cost analysis'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpgradeBenefitsView(APIView):
    """
    Get upgrade benefits.

    GET /api/smart/plans/upgrade-benefits/<plan_id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, plan_id):
        """Get upgrade benefits for specific plan."""
        from coreapp.services.plan_recommender import plan_recommender

        try:
            benefits = plan_recommender.get_upgrade_benefits(
                user_id=request.user.id,
                target_plan=plan_id
            )

            return Response(benefits)

        except Exception as e:
            logger.exception(f"Failed to get upgrade benefits for {plan_id}")
            return Response(
                {'error': 'Failed to get upgrade benefits'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Token Estimation Views
# =============================================================================

class TokenEstimateView(APIView):
    """
    Estimate tokens and cost for a prompt.

    POST /api/smart/tokens/estimate/
    {
        "prompt": "Your prompt text...",
        "model": "gpt-4"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Estimate tokens and cost."""
        from coreapp.services.token_service import token_usage_service

        prompt = request.data.get('prompt', '')
        model = request.data.get('model', 'gpt-3.5-turbo')

        if not prompt:
            return Response(
                {'error': 'Prompt is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            estimate = token_usage_service.estimate_cost(
                prompt=prompt,
                model=model
            )

            return Response(estimate)

        except Exception as e:
            logger.exception("Failed to estimate tokens")
            return Response(
                {'error': 'Failed to estimate tokens'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModelComparisonView(APIView):
    """
    Compare costs across models.

    POST /api/smart/tokens/compare/
    {
        "prompt": "Your prompt text..."
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Compare models for a prompt."""
        from coreapp.services.token_service import token_usage_service

        prompt = request.data.get('prompt', '')

        if not prompt:
            return Response(
                {'error': 'Prompt is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            comparison = token_usage_service.compare_models(prompt=prompt)
            return Response({'models': comparison})

        except Exception as e:
            logger.exception("Failed to compare models")
            return Response(
                {'error': 'Failed to compare models'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UsageForecastView(APIView):
    """
    Forecast token usage.

    GET /api/smart/tokens/forecast/?days=30
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get usage forecast."""
        from coreapp.services.token_service import token_usage_service

        days = int(request.query_params.get('days', 30))

        try:
            forecast = token_usage_service.forecast_usage(
                user=request.user,
                days=days
            )

            return Response(forecast)

        except Exception as e:
            logger.exception("Failed to forecast usage")
            return Response(
                {'error': 'Failed to forecast usage'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BudgetStatusView(APIView):
    """
    Get budget status.

    GET /api/smart/tokens/budget/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get budget status."""
        from coreapp.services.token_service import token_usage_service

        try:
            budget_status = token_usage_service.get_budget_status(request.user)
            return Response(budget_status)

        except Exception as e:
            logger.exception("Failed to get budget status")
            return Response(
                {'error': 'Failed to get budget status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Conversation Compression Views
# =============================================================================

class CompressConversationView(APIView):
    """
    Compress a conversation to fit within token limits.

    POST /api/smart/conversation/compress/
    {
        "messages": [...],
        "max_tokens": 4096,
        "strategy": "hybrid"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Compress conversation."""
        from coreapp.services.conversation_compression import (
            conversation_compressor,
            CompressionStrategy
        )

        messages = request.data.get('messages', [])
        max_tokens = int(request.data.get('max_tokens', 4096))
        strategy_str = request.data.get('strategy', 'hybrid')

        if not messages:
            return Response(
                {'error': 'Messages are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            strategy = CompressionStrategy(strategy_str)
        except ValueError:
            strategy = CompressionStrategy.HYBRID

        try:
            result = conversation_compressor.compress(
                messages=messages,
                max_tokens=max_tokens,
                strategy=strategy
            )

            return Response(result.to_dict())

        except Exception as e:
            logger.exception("Failed to compress conversation")
            return Response(
                {'error': 'Failed to compress conversation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PrepareContextView(APIView):
    """
    Prepare context for LLM call.

    POST /api/smart/conversation/prepare-context/
    {
        "messages": [...],
        "new_message": "User's new message",
        "system_prompt": "Optional system prompt",
        "max_tokens": 4096
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Prepare context."""
        from coreapp.services.conversation_compression import context_manager

        messages = request.data.get('messages', [])
        new_message = request.data.get('new_message')
        system_prompt = request.data.get('system_prompt')
        max_tokens = int(request.data.get('max_tokens', 4096))

        try:
            # Update context manager's max tokens
            context_manager.max_tokens = max_tokens

            result = context_manager.prepare_context(
                messages=messages,
                new_message=new_message,
                system_prompt=system_prompt
            )

            return Response(result)

        except Exception as e:
            logger.exception("Failed to prepare context")
            return Response(
                {'error': 'Failed to prepare context'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
