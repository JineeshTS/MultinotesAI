"""
API Key Generation Service for MultinotesAI.

This module provides:
- User API key generation
- Key management and rotation
- Key authentication
- Usage tracking per key
"""

import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# API Key Model
# =============================================================================

class UserAPIKey(models.Model):
    """User API key for external integrations."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )

    # Key identification
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=8, db_index=True)  # First 8 chars for lookup
    key_hash = models.CharField(max_length=64, unique=True)  # SHA-256 hash

    # Permissions
    scopes = models.JSONField(default=list)  # ['read', 'write', 'generate']
    rate_limit = models.IntegerField(default=1000)  # Requests per hour

    # Metadata
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)
    total_requests = models.IntegerField(default=0)

    # Validity
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_api_keys'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['prefix']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.name} ({self.prefix}...)"

    @property
    def is_valid(self) -> bool:
        """Check if key is valid."""
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Check if key is expired."""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False


class APIKeyUsageLog(models.Model):
    """Log API key usage for analytics."""

    api_key = models.ForeignKey(
        UserAPIKey,
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_key_usage_logs'
        indexes = [
            models.Index(fields=['api_key', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-created_at']


# =============================================================================
# API Key Service
# =============================================================================

class APIKeyService:
    """
    Service for API key management.

    Usage:
        service = APIKeyService()
        key, raw_key = service.create_key(
            user=user,
            name='My Integration',
            scopes=['read', 'generate']
        )
    """

    KEY_PREFIX = 'mna_'  # MultinotesAI
    KEY_LENGTH = 40
    CACHE_PREFIX = 'apikey:'

    # Available scopes
    SCOPES = {
        'read': 'Read content and user data',
        'write': 'Create and modify content',
        'generate': 'Use AI generation features',
        'export': 'Export content',
        'admin': 'Full access (admin only)',
    }

    # -------------------------------------------------------------------------
    # Key Generation
    # -------------------------------------------------------------------------

    def create_key(
        self,
        user,
        name: str,
        scopes: List[str] = None,
        expires_in_days: int = None,
        rate_limit: int = 1000
    ) -> tuple:
        """
        Create a new API key.

        Args:
            user: User owning the key
            name: Key name/description
            scopes: Permission scopes
            expires_in_days: Days until expiration (None = never)
            rate_limit: Requests per hour

        Returns:
            Tuple of (UserAPIKey, raw_key)
        """
        # Validate scopes
        scopes = scopes or ['read', 'generate']
        invalid_scopes = set(scopes) - set(self.SCOPES.keys())
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}")

        # Generate raw key
        raw_key = self._generate_key()
        prefix = raw_key[:8]
        key_hash = self._hash_key(raw_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = timezone.now() + timedelta(days=expires_in_days)

        # Create key record
        api_key = UserAPIKey.objects.create(
            user=user,
            name=name,
            prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
            rate_limit=rate_limit,
            expires_at=expires_at,
        )

        logger.info(f"API key created: {api_key.id} for user {user.id}")

        # Return both the model and raw key (raw key is only shown once!)
        return api_key, raw_key

    def _generate_key(self) -> str:
        """Generate a secure API key."""
        random_part = secrets.token_urlsafe(self.KEY_LENGTH)
        return f"{self.KEY_PREFIX}{random_part}"

    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(raw_key.encode()).hexdigest()

    # -------------------------------------------------------------------------
    # Key Validation
    # -------------------------------------------------------------------------

    def validate_key(self, raw_key: str) -> Optional[UserAPIKey]:
        """
        Validate an API key.

        Args:
            raw_key: The raw API key

        Returns:
            UserAPIKey if valid, None otherwise
        """
        if not raw_key or not raw_key.startswith(self.KEY_PREFIX):
            return None

        # Check cache first
        cache_key = f"{self.CACHE_PREFIX}validated:{raw_key[:8]}"
        cached_key_id = cache.get(cache_key)

        if cached_key_id:
            try:
                api_key = UserAPIKey.objects.select_related('user').get(id=cached_key_id)
                if api_key.is_valid:
                    return api_key
            except UserAPIKey.DoesNotExist:
                cache.delete(cache_key)

        # Look up by prefix and verify hash
        key_hash = self._hash_key(raw_key)
        prefix = raw_key[:8]

        try:
            api_key = UserAPIKey.objects.select_related('user').get(
                prefix=prefix,
                key_hash=key_hash
            )

            if not api_key.is_valid:
                return None

            # Cache for future lookups
            cache.set(cache_key, api_key.id, 300)  # 5 minutes

            return api_key

        except UserAPIKey.DoesNotExist:
            return None

    def authenticate(self, raw_key: str, required_scope: str = None) -> tuple:
        """
        Authenticate using API key.

        Args:
            raw_key: The raw API key
            required_scope: Required scope for the operation

        Returns:
            Tuple of (user, api_key) or (None, None)
        """
        api_key = self.validate_key(raw_key)

        if not api_key:
            return None, None

        # Check scope if required
        if required_scope and required_scope not in api_key.scopes:
            if 'admin' not in api_key.scopes:  # Admin scope grants all
                return None, None

        return api_key.user, api_key

    # -------------------------------------------------------------------------
    # Key Management
    # -------------------------------------------------------------------------

    def get_user_keys(self, user, include_inactive: bool = False) -> List[UserAPIKey]:
        """Get all API keys for a user."""
        queryset = UserAPIKey.objects.filter(user=user)

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        return list(queryset)

    def revoke_key(self, key_id: int, user) -> bool:
        """Revoke an API key."""
        try:
            api_key = UserAPIKey.objects.get(id=key_id, user=user)
            api_key.is_active = False
            api_key.save()

            # Clear cache
            cache.delete(f"{self.CACHE_PREFIX}validated:{api_key.prefix}")

            logger.info(f"API key revoked: {key_id}")
            return True

        except UserAPIKey.DoesNotExist:
            return False

    def rotate_key(self, key_id: int, user) -> tuple:
        """
        Rotate an API key (revoke old, create new).

        Args:
            key_id: ID of key to rotate
            user: Key owner

        Returns:
            Tuple of (new_key, raw_key)
        """
        try:
            old_key = UserAPIKey.objects.get(id=key_id, user=user)

            # Create new key with same settings
            new_key, raw_key = self.create_key(
                user=user,
                name=f"{old_key.name} (rotated)",
                scopes=old_key.scopes,
                rate_limit=old_key.rate_limit,
            )

            # Revoke old key
            old_key.is_active = False
            old_key.save()

            logger.info(f"API key rotated: {key_id} -> {new_key.id}")
            return new_key, raw_key

        except UserAPIKey.DoesNotExist:
            return None, None

    def update_key(
        self,
        key_id: int,
        user,
        name: str = None,
        scopes: List[str] = None,
        rate_limit: int = None
    ) -> Optional[UserAPIKey]:
        """Update API key settings."""
        try:
            api_key = UserAPIKey.objects.get(id=key_id, user=user)

            if name:
                api_key.name = name
            if scopes:
                api_key.scopes = scopes
            if rate_limit:
                api_key.rate_limit = rate_limit

            api_key.save()
            return api_key

        except UserAPIKey.DoesNotExist:
            return None

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------

    def check_rate_limit(self, api_key: UserAPIKey) -> tuple:
        """
        Check if API key is within rate limits.

        Args:
            api_key: The API key

        Returns:
            Tuple of (is_allowed, remaining, reset_time)
        """
        cache_key = f"{self.CACHE_PREFIX}ratelimit:{api_key.id}"
        current_count = cache.get(cache_key, 0)

        if current_count >= api_key.rate_limit:
            # Get TTL for reset time
            ttl = cache.ttl(cache_key) or 3600
            return False, 0, ttl

        return True, api_key.rate_limit - current_count - 1, 3600

    def increment_usage(self, api_key: UserAPIKey):
        """Increment API key usage counter."""
        cache_key = f"{self.CACHE_PREFIX}ratelimit:{api_key.id}"
        current = cache.get(cache_key, 0)

        if current == 0:
            cache.set(cache_key, 1, 3600)  # 1 hour window
        else:
            cache.incr(cache_key)

    # -------------------------------------------------------------------------
    # Usage Logging
    # -------------------------------------------------------------------------

    def log_usage(
        self,
        api_key: UserAPIKey,
        endpoint: str,
        method: str,
        status_code: int,
        ip_address: str = None,
        response_time_ms: int = None
    ):
        """Log API key usage."""
        try:
            APIKeyUsageLog.objects.create(
                api_key=api_key,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                ip_address=ip_address,
                response_time_ms=response_time_ms,
            )

            # Update key metadata
            api_key.last_used_at = timezone.now()
            api_key.last_used_ip = ip_address
            api_key.total_requests += 1
            api_key.save(update_fields=['last_used_at', 'last_used_ip', 'total_requests'])

        except Exception as e:
            logger.error(f"Error logging API key usage: {e}")

    def get_usage_stats(
        self,
        api_key: UserAPIKey,
        days: int = 30
    ) -> Dict:
        """Get usage statistics for an API key."""
        since = timezone.now() - timedelta(days=days)

        logs = APIKeyUsageLog.objects.filter(
            api_key=api_key,
            created_at__gte=since
        )

        total_requests = logs.count()
        success_requests = logs.filter(status_code__lt=400).count()

        return {
            'total_requests': total_requests,
            'success_requests': success_requests,
            'error_requests': total_requests - success_requests,
            'success_rate': round((success_requests / max(total_requests, 1)) * 100, 2),
            'last_used': api_key.last_used_at,
            'last_ip': api_key.last_used_ip,
        }

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def cleanup_expired_keys(self) -> int:
        """Deactivate expired API keys."""
        expired = UserAPIKey.objects.filter(
            is_active=True,
            expires_at__lt=timezone.now()
        )

        count = expired.count()
        expired.update(is_active=False)

        logger.info(f"Deactivated {count} expired API keys")
        return count

    def cleanup_old_logs(self, days: int = 90) -> int:
        """Delete old usage logs."""
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = APIKeyUsageLog.objects.filter(
            created_at__lt=cutoff
        ).delete()

        logger.info(f"Deleted {deleted} old API key usage logs")
        return deleted


# =============================================================================
# API Key Authentication Backend
# =============================================================================

class APIKeyAuthentication:
    """
    DRF Authentication class for API keys.

    Usage in views:
        authentication_classes = [APIKeyAuthentication]

    Header format:
        Authorization: Bearer mna_xxxxx...
        or
        X-API-Key: mna_xxxxx...
    """

    def authenticate(self, request):
        """Authenticate request using API key."""
        api_key_service = APIKeyService()

        # Try Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            raw_key = auth_header[7:]
        else:
            # Try X-API-Key header
            raw_key = request.META.get('HTTP_X_API_KEY', '')

        if not raw_key:
            return None

        user, api_key = api_key_service.authenticate(raw_key)

        if not user:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Invalid API key')

        # Check rate limit
        is_allowed, remaining, reset = api_key_service.check_rate_limit(api_key)
        if not is_allowed:
            from rest_framework.exceptions import Throttled
            raise Throttled(detail='API key rate limit exceeded')

        # Increment usage
        api_key_service.increment_usage(api_key)

        # Attach api_key to request for later use
        request.api_key = api_key

        return (user, api_key)

    def authenticate_header(self, request):
        """Return authentication header."""
        return 'Bearer'


# =============================================================================
# Singleton Instance
# =============================================================================

api_key_service = APIKeyService()
