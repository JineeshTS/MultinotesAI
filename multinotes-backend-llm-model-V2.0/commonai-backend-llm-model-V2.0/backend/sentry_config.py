"""
Sentry configuration for MultinotesAI.

This module provides:
- Sentry SDK initialization
- Custom error filtering
- Performance tracing configuration
- User context enrichment
"""

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging
from django.conf import settings


# =============================================================================
# Error Filtering
# =============================================================================

IGNORED_ERRORS = [
    # Common expected errors
    'django.http.Http404',
    'rest_framework.exceptions.NotAuthenticated',
    'rest_framework.exceptions.AuthenticationFailed',
    'rest_framework.exceptions.PermissionDenied',
    'rest_framework.exceptions.ValidationError',
    'django.core.exceptions.PermissionDenied',

    # Rate limiting
    'rest_framework.exceptions.Throttled',

    # Connection errors (usually transient)
    'ConnectionResetError',
    'BrokenPipeError',
]

IGNORED_TRANSACTIONS = [
    '/health/',
    '/api/health/',
    '/metrics/',
    '/favicon.ico',
    '/robots.txt',
]


def before_send(event, hint):
    """
    Filter events before sending to Sentry.

    Args:
        event: The event dict
        hint: Additional information about the event

    Returns:
        The event to send, or None to discard
    """
    # Get exception info
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        exc_name = f"{exc_type.__module__}.{exc_type.__name__}"

        # Filter out ignored errors
        if exc_name in IGNORED_ERRORS:
            return None

        # Filter out common HTTP errors
        if hasattr(exc_value, 'status_code'):
            if exc_value.status_code in [400, 401, 403, 404, 429]:
                return None

    # Filter out specific error messages
    if 'message' in event:
        message = event['message'].lower()
        if any(ignore in message for ignore in ['rate limit', 'timeout', 'connection reset']):
            return None

    return event


def before_send_transaction(event, hint):
    """
    Filter transactions before sending to Sentry.

    Args:
        event: The transaction event
        hint: Additional information

    Returns:
        The event to send, or None to discard
    """
    # Filter out health checks and static files
    transaction_name = event.get('transaction', '')
    if any(ignored in transaction_name for ignored in IGNORED_TRANSACTIONS):
        return None

    return event


def traces_sampler(sampling_context):
    """
    Dynamic trace sampling based on transaction type.

    Args:
        sampling_context: Context about the transaction

    Returns:
        Sample rate between 0.0 and 1.0
    """
    transaction_name = sampling_context.get('transaction_context', {}).get('name', '')

    # Don't trace health checks
    if any(ignored in transaction_name for ignored in IGNORED_TRANSACTIONS):
        return 0.0

    # Higher sampling for slow endpoints
    if 'generate' in transaction_name.lower():
        return 0.5  # Sample 50% of AI generation

    # Higher sampling for payment endpoints
    if 'payment' in transaction_name.lower() or 'subscription' in transaction_name.lower():
        return 0.8  # Sample 80% of payment transactions

    # Default sampling rate
    return 0.1  # Sample 10% of other transactions


# =============================================================================
# User Context
# =============================================================================

def set_user_context(user):
    """
    Set user context for Sentry events.

    Args:
        user: Django user instance
    """
    if user and user.is_authenticated:
        sentry_sdk.set_user({
            'id': user.id,
            'email': user.email,
            'username': getattr(user, 'username', None),
        })
    else:
        sentry_sdk.set_user(None)


def add_context(key, data):
    """
    Add custom context to Sentry events.

    Args:
        key: Context category name
        data: Dict of context data
    """
    sentry_sdk.set_context(key, data)


def add_tag(key, value):
    """
    Add a tag to Sentry events.

    Args:
        key: Tag name
        value: Tag value
    """
    sentry_sdk.set_tag(key, value)


# =============================================================================
# Initialization
# =============================================================================

def init_sentry():
    """
    Initialize Sentry SDK with MultinotesAI configuration.

    Call this in your Django settings or wsgi/asgi file.
    """
    sentry_dsn = getattr(settings, 'SENTRY_DSN', None)

    if not sentry_dsn:
        logging.warning("Sentry DSN not configured, error tracking disabled")
        return

    environment = getattr(settings, 'ENVIRONMENT', 'development')

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,

        # Integrations
        integrations=[
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,
            ),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],

        # Performance monitoring
        traces_sample_rate=0.1,  # Base sample rate
        traces_sampler=traces_sampler,
        profiles_sample_rate=0.1,

        # Error filtering
        before_send=before_send,
        before_send_transaction=before_send_transaction,

        # Context
        send_default_pii=False,  # Don't send PII by default
        attach_stacktrace=True,

        # Release tracking
        release=getattr(settings, 'APP_VERSION', 'unknown'),

        # Additional options
        max_breadcrumbs=50,
        debug=settings.DEBUG,

        # Ignore specific loggers
        ignore_errors=[
            KeyboardInterrupt,
            SystemExit,
        ],
    )

    # Set global tags
    sentry_sdk.set_tag('app', 'multinotesai')
    sentry_sdk.set_tag('environment', environment)

    logging.info(f"Sentry initialized for environment: {environment}")


# =============================================================================
# Utility Functions
# =============================================================================

def capture_message(message, level='info', extra=None):
    """
    Capture a message to Sentry.

    Args:
        message: The message to capture
        level: Log level (info, warning, error)
        extra: Additional context data
    """
    with sentry_sdk.push_scope() as scope:
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        sentry_sdk.capture_message(message, level=level)


def capture_exception(exception, extra=None):
    """
    Capture an exception to Sentry.

    Args:
        exception: The exception to capture
        extra: Additional context data
    """
    with sentry_sdk.push_scope() as scope:
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        sentry_sdk.capture_exception(exception)


class SentryContextManager:
    """
    Context manager for adding Sentry context.

    Usage:
        with SentryContextManager(user=user, tags={'feature': 'ai_gen'}):
            # Code that might raise exceptions
            result = generate_ai_response()
    """

    def __init__(self, user=None, tags=None, extra=None):
        self.user = user
        self.tags = tags or {}
        self.extra = extra or {}

    def __enter__(self):
        self.scope = sentry_sdk.push_scope()
        self.scope.__enter__()

        if self.user:
            set_user_context(self.user)

        for key, value in self.tags.items():
            sentry_sdk.set_tag(key, value)

        for key, value in self.extra.items():
            sentry_sdk.set_extra(key, value)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.scope.__exit__(exc_type, exc_val, exc_tb)
        return False  # Don't suppress exceptions


# =============================================================================
# Settings Configuration
# =============================================================================

"""
Add to your settings.py:

# Sentry Configuration
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')
APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')

# Initialize Sentry (at the end of settings.py)
if SENTRY_DSN:
    from backend.sentry_config import init_sentry
    init_sentry()
"""
