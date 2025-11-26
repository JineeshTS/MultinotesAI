"""
Email notification service for MultinotesAI.

This module provides email sending functionality with:
- Template-based HTML emails
- Async sending via Celery
- Support for various notification types
- Error handling and logging
"""

import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from celery import shared_task

logger = logging.getLogger(__name__)


# =============================================================================
# Email Types
# =============================================================================

class EmailType:
    """Email type constants."""
    WELCOME = 'welcome'
    EMAIL_VERIFICATION = 'email_verification'
    PASSWORD_RESET = 'password_reset'
    PASSWORD_CHANGED = 'password_changed'
    SUBSCRIPTION_CREATED = 'subscription_created'
    SUBSCRIPTION_RENEWED = 'subscription_renewed'
    SUBSCRIPTION_CANCELLED = 'subscription_cancelled'
    SUBSCRIPTION_EXPIRING = 'subscription_expiring'
    PAYMENT_SUCCESS = 'payment_success'
    PAYMENT_FAILED = 'payment_failed'
    REFUND_PROCESSED = 'refund_processed'
    LOW_TOKENS = 'low_tokens'
    TOKENS_EXHAUSTED = 'tokens_exhausted'
    ACCOUNT_BLOCKED = 'account_blocked'
    ACCOUNT_UNBLOCKED = 'account_unblocked'


# =============================================================================
# Email Templates
# =============================================================================

EMAIL_TEMPLATES = {
    EmailType.WELCOME: {
        'subject': 'Welcome to MultinotesAI!',
        'template': 'emails/welcome.html',
    },
    EmailType.EMAIL_VERIFICATION: {
        'subject': 'Verify your MultinotesAI account',
        'template': 'emails/verify_email.html',
    },
    EmailType.PASSWORD_RESET: {
        'subject': 'Reset your MultinotesAI password',
        'template': 'emails/password_reset.html',
    },
    EmailType.PASSWORD_CHANGED: {
        'subject': 'Your password has been changed',
        'template': 'emails/password_changed.html',
    },
    EmailType.SUBSCRIPTION_CREATED: {
        'subject': 'Subscription activated - MultinotesAI',
        'template': 'emails/subscription_created.html',
    },
    EmailType.SUBSCRIPTION_RENEWED: {
        'subject': 'Subscription renewed - MultinotesAI',
        'template': 'emails/subscription_renewed.html',
    },
    EmailType.SUBSCRIPTION_CANCELLED: {
        'subject': 'Subscription cancelled - MultinotesAI',
        'template': 'emails/subscription_cancelled.html',
    },
    EmailType.SUBSCRIPTION_EXPIRING: {
        'subject': 'Your subscription is expiring soon',
        'template': 'emails/subscription_expiring.html',
    },
    EmailType.PAYMENT_SUCCESS: {
        'subject': 'Payment confirmation - MultinotesAI',
        'template': 'emails/payment_success.html',
    },
    EmailType.PAYMENT_FAILED: {
        'subject': 'Payment failed - Action required',
        'template': 'emails/payment_failed.html',
    },
    EmailType.REFUND_PROCESSED: {
        'subject': 'Refund processed - MultinotesAI',
        'template': 'emails/refund_processed.html',
    },
    EmailType.LOW_TOKENS: {
        'subject': 'Low token balance alert',
        'template': 'emails/low_tokens.html',
    },
    EmailType.TOKENS_EXHAUSTED: {
        'subject': 'Token balance exhausted',
        'template': 'emails/tokens_exhausted.html',
    },
    EmailType.ACCOUNT_BLOCKED: {
        'subject': 'Account suspended - MultinotesAI',
        'template': 'emails/account_blocked.html',
    },
    EmailType.ACCOUNT_UNBLOCKED: {
        'subject': 'Account reactivated - MultinotesAI',
        'template': 'emails/account_unblocked.html',
    },
}


# =============================================================================
# Email Service Class
# =============================================================================

