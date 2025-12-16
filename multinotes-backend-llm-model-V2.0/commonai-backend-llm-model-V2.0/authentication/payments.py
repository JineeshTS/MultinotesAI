"""
Payment utilities for MultinotesAI authentication module.

This module provides Razorpay integration for handling recurring subscription
payments and automatic renewal functionality.

Note: Main payment flows are handled in planandsubscription/razorpay_service.py
This module handles background/automated payment tasks.
"""

import logging
import razorpay
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from planandsubscription.models import UserPlan, Subscription, Transaction
from backend.exceptions import success_response, ErrorCodes

logger = logging.getLogger(__name__)


# =============================================================================
# RAZORPAY CLIENT
# =============================================================================

def get_razorpay_client():
    """
    Get Razorpay client instance.

    Returns:
        razorpay.Client: Configured Razorpay client
    """
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    if not key_id or not key_secret:
        logger.error("Razorpay credentials not configured")
        return None

    return razorpay.Client(auth=(key_id, key_secret))


# =============================================================================
# SUBSCRIPTION RENEWAL (CRON JOB)
# =============================================================================

def process_subscription_renewals():
    """
    Process automatic subscription renewals for subscriptions that are
    expiring soon or have low token balance.

    This function is intended to be called by a cron job.

    Note: Razorpay doesn't support automatic recurring payments in the same
    way Stripe does. This function logs subscriptions that need renewal
    and can be extended to send reminder emails.
    """
    logger.info("Starting subscription renewal check...")

    # Find subscriptions that are expiring within 7 days or have low tokens
    expiring_soon = timezone.now() + timedelta(days=7)

    subscriptions = Subscription.objects.filter(
        is_delete=False,
        status__in=['active', 'trial'],
        isSubscribe=True,
    ).filter(
        subscriptionExpiryDate__lte=expiring_soon
    ) | Subscription.objects.filter(
        is_delete=False,
        status__in=['active', 'trial'],
        isSubscribe=True,
        balanceToken__lte=100
    )

    renewals_needed = []
    for subscription in subscriptions:
        renewal_info = {
            'user_id': subscription.user.id,
            'user_email': subscription.user.email,
            'plan_name': subscription.plan_name,
            'expiry_date': subscription.subscriptionExpiryDate,
            'balance_tokens': subscription.balanceToken,
        }
        renewals_needed.append(renewal_info)

        # Mark subscription as needing renewal notification
        # You can extend this to send email notifications

        logger.info(
            f"Subscription renewal needed: user={subscription.user.id}, "
            f"plan={subscription.plan_name}, expires={subscription.subscriptionExpiryDate}"
        )

    logger.info(f"Subscription renewal check complete. {len(renewals_needed)} renewals needed.")

    return renewals_needed


def expire_subscriptions():
    """
    Expire subscriptions that have passed their end date.

    This function is intended to be called by a cron job.
    """
    logger.info("Starting subscription expiration check...")

    # Find subscriptions past their end date
    now = timezone.now()

    expired_subscriptions = Subscription.objects.filter(
        is_delete=False,
        status='active',
        subscriptionEndDate__lt=now
    )

    expired_count = 0
    for subscription in expired_subscriptions:
        # Move remaining balance to expired tokens
        subscription.expireToken += subscription.balanceToken
        subscription.expireFileToken += subscription.fileToken
        subscription.balanceToken = 0
        subscription.fileToken = 0
        subscription.status = 'expire'
        subscription.save()

        expired_count += 1

        logger.info(
            f"Subscription expired: user={subscription.user.id}, "
            f"plan={subscription.plan_name}"
        )

    logger.info(f"Subscription expiration check complete. {expired_count} subscriptions expired.")

    return expired_count


# =============================================================================
# API VIEWS
# =============================================================================

