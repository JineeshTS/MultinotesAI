"""
Abuse Detection System for MultinotesAI.

This module provides:
- Rate limiting and abuse detection
- Suspicious activity monitoring
- Content moderation
- IP-based blocking
- Account security monitoring
"""

import logging
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from collections import defaultdict

from django.db import models
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Abuse Types
# =============================================================================

class AbuseType(Enum):
    """Types of abuse detected."""
    RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded'
    SUSPICIOUS_LOGIN = 'suspicious_login'
    BRUTE_FORCE_ATTEMPT = 'brute_force_attempt'
    CONTENT_SPAM = 'content_spam'
    API_ABUSE = 'api_abuse'
    PAYMENT_FRAUD = 'payment_fraud'
    ACCOUNT_SHARING = 'account_sharing'
    BOT_ACTIVITY = 'bot_activity'
    CONTENT_VIOLATION = 'content_violation'
    TOKEN_MANIPULATION = 'token_manipulation'


class AbuseAction(Enum):
    """Actions to take on abuse detection."""
    LOG_ONLY = 'log_only'
    WARN_USER = 'warn_user'
    RATE_LIMIT = 'rate_limit'
    TEMPORARY_BLOCK = 'temporary_block'
    PERMANENT_BLOCK = 'permanent_block'
    REQUIRE_VERIFICATION = 'require_verification'
    NOTIFY_ADMIN = 'notify_admin'