class EmailService:
    """Service for sending emails."""

    def __init__(self):
        """Initialize email service."""
        self.from_email = getattr(
            settings, 'DEFAULT_FROM_EMAIL',
            'MultinotesAI <noreply@multinotesai.com>'
        )
        self.site_url = getattr(settings, 'SITE_URL', 'https://multinotesai.com')
        self.support_email = getattr(
            settings, 'SUPPORT_EMAIL',
            'support@multinotesai.com'
        )

    def get_base_context(self) -> Dict[str, Any]:
        """Get base context for all email templates."""
        return {
            'site_url': self.site_url,
            'support_email': self.support_email,
            'company_name': 'MultinotesAI',
            'current_year': __import__('datetime').datetime.now().year,
        }

    def send_email(
        self,
        to_emails: List[str],
        email_type: str,
        context: Dict[str, Any] = None,
        attachments: List[tuple] = None,
    ) -> bool:
        """
        Send an email.

        Args:
            to_emails: List of recipient email addresses
            email_type: Type of email (from EmailType constants)
            context: Additional context for the email template
            attachments: List of (filename, content, mimetype) tuples

        Returns:
            bool: True if email was sent successfully
        """
        try:
            template_info = EMAIL_TEMPLATES.get(email_type)
            if not template_info:
                logger.error(f"Unknown email type: {email_type}")
                return False

            # Build context
            full_context = self.get_base_context()
            if context:
                full_context.update(context)

            # Render HTML content
            try:
                html_content = render_to_string(
                    template_info['template'],
                    full_context
                )
            except Exception as e:
                # Fallback to simple HTML if template doesn't exist
                logger.warning(f"Template not found, using fallback: {e}")
                html_content = self._generate_fallback_html(
                    email_type, full_context
                )

            # Create plain text version
            text_content = strip_tags(html_content)

            # Create email
            subject = template_info['subject']
            if context and 'subject_prefix' in context:
                subject = f"{context['subject_prefix']} {subject}"

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=to_emails,
            )
            email.attach_alternative(html_content, "text/html")

            # Add attachments
            if attachments:
                for filename, content, mimetype in attachments:
                    email.attach(filename, content, mimetype)

            # Send email
            email.send(fail_silently=False)
            logger.info(f"Email sent successfully: {email_type} to {to_emails}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {email_type} to {to_emails}: {e}")
            return False

    def _generate_fallback_html(
        self,
        email_type: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate fallback HTML when template is not available."""
        messages = {
            EmailType.WELCOME: f"""
                <h2>Welcome to {context.get('company_name', 'MultinotesAI')}!</h2>
                <p>Hi {context.get('username', 'there')},</p>
                <p>Thank you for joining MultinotesAI. We're excited to have you on board!</p>
                <p>Get started by exploring our AI-powered features.</p>
            """,
            EmailType.EMAIL_VERIFICATION: f"""
                <h2>Verify Your Email</h2>
                <p>Hi {context.get('username', 'there')},</p>
                <p>Please verify your email address by clicking the link below:</p>
                <p><a href="{context.get('verification_url', '#')}">Verify Email</a></p>
                <p>This link will expire in 24 hours.</p>
            """,
            EmailType.PASSWORD_RESET: f"""
                <h2>Reset Your Password</h2>
                <p>Hi {context.get('username', 'there')},</p>
                <p>You requested to reset your password. Click the link below:</p>
                <p><a href="{context.get('reset_url', '#')}">Reset Password</a></p>
                <p>This link will expire in 1 hour.</p>
                <p>If you didn't request this, please ignore this email.</p>
            """,
            EmailType.PASSWORD_CHANGED: f"""
                <h2>Password Changed</h2>
                <p>Hi {context.get('username', 'there')},</p>
                <p>Your password has been successfully changed.</p>
                <p>If you didn't make this change, please contact support immediately.</p>
            """,
            EmailType.PAYMENT_SUCCESS: f"""
                <h2>Payment Successful</h2>
                <p>Hi {context.get('username', 'there')},</p>
                <p>Your payment of ₹{context.get('amount', '0')} was successful.</p>
                <p>Order ID: {context.get('order_id', 'N/A')}</p>
                <p>Plan: {context.get('plan_name', 'N/A')}</p>
            """,
            EmailType.SUBSCRIPTION_CREATED: f"""
                <h2>Subscription Activated</h2>
                <p>Hi {context.get('username', 'there')},</p>
                <p>Your subscription to {context.get('plan_name', 'N/A')} has been activated.</p>
                <p>You now have access to {context.get('tokens', '0')} tokens.</p>
            """,
            EmailType.LOW_TOKENS: f"""
                <h2>Low Token Balance</h2>
                <p>Hi {context.get('username', 'there')},</p>
                <p>Your token balance is running low ({context.get('remaining_tokens', '0')} tokens remaining).</p>
                <p>Consider upgrading your plan to continue using our AI services.</p>
            """,
        }

        body = messages.get(email_type, f"""
            <h2>MultinotesAI Notification</h2>
            <p>Hi {context.get('username', 'there')},</p>
            <p>This is a notification from MultinotesAI.</p>
        """)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h2 {{ color: #2563eb; }}
                a {{ color: #2563eb; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                {body}
                <div class="footer">
                    <p>© {context.get('current_year', '2024')} {context.get('company_name', 'MultinotesAI')}. All rights reserved.</p>
                    <p>Need help? Contact us at <a href="mailto:{context.get('support_email', 'support@multinotesai.com')}">{context.get('support_email', 'support@multinotesai.com')}</a></p>
                </div>
            </div>
        </body>
        </html>
        """


# =============================================================================
# Celery Tasks for Async Email Sending
# =============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(
    self,
    to_emails: List[str],
    email_type: str,
    context: Dict[str, Any] = None,
):
    """
    Celery task for sending emails asynchronously.

    Args:
        to_emails: List of recipient email addresses
        email_type: Type of email to send
        context: Context data for email template
    """
    try:
        service = EmailService()
        success = service.send_email(to_emails, email_type, context)
        if not success:
            raise Exception("Email sending returned False")
        return {'status': 'success', 'email_type': email_type}
    except Exception as e:
        logger.error(f"Email task failed: {e}")
        raise self.retry(exc=e)


