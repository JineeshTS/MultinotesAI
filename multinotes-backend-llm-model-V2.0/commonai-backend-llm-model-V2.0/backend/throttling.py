"""
Custom throttling classes for MultinotesAI API.

This module provides rate limiting for:
- Anonymous users
- Authenticated users
- AI generation endpoints
- Payment endpoints
- File upload endpoints
"""

from rest_framework.throttling import (
    UserRateThrottle,
    AnonRateThrottle,
    SimpleRateThrottle,
)
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Base Throttle Classes
# =============================================================================

class AnonymousThrottle(AnonRateThrottle):
    """
    Throttle for anonymous (unauthenticated) users.

    Default: 100 requests per hour
    """
    rate = '100/hour'
    scope = 'anon'


class AuthenticatedThrottle(UserRateThrottle):
    """
    Throttle for authenticated users.

    Default: 1000 requests per hour
    """
    rate = '1000/hour'
    scope = 'user'


class BurstThrottle(UserRateThrottle):
    """
    Throttle to prevent burst requests.

    Default: 60 requests per minute
    """
    rate = '60/minute'
    scope = 'burst'


# =============================================================================
# AI Generation Throttles
# =============================================================================

class AIGenerationThrottle(SimpleRateThrottle):
    """
    Throttle for AI text generation endpoints.

    Limits based on user's subscription tier:
    - Free: 10/hour
    - Basic: 50/hour
    - Pro: 200/hour
    - Enterprise: 1000/hour
    """
    scope = 'ai_generation'

    # Default rates by plan
    PLAN_RATES = {
        'free': '10/hour',
        'basic': '50/hour',
        'pro': '200/hour',
        'enterprise': '1000/hour',
    }

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return f"throttle_ai_gen_{request.user.id}"
        return self.get_ident(request)

    def get_rate(self):
        """Get rate based on user's subscription."""
        if hasattr(self, '_rate'):
            return self._rate
        return self.PLAN_RATES.get('free')

    def allow_request(self, request, view):
        if request.user.is_authenticated:
            # Get user's subscription plan
            plan = self._get_user_plan(request.user)
            self._rate = self.PLAN_RATES.get(plan, self.PLAN_RATES['free'])
        else:
            self._rate = self.PLAN_RATES['free']

        return super().allow_request(request, view)

    def _get_user_plan(self, user):
        """Get user's current subscription plan."""
        try:
            from planandsubscription.models import Subscription
            subscription = Subscription.objects.filter(
                user=user,
                is_delete=False,
                status='active'
            ).select_related('plan').first()

            if subscription and subscription.plan:
                return subscription.plan.name.lower()
        except Exception as e:
            logger.warning(f"Error getting user plan for throttling: {e}")
        return 'free'


class AIImageGenerationThrottle(AIGenerationThrottle):
    """
    Throttle for AI image generation endpoints.

    More restrictive than text generation:
    - Free: 5/hour
    - Basic: 20/hour
    - Pro: 100/hour
    - Enterprise: 500/hour
    """
    scope = 'ai_image_generation'

    PLAN_RATES = {
        'free': '5/hour',
        'basic': '20/hour',
        'pro': '100/hour',
        'enterprise': '500/hour',
    }

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return f"throttle_ai_img_{request.user.id}"
        return self.get_ident(request)


class StreamingThrottle(SimpleRateThrottle):
    """
    Throttle for streaming AI responses.

    - Free: 5/hour
    - Basic: 30/hour
    - Pro: 100/hour
    - Enterprise: unlimited
    """
    scope = 'streaming'

    PLAN_RATES = {
        'free': '5/hour',
        'basic': '30/hour',
        'pro': '100/hour',
        'enterprise': '10000/hour',  # Effectively unlimited
    }

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return f"throttle_stream_{request.user.id}"
        return self.get_ident(request)


# =============================================================================
# File Upload Throttles
# =============================================================================

class FileUploadThrottle(SimpleRateThrottle):
    """
    Throttle for file upload endpoints.

    - Free: 10/day
    - Basic: 50/day
    - Pro: 200/day
    - Enterprise: 1000/day
    """
    scope = 'file_upload'

    PLAN_RATES = {
        'free': '10/day',
        'basic': '50/day',
        'pro': '200/day',
        'enterprise': '1000/day',
    }

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return f"throttle_upload_{request.user.id}"
        return self.get_ident(request)

    def allow_request(self, request, view):
        if request.user.is_authenticated:
            plan = self._get_user_plan(request.user)
            self.rate = self.PLAN_RATES.get(plan, self.PLAN_RATES['free'])
        else:
            self.rate = self.PLAN_RATES['free']

        return super().allow_request(request, view)

    def _get_user_plan(self, user):
        """Get user's current subscription plan."""
        try:
            from planandsubscription.models import Subscription
            subscription = Subscription.objects.filter(
                user=user,
                is_delete=False,
                status='active'
            ).select_related('plan').first()

            if subscription and subscription.plan:
                return subscription.plan.name.lower()
        except Exception:
            pass
        return 'free'


