"""
Notification Service for MultinotesAI.

This module provides unified notification handling:
- In-app notifications
- Email notifications
- Push notifications (future)
- Webhook notifications
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


# =============================================================================
# Notification Types
# =============================================================================

class NotificationType(Enum):
    """Notification type constants."""

    # User events
    WELCOME = 'welcome'
    EMAIL_VERIFIED = 'email_verified'
    PASSWORD_CHANGED = 'password_changed'
    PROFILE_UPDATED = 'profile_updated'

    # Subscription events
    SUBSCRIPTION_CREATED = 'subscription_created'
    SUBSCRIPTION_RENEWED = 'subscription_renewed'
    SUBSCRIPTION_CANCELLED = 'subscription_cancelled'
    SUBSCRIPTION_EXPIRING = 'subscription_expiring'
    PAYMENT_FAILED = 'payment_failed'
    PAYMENT_SUCCESSFUL = 'payment_successful'

    # Content events
    CONTENT_SHARED = 'content_shared'
    SHARE_ACCESSED = 'share_accessed'
    EXPORT_READY = 'export_ready'

    # System events
    STORAGE_WARNING = 'storage_warning'
    TOKEN_LOW = 'token_low'
    MAINTENANCE = 'maintenance'
    FEATURE_UPDATE = 'feature_update'


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    URGENT = 'urgent'


# =============================================================================
# Notification Templates
# =============================================================================

NOTIFICATION_TEMPLATES = {
    NotificationType.WELCOME: {
        'title': 'Welcome to MultinotesAI!',
        'template': 'emails/welcome.html',
        'priority': NotificationPriority.NORMAL,
    },
    NotificationType.SUBSCRIPTION_CREATED: {
        'title': 'Subscription Activated',
        'template': 'emails/subscription_created.html',
        'priority': NotificationPriority.NORMAL,
    },
    NotificationType.SUBSCRIPTION_EXPIRING: {
        'title': 'Your Subscription is Expiring Soon',
        'template': 'emails/subscription_expiring.html',
        'priority': NotificationPriority.HIGH,
    },
    NotificationType.PAYMENT_FAILED: {
        'title': 'Payment Failed',
        'template': 'emails/payment_failed.html',
        'priority': NotificationPriority.URGENT,
    },
    NotificationType.STORAGE_WARNING: {
        'title': 'Storage Limit Warning',
        'template': 'emails/storage_warning.html',
        'priority': NotificationPriority.HIGH,
    },
    NotificationType.TOKEN_LOW: {
        'title': 'Low Token Balance',
        'template': 'emails/token_low.html',
        'priority': NotificationPriority.NORMAL,
    },
}


# =============================================================================
# Notification Model (for in-app notifications)
# =============================================================================

from django.db import models


class Notification(models.Model):
    """Model for in-app notifications."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    priority = models.CharField(max_length=20, default='normal')

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.email}"

    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.now()
            self.save(update_fields=['is_read', 'read_at'])


# =============================================================================
# Notification Service
# =============================================================================

