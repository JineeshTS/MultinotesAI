"""
Password reset functionality for MultinotesAI.

This module provides:
- Password reset token generation
- Password reset email sending
- Token validation and password update
"""

import secrets
import hashlib
import logging
from datetime import timedelta
from typing import Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)
User = get_user_model()


# =============================================================================
# Configuration
# =============================================================================

class PasswordResetConfig:
    """Password reset configuration."""

    TOKEN_EXPIRY_HOURS = 24
    TOKEN_LENGTH = 64
    MAX_REQUESTS_PER_HOUR = 3

    # Email settings
    EMAIL_SUBJECT = "Reset Your MultinotesAI Password"
    FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@multinotesai.com')

    # URLs
    RESET_URL_TEMPLATE = getattr(
        settings,
        'PASSWORD_RESET_URL',
        '{frontend_url}/reset-password?token={token}'
    )
    FRONTEND_URL = getattr(settings, 'FRONTEND_URL', 'https://app.multinotesai.com')


# =============================================================================
# Password Reset Token Model
# =============================================================================

from django.db import models


class PasswordResetToken(models.Model):
    """Model to store password reset tokens."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token_hash = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'password_reset_tokens'
        indexes = [
            models.Index(fields=['token_hash']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"Reset token for {self.user.email}"

    @classmethod
    def create_token(cls, user, ip_address: str = None) -> Tuple[str, 'PasswordResetToken']:
        """
        Create a new password reset token.

        Args:
            user: User requesting reset
            ip_address: IP address of request

        Returns:
            Tuple of (raw_token, PasswordResetToken instance)
        """
        # Generate secure token
        raw_token = secrets.token_urlsafe(PasswordResetConfig.TOKEN_LENGTH)

        # Hash token for storage
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Create expiry time
        expires_at = timezone.now() + timedelta(hours=PasswordResetConfig.TOKEN_EXPIRY_HOURS)

        # Invalidate existing tokens for user
        cls.objects.filter(user=user, used_at__isnull=True).update(
            used_at=timezone.now()
        )

        # Create new token
        token_obj = cls.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
        )

        return raw_token, token_obj

    @classmethod
    def verify_token(cls, raw_token: str) -> Optional['PasswordResetToken']:
        """
        Verify a password reset token.

        Args:
            raw_token: The raw token from the URL

        Returns:
            PasswordResetToken if valid, None otherwise
        """
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        try:
            token = cls.objects.get(
                token_hash=token_hash,
                used_at__isnull=True,
                expires_at__gt=timezone.now()
            )
            return token
        except cls.DoesNotExist:
            return None

    def mark_used(self):
        """Mark token as used."""
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])


# =============================================================================
# Password Reset Service
# =============================================================================

class PasswordResetService:
    """
    Service for handling password reset operations.

    Usage:
        service = PasswordResetService()
        success = service.initiate_reset("user@example.com", request)
    """

    def __init__(self):
        self.config = PasswordResetConfig

    def initiate_reset(self, email: str, ip_address: str = None) -> Tuple[bool, str]:
        """
        Initiate password reset process.

        Args:
            email: User's email address
            ip_address: IP address of request

        Returns:
            Tuple of (success, message)
        """
        # Find user
        user = User.objects.filter(email__iexact=email).first()

        if not user:
            # Don't reveal if user exists
            logger.info(f"Password reset requested for non-existent email: {email}")
            return True, "If an account exists, a reset email has been sent."

        # Check rate limit
        if self._is_rate_limited(user):
            logger.warning(f"Rate limit exceeded for password reset: {email}")
            return False, "Too many reset requests. Please try again later."

        # Create token
        raw_token, token_obj = PasswordResetToken.create_token(user, ip_address)

        # Generate reset URL
        reset_url = self.config.RESET_URL_TEMPLATE.format(
            frontend_url=self.config.FRONTEND_URL,
            token=raw_token
        )

        # Send email
        success = self._send_reset_email(user, reset_url)

        if success:
            logger.info(f"Password reset email sent to: {email}")
            return True, "If an account exists, a reset email has been sent."
        else:
            logger.error(f"Failed to send password reset email to: {email}")
            return False, "Failed to send reset email. Please try again."

    def complete_reset(self, token: str, new_password: str) -> Tuple[bool, str]:
        """
        Complete password reset with new password.

        Args:
            token: Reset token from email
            new_password: New password

        Returns:
            Tuple of (success, message)
        """
        # Verify token
        token_obj = PasswordResetToken.verify_token(token)

        if not token_obj:
            return False, "Invalid or expired reset token."

        user = token_obj.user

        # Validate password
        is_valid, validation_msg = self._validate_password(new_password, user)
        if not is_valid:
            return False, validation_msg

        # Update password
        user.set_password(new_password)
        user.save()

        # Mark token as used
        token_obj.mark_used()

        # Send confirmation email
        self._send_confirmation_email(user)

        logger.info(f"Password reset completed for: {user.email}")
        return True, "Password has been reset successfully."

    def verify_token(self, token: str) -> Tuple[bool, str]:
        """
        Verify if a reset token is valid.

        Args:
            token: Reset token to verify

        Returns:
            Tuple of (is_valid, message)
        """
        token_obj = PasswordResetToken.verify_token(token)

        if token_obj:
            return True, "Token is valid."
        return False, "Invalid or expired reset token."

    def _is_rate_limited(self, user) -> bool:
        """Check if user has exceeded rate limit."""
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_requests = PasswordResetToken.objects.filter(
            user=user,
            created_at__gte=one_hour_ago
        ).count()

        return recent_requests >= self.config.MAX_REQUESTS_PER_HOUR

    def _validate_password(self, password: str, user) -> Tuple[bool, str]:
        """Validate password meets requirements."""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."

        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter."

        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter."

        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number."

        # Check against user attributes
        if user.email and user.email.lower() in password.lower():
            return False, "Password cannot contain your email address."

        return True, "Password is valid."

    def _send_reset_email(self, user, reset_url: str) -> bool:
        """Send password reset email."""
        try:
            context = {
                'user': user,
                'reset_url': reset_url,
                'expiry_hours': self.config.TOKEN_EXPIRY_HOURS,
                'support_email': 'support@multinotesai.com',
            }

            # Try to render template, fall back to plain text
            try:
                html_message = render_to_string('emails/password_reset.html', context)
                plain_message = strip_tags(html_message)
            except Exception:
                html_message = None
                plain_message = self._get_plain_reset_email(user, reset_url)

            send_mail(
                subject=self.config.EMAIL_SUBJECT,
                message=plain_message,
                from_email=self.config.FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            return True

        except Exception as e:
            logger.error(f"Error sending reset email: {e}")
            return False

    def _get_plain_reset_email(self, user, reset_url: str) -> str:
        """Generate plain text reset email."""
        return f"""
