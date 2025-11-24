"""
Social authentication configuration for MultinotesAI.

This module provides:
- Google OAuth integration
- Facebook OAuth integration
- GitHub OAuth integration (optional)
- Token validation and user creation
"""

import logging
import requests
from typing import Optional, Dict, Any

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)
User = get_user_model()


# =============================================================================
# Social Auth Configuration
# =============================================================================

class SocialAuthConfig:
    """Social authentication configuration."""

    # Google OAuth
    GOOGLE_CLIENT_ID = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
    GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
    GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'

    # Facebook OAuth
    FACEBOOK_APP_ID = getattr(settings, 'FACEBOOK_APP_ID', '')
    FACEBOOK_APP_SECRET = getattr(settings, 'FACEBOOK_APP_SECRET', '')
    FACEBOOK_TOKEN_URL = 'https://graph.facebook.com/v18.0/oauth/access_token'
    FACEBOOK_USERINFO_URL = 'https://graph.facebook.com/me'

    # GitHub OAuth
    GITHUB_CLIENT_ID = getattr(settings, 'GITHUB_CLIENT_ID', '')
    GITHUB_CLIENT_SECRET = getattr(settings, 'GITHUB_CLIENT_SECRET', '')
    GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
    GITHUB_USERINFO_URL = 'https://api.github.com/user'


# =============================================================================
# Social Auth Base Class
# =============================================================================

class SocialAuthProvider:
    """Base class for social auth providers."""

    provider_name = 'social'

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user info from provider.

        Args:
            access_token: OAuth access token

        Returns:
            Dict with user info or None
        """
        raise NotImplementedError

    def get_or_create_user(self, user_info: Dict) -> User:
        """
        Get or create user from social auth info.

        Args:
            user_info: User info from provider

        Returns:
            User instance
        """
        email = user_info.get('email')
        if not email:
            raise ValueError("Email is required for social authentication")

        # Check if user exists
        user = User.objects.filter(email=email).first()

        if user:
            # Update social auth info if needed
            self._update_social_info(user, user_info)
            return user

        # Create new user
        user = self._create_user(user_info)
        return user

    def _create_user(self, user_info: Dict) -> User:
        """Create a new user from social auth info."""
        email = user_info['email']
        name = user_info.get('name', '')
        first_name = user_info.get('first_name', name.split()[0] if name else '')
        last_name = user_info.get('last_name', ' '.join(name.split()[1:]) if name else '')

        user = User.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_email_verified=True,  # Email verified by provider
        )

        # Set unusable password (user authenticated via social)
        user.set_unusable_password()
        user.save()

        logger.info(f"Created new user via {self.provider_name}: {email}")
        return user

    def _update_social_info(self, user: User, user_info: Dict):
        """Update user's social auth info."""
        # Update profile picture if available
        picture_url = user_info.get('picture') or user_info.get('avatar_url')
        if picture_url and hasattr(user, 'profile'):
            # Could update profile picture here
            pass


# =============================================================================
# Google Auth Provider
# =============================================================================

