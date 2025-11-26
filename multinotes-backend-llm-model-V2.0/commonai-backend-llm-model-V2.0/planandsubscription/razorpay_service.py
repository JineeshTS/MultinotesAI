"""
Razorpay Payment Integration Service for MultinotesAI.

This module provides a complete integration with Razorpay payment gateway
for handling subscriptions, payments, and webhooks.
"""

import razorpay
import hmac
import hashlib
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import UserPlan, Subscription, Transaction
from ticketandcategory.models import Coupon
from authentication.models import CustomUser, Referral, ReferralSetting
from backend.exceptions import (
    PaymentFailedError,
    InvalidCouponError,
    InvalidSignatureError,
    success_response,
    ErrorCodes,
)

logger = logging.getLogger(__name__)


# =============================================================================
# RAZORPAY CLIENT INITIALIZATION
# =============================================================================

def get_razorpay_client():
    """
    Get Razorpay client instance.

    Returns:
        razorpay.Client: Configured Razorpay client

    Raises:
        ValueError: If Razorpay credentials are not configured
    """
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    if not key_id or not key_secret:
        raise ValueError("Razorpay credentials not configured")

    return razorpay.Client(auth=(key_id, key_secret))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_discount(plan_amount, coupon):
    """
    Calculate discount amount based on coupon type.

    Args:
        plan_amount: Original plan amount
        coupon: Coupon model instance

    Returns:
        tuple: (discount_amount, final_amount)
    """
    if coupon.coupon_type == 'percentage':
        discount = (plan_amount * coupon.discount_value) / 100
        if coupon.max_discount_amount:
            discount = min(discount, coupon.max_discount_amount)
    else:  # fixed
        discount = coupon.discount_value

    final_amount = max(plan_amount - discount, 0)
    return float(discount), float(final_amount)