Hello {user.first_name or 'there'},

You requested to reset your password for your MultinotesAI account.

Click the link below to reset your password:
{reset_url}

This link will expire in {self.config.TOKEN_EXPIRY_HOURS} hours.

If you didn't request this reset, you can safely ignore this email.
Your password will not be changed unless you click the link above.

Best regards,
The MultinotesAI Team

Need help? Contact us at support@multinotesai.com
        """

    def _send_confirmation_email(self, user) -> bool:
        """Send password reset confirmation email."""
        try:
            send_mail(
                subject="Your MultinotesAI Password Has Been Changed",
                message=f"""
Hello {user.first_name or 'there'},

Your password has been successfully changed.

If you did not make this change, please contact us immediately at support@multinotesai.com.

Best regards,
The MultinotesAI Team
                """,
                from_email=self.config.FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            return True
        except Exception as e:
            logger.error(f"Error sending confirmation email: {e}")
            return False


# =============================================================================
# API Views
# =============================================================================

class PasswordResetRequestView(APIView):
    """
    Request password reset endpoint.

    POST /api/auth/password-reset/
    Body: { "email": "user@example.com" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ip_address = self._get_client_ip(request)
        service = PasswordResetService()
        success, message = service.initiate_reset(email, ip_address)

        return Response(
            {'message': message},
            status=status.HTTP_200_OK if success else status.HTTP_429_TOO_MANY_REQUESTS
        )

    def _get_client_ip(self, request) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class PasswordResetVerifyView(APIView):
    """
    Verify password reset token endpoint.

    POST /api/auth/password-reset/verify/
    Body: { "token": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')

        if not token:
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = PasswordResetService()
        is_valid, message = service.verify_token(token)

        return Response(
            {'valid': is_valid, 'message': message},
            status=status.HTTP_200_OK if is_valid else status.HTTP_400_BAD_REQUEST
        )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset endpoint.

    POST /api/auth/password-reset/confirm/
    Body: { "token": "...", "password": "...", "password_confirm": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        password = request.data.get('password')
        password_confirm = request.data.get('password_confirm')

        if not all([token, password, password_confirm]):
            return Response(
                {'error': 'Token, password, and password_confirm are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if password != password_confirm:
            return Response(
                {'error': 'Passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = PasswordResetService()
        success, message = service.complete_reset(token, password)

        return Response(
            {'message': message},
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        )


# =============================================================================
# URL Configuration
# =============================================================================

"""
Add to your urls.py:

from backend.password_reset import (
    PasswordResetRequestView,
    PasswordResetVerifyView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path('api/auth/password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('api/auth/password-reset/verify/', PasswordResetVerifyView.as_view(), name='password-reset-verify'),
    path('api/auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
"""


# =============================================================================
# Singleton Instance
# =============================================================================

password_reset_service = PasswordResetService()