class GoogleAuthProvider(SocialAuthProvider):
    """Google OAuth provider."""

    provider_name = 'google'

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Optional[str]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from Google
            redirect_uri: Redirect URI used in auth request

        Returns:
            Access token or None
        """
        try:
            response = requests.post(
                SocialAuthConfig.GOOGLE_TOKEN_URL,
                data={
                    'client_id': SocialAuthConfig.GOOGLE_CLIENT_ID,
                    'client_secret': SocialAuthConfig.GOOGLE_CLIENT_SECRET,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': redirect_uri,
                },
                timeout=10
            )
            data = response.json()
            return data.get('access_token')
        except Exception as e:
            logger.error(f"Google token exchange error: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user info from Google."""
        try:
            response = requests.get(
                SocialAuthConfig.GOOGLE_USERINFO_URL,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'email': data.get('email'),
                    'name': data.get('name'),
                    'first_name': data.get('given_name'),
                    'last_name': data.get('family_name'),
                    'picture': data.get('picture'),
                    'provider': 'google',
                    'provider_id': data.get('sub'),
                }
            return None
        except Exception as e:
            logger.error(f"Google user info error: {e}")
            return None

    def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google ID token.

        Args:
            id_token: Google ID token

        Returns:
            Token payload or None
        """
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            idinfo = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                SocialAuthConfig.GOOGLE_CLIENT_ID
            )

            return {
                'email': idinfo.get('email'),
                'name': idinfo.get('name'),
                'first_name': idinfo.get('given_name'),
                'last_name': idinfo.get('family_name'),
                'picture': idinfo.get('picture'),
                'provider': 'google',
                'provider_id': idinfo.get('sub'),
            }
        except Exception as e:
            logger.error(f"Google ID token verification error: {e}")
            return None


# =============================================================================
# Facebook Auth Provider
# =============================================================================

class FacebookAuthProvider(SocialAuthProvider):
    """Facebook OAuth provider."""

    provider_name = 'facebook'

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Optional[str]:
        """Exchange authorization code for access token."""
        try:
            response = requests.get(
                SocialAuthConfig.FACEBOOK_TOKEN_URL,
                params={
                    'client_id': SocialAuthConfig.FACEBOOK_APP_ID,
                    'client_secret': SocialAuthConfig.FACEBOOK_APP_SECRET,
                    'code': code,
                    'redirect_uri': redirect_uri,
                },
                timeout=10
            )
            data = response.json()
            return data.get('access_token')
        except Exception as e:
            logger.error(f"Facebook token exchange error: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user info from Facebook."""
        try:
            response = requests.get(
                SocialAuthConfig.FACEBOOK_USERINFO_URL,
                params={
                    'fields': 'id,name,email,first_name,last_name,picture',
                    'access_token': access_token,
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'email': data.get('email'),
                    'name': data.get('name'),
                    'first_name': data.get('first_name'),
                    'last_name': data.get('last_name'),
                    'picture': data.get('picture', {}).get('data', {}).get('url'),
                    'provider': 'facebook',
                    'provider_id': data.get('id'),
                }
            return None
        except Exception as e:
            logger.error(f"Facebook user info error: {e}")
            return None


# =============================================================================
# GitHub Auth Provider
# =============================================================================

class GitHubAuthProvider(SocialAuthProvider):
    """GitHub OAuth provider."""

    provider_name = 'github'

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Optional[str]:
        """Exchange authorization code for access token."""
        try:
            response = requests.post(
                SocialAuthConfig.GITHUB_TOKEN_URL,
                headers={'Accept': 'application/json'},
                data={
                    'client_id': SocialAuthConfig.GITHUB_CLIENT_ID,
                    'client_secret': SocialAuthConfig.GITHUB_CLIENT_SECRET,
                    'code': code,
                    'redirect_uri': redirect_uri,
                },
                timeout=10
            )
            data = response.json()
            return data.get('access_token')
        except Exception as e:
            logger.error(f"GitHub token exchange error: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user info from GitHub."""
        try:
            # Get user profile
            response = requests.get(
                SocialAuthConfig.GITHUB_USERINFO_URL,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if response.status_code != 200:
                return None

            data = response.json()

            # GitHub doesn't always return email, need to fetch separately
            email = data.get('email')
            if not email:
                email = self._get_github_email(access_token)

            name = data.get('name') or data.get('login')

            return {
                'email': email,
                'name': name,
                'first_name': name.split()[0] if name else '',
                'last_name': ' '.join(name.split()[1:]) if name and len(name.split()) > 1 else '',
                'picture': data.get('avatar_url'),
                'provider': 'github',
                'provider_id': str(data.get('id')),
            }
        except Exception as e:
            logger.error(f"GitHub user info error: {e}")
            return None

    def _get_github_email(self, access_token: str) -> Optional[str]:
        """Get primary email from GitHub."""
        try:
            response = requests.get(
                'https://api.github.com/user/emails',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if response.status_code == 200:
                emails = response.json()
                for email in emails:
                    if email.get('primary'):
                        return email.get('email')
                # Return first email if no primary
                if emails:
                    return emails[0].get('email')
            return None
        except Exception:
            return None


# =============================================================================
# API Views
# =============================================================================

class GoogleAuthView(APIView):
    """
    Google OAuth authentication endpoint.

    POST /api/auth/google/
    Body: { "id_token": "..." } or { "code": "...", "redirect_uri": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        provider = GoogleAuthProvider()

        # Handle ID token (from Google Sign-In button)
        id_token = request.data.get('id_token')
        if id_token:
            user_info = provider.verify_id_token(id_token)
            if not user_info:
                return Response(
                    {'error': 'Invalid ID token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        else:
            # Handle authorization code
            code = request.data.get('code')
            redirect_uri = request.data.get('redirect_uri')

            if not code or not redirect_uri:
                return Response(
                    {'error': 'code and redirect_uri are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            access_token = provider.exchange_code_for_token(code, redirect_uri)
            if not access_token:
                return Response(
                    {'error': 'Failed to exchange code for token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            user_info = provider.get_user_info(access_token)
            if not user_info:
                return Response(
                    {'error': 'Failed to get user info'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # Get or create user
        try:
            user = provider.get_or_create_user(user_info)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })


class FacebookAuthView(APIView):
    """
    Facebook OAuth authentication endpoint.

    POST /api/auth/facebook/
    Body: { "access_token": "..." } or { "code": "...", "redirect_uri": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        provider = FacebookAuthProvider()

        access_token = request.data.get('access_token')

        if not access_token:
            code = request.data.get('code')
            redirect_uri = request.data.get('redirect_uri')

            if not code or not redirect_uri:
                return Response(
                    {'error': 'access_token or code with redirect_uri required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            access_token = provider.exchange_code_for_token(code, redirect_uri)
            if not access_token:
                return Response(
                    {'error': 'Failed to exchange code for token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        user_info = provider.get_user_info(access_token)
        if not user_info:
            return Response(
                {'error': 'Failed to get user info'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            user = provider.get_or_create_user(user_info)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })


class GitHubAuthView(APIView):
    """
    GitHub OAuth authentication endpoint.

    POST /api/auth/github/
    Body: { "code": "...", "redirect_uri": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        provider = GitHubAuthProvider()

        code = request.data.get('code')
        redirect_uri = request.data.get('redirect_uri')

        if not code or not redirect_uri:
            return Response(
                {'error': 'code and redirect_uri are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        access_token = provider.exchange_code_for_token(code, redirect_uri)
        if not access_token:
            return Response(
                {'error': 'Failed to exchange code for token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user_info = provider.get_user_info(access_token)
        if not user_info or not user_info.get('email'):
            return Response(
                {'error': 'Could not get email from GitHub. Please ensure email is public or grant email permission.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            user = provider.get_or_create_user(user_info)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })


# =============================================================================
# URL Configuration
# =============================================================================

"""
Add to your urls.py:

from backend.social_auth import GoogleAuthView, FacebookAuthView, GitHubAuthView

urlpatterns = [
    path('api/auth/google/', GoogleAuthView.as_view(), name='auth-google'),
    path('api/auth/facebook/', FacebookAuthView.as_view(), name='auth-facebook'),
    path('api/auth/github/', GitHubAuthView.as_view(), name='auth-github'),
]
"""