class GetUserPaymentHistory(APIView):
    """
    Get payment history for the authenticated user.

    GET /api/auth/payment-history/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = Transaction.objects.filter(
            user=request.user,
            is_delete=False
        ).order_by('-created_at')[:20]

        history = []
        for trans in transactions:
            history.append({
                'id': trans.id,
                'transaction_id': trans.transactionId,
                'amount': float(trans.amount),
                'plan_name': trans.plan_name,
                'duration': trans.duration,
                'tokens': trans.tokenCount,
                'file_tokens': trans.fileToken,
                'status': trans.payment_status,
                'payment_method': trans.payment_method,
                'created_at': trans.created_at.isoformat(),
            })

        return success_response({'transactions': history})


class GetCurrentSubscription(APIView):
    """
    Get current subscription details for the authenticated user.

    GET /api/auth/subscription/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Check if user is part of a cluster
        if request.user.cluster:
            subscription = request.user.cluster.subscription
        else:
            subscription = Subscription.objects.filter(
                user=request.user,
                is_delete=False
            ).first()

        if not subscription:
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.SUB_NOT_FOUND,
                    'message': 'No subscription found.'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        data = {
            'id': subscription.id,
            'plan_name': subscription.plan_name,
            'plan_for': subscription.plan_for,
            'status': subscription.status,
            'amount': float(subscription.amount) if subscription.amount else 0,

            # Token information
            'balance_token': subscription.balanceToken,
            'used_token': subscription.usedToken,
            'expire_token': subscription.expireToken,
            'total_token': subscription.totalToken,

            # File token information
            'file_token': subscription.fileToken,
            'used_file_token': subscription.usedFileToken,
            'expire_file_token': subscription.expireFileToken,
            'total_file_token': subscription.totalFileToken,

            # Dates
            'expiry_date': subscription.subscriptionExpiryDate.isoformat() if subscription.subscriptionExpiryDate else None,
            'end_date': subscription.subscriptionEndDate.isoformat() if subscription.subscriptionEndDate else None,

            # Additional info
            'feature': subscription.feature,
            'is_cluster': request.user.cluster is not None,
            'payment_status': subscription.payment_status,
        }

        return success_response(data)


class CancelSubscription(APIView):
    """
    Cancel the current subscription (disable auto-renewal).

    POST /api/auth/subscription/cancel/

    Note: This doesn't provide a refund, just disables auto-renewal.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.cluster:
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.AUTH_PERMISSION_DENIED,
                    'message': 'Cluster subscriptions can only be managed by cluster admin.'
                }
            }, status=status.HTTP_403_FORBIDDEN)

        subscription = Subscription.objects.filter(
            user=request.user,
            is_delete=False,
            status='active'
        ).first()

        if not subscription:
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.SUB_NOT_FOUND,
                    'message': 'No active subscription to cancel.'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        # Disable auto-renewal
        subscription.isSubscribe = False
        subscription.save()

        logger.info(
            f"Subscription cancelled: user={request.user.id}, "
            f"plan={subscription.plan_name}"
        )

        return success_response({
            'message': 'Subscription auto-renewal has been cancelled. '
                      'You can continue using the service until your current period ends.',
            'expiry_date': subscription.subscriptionExpiryDate.isoformat(),
        })


# =============================================================================
# LEGACY STRIPE API VIEWS (Stubs for backwards compatibility)
# =============================================================================

class CreatePaymentIntent(APIView):
    """Legacy Stripe CreatePaymentIntent stub - use Razorpay instead."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({
            'success': False,
            'error': {
                'code': 'DEPRECATED',
                'message': 'Stripe payments are deprecated. Please use Razorpay.'
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class AddCard(APIView):
    """Legacy Stripe AddCard stub - use Razorpay instead."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({
            'success': False,
            'error': {
                'code': 'DEPRECATED',
                'message': 'Stripe card management is deprecated. Please use Razorpay.'
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class GetCards(APIView):
    """Legacy Stripe GetCards stub."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success_response({'cards': []})


class UpdateCard(APIView):
    """Legacy Stripe UpdateCard stub."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({
            'success': False,
            'error': {
                'code': 'DEPRECATED',
                'message': 'Stripe card management is deprecated. Please use Razorpay.'
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class DeleteCard(APIView):
    """Legacy Stripe DeleteCard stub."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({
            'success': False,
            'error': {
                'code': 'DEPRECATED',
                'message': 'Stripe card management is deprecated. Please use Razorpay.'
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class GetCustomerDetails(APIView):
    """Legacy Stripe GetCustomerDetails stub."""
    permission_classes = [IsAuthenticated]

    def get(self, request, custId):
        return Response({
            'success': False,
            'error': {
                'code': 'DEPRECATED',
                'message': 'Stripe customer details are deprecated. Please use Razorpay.'
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class MarkCardDefault(APIView):
    """Legacy Stripe MarkCardDefault stub."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({
            'success': False,
            'error': {
                'code': 'DEPRECATED',
                'message': 'Stripe card management is deprecated. Please use Razorpay.'
            }
        }, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# LEGACY FUNCTIONS (For backwards compatibility)
# =============================================================================

def createCustomerOnStripe(name, email):
    """
    Legacy Stripe customer creation stub.

    This function was used for Stripe integration but has been replaced
    by Razorpay. Returns None since Razorpay doesn't use customer IDs
    in the same way Stripe does.

    Args:
        name: Customer name
        email: Customer email

    Returns:
        None (Razorpay doesn't require pre-created customers)
    """
    logger.debug(f"createCustomerOnStripe called (stub): {email}")
    return None


def subscriptions():
    """
    Legacy function for cron job compatibility.

    This function is called by the cron job to handle subscription processing.
    """
    # Process expirations first
    expire_subscriptions()

    # Then check for renewals needed
    process_subscription_renewals()

    logger.info(f"Cron job completed at {timezone.now()}")
