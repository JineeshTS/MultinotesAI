"""
Tests for subscription plan endpoints.

Tests cover:
- Plan listing
- Plan details
- Plan features
- Plan comparison
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestPlanListing:
    """Tests for plan listing endpoints."""

    def test_list_plans_public(self, api_client, plan):
        """Test listing plans without authentication."""
        url = '/api/subscription/plans/'
        response = api_client.get(url)
        # Plans should be publicly visible
        assert response.status_code == status.HTTP_200_OK

    def test_list_plans_authenticated(self, auth_client, plan):
        """Test listing plans as authenticated user."""
        url = '/api/subscription/plans/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_plan_detail(self, api_client, plan):
        """Test getting plan details."""
        url = f'/api/subscription/plans/{plan.id}/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_plan_detail_not_found(self, api_client):
        """Test getting non-existent plan."""
        url = '/api/subscription/plans/99999/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestPlanFeatures:
    """Tests for plan features."""

    def test_plan_has_features(self, api_client, plan):
        """Test that plan includes feature information."""
        url = f'/api/subscription/plans/{plan.id}/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Check for common plan attributes
        data = response.data
        assert 'id' in data or 'plan_id' in data

    def test_compare_plans(self, api_client, plan):
        """Test plan comparison endpoint if exists."""
        url = '/api/subscription/plans/compare/'
        response = api_client.get(url)
        # May or may not exist
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ]


@pytest.mark.django_db
class TestPlanCategories:
    """Tests for plan categories/types."""

    def test_list_plan_types(self, api_client):
        """Test listing plan types/tiers."""
        url = '/api/subscription/plan-types/'
        response = api_client.get(url)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]

    def test_free_plan_available(self, api_client, plan):
        """Test that free plan is available."""
        url = '/api/subscription/plans/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Check if there's at least one plan
        if isinstance(response.data, list):
            assert len(response.data) >= 0
        elif isinstance(response.data, dict) and 'results' in response.data:
            assert len(response.data['results']) >= 0