# =============================================================================
# Payment Throttles
# =============================================================================

class PaymentThrottle(SimpleRateThrottle):
    """
    Throttle for payment-related endpoints.

    Very restrictive to prevent abuse:
    - 10 requests per hour per user
    """
    scope = 'payment'
    rate = '10/hour'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return f"throttle_payment_{request.user.id}"
        return self.get_ident(request)


class WebhookThrottle(SimpleRateThrottle):
    """
    Throttle for webhook endpoints.

    More permissive for payment provider webhooks:
    - 100 requests per minute per IP
    """
    scope = 'webhook'
    rate = '100/minute'

    def get_cache_key(self, request, view):
        return f"throttle_webhook_{self.get_ident(request)}"


# =============================================================================
# Authentication Throttles
# =============================================================================

class LoginThrottle(SimpleRateThrottle):
    """
    Throttle for login attempts.

    Prevents brute force attacks:
    - 5 attempts per minute per IP
    - 20 attempts per hour per IP
    """
    scope = 'login'
    rate = '5/minute'

    def get_cache_key(self, request, view):
        return f"throttle_login_{self.get_ident(request)}"


class PasswordResetThrottle(SimpleRateThrottle):
    """
    Throttle for password reset requests.

    - 3 requests per hour per IP
    """
    scope = 'password_reset'
    rate = '3/hour'

    def get_cache_key(self, request, view):
        # Also throttle by email if provided
        email = request.data.get('email', '')
        if email:
            return f"throttle_pwreset_{email}"
        return f"throttle_pwreset_{self.get_ident(request)}"


class RegistrationThrottle(SimpleRateThrottle):
    """
    Throttle for user registration.

    - 5 registrations per hour per IP
    """
    scope = 'registration'
    rate = '5/hour'

    def get_cache_key(self, request, view):
        return f"throttle_register_{self.get_ident(request)}"


# =============================================================================
# Admin Throttles
# =============================================================================

class AdminThrottle(UserRateThrottle):
    """
    Throttle for admin endpoints.

    Higher limits for admin users:
    - 5000 requests per hour
    """
    rate = '5000/hour'
    scope = 'admin'

    def allow_request(self, request, view):
        # Only apply to admin users
        if not request.user.is_authenticated or not request.user.is_staff:
            return True  # Let other throttles handle non-admin users
        return super().allow_request(request, view)


# =============================================================================
# Utility Functions
# =============================================================================

def get_throttle_status(user):
    """
    Get current throttle status for a user.

    Returns dict with remaining requests for each throttle type.
    """
    status = {}

    throttle_types = [
        ('ai_generation', AIGenerationThrottle),
        ('ai_image', AIImageGenerationThrottle),
        ('file_upload', FileUploadThrottle),
        ('payment', PaymentThrottle),
    ]

    for name, throttle_class in throttle_types:
        throttle = throttle_class()
        cache_key = f"throttle_{name}_{user.id}"

        # Get current request count from cache
        history = cache.get(cache_key, [])
        rate = throttle.get_rate() if hasattr(throttle, 'get_rate') else throttle.rate

        if rate:
            num_requests, duration = throttle.parse_rate(rate)
            remaining = max(0, num_requests - len(history))
            status[name] = {
                'limit': num_requests,
                'remaining': remaining,
                'reset_seconds': duration,
            }

    return status


def clear_throttle(user, throttle_type='all'):
    """
    Clear throttle cache for a user.

    Args:
        user: User instance
        throttle_type: 'all' or specific type like 'ai_generation'
    """
    if throttle_type == 'all':
        types = ['ai_gen', 'ai_img', 'stream', 'upload', 'payment']
    else:
        types = [throttle_type]

    for t in types:
        cache_key = f"throttle_{t}_{user.id}"
        cache.delete(cache_key)

    logger.info(f"Cleared throttle cache for user {user.id}: {throttle_type}")


# =============================================================================
# DRF Settings Configuration
# =============================================================================

# Add this to your settings.py:
"""
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'backend.throttling.AnonymousThrottle',
        'backend.throttling.AuthenticatedThrottle',
        'backend.throttling.BurstThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'burst': '60/minute',
        'ai_generation': '50/hour',
        'ai_image_generation': '20/hour',
        'file_upload': '50/day',
        'payment': '10/hour',
        'login': '5/minute',
        'password_reset': '3/hour',
        'registration': '5/hour',
    },
}
"""
