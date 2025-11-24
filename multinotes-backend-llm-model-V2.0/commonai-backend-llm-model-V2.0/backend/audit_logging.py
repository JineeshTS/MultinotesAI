"""
Security Audit Logging for MultinotesAI.

This module provides:
- Security event logging
- Request/Response logging
- User activity audit trail
- Compliance logging
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


# =============================================================================
# Audit Event Types
# =============================================================================

class AuditEventType:
    """Audit event type constants."""

    # Authentication events
    LOGIN_SUCCESS = 'auth.login.success'
    LOGIN_FAILURE = 'auth.login.failure'
    LOGOUT = 'auth.logout'
    PASSWORD_CHANGE = 'auth.password.change'
    PASSWORD_RESET_REQUEST = 'auth.password.reset_request'
    PASSWORD_RESET_COMPLETE = 'auth.password.reset_complete'
    MFA_ENABLED = 'auth.mfa.enabled'
    MFA_DISABLED = 'auth.mfa.disabled'
    TOKEN_REFRESH = 'auth.token.refresh'
    SESSION_EXPIRED = 'auth.session.expired'

    # User events
    USER_CREATED = 'user.created'
    USER_UPDATED = 'user.updated'
    USER_DELETED = 'user.deleted'
    USER_BLOCKED = 'user.blocked'
    USER_UNBLOCKED = 'user.unblocked'
    EMAIL_VERIFIED = 'user.email.verified'
    PROFILE_UPDATED = 'user.profile.updated'

    # Data events
    DATA_CREATED = 'data.created'
    DATA_UPDATED = 'data.updated'
    DATA_DELETED = 'data.deleted'
    DATA_EXPORTED = 'data.exported'
    DATA_SHARED = 'data.shared'
    DATA_ACCESSED = 'data.accessed'

    # Subscription events
    SUBSCRIPTION_CREATED = 'subscription.created'
    SUBSCRIPTION_UPDATED = 'subscription.updated'
    SUBSCRIPTION_CANCELLED = 'subscription.cancelled'
    PAYMENT_SUCCESS = 'payment.success'
    PAYMENT_FAILURE = 'payment.failure'

    # Admin events
    ADMIN_ACCESS = 'admin.access'
    ADMIN_USER_MODIFY = 'admin.user.modify'
    ADMIN_CONFIG_CHANGE = 'admin.config.change'
    ADMIN_DATA_ACCESS = 'admin.data.access'

    # Security events
    SECURITY_VIOLATION = 'security.violation'
    RATE_LIMIT_EXCEEDED = 'security.rate_limit'
    SUSPICIOUS_ACTIVITY = 'security.suspicious'
    IP_BLOCKED = 'security.ip.blocked'
    API_KEY_CREATED = 'security.api_key.created'
    API_KEY_REVOKED = 'security.api_key.revoked'


# =============================================================================
# Audit Log Model
# =============================================================================

class AuditLog(models.Model):
    """
    Audit log for security and compliance tracking.

    Stores all security-relevant events with full context.
    """

    # Event identification
    event_id = models.CharField(max_length=64, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    event_category = models.CharField(max_length=50, db_index=True)

    # Actor information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    user_email = models.EmailField(blank=True)  # Stored for historical reference
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Request context
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    request_id = models.CharField(max_length=64, blank=True)

    # Event details
    description = models.TextField()
    details = models.JSONField(default=dict)

    # Target resource
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=100, blank=True)

    # Outcome
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} - {self.user_email or 'Anonymous'} - {self.created_at}"

    @staticmethod
    def generate_event_id() -> str:
        """Generate unique event ID."""
        import uuid
        return hashlib.sha256(
            f"{uuid.uuid4()}{timezone.now().isoformat()}".encode()
        ).hexdigest()[:64]


# =============================================================================
# Request Log Model
# =============================================================================

class RequestLog(models.Model):
    """
    HTTP request/response logging for debugging and monitoring.
    """

    # Request info
    request_id = models.CharField(max_length=64, unique=True, db_index=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500, db_index=True)
    query_string = models.TextField(blank=True)

    # Client info
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Request details (sanitized)
    request_headers = models.JSONField(default=dict)
    request_body_size = models.PositiveIntegerField(default=0)

    # Response details
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_size = models.PositiveIntegerField(default=0)

    # Timing
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'request_logs'
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['user', '-started_at']),
            models.Index(fields=['path', '-started_at']),
            models.Index(fields=['response_status', '-started_at']),
        ]
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.method} {self.path} - {self.response_status}"


# =============================================================================
# Audit Logger Service
# =============================================================================

class AuditLogger:
    """
    Service for creating audit log entries.

    Usage:
        audit = AuditLogger()
        audit.log(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user=user,
            request=request,
            description="User logged in successfully"
        )
    """

    # Sensitive fields to mask
    SENSITIVE_FIELDS = [
        'password', 'token', 'secret', 'api_key', 'credit_card',
        'cvv', 'ssn', 'authorization'
    ]

    def log(
        self,
        event_type: str,
        description: str,
        user=None,
        request: HttpRequest = None,
        resource_type: str = '',
        resource_id: str = '',
        details: Dict = None,
        success: bool = True,
        error_message: str = ''
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            event_type: Type of event (from AuditEventType)
            description: Human-readable description
            user: User performing the action
            request: Django request object
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional event details
            success: Whether the action succeeded
            error_message: Error message if failed

        Returns:
            Created AuditLog instance
        """
        # Extract category from event type
        category = event_type.split('.')[0] if '.' in event_type else 'general'

        # Extract request info
        ip_address = None
        user_agent = ''
        request_method = ''
        request_path = ''
        request_id = ''

        if request:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            request_method = request.method
            request_path = request.path[:500]
            request_id = getattr(request, 'request_id', '')

        # Get user info
        user_email = ''
        if user and hasattr(user, 'email'):
            user_email = user.email

        # Sanitize details
        sanitized_details = self._sanitize_data(details or {})

        # Create log entry
        audit_log = AuditLog.objects.create(
            event_id=AuditLog.generate_event_id(),
            event_type=event_type,
            event_category=category,
            user=user if user and user.is_authenticated else None,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            request_id=request_id,
            description=description,
            details=sanitized_details,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            success=success,
            error_message=error_message,
        )

        # Also log to standard logger for real-time monitoring
        log_level = logging.INFO if success else logging.WARNING
        logger.log(
            log_level,
            f"AUDIT: {event_type} - {description}",
            extra={
                'event_id': audit_log.event_id,
                'user_email': user_email,
                'ip_address': ip_address,
            }
        )

        return audit_log

    def log_auth_event(
        self,
        event_type: str,
        user=None,
        request: HttpRequest = None,
        success: bool = True,
        details: Dict = None
    ) -> AuditLog:
        """Log authentication-related event."""
        descriptions = {
            AuditEventType.LOGIN_SUCCESS: "User logged in successfully",
            AuditEventType.LOGIN_FAILURE: "Failed login attempt",
            AuditEventType.LOGOUT: "User logged out",
            AuditEventType.PASSWORD_CHANGE: "Password changed",
            AuditEventType.PASSWORD_RESET_REQUEST: "Password reset requested",
            AuditEventType.PASSWORD_RESET_COMPLETE: "Password reset completed",
            AuditEventType.TOKEN_REFRESH: "Authentication token refreshed",
        }

        return self.log(
            event_type=event_type,
            description=descriptions.get(event_type, event_type),
            user=user,
            request=request,
            success=success,
            details=details,
        )

    def log_data_event(
        self,
        event_type: str,
        resource_type: str,
        resource_id: Any,
        user=None,
        request: HttpRequest = None,
        details: Dict = None
    ) -> AuditLog:
        """Log data-related event."""
        action_map = {
            AuditEventType.DATA_CREATED: "created",
            AuditEventType.DATA_UPDATED: "updated",
            AuditEventType.DATA_DELETED: "deleted",
            AuditEventType.DATA_EXPORTED: "exported",
            AuditEventType.DATA_SHARED: "shared",
            AuditEventType.DATA_ACCESSED: "accessed",
        }

        action = action_map.get(event_type, "modified")
        description = f"{resource_type} {resource_id} was {action}"

        return self.log(
            event_type=event_type,
            description=description,
            user=user,
            request=request,
            resource_type=resource_type,
            resource_id=str(resource_id),
            details=details,
        )

    def log_security_event(
        self,
        event_type: str,
        description: str,
        user=None,
        request: HttpRequest = None,
        details: Dict = None
    ) -> AuditLog:
        """Log security-related event."""
        return self.log(
            event_type=event_type,
            description=description,
            user=user,
            request=request,
            success=False,
            details=details,
        )

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _sanitize_data(self, data: Dict) -> Dict:
        """Remove sensitive fields from data."""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            else:
                sanitized[key] = value

        return sanitized