def verify_razorpay_signature(order_id, payment_id, signature):
    """
    Verify Razorpay payment signature.

    Args:
        order_id: Razorpay order ID
        payment_id: Razorpay payment ID
        signature: Razorpay signature to verify

    Returns:
        bool: True if signature is valid
    """
    key_secret = settings.RAZORPAY_KEY_SECRET

    if not key_secret:
        return False

    message = f"{order_id}|{payment_id}"
    generated_signature = hmac.new(
        key_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(generated_signature, signature)


def verify_webhook_signature(payload, signature):
    """
    Verify Razorpay webhook signature.

    Args:
        payload: Raw request body
        signature: X-Razorpay-Signature header value

    Returns:
        bool: True if signature is valid
    """
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    if not webhook_secret:
        return False

    generated_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(generated_signature, signature)


# =============================================================================
# API VIEWS
# =============================================================================

class CreateRazorpayOrder(APIView):
    """
    Create a Razorpay order for plan subscription.

    POST /api/payment/create-order/

    Request Body:
        - plan_id: ID of the plan to subscribe
        - coupon_code: (optional) Coupon code for discount

    Response:
        - order_id: Razorpay order ID
        - amount: Amount in paise
        - currency: Currency code (INR)
        - key_id: Razorpay key ID for frontend
        - plan_name: Name of the plan
        - original_amount: Original amount before discount
        - discount_amount: Discount applied
        - coupon_code: Applied coupon code (if any)
        - bonus_token: Bonus tokens from coupon (if any)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get('plan_id')
        coupon_code = request.data.get('coupon_code')

        # Validate plan
        if not plan_id:
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.RES_INVALID_DATA,
                    'message': 'Plan ID is required.'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan = UserPlan.objects.get(
                id=plan_id,
                is_delete=False,
                status='active'
            )
        except UserPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.RES_NOT_FOUND,
                    'message': 'Plan not found or inactive.'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        # Calculate amounts
        original_amount = float(plan.amount)
        discount_amount = 0
        bonus_token = 0
        applied_coupon = None

        # Validate and apply coupon
        if coupon_code:
            try:
                coupon = Coupon.objects.get(
                    coupon_code=coupon_code,
                    is_active=True,
                    is_delete=False
                )

                # Check coupon validity
                now = timezone.now()
                if not (coupon.start_date <= now <= coupon.end_date):
                    raise InvalidCouponError('Coupon has expired.')

                # Check minimum order amount
                if coupon.min_order_amount and original_amount < float(coupon.min_order_amount):
                    raise InvalidCouponError(
                        f'Minimum order amount for this coupon is ₹{coupon.min_order_amount}'
                    )

                discount_amount, final_amount = calculate_discount(original_amount, coupon)
                bonus_token = coupon.bonus_token or 0
                applied_coupon = coupon

            except Coupon.DoesNotExist:
                raise InvalidCouponError('Invalid coupon code.')
        else:
            final_amount = original_amount

        # Convert to paise (Razorpay uses smallest currency unit)
        amount_in_paise = int(final_amount * 100)

        try:
            # Create Razorpay order
            client = get_razorpay_client()

            order_data = {
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': f'plan_{plan_id}_{request.user.id}_{int(timezone.now().timestamp())}',
                'notes': {
                    'plan_id': str(plan_id),
                    'plan_name': plan.plan_name,
                    'user_id': str(request.user.id),
                    'user_email': request.user.email,
                    'coupon_code': coupon_code or '',
                    'discount_amount': str(discount_amount),
                    'bonus_token': str(bonus_token),
                }
            }

            order = client.order.create(data=order_data)

            # Create pending transaction record
            transaction = Transaction.objects.create(
                user=request.user,
                transactionId=order['id'],
                amount=final_amount,
                plan_name=plan.plan_name,
                duration=plan.duration,
                tokenCount=plan.totalToken,
                fileToken=plan.fileToken,
                payment_status='pending',
                payment_method='razorpay',
            )

            logger.info(
                f"Razorpay order created: {order['id']} for user {request.user.id}, "
                f"plan {plan_id}, amount {final_amount}"
            )

            return success_response({
                'order_id': order['id'],
                'amount': amount_in_paise,
                'currency': 'INR',
                'key_id': settings.RAZORPAY_KEY_ID,
                'plan_id': plan_id,
                'plan_name': plan.plan_name,
                'original_amount': original_amount,
                'discount_amount': discount_amount,
                'final_amount': final_amount,
                'coupon_code': coupon_code if applied_coupon else None,
                'bonus_token': bonus_token,
                'transaction_id': transaction.id,
                'user_email': request.user.email,
                'user_name': request.user.name or request.user.username,
            })

        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay order creation failed: {e}")
            raise PaymentFailedError(f'Failed to create payment order: {str(e)}')
        except Exception as e:
            logger.exception(f"Unexpected error creating Razorpay order: {e}")
            raise PaymentFailedError('An unexpected error occurred while creating the order.')


class VerifyRazorpayPayment(APIView):
    """
    Verify Razorpay payment and activate subscription.

    POST /api/payment/verify/

    Request Body:
        - razorpay_order_id: Order ID from Razorpay
        - razorpay_payment_id: Payment ID from Razorpay
        - razorpay_signature: Signature from Razorpay
        - plan_id: ID of the subscribed plan
        - coupon_code: (optional) Applied coupon code

    Response:
        - subscription: Subscription details
        - message: Success message
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('razorpay_order_id')
        payment_id = request.data.get('razorpay_payment_id')
        signature = request.data.get('razorpay_signature')
        plan_id = request.data.get('plan_id')
        coupon_code = request.data.get('coupon_code')

        # Validate required fields
        if not all([order_id, payment_id, signature, plan_id]):
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.RES_INVALID_DATA,
                    'message': 'Missing required payment verification fields.'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify signature
        if not verify_razorpay_signature(order_id, payment_id, signature):
            logger.warning(
                f"Invalid payment signature for order {order_id}, user {request.user.id}"
            )
            raise InvalidSignatureError()

        # Get transaction
        try:
            transaction = Transaction.objects.get(
                transactionId=order_id,
                user=request.user,
                is_delete=False
            )
        except Transaction.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.PAY_ORDER_NOT_FOUND,
                    'message': 'Transaction not found.'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if already processed
        if transaction.payment_status == 'paid':
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.RES_ALREADY_EXISTS,
                    'message': 'Payment already processed.'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get plan
        try:
            plan = UserPlan.objects.get(
                id=plan_id,
                is_delete=False
            )
        except UserPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.RES_NOT_FOUND,
                    'message': 'Plan not found.'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        # Get coupon details
        bonus_token = 0
        coupon_type = None
        discount_value = None

        if coupon_code:
            try:
                coupon = Coupon.objects.get(
                    coupon_code=coupon_code,
                    is_active=True,
                    is_delete=False
                )
                bonus_token = coupon.bonus_token or 0
                coupon_type = coupon.coupon_type
                discount_value = float(coupon.discount_value)
            except Coupon.DoesNotExist:
                pass  # Coupon might have been deleted, continue without bonus

        # Fetch payment details from Razorpay
        try:
            client = get_razorpay_client()
            payment = client.payment.fetch(payment_id)
            payment_method = payment.get('method', 'razorpay')
        except Exception as e:
            logger.error(f"Failed to fetch payment details: {e}")
            payment_method = 'razorpay'

        # Update transaction
        transaction.payment_status = 'paid'
        transaction.payment_method = payment_method
        transaction.save()

        # Calculate subscription dates
        subscription_expiry = timezone.now() + timedelta(days=plan.duration)
        subscription_end = timezone.now() + timedelta(days=plan.duration + 7)  # Grace period

        # Create or update subscription
        subscription, created = Subscription.objects.get_or_create(
            user=request.user,
            is_delete=False,
            defaults={
                'plan': plan,
                'status': 'active',
                'subscriptionExpiryDate': subscription_expiry,
                'subscriptionEndDate': subscription_end,
                'balanceToken': plan.totalToken + bonus_token,
                'fileToken': plan.fileToken,
                'payment_mode': 'online',
                'transactionId': order_id,
                'payment_status': 'paid',
                'plan_name': plan.plan_name,
                'plan_for': plan.plan_for,
                'amount': plan.amount,
                'duration': plan.duration,
                'totalToken': plan.totalToken,
                'totalFileToken': plan.fileToken,
                'feature': plan.feature,
                'discount': plan.discount,
                'coupon_code': coupon_code,
                'coupon_type': coupon_type,
                'discount_value': discount_value,
                'bonus_token': bonus_token,
            }
        )

        if not created:
            # Update existing subscription
            old_balance = subscription.balanceToken
            old_file_tokens = subscription.fileToken

            # Handle expired subscription tokens
            if subscription.subscriptionEndDate < timezone.now():
                subscription.expireToken += old_balance if old_balance > 0 else 0
                subscription.expireFileToken += old_file_tokens
                new_balance = plan.totalToken
                new_file_tokens = plan.fileToken
            elif subscription.plan and subscription.plan.is_free:
                subscription.expireToken += old_balance if old_balance > 0 else 0
                subscription.expireFileToken += old_file_tokens
                new_balance = plan.totalToken
                new_file_tokens = plan.fileToken
            else:
                # Stack tokens for active paid subscription
                new_balance = old_balance + plan.totalToken
                new_file_tokens = old_file_tokens + plan.fileToken

            subscription.plan = plan
            subscription.status = 'active'
            subscription.subscriptionExpiryDate = subscription_expiry
            subscription.subscriptionEndDate = subscription_end
            subscription.balanceToken = new_balance + bonus_token
            subscription.fileToken = new_file_tokens
            subscription.transactionId = order_id
            subscription.payment_status = 'paid'
            subscription.plan_name = plan.plan_name
            subscription.plan_for = plan.plan_for
            subscription.amount = plan.amount
            subscription.duration = plan.duration
            subscription.totalToken = plan.totalToken
            subscription.totalFileToken = plan.fileToken
            subscription.feature = plan.feature
            subscription.discount = plan.discount
            subscription.coupon_code = coupon_code
            subscription.coupon_type = coupon_type
            subscription.discount_value = discount_value
            subscription.bonus_token = bonus_token
            subscription.save()

        # Update transaction with subscription reference
        transaction.subscription = subscription
        transaction.save()

        # Process referral rewards
        self._process_referral_reward(request.user, subscription)

        logger.info(
            f"Payment verified and subscription activated: user {request.user.id}, "
            f"plan {plan_id}, order {order_id}"
        )

        return success_response({
            'subscription_id': subscription.id,
            'plan_name': plan.plan_name,
            'balance_token': subscription.balanceToken,
            'file_token': subscription.fileToken,
            'expiry_date': subscription.subscriptionExpiryDate.isoformat(),
            'status': subscription.status,
        }, message='Payment successful! Your subscription has been activated.')

    def _process_referral_reward(self, user, subscription):
        """Process referral rewards if applicable."""
        try:
            referral = Referral.objects.filter(
                referr_to=user,
                reward_given=False,
                is_delete=False
            ).first()

            if referral:
                # Add referral tokens to new user
                subscription.balanceToken += referral.refer_to_token
                subscription.save()

                # Add tokens to referrer's subscription
                referrer_subscription = Subscription.objects.filter(
                    user=referral.referr_by,
                    status__in=['active', 'trial'],
                    is_delete=False
                ).first()

                if referrer_subscription:
                    referrer_subscription.balanceToken += referral.refer_by_token
                    referrer_subscription.save()

                    referral.reward_given = True
                    referral.save()

                    logger.info(
                        f"Referral rewards processed: referrer {referral.referr_by.id}, "
                        f"new user {user.id}"
                    )
        except Exception as e:
            logger.error(f"Error processing referral reward: {e}")


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhook(APIView):
    """
    Handle Razorpay webhook events.

    POST /api/payment/webhook/

    Events handled:
        - payment.captured: Payment was successful
        - payment.failed: Payment failed
        - refund.processed: Refund was processed
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Get signature from header
        signature = request.headers.get('X-Razorpay-Signature')

        if not signature:
            logger.warning("Webhook received without signature")
            return Response({'status': 'error', 'message': 'Missing signature'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Verify signature
        if not verify_webhook_signature(request.body, signature):
            logger.warning("Invalid webhook signature")
            return Response({'status': 'error', 'message': 'Invalid signature'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Parse event
        try:
            event = request.data
            event_type = event.get('event')
            payload = event.get('payload', {})

            logger.info(f"Webhook received: {event_type}")

            if event_type == 'payment.captured':
                return self._handle_payment_captured(payload)
            elif event_type == 'payment.failed':
                return self._handle_payment_failed(payload)
            elif event_type == 'refund.processed':
                return self._handle_refund_processed(payload)
            else:
                logger.info(f"Unhandled webhook event: {event_type}")
                return Response({'status': 'ok'})

        except Exception as e:
            logger.exception(f"Error processing webhook: {e}")
            return Response({'status': 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_payment_captured(self, payload):
        """Handle successful payment capture."""
        payment = payload.get('payment', {}).get('entity', {})
        order_id = payment.get('order_id')
        payment_id = payment.get('id')

        if order_id:
            try:
                transaction = Transaction.objects.get(transactionId=order_id)
                if transaction.payment_status != 'paid':
                    transaction.payment_status = 'paid'
                    transaction.save()
                    logger.info(f"Payment captured via webhook: {order_id}")
            except Transaction.DoesNotExist:
                logger.warning(f"Transaction not found for order: {order_id}")

        return Response({'status': 'ok'})

    def _handle_payment_failed(self, payload):
        """Handle failed payment."""
        payment = payload.get('payment', {}).get('entity', {})
        order_id = payment.get('order_id')
        error_description = payment.get('error_description', 'Payment failed')

        if order_id:
            try:
                transaction = Transaction.objects.get(transactionId=order_id)
                transaction.payment_status = 'failure'
                transaction.save()
                logger.info(f"Payment failed via webhook: {order_id}, reason: {error_description}")
            except Transaction.DoesNotExist:
                logger.warning(f"Transaction not found for failed payment: {order_id}")

        return Response({'status': 'ok'})

    def _handle_refund_processed(self, payload):
        """Handle processed refund."""
        refund = payload.get('refund', {}).get('entity', {})
        payment_id = refund.get('payment_id')
        refund_amount = refund.get('amount', 0) / 100  # Convert from paise

        logger.info(f"Refund processed: payment {payment_id}, amount {refund_amount}")

        # You can add logic here to update subscription status if needed

        return Response({'status': 'ok'})


class CreateRefund(APIView):
    """
    Create a refund for a payment.

    POST /api/payment/refund/

    Request Body:
        - payment_id: Razorpay payment ID
        - amount: (optional) Amount to refund in INR (full refund if not provided)
        - reason: (optional) Reason for refund
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get('payment_id')
        amount = request.data.get('amount')
        reason = request.data.get('reason', 'requested_by_customer')

        if not payment_id:
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.RES_INVALID_DATA,
                    'message': 'Payment ID is required.'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = get_razorpay_client()

            refund_data = {
                'speed': 'normal',
                'notes': {
                    'reason': reason,
                    'user_id': str(request.user.id),
                }
            }

            if amount:
                refund_data['amount'] = int(float(amount) * 100)  # Convert to paise

            refund = client.payment.refund(payment_id, refund_data)

            logger.info(
                f"Refund initiated: payment {payment_id}, refund {refund['id']}, "
                f"user {request.user.id}"
            )

            return success_response({
                'refund_id': refund['id'],
                'payment_id': payment_id,
                'amount': refund['amount'] / 100,
                'status': refund['status'],
            }, message='Refund initiated successfully.')

        except razorpay.errors.BadRequestError as e:
            logger.error(f"Refund creation failed: {e}")
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.PAY_FAILED,
                    'message': f'Refund failed: {str(e)}'
                }
            }, status=status.HTTP_400_BAD_REQUEST)


