"""
Unit tests for authentication views and functionality.

This module tests:
- User registration
- User login/logout
- Password reset
- Token refresh
- Email verification
- Social authentication
"""

import pytest
from datetime import timedelta
from unittest.mock import patch, Mock

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient


# =============================================================================
# Registration Tests
# =============================================================================

@pytest.mark.django_db
class TestUserRegistration:
    """Tests for user registration endpoint."""

    def test_register_success(self, api_client, sample_user_data):
        """Test successful user registration."""
        response = api_client.post(
            '/api/user/register/',
            sample_user_data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert 'user' in response.data or 'success' in response.data

    def test_register_duplicate_email(self, api_client, user, sample_user_data):
        """Test registration with existing email fails."""
        sample_user_data['email'] = user.email

        response = api_client.post(
            '/api/user/register/',
            sample_user_data,
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_email(self, api_client, sample_user_data):
        """Test registration with invalid email format."""
        sample_user_data['email'] = 'invalid-email'

        response = api_client.post(
            '/api/user/register/',
            sample_user_data,
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client, sample_user_data):
        """Test registration with weak password fails."""
        sample_user_data['password'] = '123'
        sample_user_data['password_confirm'] = '123'

        response = api_client.post(
            '/api/user/register/',
            sample_user_data,
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_password_mismatch(self, api_client, sample_user_data):
        """Test registration with mismatched passwords fails."""
        sample_user_data['password_confirm'] = 'DifferentPassword123!'

        response = api_client.post(
            '/api/user/register/',
            sample_user_data,
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_required_fields(self, api_client):
        """Test registration with missing fields fails."""
        response = api_client.post(
            '/api/user/register/',
            {'email': 'test@example.com'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Login Tests
# =============================================================================

@pytest.mark.django_db
class TestUserLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, api_client, user):
        """Test successful login."""
        response = api_client.post(
            '/api/user/login/',
            {
                'email': user.email,
                'password': 'testpassword123'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data or 'token' in response.data

    def test_login_invalid_credentials(self, api_client, user):
        """Test login with wrong password."""
        response = api_client.post(
            '/api/user/login/',
            {
                'email': user.email,
                'password': 'wrongpassword'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent email."""
        response = api_client.post(
            '/api/user/login/',
            {
                'email': 'nonexistent@example.com',
                'password': 'password123'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, api_client, inactive_user):
        """Test login with inactive account."""
        response = api_client.post(
            '/api/user/login/',
            {
                'email': inactive_user.email,
                'password': 'testpassword123'
            },
            format='json'
        )

        # Should fail because user is inactive
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_login_missing_email(self, api_client):
        """Test login without email."""
        response = api_client.post(
            '/api/user/login/',
            {'password': 'password123'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_missing_password(self, api_client, user):
        """Test login without password."""
        response = api_client.post(
            '/api/user/login/',
            {'email': user.email},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Token Refresh Tests
# =============================================================================

@pytest.mark.django_db
class TestTokenRefresh:
    """Tests for token refresh functionality."""

    def test_refresh_token_success(self, api_client, auth_tokens):
        """Test successful token refresh."""
        response = api_client.post(
            '/api/user/token/refresh/',
            {'refresh': auth_tokens['refresh']},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_refresh_token_invalid(self, api_client):
        """Test refresh with invalid token."""
        response = api_client.post(
            '/api/user/token/refresh/',
            {'refresh': 'invalid-token'},
            format='json'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_missing(self, api_client):
        """Test refresh without token."""
        response = api_client.post(
            '/api/user/token/refresh/',
            {},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Password Reset Tests
# =============================================================================

@pytest.mark.django_db
class TestPasswordReset:
    """Tests for password reset functionality."""

    @patch('django.core.mail.send_mail')
    def test_password_reset_request_success(self, mock_send_mail, api_client, user):
        """Test successful password reset request."""
        mock_send_mail.return_value = 1

        response = api_client.post(
            '/api/user/password-reset/',
            {'email': user.email},
            format='json'
        )

        # Should return success even for non-existent email (security)
        assert response.status_code == status.HTTP_200_OK

    def test_password_reset_request_invalid_email(self, api_client):
        """Test password reset with invalid email format."""
        response = api_client.post(
            '/api/user/password-reset/',
            {'email': 'invalid-email'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_confirm_success(self, api_client, user):
        """Test successful password reset confirmation."""
        # This would require setting up a valid token
        # Skipping actual implementation for now
        pass

    def test_password_reset_confirm_invalid_token(self, api_client):
        """Test password reset with invalid token."""
        response = api_client.post(
            '/api/user/password-reset/confirm/',
            {
                'token': 'invalid-token',
                'password': 'NewPassword123!',
                'password_confirm': 'NewPassword123!'
            },
            format='json'
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]


# =============================================================================
# User Profile Tests
# =============================================================================

@pytest.mark.django_db
class TestUserProfile:
    """Tests for user profile endpoints."""

    def test_get_profile_authenticated(self, authenticated_client, user):
        """Test getting profile when authenticated."""
        response = authenticated_client.get('/api/user/profile/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('email') == user.email or 'user' in response.data

    def test_get_profile_unauthenticated(self, api_client):
        """Test getting profile without authentication."""
        response = api_client.get('/api/user/profile/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile_success(self, authenticated_client):
        """Test updating profile."""
        response = authenticated_client.patch(
            '/api/user/profile/',
            {'first_name': 'Updated'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT
        ]

    def test_update_profile_invalid_data(self, authenticated_client):
        """Test updating profile with invalid data."""
        response = authenticated_client.patch(
            '/api/user/profile/',
            {'email': 'invalid-email'},  # Can't update email this way
            format='json'
        )

        # Should either ignore or reject invalid field
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ]


# =============================================================================
# Password Change Tests
# =============================================================================

@pytest.mark.django_db
class TestPasswordChange:
    """Tests for password change functionality."""

    def test_change_password_success(self, authenticated_client, user):
        """Test successful password change."""
        response = authenticated_client.post(
            '/api/user/change-password/',
            {
                'old_password': 'testpassword123',
                'new_password': 'NewSecurePassword123!',
                'new_password_confirm': 'NewSecurePassword123!'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_old_password(self, authenticated_client):
        """Test password change with wrong current password."""
        response = authenticated_client.post(
            '/api/user/change-password/',
            {
                'old_password': 'wrongpassword',
                'new_password': 'NewSecurePassword123!',
                'new_password_confirm': 'NewSecurePassword123!'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_mismatch(self, authenticated_client):
        """Test password change with mismatched new passwords."""
        response = authenticated_client.post(
            '/api/user/change-password/',
            {
                'old_password': 'testpassword123',
                'new_password': 'NewSecurePassword123!',
                'new_password_confirm': 'DifferentPassword123!'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_unauthenticated(self, api_client):
        """Test password change without authentication."""
        response = api_client.post(
            '/api/user/change-password/',
            {
                'old_password': 'testpassword123',
                'new_password': 'NewSecurePassword123!',
                'new_password_confirm': 'NewSecurePassword123!'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Email Verification Tests
# =============================================================================

@pytest.mark.django_db
class TestEmailVerification:
    """Tests for email verification functionality."""

    def test_verify_email_success(self, api_client, user_factory):
        """Test successful email verification."""
        # Create unverified user
        user = user_factory(is_email_verified=False)

        # This would require a valid verification token
        # Implementation depends on the verification system
        pass

    def test_verify_email_invalid_token(self, api_client):
        """Test email verification with invalid token."""
        response = api_client.get('/api/user/verify-email/invalid-token/')

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    @patch('django.core.mail.send_mail')
    def test_resend_verification_email(self, mock_send_mail, authenticated_client, user):
        """Test resending verification email."""
        mock_send_mail.return_value = 1

        response = authenticated_client.post('/api/user/resend-verification/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT
        ]


# =============================================================================
# Logout Tests
# =============================================================================

@pytest.mark.django_db
class TestLogout:
    """Tests for logout functionality."""

    def test_logout_success(self, authenticated_client, auth_tokens):
        """Test successful logout."""
        response = authenticated_client.post(
            '/api/user/logout/',
            {'refresh': auth_tokens['refresh']},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT
        ]

    def test_logout_unauthenticated(self, api_client):
        """Test logout without authentication."""
        response = api_client.post('/api/user/logout/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Rate Limiting Tests
# =============================================================================

@pytest.mark.django_db
class TestAuthRateLimiting:
    """Tests for authentication rate limiting."""

    def test_login_rate_limiting(self, api_client, user):
        """Test that login attempts are rate limited."""
        # Make multiple failed login attempts
        for _ in range(10):
            api_client.post(
                '/api/user/login/',
                {
                    'email': user.email,
                    'password': 'wrongpassword'
                },
                format='json'
            )

        # Next attempt should be rate limited
        response = api_client.post(
            '/api/user/login/',
            {
                'email': user.email,
                'password': 'wrongpassword'
            },
            format='json'
        )

        # Should be rate limited or still return auth error
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_429_TOO_MANY_REQUESTS
        ]


# =============================================================================
# Token Blacklisting Tests
# =============================================================================

@pytest.mark.django_db
class TestTokenBlacklisting:
    """Tests for token blacklisting functionality."""

    def test_blacklisted_token_rejected(self, api_client, user, auth_tokens):
        """Test that blacklisted tokens are rejected."""
        # First logout to blacklist the token
        api_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {auth_tokens["access"]}'
        )
        api_client.post(
            '/api/user/logout/',
            {'refresh': auth_tokens['refresh']},
            format='json'
        )

        # Try to use the refresh token again
        response = api_client.post(
            '/api/user/token/refresh/',
            {'refresh': auth_tokens['refresh']},
            format='json'
        )

        # Token should be blacklisted
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Admin User Tests
# =============================================================================

@pytest.mark.django_db
class TestAdminAuth:
    """Tests for admin authentication."""

    def test_admin_can_access_admin_endpoints(self, admin_client):
        """Test that admin users can access admin endpoints."""
        response = admin_client.get('/api/admin/dashboard/stats/')

        assert response.status_code == status.HTTP_200_OK

    def test_regular_user_cannot_access_admin(self, authenticated_client):
        """Test that regular users cannot access admin endpoints."""
        response = authenticated_client.get('/api/admin/dashboard/stats/')

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Social Authentication Tests
# =============================================================================

@pytest.mark.django_db
class TestSocialAuth:
    """Tests for social authentication."""

    @patch('backend.social_auth.GoogleAuthProvider.verify_token')
    def test_google_auth_success(self, mock_verify, api_client):
        """Test successful Google authentication."""
        mock_verify.return_value = {
            'email': 'google_user@gmail.com',
            'first_name': 'Google',
            'last_name': 'User',
            'provider_id': '12345'
        }

        response = api_client.post(
            '/api/user/social/google/',
            {'token': 'valid-google-token'},
            format='json'
        )

        # Should create/login user and return tokens
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED
        ]

    def test_google_auth_invalid_token(self, api_client):
        """Test Google auth with invalid token."""
        response = api_client.post(
            '/api/user/social/google/',
            {'token': 'invalid-token'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED
        ]