# =============================================================================
# Request Logging Middleware
# =============================================================================

class RequestLoggingMiddleware:
    """
    Middleware for logging HTTP requests and responses.

    Add to MIDDLEWARE in settings.py:
        'backend.audit_logging.RequestLoggingMiddleware',
    """

    # Paths to exclude from logging
    EXCLUDED_PATHS = [
        '/health/',
        '/api/health/',
        '/static/',
        '/media/',
        '/favicon.ico',
    ]

    # Paths that are always logged (even if they would otherwise be excluded)
    ALWAYS_LOG_PATHS = [
        '/api/admin/',
        '/api/user/login/',
        '/api/user/register/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if this request should be logged
        if not self._should_log(request):
            return self.get_response(request)

        # Generate request ID
        import uuid
        request.request_id = str(uuid.uuid4())[:32]

        # Record start time
        start_time = timezone.now()

        # Create request log entry
        request_log = self._create_request_log(request, start_time)

        # Process request
        response = self.get_response(request)

        # Update log with response info
        self._update_request_log(request_log, response, start_time)

        # Add request ID to response headers
        response['X-Request-ID'] = request.request_id

        return response

    def _should_log(self, request) -> bool:
        """Determine if request should be logged."""
        path = request.path

        # Always log certain paths
        for always_path in self.ALWAYS_LOG_PATHS:
            if path.startswith(always_path):
                return True

        # Exclude certain paths
        for excluded in self.EXCLUDED_PATHS:
            if path.startswith(excluded):
                return False

        # Log all API requests
        return path.startswith('/api/')

    def _create_request_log(self, request, start_time) -> RequestLog:
        """Create initial request log entry."""
        # Sanitize headers
        headers = {}
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').title()
                if 'AUTHORIZATION' not in key and 'COOKIE' not in key:
                    headers[header_name] = value[:200]

        return RequestLog.objects.create(
            request_id=request.request_id,
            method=request.method,
            path=request.path[:500],
            query_string=request.META.get('QUERY_STRING', '')[:1000],
            user=request.user if request.user.is_authenticated else None,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            request_headers=headers,
            request_body_size=len(request.body) if hasattr(request, 'body') else 0,
            started_at=start_time,
        )

    def _update_request_log(self, request_log, response, start_time):
        """Update request log with response info."""
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds() * 1000

        request_log.response_status = response.status_code
        request_log.response_size = len(response.content) if hasattr(response, 'content') else 0
        request_log.completed_at = end_time
        request_log.duration_ms = int(duration)
        request_log.save()

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


# =============================================================================
# Audit Decorators
# =============================================================================

def audit_action(event_type: str, resource_type: str = ''):
    """
    Decorator to automatically audit view actions.

    Usage:
        @audit_action(AuditEventType.DATA_CREATED, 'Note')
        def create_note(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            audit = AuditLogger()

            try:
                response = view_func(request, *args, **kwargs)

                # Log success
                audit.log(
                    event_type=event_type,
                    description=f"{event_type} action completed",
                    user=request.user if request.user.is_authenticated else None,
                    request=request,
                    resource_type=resource_type,
                    success=True,
                )

                return response

            except Exception as e:
                # Log failure
                audit.log(
                    event_type=event_type,
                    description=f"{event_type} action failed",
                    user=request.user if request.user.is_authenticated else None,
                    request=request,
                    resource_type=resource_type,
                    success=False,
                    error_message=str(e),
                )
                raise

        return wrapper
    return decorator


# =============================================================================
# Audit Query Service
# =============================================================================

class AuditQueryService:
    """Service for querying audit logs."""

    def get_user_activity(
        self,
        user,
        days: int = 30,
        event_types: List[str] = None
    ) -> List[AuditLog]:
        """Get audit logs for a specific user."""
        since = timezone.now() - timedelta(days=days)

        queryset = AuditLog.objects.filter(
            user=user,
            created_at__gte=since
        )

        if event_types:
            queryset = queryset.filter(event_type__in=event_types)

        return list(queryset[:100])

    def get_security_events(
        self,
        days: int = 7,
        success_only: bool = False
    ) -> List[AuditLog]:
        """Get security-related events."""
        since = timezone.now() - timedelta(days=days)

        queryset = AuditLog.objects.filter(
            event_category='security',
            created_at__gte=since
        )

        if success_only:
            queryset = queryset.filter(success=True)

        return list(queryset[:500])

    def get_failed_logins(
        self,
        hours: int = 24,
        ip_address: str = None
    ) -> List[AuditLog]:
        """Get failed login attempts."""
        since = timezone.now() - timedelta(hours=hours)

        queryset = AuditLog.objects.filter(
            event_type=AuditEventType.LOGIN_FAILURE,
            created_at__gte=since
        )

        if ip_address:
            queryset = queryset.filter(ip_address=ip_address)

        return list(queryset)

    def get_resource_history(
        self,
        resource_type: str,
        resource_id: str
    ) -> List[AuditLog]:
        """Get audit history for a specific resource."""
        return list(AuditLog.objects.filter(
            resource_type=resource_type,
            resource_id=resource_id
        )[:50])


# =============================================================================
# Singleton Instances
# =============================================================================

audit_logger = AuditLogger()
audit_query_service = AuditQueryService()