# =============================================================================
# Convenience Functions
# =============================================================================

def send_welcome_email(user) -> None:
    """Send welcome email to new user."""
    send_email_task.delay(
        to_emails=[user.email],
        email_type=EmailType.WELCOME,
        context={
            'username': user.username,
            'name': user.name or user.username,
        }
    )


def send_verification_email(user, verification_url: str) -> None:
    """Send email verification email."""
    send_email_task.delay(
        to_emails=[user.email],
        email_type=EmailType.EMAIL_VERIFICATION,
        context={
            'username': user.username,
            'verification_url': verification_url,
        }
    )


def send_password_reset_email(user, reset_url: str) -> None:
    """Send password reset email."""
    send_email_task.delay(
        to_emails=[user.email],
        email_type=EmailType.PASSWORD_RESET,
        context={
            'username': user.username,
            'reset_url': reset_url,
        }
    )


def send_password_changed_email(user) -> None:
    """Send password changed notification."""
    send_email_task.delay(
        to_emails=[user.email],
        email_type=EmailType.PASSWORD_CHANGED,
        context={
            'username': user.username,
        }
    )


def send_payment_success_email(
    user,
    amount: float,
    order_id: str,
    plan_name: str,
    payment_id: str = None,
) -> None:
    """Send payment success email."""
    send_email_task.delay(
        to_emails=[user.email],
        email_type=EmailType.PAYMENT_SUCCESS,
        context={
            'username': user.username,
            'amount': amount,
            'order_id': order_id,
            'plan_name': plan_name,
            'payment_id': payment_id,
        }
    )


def send_payment_failed_email(user, amount: float, reason: str = None) -> None:
    """Send payment failed email."""
    send_email_task.delay(
        to_emails=[user.email],
        email_type=EmailType.PAYMENT_FAILED,
        context={
            'username': user.username,
            'amount': amount,
            'reason': reason or 'Payment could not be processed',
        }
    )


def send_subscription_created_email(
    user,
    plan_name: str,
    tokens: int,
    expiry_date: str,
) -> None:
    """Send subscription created email."""
    send_email_task.delay(
        to_emails=[user.email],
        email_type=EmailType.SUBSCRIPTION_CREATED,
        context={
            'username': user.username,
            'plan_name': plan_name,
            'tokens': tokens,
            'expiry_date': expiry_date,
        }
    )


def send_subscription_expiring_email(
    user,
    plan_name: str,
    days_remaining: int,
) -> None:
    """Send subscription expiring warning email."""
    send_email_task.delay(
        to_emails=[user.email],
        email_type=EmailType.SUBSCRIPTION_EXPIRING,
        context={
            'username': user.username,
            'plan_name': plan_name,
            'days_remaining': days_remaining,
        }
    )


def send_low_tokens_email(user, remaining_tokens: int) -> None:
    """Send low token balance alert."""
    send_email_task.delay(
        to_emails=[user.email],
        email_type=EmailType.LOW_TOKENS,
        context={
            'username': user.username,
            'remaining_tokens': remaining_tokens,
        }
    )


def send_tokens_exhausted_email(user) -> None:
    """Send tokens exhausted notification."""
    send_email_task.delay(
        to_emails=[user.email],
        email_type=EmailType.TOKENS_EXHAUSTED,
        context={
            'username': user.username,
        }
    )


def send_refund_email(
    user,
    amount: float,
    refund_id: str,
    reason: str = None,
) -> None:
    """Send refund processed email."""
    send_email_task.delay(
        to_emails=[user.email],
        email_type=EmailType.REFUND_PROCESSED,
        context={
            'username': user.username,
            'amount': amount,
            'refund_id': refund_id,
            'reason': reason,
        }
    )
