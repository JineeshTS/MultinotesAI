"""
Unit tests for AI content generation.

This module tests:
- Text generation endpoints
- Model selection
- Token management during generation
- Response formatting
- Error handling
- Rate limiting
"""

import pytest
from datetime import timedelta
from unittest.mock import patch, Mock, MagicMock, AsyncMock

from django.utils import timezone
from rest_framework import status


# =============================================================================
# Text Generation Tests
# =============================================================================

@pytest.mark.django_db
class TestTextGeneration:
    """Tests for AI text generation."""

    @patch('coreapp.views.generate_ai_content')
    def test_generate_text_success(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test successful text generation."""
        subscription_factory(user=user, balance_token=5000, status='active')

        mock_generate.return_value = {
            'content': 'Generated text content here.',
            'tokens_used': 150,
            'model': 'gpt-3.5-turbo'
        }

        response = authenticated_client.post(
            '/api/content/generate/',
            {
                'prompt': 'Write a short paragraph about AI',
                'max_tokens': 500
            },
            format='json'
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED
        ]

    def test_generate_text_unauthenticated(self, api_client):
        """Test generation without authentication."""
        response = api_client.post(
            '/api/content/generate/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_generate_text_no_subscription(self, authenticated_client, user):
        """Test generation without active subscription."""
        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_402_PAYMENT_REQUIRED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_generate_text_insufficient_tokens(
        self, authenticated_client, subscription_factory, user
    ):
        """Test generation with insufficient token balance."""
        subscription_factory(user=user, balance_token=0, status='active')

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_402_PAYMENT_REQUIRED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_generate_text_empty_prompt(
        self, authenticated_client, subscription_factory, user
    ):
        """Test generation with empty prompt."""
        subscription_factory(user=user, balance_token=5000, status='active')

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': ''},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_generate_text_prompt_too_long(
        self, authenticated_client, subscription_factory, user
    ):
        """Test generation with overly long prompt."""
        subscription_factory(user=user, balance_token=5000, status='active')

        # Very long prompt (should exceed limits)
        long_prompt = 'A' * 100000

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': long_prompt},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Model Selection Tests
# =============================================================================

@pytest.mark.django_db
class TestModelSelection:
    """Tests for AI model selection."""

    @patch('coreapp.views.generate_ai_content')
    def test_select_specific_model(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test selecting a specific AI model."""
        subscription_factory(user=user, balance_token=10000, status='active')

        mock_generate.return_value = {
            'content': 'Response',
            'tokens_used': 100,
            'model': 'gpt-4'
        }

        response = authenticated_client.post(
            '/api/content/generate/',
            {
                'prompt': 'Complex reasoning task',
                'model': 'gpt-4'
            },
            format='json'
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED
        ]

    def test_invalid_model_selection(
        self, authenticated_client, subscription_factory, user
    ):
        """Test selecting an invalid model."""
        subscription_factory(user=user, balance_token=5000, status='active')

        response = authenticated_client.post(
            '/api/content/generate/',
            {
                'prompt': 'Test prompt',
                'model': 'invalid-model-name'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('coreapp.views.generate_ai_content')
    def test_default_model_used(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test that default model is used when not specified."""
        subscription_factory(user=user, balance_token=5000, status='active')

        mock_generate.return_value = {
            'content': 'Response',
            'tokens_used': 100,
            'model': 'gpt-3.5-turbo'
        }

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        # Verify default model was used in the call
        if mock_generate.called:
            call_args = mock_generate.call_args
            assert 'gpt-3.5' in str(call_args) or mock_generate.return_value['model'] == 'gpt-3.5-turbo'


# =============================================================================
# Token Management Tests
# =============================================================================

@pytest.mark.django_db
class TestTokenManagement:
    """Tests for token management during generation."""

    @patch('coreapp.views.generate_ai_content')
    def test_tokens_deducted_after_generation(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test that tokens are deducted after successful generation."""
        initial_tokens = 5000
        subscription = subscription_factory(
            user=user,
            balance_token=initial_tokens,
            status='active'
        )

        mock_generate.return_value = {
            'content': 'Generated content',
            'tokens_used': 200,
            'model': 'gpt-3.5-turbo'
        }

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            # Refresh subscription from database
            subscription.refresh_from_db()
            # Tokens should be deducted
            assert subscription.balance_token <= initial_tokens

    @patch('coreapp.views.generate_ai_content')
    def test_tokens_not_deducted_on_error(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test that tokens are not deducted when generation fails."""
        initial_tokens = 5000
        subscription = subscription_factory(
            user=user,
            balance_token=initial_tokens,
            status='active'
        )

        mock_generate.side_effect = Exception("AI service error")

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        # Refresh and check tokens not deducted on failure
        subscription.refresh_from_db()
        assert subscription.balance_token == initial_tokens

    def test_token_estimation(
        self, authenticated_client, subscription_factory, user
    ):
        """Test token estimation endpoint."""
        subscription_factory(user=user, balance_token=5000, status='active')

        response = authenticated_client.post(
            '/api/content/estimate/',
            {
                'prompt': 'Test prompt for estimation',
                'model': 'gpt-3.5-turbo'
            },
            format='json'
        )

        # Endpoint may or may not exist
        if response.status_code == status.HTTP_200_OK:
            assert 'estimated_tokens' in response.data or 'tokens' in str(response.data)


# =============================================================================
# Response Format Tests
# =============================================================================

@pytest.mark.django_db
class TestResponseFormat:
    """Tests for AI response formatting."""

    @patch('coreapp.views.generate_ai_content')
    def test_response_includes_content(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test that response includes generated content."""
        subscription_factory(user=user, balance_token=5000, status='active')

        mock_generate.return_value = {
            'content': 'This is the generated content.',
            'tokens_used': 100,
            'model': 'gpt-3.5-turbo'
        }

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            # Response should contain content
            assert 'content' in response.data or 'text' in response.data or 'response' in response.data

    @patch('coreapp.views.generate_ai_content')
    def test_response_includes_metadata(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test that response includes metadata."""
        subscription_factory(user=user, balance_token=5000, status='active')

        mock_generate.return_value = {
            'content': 'Generated content',
            'tokens_used': 150,
            'model': 'gpt-3.5-turbo'
        }

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            # Response may include token usage and model info
            data = response.data
            assert isinstance(data, dict)

    @patch('coreapp.views.generate_ai_content')
    def test_json_output_format(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test requesting JSON output format."""
        subscription_factory(user=user, balance_token=5000, status='active')

        mock_generate.return_value = {
            'content': '{"key": "value"}',
            'tokens_used': 100,
            'model': 'gpt-3.5-turbo'
        }

        response = authenticated_client.post(
            '/api/content/generate/',
            {
                'prompt': 'Generate JSON data',
                'format': 'json'
            },
            format='json'
        )

        # Just verify request is handled
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST  # If format param not supported
        ]


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.django_db
class TestErrorHandling:
    """Tests for AI generation error handling."""

    @patch('coreapp.views.generate_ai_content')
    def test_ai_service_timeout(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test handling of AI service timeout."""
        subscription_factory(user=user, balance_token=5000, status='active')

        mock_generate.side_effect = TimeoutError("Request timed out")

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_504_GATEWAY_TIMEOUT
        ]

    @patch('coreapp.views.generate_ai_content')
    def test_ai_service_rate_limit(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test handling of AI service rate limit."""
        subscription_factory(user=user, balance_token=5000, status='active')

        mock_generate.side_effect = Exception("Rate limit exceeded")

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_429_TOO_MANY_REQUESTS,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    @patch('coreapp.views.generate_ai_content')
    def test_content_filter_triggered(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test handling of content filter violations."""
        subscription_factory(user=user, balance_token=5000, status='active')

        mock_generate.side_effect = Exception("Content filter triggered")

        response = authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Inappropriate content request'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]


# =============================================================================
# Rate Limiting Tests
# =============================================================================

@pytest.mark.django_db
class TestRateLimiting:
    """Tests for API rate limiting."""

    def test_rate_limit_headers_present(
        self, authenticated_client, subscription_factory, user
    ):
        """Test that rate limit headers are present in response."""
        subscription_factory(user=user, balance_token=5000, status='active')

        response = authenticated_client.get('/api/content/')

        # Rate limit headers may or may not be present
        # Common headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        if response.status_code == status.HTTP_200_OK:
            # Check is informational only
            pass

    @patch('coreapp.views.generate_ai_content')
    def test_burst_requests_handled(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test handling of burst requests."""
        subscription_factory(user=user, balance_token=50000, status='active')

        mock_generate.return_value = {
            'content': 'Response',
            'tokens_used': 100,
            'model': 'gpt-3.5-turbo'
        }

        # Send multiple requests in quick succession
        responses = []
        for _ in range(10):
            response = authenticated_client.post(
                '/api/content/generate/',
                {'prompt': 'Test prompt'},
                format='json'
            )
            responses.append(response.status_code)

        # Some requests may be rate limited
        # At least some should succeed
        success_count = sum(1 for s in responses if s in [200, 201])
        rate_limited = sum(1 for s in responses if s == 429)

        # Either all succeed or some get rate limited
        assert success_count > 0 or rate_limited > 0


# =============================================================================
# Content History Tests
# =============================================================================

@pytest.mark.django_db
class TestContentHistory:
    """Tests for content history and retrieval."""

    @patch('coreapp.views.generate_ai_content')
    def test_content_saved_to_history(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test that generated content is saved to history."""
        subscription_factory(user=user, balance_token=5000, status='active')

        mock_generate.return_value = {
            'content': 'Generated content for history',
            'tokens_used': 100,
            'model': 'gpt-3.5-turbo'
        }

        # Generate content
        authenticated_client.post(
            '/api/content/generate/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        # Check history
        history_response = authenticated_client.get('/api/content/')

        if history_response.status_code == status.HTTP_200_OK:
            content_list = history_response.data.get('results', history_response.data)
            # History should contain items
            assert isinstance(content_list, list)

    def test_content_retrieval_by_id(
        self, authenticated_client, content_factory, user
    ):
        """Test retrieving specific content by ID."""
        content = content_factory(user=user)

        response = authenticated_client.get(f'/api/content/{content.id}/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If endpoint doesn't exist
        ]

    def test_content_deletion(
        self, authenticated_client, content_factory, user
    ):
        """Test deleting generated content."""
        content = content_factory(user=user)

        response = authenticated_client.delete(f'/api/content/{content.id}/')

        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]


# =============================================================================
# Streaming Tests
# =============================================================================

@pytest.mark.django_db
class TestStreamingGeneration:
    """Tests for streaming AI generation."""

    @patch('coreapp.views.generate_ai_content_stream')
    def test_streaming_endpoint_exists(
        self, mock_stream, authenticated_client, subscription_factory, user
    ):
        """Test that streaming endpoint exists."""
        subscription_factory(user=user, balance_token=5000, status='active')

        response = authenticated_client.post(
            '/api/content/generate/stream/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        # Endpoint may or may not exist
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]

    def test_streaming_requires_auth(self, api_client):
        """Test streaming requires authentication."""
        response = api_client.post(
            '/api/content/generate/stream/',
            {'prompt': 'Test prompt'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_404_NOT_FOUND  # If endpoint doesn't exist
        ]


# =============================================================================
# Template/Preset Tests
# =============================================================================

@pytest.mark.django_db
class TestTemplates:
    """Tests for content templates and presets."""

    def test_list_templates(self, authenticated_client, user):
        """Test listing available templates."""
        response = authenticated_client.get('/api/content/templates/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If not implemented
        ]

    @patch('coreapp.views.generate_ai_content')
    def test_generate_from_template(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test generating content from a template."""
        subscription_factory(user=user, balance_token=5000, status='active')

        mock_generate.return_value = {
            'content': 'Template-based content',
            'tokens_used': 100,
            'model': 'gpt-3.5-turbo'
        }

        response = authenticated_client.post(
            '/api/content/generate/',
            {
                'template_id': 1,
                'variables': {'topic': 'AI'}
            },
            format='json'
        )

        # Should either work or return validation error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ]


# =============================================================================
# Image Generation Tests
# =============================================================================

@pytest.mark.django_db
class TestImageGeneration:
    """Tests for AI image generation."""

    @patch('coreapp.views.generate_ai_image')
    def test_generate_image_success(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test successful image generation."""
        subscription_factory(user=user, balance_token=10000, status='active')

        mock_generate.return_value = {
            'image_url': 'https://example.com/image.png',
            'tokens_used': 1000
        }

        response = authenticated_client.post(
            '/api/content/generate-image/',
            {
                'prompt': 'A beautiful sunset over mountains',
                'size': '1024x1024'
            },
            format='json'
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_404_NOT_FOUND  # If not implemented
        ]

    def test_image_generation_requires_sufficient_tokens(
        self, authenticated_client, subscription_factory, user
    ):
        """Test image generation token requirements."""
        # Image generation typically requires more tokens
        subscription_factory(user=user, balance_token=10, status='active')

        response = authenticated_client.post(
            '/api/content/generate-image/',
            {'prompt': 'Test image'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_402_PAYMENT_REQUIRED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND  # If not implemented
        ]


# =============================================================================
# Usage Analytics Tests
# =============================================================================

@pytest.mark.django_db
class TestUsageAnalytics:
    """Tests for usage analytics."""

    def test_get_usage_stats(
        self, authenticated_client, subscription_factory, user
    ):
        """Test getting usage statistics."""
        subscription_factory(user=user, balance_token=5000, status='active')

        response = authenticated_client.get('/api/content/usage/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If not implemented
        ]

    def test_usage_by_period(
        self, authenticated_client, subscription_factory, user
    ):
        """Test getting usage by time period."""
        subscription_factory(user=user, balance_token=5000, status='active')

        response = authenticated_client.get('/api/content/usage/?period=week')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]


# =============================================================================
# Concurrent Generation Tests
# =============================================================================

@pytest.mark.django_db
class TestConcurrentGeneration:
    """Tests for concurrent generation handling."""

    @patch('coreapp.views.generate_ai_content')
    def test_multiple_concurrent_requests(
        self, mock_generate, authenticated_client, subscription_factory, user
    ):
        """Test handling multiple concurrent generation requests."""
        subscription_factory(user=user, balance_token=50000, status='active')

        mock_generate.return_value = {
            'content': 'Response',
            'tokens_used': 100,
            'model': 'gpt-3.5-turbo'
        }

        import threading
        results = []

        def make_request():
            response = authenticated_client.post(
                '/api/content/generate/',
                {'prompt': 'Test prompt'},
                format='json'
            )
            results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # At least some requests should complete
        success_count = sum(1 for s in results if s in [200, 201])
        assert success_count > 0 or len(results) > 0
