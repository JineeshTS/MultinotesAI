"""
Webhook Service for MultinotesAI.

This module provides webhook functionality:
- Webhook registration and management
- Event dispatching
- Retry logic with exponential backoff
- Signature verification
"""

import logging
import hmac
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

import requests
from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Webhook Event Types
# =============================================================================

class WebhookEventType(Enum):
    """Webhook event type constants."""

    # User events
    USER_CREATED = 'user.created'
    USER_UPDATED = 'user.updated'
    USER_DELETED = 'user.deleted'

    # Subscription events
    SUBSCRIPTION_CREATED = 'subscription.created'
    SUBSCRIPTION_UPDATED = 'subscription.updated'
    SUBSCRIPTION_CANCELLED = 'subscription.cancelled'
    SUBSCRIPTION_EXPIRED = 'subscription.expired'

    # Payment events
    PAYMENT_COMPLETED = 'payment.completed'
    PAYMENT_FAILED = 'payment.failed'
    PAYMENT_REFUNDED = 'payment.refunded'

    # Content events
    NOTE_CREATED = 'note.created'
    NOTE_UPDATED = 'note.updated'
    NOTE_DELETED = 'note.deleted'
    NOTE_SHARED = 'note.shared'

    # AI events
    AI_GENERATION_COMPLETED = 'ai.generation.completed'
    AI_GENERATION_FAILED = 'ai.generation.failed'

    # Export events
    EXPORT_COMPLETED = 'export.completed'
    EXPORT_FAILED = 'export.failed'


class WebhookDeliveryStatus(Enum):
    """Webhook delivery status."""
    PENDING = 'pending'
    SUCCESS = 'success'
    FAILED = 'failed'
    RETRYING = 'retrying'


# =============================================================================
# Webhook Models
# =============================================================================

