"""
Tests for LLM-related endpoints.

Tests cover:
- LLM listing
- LLM selection
- LLM ratings
- Token usage tracking
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestLLMList:
    """Tests for LLM listing endpoints."""

    def test_list_llms_authenticated(self, auth_client, llm):
        """Test listing LLMs as authenticated user."""
        url = '/api/core/llm/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, (list, dict))

    def test_list_llms_unauthenticated(self, api_client):
        """Test listing LLMs without authentication fails."""
        url = '/api/core/llm/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_llm_detail(self, auth_client, llm):
        """Test getting LLM details."""
        url = f'/api/core/llm/{llm.id}/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestUserLLM:
    """Tests for user LLM selection endpoints."""

    def test_select_llm(self, auth_client, llm, user):
        """Test selecting an LLM for user."""
        url = '/api/core/user-llm/'
        data = {
            'llm': llm.id
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_get_user_llms(self, auth_client, user_llm):
        """Test getting user's selected LLMs."""
        url = '/api/core/user-llm/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestLLMRatings:
    """Tests for LLM rating endpoints."""

    def test_rate_llm(self, auth_client, llm, user):
        """Test rating an LLM."""
        url = '/api/core/llm-ratings/'
        data = {
            'llm': llm.id,
            'rating': 4,
            'feedback': 'Good performance'
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_rate_llm_invalid_rating(self, auth_client, llm):
        """Test rating with invalid value fails."""
        url = '/api/core/llm-ratings/'
        data = {
            'llm': llm.id,
            'rating': 10,  # Invalid rating
            'feedback': 'Test'
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTokenUsage:
    """Tests for token usage tracking."""

    def test_get_token_usage(self, auth_client, user):
        """Test getting user token usage."""
        url = '/api/core/token-usage/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_token_usage_history(self, auth_client, user):
        """Test getting token usage history."""
        url = '/api/core/token-history/'
        response = auth_client.get(url)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
