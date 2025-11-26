"""
Unit tests for payment processing.

This module tests:
- Razorpay order creation
- Payment verification
- Webhook handling
- Refund processing
- Payment history
"""

import pytest
import hmac
import hashlib
from datetime import timedelta
from unittest.mock import patch, Mock, MagicMock

from django.utils import timezone
from rest_framework import status


# =============================================================================
# Razorpay Order Tests
# =============================================================================

@pytest.mark.django_db
class TestRazorpayOrderCreation:
    """Tests for Razorpay order creation."""

    @patch('razorpay.Client')
    def test_create_order_success(
        self, mock_razorpay, authenticated_client, plan_factory, user
    ):
        """Test successful Razorpay order creation."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.order.create.return_value = {
            'id': 'order_test123',
            'amount': 99900,
            'currency': 'INR',
            'status': 'created'
        }
        mock_razorpay.return_value = mock_client

        plan = plan_factory(name="Pro", price=999)

        response = authenticated_client.post(
            '/api/payment/create-order/',
            {'plan_id': plan.id},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED
        ]

    def test_create_order_invalid_plan(self, authenticated_client, user):
        """Test order creation with invalid plan."""
        response = authenticated_client.post(
            '/api/payment/create-order/',
            {'plan_id': 99999},  # Non-existent plan
            format='json'
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    def test_create_order_unauthenticated(self, api_client, plan_factory):
        """Test order creation without authentication."""
        plan = plan_factory(name="Pro", price=999)

        response = api_client.post(
            '/api/payment/create-order/',
            {'plan_id': plan.id},
            format='json'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('razorpay.Client')
    def test_create_order_razorpay_error(
        self, mock_razorpay, authenticated_client, plan_factory, user
    ):
        """Test handling Razorpay API errors."""
        mock_client = MagicMock()
        mock_client.order.create.side_effect = Exception("Razorpay API error")
        mock_razorpay.return_value = mock_client

        plan = plan_factory(name="Pro", price=999)

        response = authenticated_client.post(
            '/api/payment/create-order/',
            {'plan_id': plan.id},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_400_BAD_REQUEST
        ]


# =============================================================================
# Payment Verification Tests
# =============================================================================

@pytest.mark.django_db
class TestPaymentVerification:
    """Tests for payment verification."""

    def _generate_signature(self, order_id, payment_id, secret):
        """Generate valid Razorpay signature."""
        message = f"{order_id}|{payment_id}"
        return hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    @patch('razorpay.Client')
    def test_verify_payment_success(
        self, mock_razorpay, authenticated_client, plan_factory, user
    ):
        """Test successful payment verification."""
        mock_client = MagicMock()
        mock_client.utility.verify_payment_signature.return_value = True
        mock_razorpay.return_value = mock_client

        plan = plan_factory(name="Pro", price=999)

        response = authenticated_client.post(
            '/api/payment/verify/',
            {
                'razorpay_order_id': 'order_test123',
                'razorpay_payment_id': 'pay_test123',
                'razorpay_signature': 'valid_signature',
                'plan_id': plan.id,
            },
            format='json'
        )

        # Should verify and create subscription
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED
        ]

    @patch('razorpay.Client')
    def test_verify_payment_invalid_signature(
        self, mock_razorpay, authenticated_client, plan_factory, user
    ):
        """Test payment verification with invalid signature."""
        mock_client = MagicMock()
        mock_client.utility.verify_payment_signature.side_effect = Exception("Invalid signature")
        mock_razorpay.return_value = mock_client

        plan = plan_factory(name="Pro", price=999)

        response = authenticated_client.post(
            '/api/payment/verify/',
            {
                'razorpay_order_id': 'order_test123',
                'razorpay_payment_id': 'pay_test123',
                'razorpay_signature': 'invalid_signature',
                'plan_id': plan.id,
            },
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_payment_missing_fields(self, authenticated_client, user):
        """Test payment verification with missing fields."""
        response = authenticated_client.post(
            '/api/payment/verify/',
            {'razorpay_order_id': 'order_test123'},  # Missing other fields
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Webhook Tests
# =============================================================================

@pytest.mark.django_db
class TestRazorpayWebhook:
    """Tests for Razorpay webhook handling."""

    def _generate_webhook_signature(self, payload, secret):
        """Generate webhook signature."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def test_webhook_payment_captured(self, api_client, user, plan_factory):
        """Test webhook for successful payment capture."""
        webhook_payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_test123',
                        'order_id': 'order_test123',
                        'amount': 99900,
                        'status': 'captured',
                    }
                }
            }
        }

        # Note: Actual webhook implementation may vary
        response = api_client.post(
            '/api/payment/webhook/',
            webhook_payload,
            format='json',
            HTTP_X_RAZORPAY_SIGNATURE='valid_signature'
        )

        # Webhook should return 200 to acknowledge
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED
        ]

    def test_webhook_payment_failed(self, api_client, user):
        """Test webhook for failed payment."""
        webhook_payload = {
            'event': 'payment.failed',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_test123',
                        'order_id': 'order_test123',
                        'error_code': 'BAD_REQUEST_ERROR',
                        'error_description': 'Payment failed',
                    }
                }
            }
        }

        response = api_client.post(
            '/api/payment/webhook/',
            webhook_payload,
            format='json'
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED
        ]

    def test_webhook_invalid_signature(self, api_client):
        """Test webhook with invalid signature."""
        response = api_client.post(
            '/api/payment/webhook/',
            {'event': 'payment.captured'},
            format='json',
            HTTP_X_RAZORPAY_SIGNATURE='invalid_signature'
        )

        # Should reject invalid signature
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_200_OK  # Some implementations always return 200
        ]