class GetPaymentStatus(APIView):
    """
    Get payment status for an order.

    GET /api/payment/status/<order_id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            transaction = Transaction.objects.get(
                transactionId=order_id,
                user=request.user,
                is_delete=False
            )

            return success_response({
                'order_id': order_id,
                'payment_status': transaction.payment_status,
                'amount': float(transaction.amount),
                'plan_name': transaction.plan_name,
                'created_at': transaction.created_at.isoformat(),
            })

        except Transaction.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.PAY_ORDER_NOT_FOUND,
                    'message': 'Order not found.'
                }
            }, status=status.HTTP_404_NOT_FOUND)


class ValidateCoupon(APIView):
    """
    Validate a coupon code.

    POST /api/payment/validate-coupon/

    Request Body:
        - coupon_code: Coupon code to validate
        - plan_id: Plan ID to apply coupon to
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        coupon_code = request.data.get('coupon_code')
        plan_id = request.data.get('plan_id')

        if not coupon_code:
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.RES_INVALID_DATA,
                    'message': 'Coupon code is required.'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            coupon = Coupon.objects.get(
                coupon_code=coupon_code,
                is_active=True,
                is_delete=False
            )

            # Check validity dates
            now = timezone.now()
            if now < coupon.start_date:
                return Response({
                    'success': False,
                    'error': {
                        'code': ErrorCodes.PAY_INVALID_COUPON,
                        'message': 'Coupon is not yet active.'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            if now > coupon.end_date:
                return Response({
                    'success': False,
                    'error': {
                        'code': ErrorCodes.PAY_COUPON_EXPIRED,
                        'message': 'Coupon has expired.'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate discount if plan is provided
            discount_info = {}
            if plan_id:
                try:
                    plan = UserPlan.objects.get(id=plan_id, is_delete=False, status='active')
                    original_amount = float(plan.amount)

                    # Check minimum order amount
                    if coupon.min_order_amount and original_amount < float(coupon.min_order_amount):
                        return Response({
                            'success': False,
                            'error': {
                                'code': ErrorCodes.PAY_INVALID_COUPON,
                                'message': f'Minimum order amount is ₹{coupon.min_order_amount}'
                            }
                        }, status=status.HTTP_400_BAD_REQUEST)

                    discount_amount, final_amount = calculate_discount(original_amount, coupon)
                    discount_info = {
                        'original_amount': original_amount,
                        'discount_amount': discount_amount,
                        'final_amount': final_amount,
                    }
                except UserPlan.DoesNotExist:
                    pass

            return success_response({
                'valid': True,
                'coupon_code': coupon.coupon_code,
                'coupon_name': coupon.coupon_name,
                'coupon_type': coupon.coupon_type,
                'discount_value': float(coupon.discount_value),
                'max_discount': float(coupon.max_discount_amount) if coupon.max_discount_amount else None,
                'min_order_amount': float(coupon.min_order_amount) if coupon.min_order_amount else None,
                'bonus_token': coupon.bonus_token,
                'expires_at': coupon.end_date.isoformat(),
                **discount_info,
            }, message='Coupon is valid!')

        except Coupon.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': ErrorCodes.PAY_INVALID_COUPON,
                    'message': 'Invalid coupon code.'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
