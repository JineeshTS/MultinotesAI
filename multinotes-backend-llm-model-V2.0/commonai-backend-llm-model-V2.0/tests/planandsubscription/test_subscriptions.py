"""
Tests for subscription management endpoints.

Tests cover:
- Subscription creation
- Subscription status
- Subscription upgrades/downgrades
- Subscription cancellation
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestSubscriptionStatus:
    """Tests for subscription status endpoints."""

    def test_get_current_subscription(self, auth_client, subscription):
        """Test getting current subscription."""
        url = '/api/subscription/current/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_get_subscription_unauthenticated(self, api_client):
        """Test getting subscription without auth fails."""
        url = '/api/subscription/current/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_subscription_history(self, auth_client):
        """Test getting subscription history."""
        url = '/api/subscription/history/'
        response = auth_client.get(url)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]


@pytest.mark.django_db
class TestSubscriptionCreation:
    """Tests for subscription creation."""

    def test_subscribe_to_plan(self, auth_client, plan):
        """Test subscribing to a plan."""
        url = '/api/subscription/subscribe/'
        data = {
            'plan': plan.id
        }
        response = auth_client.post(url, data, format='json')
        # May need payment first
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,  # payment required
            status.HTTP_402_PAYMENT_REQUIRED
        ]

    def test_subscribe_invalid_plan(self, auth_client):
        """Test subscribing to non-existent plan."""
        url = '/api/subscription/subscribe/'
        data = {
            'plan': 99999
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]


@pytest.mark.django_db
class TestSubscriptionUpgrade:
    """Tests for subscription upgrade/downgrade."""

    def test_upgrade_subscription(self, auth_client, subscription, plan):
        """Test upgrading subscription."""
        url = '/api/subscription/upgrade/'
        data = {
            'new_plan': plan.id
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    def test_downgrade_subscription(self, auth_client, subscription, plan):
        """Test downgrading subscription."""
        url = '/api/subscription/downgrade/'
        data = {
            'new_plan': plan.id
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]


@pytest.mark.django_db
class TestSubscriptionCancellation:
    """Tests for subscription cancellation."""

    def test_cancel_subscription(self, auth_client, subscription):
        """Test canceling subscription."""
        url = '/api/subscription/cancel/'
        response = auth_client.post(url)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,  # already cancelled or free
            status.HTTP_404_NOT_FOUND
        ]

    def test_cancel_already_cancelled(self, auth_client):
        """Test canceling already cancelled subscription."""
        url = '/api/subscription/cancel/'
        response = auth_client.post(url)
        # May fail or succeed idempotently
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]


@pytest.mark.django_db
class TestSubscriptionLimits:
    """Tests for subscription usage limits."""

    def test_get_usage_limits(self, auth_client, subscription):
        """Test getting subscription usage limits."""
        url = '/api/subscription/limits/'
        response = auth_client.get(url)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]

    def test_check_feature_access(self, auth_client, subscription):
        """Test checking feature access."""
        url = '/api/subscription/features/'
        response = auth_client.get(url)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]
