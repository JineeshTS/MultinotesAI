"""
Base utilities and common functions for coreapp views.

This module contains shared utilities, formatters, and base classes
used across all view modules.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Pagination Classes
# =============================================================================

class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for list views."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargeResultsSetPagination(PageNumberPagination):
    """Larger pagination for data-heavy endpoints."""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200


# =============================================================================
# Utility Functions
# =============================================================================

def format_number(num):
    """Format large numbers with K/M/B suffixes."""
    if num is None:
        return "0"
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def calculate_storage_size(size_bytes):
    """Convert bytes to human-readable format."""
    if size_bytes is None:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def get_date_range(days=30):
    """Get start and end dates for analytics."""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


# =============================================================================
# Response Helpers
# =============================================================================

def success_response(data=None, message="Success", status_code=200):
    """Create a standardized success response."""
    response = {
        'status': status_code,
        'message': message,
    }
    if data is not None:
        response['data'] = data
    return Response(response, status=status_code)


def error_response(message="An error occurred", status_code=400, errors=None):
    """Create a standardized error response."""
    response = {
        'status': status_code,
        'message': message,
    }
    if errors:
        response['errors'] = errors
    return Response(response, status=status_code)


def paginated_response(queryset, serializer_class, request, context=None):
    """Helper to create paginated responses."""
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = serializer_class(page, many=True, context=context or {})
        return paginator.get_paginated_response(serializer.data)
    serializer = serializer_class(queryset, many=True, context=context or {})
    return Response(serializer.data)


# =============================================================================
# Token Management Utilities
# =============================================================================

def check_user_tokens(user, required_tokens=1, token_type='text'):
    """
    Check if user has enough tokens.

    Args:
        user: User instance
        required_tokens: Number of tokens required
        token_type: 'text' or 'file'

    Returns:
        tuple: (has_tokens: bool, remaining: int, message: str)
    """
    from planandsubscription.models import Subscription

    try:
        subscription = Subscription.objects.filter(
            user=user,
            is_delete=False,
            status='active'
        ).first()

        if not subscription:
            return False, 0, "No active subscription found"

        if token_type == 'text':
            remaining = subscription.balanceToken or 0
        else:
            remaining = subscription.fileToken or 0

        if remaining < required_tokens:
            return False, remaining, f"Insufficient {token_type} tokens"

        return True, remaining, "OK"

    except Exception as e:
        logger.error(f"Error checking tokens for user {user.id}: {e}")
        return False, 0, "Error checking token balance"


def deduct_tokens(user, tokens_used, token_type='text'):
    """
    Deduct tokens from user's subscription.

    Args:
        user: User instance
        tokens_used: Number of tokens to deduct
        token_type: 'text' or 'file'

    Returns:
        bool: True if successful
    """
    from planandsubscription.models import Subscription

    try:
        subscription = Subscription.objects.filter(
            user=user,
            is_delete=False,
            status='active'
        ).first()

        if not subscription:
            return False

        if token_type == 'text':
            subscription.balanceToken = max(0, (subscription.balanceToken or 0) - tokens_used)
            subscription.usedToken = (subscription.usedToken or 0) + tokens_used
        else:
            subscription.fileToken = max(0, (subscription.fileToken or 0) - tokens_used)

        subscription.save()
        return True

    except Exception as e:
        logger.error(f"Error deducting tokens for user {user.id}: {e}")
        return False


# =============================================================================
# Validation Helpers
# =============================================================================

def validate_ownership(user, obj, owner_field='user'):
    """
    Validate that user owns the object.

    Args:
        user: User instance
        obj: Model instance to check
        owner_field: Name of the owner field

    Returns:
        bool: True if user owns the object
    """
    owner = getattr(obj, owner_field, None)
    if hasattr(owner, 'id'):
        return owner.id == user.id
    return owner == user.id


def get_user_subscription(user):
    """Get user's active subscription."""
    from planandsubscription.models import Subscription

    return Subscription.objects.filter(
        user=user,
        is_delete=False,
        status='active'
    ).select_related('plan').first()


def get_user_storage(user):
    """Get user's storage usage record."""
    from coreapp.models import StorageUsage

    storage, created = StorageUsage.objects.get_or_create(
        user=user,
        is_delete=False,
        defaults={'status': 'active'}
    )
    return storage