class Webhook(models.Model):
    """Webhook endpoint registration model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='webhooks'
    )

    name = models.CharField(max_length=255)
    url = models.URLField(max_length=500)
    secret = models.CharField(max_length=255)
    events = models.JSONField(default=list)  # List of event types to subscribe to

    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)

    # Stats
    total_deliveries = models.IntegerField(default=0)
    successful_deliveries = models.IntegerField(default=0)
    failed_deliveries = models.IntegerField(default=0)
    last_delivery_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'webhooks'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['is_active', 'is_delete']),
        ]

    def __str__(self):
        return f"{self.name} - {self.url}"

    def save(self, *args, **kwargs):
        if not self.secret:
            self.secret = self._generate_secret()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_secret() -> str:
        """Generate a random webhook secret."""
        return f"whsec_{uuid.uuid4().hex}"


class WebhookDelivery(models.Model):
    """Webhook delivery attempt record."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        related_name='deliveries'
    )

    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    status = models.CharField(
        max_length=20,
        default=WebhookDeliveryStatus.PENDING.value
    )

    # Response info
    response_status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)

    # Retry info
    attempt_count = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'webhook_deliveries'
        indexes = [
            models.Index(fields=['webhook', '-created_at']),
            models.Index(fields=['status', 'next_retry_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} - {self.status}"


# =============================================================================
# Webhook Service
# =============================================================================

class WebhookService:
    """
    Webhook management and delivery service.

    Usage:
        service = WebhookService()
        service.dispatch(
            event_type=WebhookEventType.PAYMENT_COMPLETED,
            user_id=123,
            payload={'order_id': 'order_abc123'}
        )
    """

    DEFAULT_TIMEOUT = 30  # seconds
    MAX_RETRIES = 5
    RETRY_DELAYS = [60, 300, 900, 3600, 7200]  # 1min, 5min, 15min, 1hr, 2hr

    def __init__(self):
        self.timeout = getattr(settings, 'WEBHOOK_TIMEOUT', self.DEFAULT_TIMEOUT)

    # -------------------------------------------------------------------------
    # Webhook Registration
    # -------------------------------------------------------------------------

    def register_webhook(
        self,
        user,
        name: str,
        url: str,
        events: List[str],
        secret: str = None
    ) -> Webhook:
        """
        Register a new webhook endpoint.

        Args:
            user: User registering the webhook
            name: Webhook name/description
            url: Target URL
            events: List of event types to subscribe to
            secret: Optional custom secret

        Returns:
            Created Webhook instance
        """
        webhook = Webhook.objects.create(
            user=user,
            name=name,
            url=url,
            events=events,
            secret=secret or Webhook._generate_secret()
        )

        logger.info(f"Webhook registered: {webhook.id} for user {user.id}")
        return webhook

    def update_webhook(
        self,
        webhook_id: str,
        user,
        **kwargs
    ) -> Optional[Webhook]:
        """Update webhook configuration."""
        try:
            webhook = Webhook.objects.get(
                id=webhook_id,
                user=user,
                is_delete=False
            )

            for field, value in kwargs.items():
                if hasattr(webhook, field):
                    setattr(webhook, field, value)

            webhook.save()
            return webhook

        except Webhook.DoesNotExist:
            return None

    def delete_webhook(self, webhook_id: str, user) -> bool:
        """Soft delete a webhook."""
        try:
            webhook = Webhook.objects.get(id=webhook_id, user=user)
            webhook.is_delete = True
            webhook.is_active = False
            webhook.save()
            return True
        except Webhook.DoesNotExist:
            return False

    def get_user_webhooks(self, user) -> List[Webhook]:
        """Get all webhooks for a user."""
        return list(Webhook.objects.filter(
            user=user,
            is_delete=False
        ).order_by('-created_at'))

    # -------------------------------------------------------------------------
    # Event Dispatching
    # -------------------------------------------------------------------------

    def dispatch(
        self,
        event_type: WebhookEventType,
        user_id: int = None,
        payload: Dict[str, Any] = None,
        async_delivery: bool = True
    ) -> int:
        """
        Dispatch a webhook event to all subscribed endpoints.

        Args:
            event_type: Type of event
            user_id: Optional user ID to filter webhooks
            payload: Event payload data
            async_delivery: Whether to deliver asynchronously

        Returns:
            Number of webhooks triggered
        """
        payload = payload or {}
        event_name = event_type.value if isinstance(event_type, WebhookEventType) else event_type

        # Find matching webhooks
        queryset = Webhook.objects.filter(
            is_active=True,
            is_delete=False
        )

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by event subscription
        webhooks = [
            w for w in queryset
            if event_name in w.events or '*' in w.events
        ]

        if not webhooks:
            logger.debug(f"No webhooks subscribed to event: {event_name}")
            return 0

        # Create delivery records
        deliveries = []
        for webhook in webhooks:
            delivery = WebhookDelivery.objects.create(
                webhook=webhook,
                event_type=event_name,
                payload=self._build_payload(event_name, payload, webhook),
            )
            deliveries.append(delivery)

        # Deliver webhooks
        if async_delivery:
            self._deliver_async(deliveries)
        else:
            for delivery in deliveries:
                self._deliver(delivery)

        logger.info(f"Dispatched {len(deliveries)} webhooks for event: {event_name}")
        return len(deliveries)

    def _build_payload(
        self,
        event_type: str,
        data: Dict,
        webhook: Webhook
    ) -> Dict:
        """Build the webhook payload."""
        return {
            'id': str(uuid.uuid4()),
            'type': event_type,
            'created_at': timezone.now().isoformat(),
            'data': data,
            'webhook_id': str(webhook.id),
        }

    def _deliver(self, delivery: WebhookDelivery) -> bool:
        """
        Deliver a single webhook.

        Args:
            delivery: WebhookDelivery instance

        Returns:
            True if successful
        """
        webhook = delivery.webhook
        delivery.attempt_count += 1

        try:
            # Generate signature
            signature = self._generate_signature(
                delivery.payload,
                webhook.secret
            )

            # Make request
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'MultinotesAI-Webhook/1.0',
                'X-Webhook-ID': str(webhook.id),
                'X-Webhook-Signature': signature,
                'X-Webhook-Timestamp': str(int(timezone.now().timestamp())),
            }

            start_time = timezone.now()
            response = requests.post(
                webhook.url,
                json=delivery.payload,
                headers=headers,
                timeout=self.timeout
            )
            end_time = timezone.now()

            # Update delivery record
            delivery.response_status_code = response.status_code
            delivery.response_body = response.text[:5000]  # Limit stored response
            delivery.response_time_ms = int((end_time - start_time).total_seconds() * 1000)

            if 200 <= response.status_code < 300:
                delivery.status = WebhookDeliveryStatus.SUCCESS.value
                delivery.delivered_at = timezone.now()

                # Update webhook stats
                webhook.total_deliveries += 1
                webhook.successful_deliveries += 1
                webhook.last_delivery_at = timezone.now()
                webhook.save()

                logger.info(f"Webhook delivered: {delivery.id} to {webhook.url}")
                delivery.save()
                return True
            else:
                delivery.error_message = f"HTTP {response.status_code}: {response.text[:500]}"
                self._handle_failure(delivery)
                return False

        except requests.Timeout:
            delivery.error_message = "Request timed out"
            self._handle_failure(delivery)
            return False

        except requests.RequestException as e:
            delivery.error_message = str(e)
            self._handle_failure(delivery)
            return False

        except Exception as e:
            logger.exception(f"Webhook delivery error: {e}")
            delivery.error_message = str(e)
            delivery.status = WebhookDeliveryStatus.FAILED.value
            delivery.save()
            return False

    def _handle_failure(self, delivery: WebhookDelivery):
        """Handle delivery failure and schedule retry if applicable."""
        webhook = delivery.webhook

        if delivery.attempt_count < delivery.max_attempts:
            # Schedule retry
            retry_index = min(delivery.attempt_count - 1, len(self.RETRY_DELAYS) - 1)
            retry_delay = self.RETRY_DELAYS[retry_index]

            delivery.status = WebhookDeliveryStatus.RETRYING.value
            delivery.next_retry_at = timezone.now() + timedelta(seconds=retry_delay)

            logger.warning(
                f"Webhook delivery failed, scheduling retry "
                f"(attempt {delivery.attempt_count}/{delivery.max_attempts}): {delivery.id}"
            )
        else:
            # Max retries reached
            delivery.status = WebhookDeliveryStatus.FAILED.value
            webhook.failed_deliveries += 1

            logger.error(f"Webhook delivery permanently failed: {delivery.id}")

        webhook.total_deliveries += 1
        webhook.save()
        delivery.save()

    def _deliver_async(self, deliveries: List[WebhookDelivery]):
        """Deliver webhooks asynchronously using Celery."""
        try:
            from backend.celery_tasks import deliver_webhook_task

            for delivery in deliveries:
                deliver_webhook_task.delay(str(delivery.id))

        except ImportError:
            # Celery not available, deliver synchronously
            logger.warning("Celery not available, delivering webhooks synchronously")
            for delivery in deliveries:
                self._deliver(delivery)

    def _generate_signature(self, payload: Dict, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        return hmac.new(
            secret.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    # -------------------------------------------------------------------------
    # Retry Processing
    # -------------------------------------------------------------------------

    def process_pending_retries(self) -> int:
        """Process all pending webhook retries."""
        pending = WebhookDelivery.objects.filter(
            status=WebhookDeliveryStatus.RETRYING.value,
            next_retry_at__lte=timezone.now()
        )

        count = 0
        for delivery in pending:
            self._deliver(delivery)
            count += 1

        if count > 0:
            logger.info(f"Processed {count} webhook retries")

        return count

    # -------------------------------------------------------------------------
    # Signature Verification (for incoming webhooks)
    # -------------------------------------------------------------------------

    @staticmethod
    def verify_signature(
        payload: bytes,
        signature: str,
        secret: str,
        tolerance: int = 300
    ) -> bool:
        """
        Verify incoming webhook signature.

        Args:
            payload: Raw request body
            signature: Signature from header
            secret: Webhook secret
            tolerance: Time tolerance in seconds

        Returns:
            True if signature is valid
        """
        expected = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def get_delivery_history(
        self,
        webhook_id: str,
        limit: int = 50
    ) -> List[WebhookDelivery]:
        """Get delivery history for a webhook."""
        return list(WebhookDelivery.objects.filter(
            webhook_id=webhook_id
        )[:limit])

    def get_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Get a specific delivery record."""
        try:
            return WebhookDelivery.objects.select_related('webhook').get(id=delivery_id)
        except WebhookDelivery.DoesNotExist:
            return None

    def retry_delivery(self, delivery_id: str) -> bool:
        """Manually retry a failed delivery."""
        try:
            delivery = WebhookDelivery.objects.get(id=delivery_id)

            if delivery.status != WebhookDeliveryStatus.FAILED.value:
                return False

            delivery.attempt_count = 0
            delivery.status = WebhookDeliveryStatus.PENDING.value
            delivery.save()

            return self._deliver(delivery)

        except WebhookDelivery.DoesNotExist:
            return False

    def cleanup_old_deliveries(self, days: int = 30) -> int:
        """Delete old delivery records."""
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = WebhookDelivery.objects.filter(
            created_at__lt=cutoff
        ).delete()

        logger.info(f"Deleted {deleted} old webhook deliveries")
        return deleted


# =============================================================================
# Singleton Instance
# =============================================================================

webhook_service = WebhookService()