class AbuseSeverity(Enum):
    """Severity levels for abuse."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# =============================================================================
# Abuse Log Model
# =============================================================================

class AbuseLog(models.Model):
    """Log of detected abuse incidents."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='abuse_logs'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    abuse_type = models.CharField(max_length=50)
    severity = models.IntegerField(default=1)
    description = models.TextField()
    metadata = models.JSONField(default=dict)

    action_taken = models.CharField(max_length=50, default='log_only')
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_abuse_logs'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'abuse_logs'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
            models.Index(fields=['abuse_type', '-created_at']),
            models.Index(fields=['is_resolved', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.abuse_type} - {self.ip_address or self.user}"


class BlockedIP(models.Model):
    """Blocked IP addresses."""

    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.TextField()
    blocked_until = models.DateTimeField(null=True, blank=True)
    is_permanent = models.BooleanField(default=False)

    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blocked_ips'

    def __str__(self):
        return f"{self.ip_address} - {'Permanent' if self.is_permanent else 'Temporary'}"

    @property
    def is_active(self) -> bool:
        if self.is_permanent:
            return True
        if self.blocked_until:
            return timezone.now() < self.blocked_until
        return False


# =============================================================================
# Abuse Detection Configuration
# =============================================================================

class AbuseConfig:
    """Abuse detection configuration."""

    # Rate limits (requests per time window)
    RATE_LIMITS = {
        'login_attempts': {'limit': 5, 'window': 300},  # 5 per 5 minutes
        'password_reset': {'limit': 3, 'window': 3600},  # 3 per hour
        'api_requests': {'limit': 1000, 'window': 3600},  # 1000 per hour
        'ai_generations': {'limit': 100, 'window': 3600},  # 100 per hour
        'file_uploads': {'limit': 50, 'window': 3600},  # 50 per hour
        'exports': {'limit': 20, 'window': 3600},  # 20 per hour
    }

    # Thresholds
    FAILED_LOGIN_BLOCK_THRESHOLD = 10  # Block after 10 failed logins
    FAILED_LOGIN_BLOCK_DURATION = 3600  # 1 hour block
    SUSPICIOUS_LOCATION_THRESHOLD = 5  # Alerts after 5 different locations
    CONCURRENT_SESSION_LIMIT = 3  # Max concurrent sessions

    # Content moderation patterns
    SPAM_PATTERNS = [
        r'(?i)(buy|sell|discount|offer|click here|limited time)',
        r'(?i)(viagra|casino|lottery|winner)',
        r'(.)\1{10,}',  # Repeated characters
        r'(?i)(http[s]?://\S+){5,}',  # Multiple URLs
    ]

    # Bot detection
    BOT_USER_AGENTS = [
        'bot', 'crawler', 'spider', 'scraper',
        'headless', 'phantom', 'selenium'
    ]


# =============================================================================
# Abuse Detection Service
# =============================================================================

class AbuseDetectionService:
    """
    Main abuse detection service.

    Usage:
        service = AbuseDetectionService()
        is_blocked, reason = service.check_request(request)
        if is_blocked:
            return HttpResponseForbidden(reason)
    """

    def __init__(self):
        self.config = AbuseConfig
        self.cache_prefix = 'abuse:'

    # -------------------------------------------------------------------------
    # Request Checking
    # -------------------------------------------------------------------------

    def check_request(self, request) -> Tuple[bool, Optional[str]]:
        """
        Check if a request should be blocked.

        Args:
            request: Django request object

        Returns:
            Tuple of (is_blocked, reason)
        """
        ip = self._get_client_ip(request)
        user = request.user if request.user.is_authenticated else None

        # Check if IP is blocked
        if self._is_ip_blocked(ip):
            return True, "Your IP address has been blocked"

        # Check if user is blocked
        if user and hasattr(user, 'is_blocked') and user.is_blocked:
            return True, "Your account has been suspended"

        # Check for bot activity
        if self._is_bot(request):
            self._log_abuse(
                abuse_type=AbuseType.BOT_ACTIVITY,
                ip_address=ip,
                user=user,
                description="Bot activity detected",
                metadata={'user_agent': request.META.get('HTTP_USER_AGENT', '')}
            )
            return True, "Automated requests are not allowed"

        return False, None

    def check_rate_limit(
        self,
        identifier: str,
        limit_type: str,
        request=None
    ) -> Tuple[bool, int]:
        """
        Check rate limit for an action.

        Args:
            identifier: User ID or IP address
            limit_type: Type of rate limit to check
            request: Optional request object

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        config = self.config.RATE_LIMITS.get(limit_type)
        if not config:
            return True, -1

        cache_key = f"{self.cache_prefix}rate:{limit_type}:{identifier}"
        window = config['window']
        limit = config['limit']

        # Get current count
        current = cache.get(cache_key, 0)

        if current >= limit:
            # Rate limit exceeded
            if request:
                self._log_abuse(
                    abuse_type=AbuseType.RATE_LIMIT_EXCEEDED,
                    ip_address=self._get_client_ip(request),
                    user=request.user if request.user.is_authenticated else None,
                    description=f"Rate limit exceeded for {limit_type}",
                    severity=AbuseSeverity.MEDIUM
                )
            return False, 0

        # Increment counter
        if current == 0:
            cache.set(cache_key, 1, window)
        else:
            cache.incr(cache_key)

        return True, limit - current - 1

    # -------------------------------------------------------------------------
    # Login Monitoring
    # -------------------------------------------------------------------------

    def record_login_attempt(
        self,
        email: str,
        ip_address: str,
        success: bool,
        user_agent: str = ''
    ) -> Optional[Dict]:
        """
        Record a login attempt and check for suspicious activity.

        Args:
            email: Email address used
            ip_address: Source IP address
            success: Whether login was successful
            user_agent: Browser user agent

        Returns:
            Alert dict if suspicious activity detected
        """
        cache_key = f"{self.cache_prefix}login:{ip_address}"

        if success:
            # Clear failed attempts on success
            cache.delete(cache_key)
            return None

        # Increment failed attempts
        failed_count = cache.get(cache_key, 0) + 1
        cache.set(cache_key, failed_count, self.config.FAILED_LOGIN_BLOCK_DURATION)

        if failed_count >= self.config.FAILED_LOGIN_BLOCK_THRESHOLD:
            # Block IP
            self._block_ip(
                ip_address=ip_address,
                reason="Too many failed login attempts",
                duration_seconds=self.config.FAILED_LOGIN_BLOCK_DURATION
            )

            self._log_abuse(
                abuse_type=AbuseType.BRUTE_FORCE_ATTEMPT,
                ip_address=ip_address,
                description=f"Brute force attempt detected: {failed_count} failed logins",
                severity=AbuseSeverity.HIGH,
                action=AbuseAction.TEMPORARY_BLOCK,
                metadata={'email': email, 'attempts': failed_count}
            )

            return {
                'alert': 'brute_force',
                'ip': ip_address,
                'attempts': failed_count
            }

        return None

    def check_suspicious_login(
        self,
        user,
        ip_address: str,
        user_agent: str
    ) -> Optional[Dict]:
        """
        Check for suspicious login patterns.

        Args:
            user: User logging in
            ip_address: Login IP address
            user_agent: Browser user agent

        Returns:
            Alert dict if suspicious
        """
        alerts = []

        # Check for new location
        cache_key = f"{self.cache_prefix}locations:{user.id}"
        known_locations = set(cache.get(cache_key, []))

        # Get approximate location from IP (simplified)
        location = self._get_location_key(ip_address)

        if location not in known_locations:
            known_locations.add(location)
            cache.set(cache_key, list(known_locations), 86400 * 30)  # 30 days

            if len(known_locations) > self.config.SUSPICIOUS_LOCATION_THRESHOLD:
                alerts.append({
                    'type': 'new_location',
                    'location': location
                })

        # Check for device change
        device_key = f"{self.cache_prefix}device:{user.id}"
        known_devices = cache.get(device_key, [])
        device_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]

        if device_hash not in known_devices:
            known_devices.append(device_hash)
            cache.set(device_key, known_devices[-10:], 86400 * 30)  # Keep last 10

            alerts.append({
                'type': 'new_device',
                'device': user_agent[:100]
            })

        if alerts:
            self._log_abuse(
                abuse_type=AbuseType.SUSPICIOUS_LOGIN,
                user=user,
                ip_address=ip_address,
                description="Suspicious login detected",
                severity=AbuseSeverity.MEDIUM,
                metadata={'alerts': alerts}
            )

        return {'alerts': alerts} if alerts else None

    # -------------------------------------------------------------------------
    # Content Moderation
    # -------------------------------------------------------------------------

    def check_content(self, content: str) -> Tuple[bool, List[str]]:
        """
        Check content for spam or violations.

        Args:
            content: Text content to check

        Returns:
            Tuple of (is_safe, violations)
        """
        violations = []

        for pattern in self.config.SPAM_PATTERNS:
            if re.search(pattern, content):
                violations.append(f"Pattern match: {pattern[:30]}...")

        # Check content length
        if len(content) > 100000:  # 100KB
            violations.append("Content too long")

        # Check for excessive repetition
        words = content.lower().split()
        if words:
            word_freq = defaultdict(int)
            for word in words:
                word_freq[word] += 1

            max_freq = max(word_freq.values())
            if max_freq > len(words) * 0.3:  # Same word > 30% of content
                violations.append("Excessive word repetition")

        return len(violations) == 0, violations

    def moderate_content(
        self,
        content: str,
        user=None,
        content_type: str = 'text'
    ) -> Dict:
        """
        Full content moderation check.

        Args:
            content: Content to moderate
            user: Content author
            content_type: Type of content

        Returns:
            Moderation result dict
        """
        is_safe, violations = self.check_content(content)

        result = {
            'is_safe': is_safe,
            'violations': violations,
            'action': 'approved' if is_safe else 'flagged'
        }

        if not is_safe:
            self._log_abuse(
                abuse_type=AbuseType.CONTENT_VIOLATION,
                user=user,
                description=f"Content flagged: {', '.join(violations)}",
                severity=AbuseSeverity.MEDIUM,
                metadata={
                    'content_type': content_type,
                    'content_preview': content[:200],
                    'violations': violations
                }
            )

        return result

    # -------------------------------------------------------------------------
    # IP Management
    # -------------------------------------------------------------------------

    def _is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked."""
        # Check cache first
        cache_key = f"{self.cache_prefix}blocked_ip:{ip_address}"
        if cache.get(cache_key):
            return True

        # Check database
        try:
            block = BlockedIP.objects.get(ip_address=ip_address)
            if block.is_active:
                cache.set(cache_key, True, 300)  # Cache for 5 minutes
                return True
        except BlockedIP.DoesNotExist:
            pass

        return False

    def _block_ip(
        self,
        ip_address: str,
        reason: str,
        duration_seconds: int = None,
        permanent: bool = False
    ):
        """Block an IP address."""
        blocked_until = None
        if duration_seconds and not permanent:
            blocked_until = timezone.now() + timedelta(seconds=duration_seconds)

        BlockedIP.objects.update_or_create(
            ip_address=ip_address,
            defaults={
                'reason': reason,
                'blocked_until': blocked_until,
                'is_permanent': permanent,
            }
        )

        # Update cache
        cache_key = f"{self.cache_prefix}blocked_ip:{ip_address}"
        cache_duration = duration_seconds or 86400 * 365  # 1 year for permanent
        cache.set(cache_key, True, cache_duration)

        logger.warning(f"IP blocked: {ip_address} - {reason}")

    def unblock_ip(self, ip_address: str) -> bool:
        """Unblock an IP address."""
        try:
            BlockedIP.objects.filter(ip_address=ip_address).delete()
            cache.delete(f"{self.cache_prefix}blocked_ip:{ip_address}")
            logger.info(f"IP unblocked: {ip_address}")
            return True
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _get_location_key(self, ip_address: str) -> str:
        """Get location key from IP (simplified)."""
        # In production, use a GeoIP service
        parts = ip_address.split('.')[:2]
        return '.'.join(parts) if len(parts) == 2 else ip_address

    def _is_bot(self, request) -> bool:
        """Check if request appears to be from a bot."""
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()

        for pattern in self.config.BOT_USER_AGENTS:
            if pattern in user_agent:
                return True

        # Check for missing common headers
        if not request.META.get('HTTP_ACCEPT_LANGUAGE'):
            return True

        return False

    def _log_abuse(
        self,
        abuse_type: AbuseType,
        description: str,
        user=None,
        ip_address: str = None,
        severity: AbuseSeverity = AbuseSeverity.LOW,
        action: AbuseAction = AbuseAction.LOG_ONLY,
        metadata: Dict = None
    ):
        """Log an abuse incident."""
        AbuseLog.objects.create(
            user=user,
            ip_address=ip_address,
            abuse_type=abuse_type.value,
            severity=severity.value,
            description=description,
            action_taken=action.value,
            metadata=metadata or {}
        )

        # Notify admin for high severity
        if severity.value >= AbuseSeverity.HIGH.value:
            self._notify_admin(abuse_type, description, metadata)

    def _notify_admin(
        self,
        abuse_type: AbuseType,
        description: str,
        metadata: Dict = None
    ):
        """Notify admin of high-severity abuse."""
        try:
            from coreapp.services.notification_service import notification_service

            # Log for now, implement actual notification as needed
            logger.critical(
                f"ABUSE ALERT: {abuse_type.value} - {description}",
                extra={'metadata': metadata}
            )
        except Exception as e:
            logger.error(f"Failed to notify admin of abuse: {e}")

    # -------------------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------------------

    def get_abuse_stats(self, days: int = 7) -> Dict:
        """Get abuse statistics."""
        since = timezone.now() - timedelta(days=days)

        logs = AbuseLog.objects.filter(created_at__gte=since)

        stats = {
            'total_incidents': logs.count(),
            'by_type': {},
            'by_severity': {},
            'blocked_ips': BlockedIP.objects.filter(is_permanent=False).count(),
            'permanent_blocks': BlockedIP.objects.filter(is_permanent=True).count(),
        }

        # Count by type
        for abuse_type in AbuseType:
            count = logs.filter(abuse_type=abuse_type.value).count()
            if count > 0:
                stats['by_type'][abuse_type.value] = count

        # Count by severity
        for severity in AbuseSeverity:
            count = logs.filter(severity=severity.value).count()
            if count > 0:
                stats['by_severity'][severity.name] = count

        return stats


# =============================================================================
# Singleton Instance
# =============================================================================

abuse_detection_service = AbuseDetectionService()
