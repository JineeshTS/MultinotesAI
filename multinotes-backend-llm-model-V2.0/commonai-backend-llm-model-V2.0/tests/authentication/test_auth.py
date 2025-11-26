"""
Tests for authentication endpoints.

Tests cover:
- User registration
- Login/logout
- Password management
- Email verification
- Social login
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestUserRegistration:
    """Tests for user registration endpoint."""

    def test_register_success(self, api_client):
        """Test successful user registration."""
        url = '/api/auth/register/'
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert 'email' in response.data or 'user' in response.data

    def test_register_duplicate_email(self, api_client, user):
        """Test registration with existing email fails."""
        url = '/api/auth/register/'
        data = {
            'email': user.email,
            'username': 'differentuser',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        """Test registration with weak password fails."""
        url = '/api/auth/register/'
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': '123',
            'password2': '123'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_mismatched_passwords(self, api_client):
        """Test registration with mismatched passwords fails."""
        url = '/api/auth/register/'
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'SecurePass123!',
            'password2': 'DifferentPass123!'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, api_client, user, user_password):
        """Test successful login."""
        url = '/api/auth/login/'
        data = {
            'email': user.email,
            'password': user_password
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data or 'token' in response.data

    def test_login_invalid_credentials(self, api_client, user):
        """Test login with wrong password fails."""
        url = '/api/auth/login/'
        data = {
            'email': user.email,
            'password': 'wrongpassword'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED]

    def test_login_blocked_user(self, api_client, create_user, user_password):
        """Test blocked user cannot login."""
        blocked_user = create_user(
            email='blocked@example.com',
            username='blockeduser',
            is_blocked=True
        )
        url = '/api/auth/login/'
        data = {
            'email': blocked_user.email,
            'password': user_password
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_login_unverified_user(self, api_client, create_user, user_password):
        """Test unverified user cannot login."""
        unverified_user = create_user(
            email='unverified@example.com',
            username='unverifieduser',
            is_verified=False
        )
        url = '/api/auth/login/'
        data = {
            'email': unverified_user.email,
            'password': user_password
        }
        response = api_client.post(url, data, format='json')
        # Should fail with appropriate error
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN, status.HTTP_406_NOT_ACCEPTABLE]


@pytest.mark.django_db
class TestPasswordManagement:
    """Tests for password management endpoints."""

    def test_change_password_success(self, auth_client, user, user_password):
        """Test successful password change."""
        url = '/api/auth/change-password/'
        data = {
            'old_password': user_password,
            'new_password': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!'
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_old(self, auth_client):
        """Test password change with wrong old password fails."""
        url = '/api/auth/change-password/'
        data = {
            'old_password': 'wrongoldpassword',
            'new_password': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!'
        }
        response = auth_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_forgot_password(self, api_client, user):
        """Test forgot password request."""
        url = '/api/auth/forgot-password/'
        data = {
            'email': user.email
        }
        response = api_client.post(url, data, format='json')
        # Should accept the request (even if email not sent in test)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]


@pytest.mark.django_db
class TestUserProfile:
    """Tests for user profile endpoints."""

    def test_get_profile(self, auth_client, user):
        """Test getting user profile."""
        url = f'/api/auth/user/{user.id}/'
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('email') == user.email or 'user' in response.data

    def test_update_profile(self, auth_client, user):
        """Test updating user profile."""
        url = f'/api/auth/user/{user.id}/'
        data = {
            'name': 'Updated Name'
        }
        response = auth_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_get_profile_unauthorized(self, api_client, user):
        """Test getting profile without auth fails."""
        url = f'/api/auth/user/{user.id}/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