class NotificationService:
    """
    Unified notification service.

    Usage:
        service = NotificationService()
        service.notify(
            user=user,
            notification_type=NotificationType.WELCOME,
            channels=['email', 'in_app']
        )
    """

    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@multinotesai.com')

    def notify(
        self,
        user,
        notification_type: NotificationType,
        channels: List[str] = None,
        context: Dict[str, Any] = None,
        **kwargs
    ) -> bool:
        """
        Send notification through specified channels.

        Args:
            user: User to notify
            notification_type: Type of notification
            channels: List of channels ('email', 'in_app', 'push')
            context: Additional context for templates
            **kwargs: Additional arguments

        Returns:
            True if at least one channel succeeded
        """
        channels = channels or ['in_app']
        context = context or {}
        success = False

        template_config = NOTIFICATION_TEMPLATES.get(notification_type, {})

        for channel in channels:
            try:
                if channel == 'email':
                    result = self._send_email(user, notification_type, context, template_config)
                elif channel == 'in_app':
                    result = self._create_in_app(user, notification_type, context, template_config)
                elif channel == 'push':
                    result = self._send_push(user, notification_type, context)
                else:
                    logger.warning(f"Unknown notification channel: {channel}")
                    continue

                if result:
                    success = True
                    logger.info(f"Notification sent via {channel} to {user.email}")

            except Exception as e:
                logger.error(f"Error sending {channel} notification: {e}")

        return success

    def _send_email(
        self,
        user,
        notification_type: NotificationType,
        context: Dict,
        template_config: Dict
    ) -> bool:
        """Send email notification."""
        try:
            # Build context
            email_context = {
                'user': user,
                'notification_type': notification_type.value,
                **context
            }

            title = template_config.get('title', 'Notification from MultinotesAI')
            template = template_config.get('template')

            # Try to render HTML template
            if template:
                try:
                    html_message = render_to_string(template, email_context)
                    plain_message = strip_tags(html_message)
                except Exception:
                    html_message = None
                    plain_message = self._get_plain_message(notification_type, context)
            else:
                html_message = None
                plain_message = self._get_plain_message(notification_type, context)

            send_mail(
                subject=title,
                message=plain_message,
                from_email=self.from_email,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            return True

        except Exception as e:
            logger.error(f"Email notification error: {e}")
            return False

    def _create_in_app(
        self,
        user,
        notification_type: NotificationType,
        context: Dict,
        template_config: Dict
    ) -> bool:
        """Create in-app notification."""
        try:
            title = template_config.get('title', 'Notification')
            priority = template_config.get('priority', NotificationPriority.NORMAL)

            message = self._get_plain_message(notification_type, context)

            Notification.objects.create(
                user=user,
                notification_type=notification_type.value,
                title=title,
                message=message,
                data=context,
                priority=priority.value if isinstance(priority, NotificationPriority) else priority,
            )
            return True

        except Exception as e:
            logger.error(f"In-app notification error: {e}")
            return False

    def _send_push(
        self,
        user,
        notification_type: NotificationType,
        context: Dict
    ) -> bool:
        """Send push notification (placeholder for future implementation)."""
        # TODO: Implement push notifications (Firebase, OneSignal, etc.)
        logger.info(f"Push notification not implemented yet for {notification_type.value}")
        return False

    def _get_plain_message(self, notification_type: NotificationType, context: Dict) -> str:
        """Generate plain text message for notification."""
        messages = {
            NotificationType.WELCOME: "Welcome to MultinotesAI! We're excited to have you on board.",
            NotificationType.SUBSCRIPTION_CREATED: f"Your {context.get('plan_name', 'subscription')} has been activated.",
            NotificationType.SUBSCRIPTION_EXPIRING: f"Your subscription will expire in {context.get('days', 7)} days.",
            NotificationType.PAYMENT_FAILED: "Your payment could not be processed. Please update your payment method.",
            NotificationType.STORAGE_WARNING: f"You've used {context.get('percent', 80)}% of your storage quota.",
            NotificationType.TOKEN_LOW: f"You have {context.get('tokens', 0)} tokens remaining.",
            NotificationType.CONTENT_SHARED: f"Your content has been shared with {context.get('email', 'someone')}.",
            NotificationType.EXPORT_READY: "Your export is ready for download.",
        }
        return messages.get(notification_type, "You have a new notification from MultinotesAI.")

    # -------------------------------------------------------------------------
    # User notification management
    # -------------------------------------------------------------------------

    def get_user_notifications(
        self,
        user,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user."""
        queryset = Notification.objects.filter(user=user)

        if unread_only:
            queryset = queryset.filter(is_read=False)

        return list(queryset[:limit])

    def get_unread_count(self, user) -> int:
        """Get count of unread notifications."""
        return Notification.objects.filter(user=user, is_read=False).count()

    def mark_all_read(self, user) -> int:
        """Mark all notifications as read for a user."""
        return Notification.objects.filter(
            user=user,
            is_read=False
        ).update(
            is_read=True,
            read_at=datetime.now()
        )

    def mark_as_read(self, user, notification_ids: List[int]) -> int:
        """Mark specific notifications as read."""
        return Notification.objects.filter(
            user=user,
            id__in=notification_ids,
            is_read=False
        ).update(
            is_read=True,
            read_at=datetime.now()
        )

    def delete_old_notifications(self, days: int = 90) -> int:
        """Delete notifications older than specified days."""
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = Notification.objects.filter(created_at__lt=cutoff).delete()

        logger.info(f"Deleted {deleted} old notifications")
        return deleted


# =============================================================================
# Bulk Notification Service
# =============================================================================

class BulkNotificationService:
    """Service for sending notifications to multiple users."""

    def __init__(self):
        self.notification_service = NotificationService()

    def notify_all_users(
        self,
        notification_type: NotificationType,
        context: Dict = None,
        channels: List[str] = None,
        user_filter: Dict = None
    ) -> int:
        """
        Send notification to all (or filtered) users.

        Args:
            notification_type: Type of notification
            context: Notification context
            channels: Notification channels
            user_filter: Django ORM filter for users

        Returns:
            Number of users notified
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        queryset = User.objects.filter(is_active=True)
        if user_filter:
            queryset = queryset.filter(**user_filter)

        count = 0
        for user in queryset.iterator():
            try:
                self.notification_service.notify(
                    user=user,
                    notification_type=notification_type,
                    channels=channels,
                    context=context
                )
                count += 1
            except Exception as e:
                logger.error(f"Error notifying user {user.id}: {e}")

        logger.info(f"Bulk notification sent to {count} users")
        return count


# =============================================================================
# Singleton Instances
# =============================================================================

notification_service = NotificationService()
bulk_notification_service = BulkNotificationService()