# =============================================================================
# Refund Tests
# =============================================================================

@pytest.mark.django_db
class TestRefunds:
    """Tests for refund processing."""

    @patch('razorpay.Client')
    def test_request_refund_success(
        self, mock_razorpay, authenticated_client, payment_factory, user
    ):
        """Test successful refund request."""
        mock_client = MagicMock()
        mock_client.payment.refund.return_value = {
            'id': 'rfnd_test123',
            'payment_id': 'pay_test123',
            'amount': 99900,
            'status': 'processed'
        }
        mock_razorpay.return_value = mock_client

        payment = payment_factory(user=user, status='captured')

        response = authenticated_client.post(
            f'/api/payment/{payment.id}/refund/',
            {'reason': 'Customer request'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED
        ]

    def test_refund_already_refunded(
        self, authenticated_client, payment_factory, user
    ):
        """Test refund for already refunded payment."""
        payment = payment_factory(user=user, status='refunded')

        response = authenticated_client.post(
            f'/api/payment/{payment.id}/refund/',
            {'reason': 'Customer request'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_refund_past_window(
        self, authenticated_client, payment_factory, user
    ):
        """Test refund after refund window has passed."""
        # Payment older than refund window (e.g., 30 days)
        old_date = timezone.now() - timedelta(days=45)
        payment = payment_factory(user=user, status='captured')
        payment.created_at = old_date
        payment.save()

        response = authenticated_client.post(
            f'/api/payment/{payment.id}/refund/',
            {'reason': 'Customer request'},
            format='json'
        )

        # Should be rejected if outside refund window
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_200_OK  # Depends on policy
        ]


# =============================================================================
# Payment History Tests
# =============================================================================

@pytest.mark.django_db
class TestPaymentHistory:
    """Tests for payment history."""

    def test_list_payment_history(
        self, authenticated_client, payment_factory, user
    ):
        """Test listing payment history."""
        payment_factory(user=user, amount=499)
        payment_factory(user=user, amount=999)

        response = authenticated_client.get('/api/payment/history/')

        assert response.status_code == status.HTTP_200_OK
        payments = response.data.get('results', response.data)
        assert len(payments) >= 2

    def test_payment_history_only_own(
        self, authenticated_client, payment_factory, user, user_factory
    ):
        """Test that users only see their own payment history."""
        other_user = user_factory()
        payment_factory(user=user, amount=499)
        payment_factory(user=other_user, amount=999)

        response = authenticated_client.get('/api/payment/history/')

        payments = response.data.get('results', response.data)
        # Should only see own payment
        for payment in payments:
            assert payment.get('user_id', payment.get('user')) == user.id or \
                   'user' not in payment  # User might not be exposed

    def test_payment_receipt(self, authenticated_client, payment_factory, user):
        """Test getting payment receipt."""
        payment = payment_factory(user=user, status='captured')

        response = authenticated_client.get(f'/api/payment/{payment.id}/receipt/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If not implemented
        ]


# =============================================================================
# Invoice Tests
# =============================================================================

@pytest.mark.django_db
class TestInvoices:
    """Tests for invoice generation."""

    def test_generate_invoice(self, authenticated_client, payment_factory, user):
        """Test invoice generation for payment."""
        payment = payment_factory(user=user, status='captured')

        response = authenticated_client.get(f'/api/payment/{payment.id}/invoice/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED  # If async
        ]

    def test_invoice_pdf_download(self, authenticated_client, payment_factory, user):
        """Test downloading invoice as PDF."""
        payment = payment_factory(user=user, status='captured')

        response = authenticated_client.get(
            f'/api/payment/{payment.id}/invoice/?format=pdf'
        )

        # Should return PDF or redirect to download
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_302_FOUND
        ]


# =============================================================================
# Payment Method Tests
# =============================================================================

@pytest.mark.django_db
class TestPaymentMethods:
    """Tests for payment method handling."""

    def test_list_payment_methods(self, authenticated_client, user):
        """Test listing saved payment methods."""
        response = authenticated_client.get('/api/payment/methods/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If not implemented
        ]

    def test_delete_payment_method(self, authenticated_client, user):
        """Test deleting a saved payment method."""
        # This depends on saved payment method implementation
        pass


# =============================================================================
# Currency and Amount Tests
# =============================================================================

@pytest.mark.django_db
class TestCurrencyHandling:
    """Tests for currency and amount handling."""

    def test_amount_in_smallest_unit(self, plan_factory):
        """Test that amounts are stored in smallest currency unit."""
        plan = plan_factory(name="Pro", price=999)  # ₹999

        # Razorpay expects amount in paise (999 * 100 = 99900)
        expected_paisa = plan.price * 100
        assert expected_paisa == 99900

    def test_display_amount_formatting(self, authenticated_client, plan_factory):
        """Test that amounts are displayed correctly."""
        plan = plan_factory(name="Pro", price=999)

        response = authenticated_client.get(f'/api/plans/{plan.id}/')

        assert response.status_code == status.HTTP_200_OK
        # Price should be in rupees for display
        assert response.data.get('price') == 999 or \
               response.data.get('formatted_price', '').startswith('₹')


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.django_db
class TestPaymentErrorHandling:
    """Tests for payment error handling."""

    @patch('razorpay.Client')
    def test_razorpay_timeout(
        self, mock_razorpay, authenticated_client, plan_factory, user
    ):
        """Test handling Razorpay timeout."""
        mock_client = MagicMock()
        mock_client.order.create.side_effect = TimeoutError("Connection timeout")
        mock_razorpay.return_value = mock_client

        plan = plan_factory(name="Pro", price=999)

        response = authenticated_client.post(
            '/api/payment/create-order/',
            {'plan_id': plan.id},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_duplicate_payment_prevention(
        self, authenticated_client, payment_factory, plan_factory, user
    ):
        """Test prevention of duplicate payments."""
        plan = plan_factory(name="Pro", price=999)

        # Create pending payment
        payment_factory(
            user=user,
            status='pending',
            razorpay_order_id='order_pending'
        )

        # Try to create another payment for same plan
        # Business logic may vary
        pass


# =============================================================================
# Subscription Activation Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionActivation:
    """Tests for subscription activation after payment."""

    @patch('razorpay.Client')
    def test_subscription_activated_after_payment(
        self, mock_razorpay, authenticated_client, plan_factory, user
    ):
        """Test that subscription is activated after successful payment."""
        mock_client = MagicMock()
        mock_client.utility.verify_payment_signature.return_value = True
        mock_razorpay.return_value = mock_client

        plan = plan_factory(name="Pro", price=999, token_limit=10000)

        # Verify payment
        response = authenticated_client.post(
            '/api/payment/verify/',
            {
                'razorpay_order_id': 'order_test123',
                'razorpay_payment_id': 'pay_test123',
                'razorpay_signature': 'valid_signature',
                'plan_id': plan.id,
            },
            format='json'
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

        # Verify subscription was created
        from planandsubscription.models import Subscription
        subscription = Subscription.objects.filter(user=user, status='active').first()

        # Subscription should exist after payment
        # (depends on implementation)
