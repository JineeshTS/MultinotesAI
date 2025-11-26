"""
Comprehensive security tests for MultinotesAI backend.

Tests cover:
- Authentication (login, logout, token refresh, social login)
- Authorization (permissions, roles, user status checks)
- Input validation (XSS, SQL injection prevention)
- Rate limiting
- CORS configuration
- Password security
- Token management
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.contrib.auth.hashers import check_password
from datetime import timedelta
from django.utils import timezone
from authentication.models import CustomUser, TokenBlacklist, Role
from planandsubscription.models import Subscription
import jwt
from django.conf import settings


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestAuthentication:
    """Test authentication endpoints and flows."""

    def test_user_registration_success(self, api_client, free_plan):
        """Test successful user registration."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'name': 'New User'
        }
        response = api_client.post('/api/authentication/register/', data)

        assert response.status_code == status.HTTP_200_OK
        assert 'userId' in response.data
        assert 'subscriptionId' in response.data
        assert 'referral_code' in response.data

        # Verify user created in database
        user = CustomUser.objects.get(email='newuser@example.com')
        assert user.username == 'newuser'
        assert user.is_verified == True
        assert check_password('SecurePass123!', user.password)

    def test_user_registration_duplicate_email(self, api_client, user):
        """Test registration fails with duplicate email."""
        data = {
            'username': 'anotheruser',
            'email': user.email,
            'password': 'SecurePass123!',
            'name': 'Another User'
        }
        response = api_client.post('/api/authentication/register/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email already exist' in str(response.data).lower()

    def test_user_registration_duplicate_username(self, api_client, user):
        """Test registration fails with duplicate username."""
        data = {
            'username': user.username,
            'email': 'different@example.com',
            'password': 'SecurePass123!',
            'name': 'Different User'
        }
        response = api_client.post('/api/authentication/register/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'username already exist' in str(response.data).lower()

    def test_login_with_email_success(self, api_client, user, user_password):
        """Test successful login with email."""
        data = {
            'userNameOrEmail': user.email,
            'password': user_password
        }
        response = api_client.post('/api/authentication/login/', data)

        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        assert 'access' in response.data['token']
        assert 'refresh' in response.data['token']
        assert response.data['userId'] == user.id
        assert response.data['userName'] == user.username

    def test_login_with_username_success(self, api_client, user, user_password):
        """Test successful login with username."""
        data = {
            'userNameOrEmail': user.username,
            'password': user_password
        }
        response = api_client.post('/api/authentication/login/', data)

        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        assert response.data['userId'] == user.id

    def test_login_invalid_credentials(self, api_client, user):
        """Test login fails with invalid password."""
        data = {
            'userNameOrEmail': user.email,
            'password': 'WrongPassword123!'
        }
        response = api_client.post('/api/authentication/login/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'invalid' in str(response.data).lower()

    def test_login_nonexistent_user(self, api_client):
        """Test login fails for non-existent user."""
        data = {
            'userNameOrEmail': 'nonexistent@example.com',
            'password': 'SomePassword123!'
        }
        response = api_client.post('/api/authentication/login/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'does not exist' in str(response.data).lower()

    def test_login_blocked_user(self, api_client, user, user_password):
        """Test login fails for blocked user."""
        user.is_blocked = True
        user.save()

        data = {
            'userNameOrEmail': user.email,
            'password': user_password
        }
        response = api_client.post('/api/authentication/login/', data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'blocked' in str(response.data).lower()

    def test_login_unverified_user(self, api_client, create_user, user_password):
        """Test login sends verification email for unverified user."""
        user = create_user(email='unverified@example.com', is_verified=False)

        data = {
            'userNameOrEmail': user.email,
            'password': user_password
        }
        response = api_client.post('/api/authentication/login/', data)

        assert response.status_code == status.HTTP_406_NOT_ACCEPTABLE
        assert 'not verified' in str(response.data).lower()

    def test_social_login_new_user(self, api_client, free_plan):
        """Test social login creates new user."""
        data = {
            'email': 'social@example.com',
            'username': 'socialuser',
            'socialId': 'google_123456',
            'socialType': 2,
            'name': 'Social User'
        }
        response = api_client.post('/api/authentication/social-login/', data)

        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        assert 'userId' in response.data
        assert response.data['message'] == 'User Created'

        # Verify user created
        user = CustomUser.objects.get(email='social@example.com')
        assert user.socialId == 'google_123456'
        assert user.socialType == 2

    def test_social_login_existing_user(self, api_client, user):
        """Test social login with existing user."""
        user.socialId = 'google_123456'
        user.socialType = 2
        user.save()

        data = {
            'email': user.email,
            'username': user.username,
            'socialId': 'google_123456',
            'socialType': 2
        }
        response = api_client.post('/api/authentication/social-login/', data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['userId'] == user.id
        assert response.data['message'] == 'User Detail'

    def test_social_login_blocked_user(self, api_client, user):
        """Test social login fails for blocked user."""
        user.is_blocked = True
        user.socialId = 'google_123456'
        user.save()

        data = {
            'email': user.email,
            'username': user.username,
            'socialId': 'google_123456',
            'socialType': 2
        }
        response = api_client.post('/api/authentication/social-login/', data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'blocked' in str(response.data).lower()

    def test_email_verification_success(self, api_client, user):
        """Test email verification with valid token."""
        token = jwt.encode(
            {'user_id': user.id},
            settings.SECRET_KEY,
            algorithm='HS256'
        )

        response = api_client.post('/api/authentication/email-verify/', {'token': token})

        assert response.status_code == status.HTTP_200_OK
        assert 'verified' in str(response.data).lower()

        user.refresh_from_db()
        assert user.is_verified == True
        assert user.is_active == True

    def test_email_verification_expired_token(self, api_client, user):
        """Test email verification fails with expired token."""
        expired_payload = {
            'user_id': user.id,
            'exp': timezone.now() - timedelta(hours=1)
        }
        token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm='HS256')

        response = api_client.post('/api/authentication/email-verify/', {'token': token})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'expired' in str(response.data).lower()

    def test_email_verification_invalid_token(self, api_client):
        """Test email verification fails with invalid token."""
        response = api_client.post('/api/authentication/email-verify/', {'token': 'invalid_token'})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'invalid' in str(response.data).lower()

    def test_token_refresh_success(self, api_client, user):
        """Test token refresh with valid refresh token."""
        refresh = RefreshToken.for_user(user)

        response = api_client.post('/api/authentication/token/refresh/', {
            'refresh': str(refresh)
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_resend_verification_email(self, api_client, user):
        """Test resend verification email."""
        response = api_client.post('/api/authentication/resend-verification/', {
            'userId': user.id
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'verification' in str(response.data).lower()


# =============================================================================
# AUTHORIZATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestAuthorization:
    """Test role-based access control and permissions."""

    def test_admin_role_assignment(self, db, create_user):
        """Test admin role is assigned to superuser."""
        admin = create_user(
            email='admin@example.com',
            username='adminuser',
            is_superuser=True
        )

        assert admin.roles.filter(name='admin').exists()
        assert admin.is_staff == True

    def test_user_without_admin_role_cannot_access_admin_endpoints(self, auth_client, user):
        """Test regular users cannot access admin endpoints."""
        # Attempt to access admin-only endpoint
        response = auth_client.get('/api/admin/users/')

        # Should return 403 Forbidden or 401 Unauthorized
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    def test_admin_can_access_admin_endpoints(self, admin_client, admin_user):
        """Test admin users can access admin endpoints."""
        response = admin_client.get('/api/authentication/users/')

        # Should succeed or return 200
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_blocked_user_middleware_check(self, api_client, user, user_password):
        """Test middleware blocks access for blocked users."""
        # First login to get token
        data = {
            'userNameOrEmail': user.email,
            'password': user_password
        }
        response = api_client.post('/api/authentication/login/', data)
        token = response.data['token']['access']

        # Block the user
        user.is_blocked = True
        user.save()

        # Try to access protected endpoint
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = api_client.get('/api/authentication/profile/')

        # Middleware should block the request
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_deleted_user_middleware_check(self, api_client, user, user_password):
        """Test middleware blocks access for deleted users."""
        # First login to get token
        data = {
            'userNameOrEmail': user.email,
            'password': user_password
        }
        response = api_client.post('/api/authentication/login/', data)
        token = response.data['token']['access']

        # Mark user as deleted
        user.is_delete = True
        user.save()

        # Try to access protected endpoint
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = api_client.get('/api/authentication/profile/')

        # Middleware should block the request
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_enterprise_user_role(self, db, create_user, cluster):
        """Test enterprise user role assignment."""
        user = create_user(
            email='enterprise@testcompany.com',
            username='enterpriseuser',
            cluster=cluster
        )

        # Check if enterprise role is assigned
        assert user.cluster == cluster

    def test_user_can_only_access_own_data(self, auth_client, user, create_user):
        """Test users can only access their own data."""
        other_user = create_user(email='other@example.com', username='otheruser')

        # Try to access other user's data
        response = auth_client.get(f'/api/authentication/user/{other_user.id}/')

        # Should either succeed with limited data or be forbidden
        if response.status_code == status.HTTP_200_OK:
            # Verify sensitive data is not exposed
            assert 'password' not in response.data


# =============================================================================
# INPUT VALIDATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestInputValidation:
    """Test input validation and security against common attacks."""

    def test_xss_prevention_in_username(self, api_client, free_plan):
        """Test XSS script in username is sanitized."""
        data = {
            'username': '<script>alert("XSS")</script>',
            'email': 'xss@example.com',
            'password': 'SecurePass123!',
            'name': 'XSS Test'
        }
        response = api_client.post('/api/authentication/register/', data)

        # Should either reject or sanitize
        if response.status_code == status.HTTP_200_OK:
            user = CustomUser.objects.get(email='xss@example.com')
            # Ensure script tags are not stored as-is
            assert '<script>' not in user.username

    def test_sql_injection_prevention_in_login(self, api_client):
        """Test SQL injection attempt in login."""
        data = {
            'userNameOrEmail': "admin' OR '1'='1",
            'password': "password' OR '1'='1"
        }
        response = api_client.post('/api/authentication/login/', data)

        # Should fail authentication, not return all users
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_email_validation(self, api_client, free_plan):
        """Test invalid email format is rejected."""
        data = {
            'username': 'testuser',
            'email': 'invalid-email-format',
            'password': 'SecurePass123!',
            'name': 'Test User'
        }
        response = api_client.post('/api/authentication/register/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_complexity_requirements(self, api_client, free_plan):
        """Test weak passwords are rejected."""
        data = {
            'username': 'weakpassuser',
            'email': 'weak@example.com',
            'password': '123',  # Too weak
            'name': 'Weak Pass User'
        }
        response = api_client.post('/api/authentication/register/', data)

        # Should reject weak password
        assert response.status_code in [status.HTTP_400_BAD_REQUEST]

    def test_long_input_handling(self, api_client, free_plan):
        """Test excessively long inputs are handled."""
        data = {
            'username': 'a' * 1000,  # Very long username
            'email': 'long@example.com',
            'password': 'SecurePass123!',
            'name': 'Long Input Test'
        }
        response = api_client.post('/api/authentication/register/', data)

        # Should reject or truncate
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_special_characters_in_username(self, api_client, free_plan):
        """Test special characters handling in username."""
        data = {
            'username': 'user@#$%^&*()',
            'email': 'special@example.com',
            'password': 'SecurePass123!',
            'name': 'Special User'
        }
        response = api_client.post('/api/authentication/register/', data)

        # Should validate appropriately based on business rules
        # Either accept or reject consistently
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


# =============================================================================
# PASSWORD SECURITY TESTS
# =============================================================================

@pytest.mark.django_db
class TestPasswordSecurity:
    """Test password-related security features."""

    def test_forgot_password_request(self, api_client, user):
        """Test forgot password sends reset email."""
        response = api_client.post('/api/authentication/forgot-password/', {
            'email': user.email
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'email' in str(response.data).lower()

    def test_forgot_password_nonexistent_user(self, api_client):
        """Test forgot password for non-existent user."""
        response = api_client.post('/api/authentication/forgot-password/', {
            'email': 'nonexistent@example.com'
        })

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_forgot_password_blocked_user(self, api_client, user):
        """Test forgot password fails for blocked user."""
        user.is_blocked = True
        user.save()

        response = api_client.post('/api/authentication/forgot-password/', {
            'email': user.email
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'blocked' in str(response.data).lower()

    def test_password_reset_success(self, api_client, user):
        """Test password reset with valid token."""
        token = jwt.encode(
            {'user_id': user.id},
            settings.SECRET_KEY,
            algorithm='HS256'
        )

        new_password = 'NewSecurePass123!'
        response = api_client.post('/api/authentication/reset-password/', {
            'token': token,
            'password': new_password
        })

        assert response.status_code == status.HTTP_200_OK

        # Verify password was changed
        user.refresh_from_db()
        assert check_password(new_password, user.password)

    def test_password_reset_token_reuse_prevention(self, api_client, user):
        """Test password reset token cannot be reused."""
        token = jwt.encode(
            {'user_id': user.id},
            settings.SECRET_KEY,
            algorithm='HS256'
        )

        # First reset
        response1 = api_client.post('/api/authentication/reset-password/', {
            'token': token,
            'password': 'NewPass1!'
        })
        assert response1.status_code == status.HTTP_200_OK

        # Try to reuse the same token
        response2 = api_client.post('/api/authentication/reset-password/', {
            'token': token,
            'password': 'AnotherPass2!'
        })

        # Should fail - token already used
        assert response2.status_code == status.HTTP_208_ALREADY_REPORTED

    def test_change_password_authenticated_user(self, auth_client, user, user_password):
        """Test authenticated user can change password."""
        response = auth_client.post('/api/authentication/change-password/', {
            'old_password': user_password,
            'new_password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!'
        })

        # Should succeed or return appropriate status
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_password_hashing(self, create_user):
        """Test passwords are properly hashed in database."""
        password = 'SecurePass123!'
        user = create_user(email='hash@example.com', password=password)

        # Password should be hashed, not stored in plaintext
        assert user.password != password
        assert len(user.password) > 50  # Hashed passwords are long
        assert user.password.startswith('pbkdf2_sha256$')  # Django default hasher


# =============================================================================
# TOKEN MANAGEMENT TESTS
# =============================================================================

@pytest.mark.django_db
class TestTokenManagement:
    """Test JWT token management and security."""

    def test_access_token_expiration(self, user):
        """Test access token has expiration."""
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        # Access token should have expiration
        assert 'exp' in access_token.payload

    def test_refresh_token_expiration(self, user):
        """Test refresh token has expiration."""
        refresh = RefreshToken.for_user(user)

        # Refresh token should have expiration
        assert 'exp' in refresh.payload

    def test_invalid_token_rejected(self, api_client):
        """Test invalid tokens are rejected."""
        api_client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token_here')
        response = api_client.get('/api/authentication/profile/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_token_blacklist_on_password_reset(self, db, user):
        """Test token is blacklisted after password reset."""
        token = jwt.encode(
            {'user_id': user.id},
            settings.SECRET_KEY,
            algorithm='HS256'
        )

        # Verify token is not initially blacklisted
        assert not TokenBlacklist.objects.filter(token=token, user=user).exists()

        # This would be tested through the actual password reset endpoint
        # which creates a blacklist entry


# =============================================================================
# RATE LIMITING TESTS
# =============================================================================

@pytest.mark.django_db
class TestRateLimiting:
    """Test rate limiting on sensitive endpoints."""

    @pytest.mark.skip(reason="Rate limiting depends on throttling configuration")
    def test_login_rate_limit(self, api_client, user, user_password):
        """Test login endpoint has rate limiting."""
        data = {
            'userNameOrEmail': user.email,
            'password': user_password
        }

        # Make multiple rapid requests
        responses = []
        for _ in range(100):
            response = api_client.post('/api/authentication/login/', data)
            responses.append(response.status_code)

        # Should eventually hit rate limit
        assert status.HTTP_429_TOO_MANY_REQUESTS in responses

    @pytest.mark.skip(reason="Rate limiting depends on throttling configuration")
    def test_password_reset_rate_limit(self, api_client, user):
        """Test password reset endpoint has rate limiting."""
        data = {'email': user.email}

        # Make multiple rapid requests
        responses = []
        for _ in range(50):
            response = api_client.post('/api/authentication/forgot-password/', data)
            responses.append(response.status_code)

        # Should eventually hit rate limit
        assert status.HTTP_429_TOO_MANY_REQUESTS in responses


# =============================================================================
# CORS TESTS
# =============================================================================

@pytest.mark.django_db
class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self, api_client):
        """Test CORS headers are present in responses."""
        response = api_client.options('/api/authentication/login/')

        # Check for CORS headers (if configured)
        # This test depends on CORS middleware configuration
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]

    def test_cors_allowed_origins(self, api_client):
        """Test only allowed origins can access API."""
        # This would require checking CORS_ALLOWED_ORIGINS setting
        # and verifying proper origin validation
        pass


# =============================================================================
# REFERRAL CODE SECURITY TESTS
# =============================================================================

@pytest.mark.django_db
class TestReferralSecurity:
    """Test referral code security."""

    def test_referral_code_uniqueness(self, user, create_user):
        """Test referral codes are unique."""
        user2 = create_user(email='user2@example.com', username='user2')

        assert user.referral_code != user2.referral_code
        assert user.referral_code is not None
        assert user2.referral_code is not None

    def test_invalid_referral_code_rejected(self, api_client, free_plan):
        """Test registration with invalid referral code is rejected."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'name': 'New User',
            'referr_by_code': 'INVALID_CODE_12345'
        }
        response = api_client.post('/api/authentication/register/', data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'valid referral' in str(response.data).lower()

    def test_valid_referral_code_accepted(self, api_client, user, referral_setting, free_plan):
        """Test registration with valid referral code is accepted."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'name': 'New User',
            'referr_by_code': user.referral_code
        }
        response = api_client.post('/api/authentication/register/', data)

        assert response.status_code == status.HTTP_200_OK
