"""
Feature Flags Management for MultinotesAI.

This module provides:
- Feature flag management
- A/B testing support
- Gradual rollout
- User targeting
"""

import logging
import random
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Feature Flag Types
# =============================================================================

class FlagType(Enum):
    """Types of feature flags."""
    BOOLEAN = 'boolean'  # Simple on/off
    PERCENTAGE = 'percentage'  # Percentage rollout
    USER_LIST = 'user_list'  # Specific users
    SUBSCRIPTION = 'subscription'  # Based on subscription plan
    DATE_RANGE = 'date_range'  # Time-based
    AB_TEST = 'ab_test'  # A/B testing


class FlagStatus(Enum):
    """Feature flag status."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SCHEDULED = 'scheduled'
    ARCHIVED = 'archived'


# =============================================================================
# Feature Flag Model
# =============================================================================

class FeatureFlag(models.Model):
    """Feature flag model."""

    # Identification
    key = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Type and configuration
    flag_type = models.CharField(
        max_length=20,
        choices=[(t.value, t.name) for t in FlagType],
        default=FlagType.BOOLEAN.value
    )
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in FlagStatus],
        default=FlagStatus.INACTIVE.value
    )

    # Value configuration (JSON for flexibility)
    default_value = models.BooleanField(default=False)
    config = models.JSONField(default=dict)
    # Config examples:
    # percentage: {"percentage": 50}
    # user_list: {"user_ids": [1, 2, 3], "user_emails": ["test@example.com"]}
    # subscription: {"plans": ["pro", "enterprise"]}
    # date_range: {"start": "2024-01-01", "end": "2024-12-31"}
    # ab_test: {"variants": ["control", "variant_a", "variant_b"], "weights": [50, 25, 25]}

    # Scheduling
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_flags'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'feature_flags'
        ordering = ['name']

    def __str__(self):
        return f"{self.key} ({self.status})"


class FeatureFlagOverride(models.Model):
    """Per-user override for feature flags."""

    flag = models.ForeignKey(
        FeatureFlag,
        on_delete=models.CASCADE,
        related_name='overrides'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='flag_overrides'
    )
    value = models.BooleanField(default=True)
    variant = models.CharField(max_length=50, blank=True)  # For A/B tests

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feature_flag_overrides'
        unique_together = ['flag', 'user']

    def __str__(self):
        return f"{self.flag.key} override for {self.user.email}"


class ABTestResult(models.Model):
    """Track A/B test results."""

    flag = models.ForeignKey(
        FeatureFlag,
        on_delete=models.CASCADE,
        related_name='ab_results'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    variant = models.CharField(max_length=50)
    converted = models.BooleanField(default=False)
    conversion_event = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ab_test_results'
        indexes = [
            models.Index(fields=['flag', 'variant']),
            models.Index(fields=['flag', '-created_at']),
        ]


# =============================================================================
# Feature Flag Service
# =============================================================================

class FeatureFlagService:
    """
    Service for evaluating feature flags.

    Usage:
        flags = FeatureFlagService()

        # Simple check
        if flags.is_enabled('new_dashboard', user=user):
            show_new_dashboard()

        # A/B test
        variant = flags.get_variant('checkout_flow', user=user)
        if variant == 'variant_a':
            show_new_checkout()
    """

    CACHE_PREFIX = 'feature_flag:'
    CACHE_TIMEOUT = 60  # 1 minute

    def is_enabled(
        self,
        flag_key: str,
        user=None,
        default: bool = False,
        context: Dict = None
    ) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag_key: Feature flag key
            user: User to evaluate for
            default: Default value if flag not found
            context: Additional context for evaluation

        Returns:
            True if enabled, False otherwise
        """
        flag = self._get_flag(flag_key)

        if not flag:
            return default

        # Check status
        if flag.status != FlagStatus.ACTIVE.value:
            if flag.status == FlagStatus.SCHEDULED.value:
                if not self._is_in_schedule(flag):
                    return default
            else:
                return default

        # Check user override first
        if user:
            override = self._get_override(flag, user)
            if override is not None:
                return override

        # Evaluate based on flag type
        return self._evaluate_flag(flag, user, context)

    def get_variant(
        self,
        flag_key: str,
        user=None,
        default: str = 'control'
    ) -> str:
        """
        Get A/B test variant for user.

        Args:
            flag_key: Feature flag key
            user: User to get variant for
            default: Default variant

        Returns:
            Variant name
        """
        flag = self._get_flag(flag_key)

        if not flag or flag.flag_type != FlagType.AB_TEST.value:
            return default

        if flag.status != FlagStatus.ACTIVE.value:
            return default

        # Check for override
        if user:
            override = FeatureFlagOverride.objects.filter(
                flag=flag,
                user=user
            ).first()
            if override and override.variant:
                return override.variant

        # Assign variant
        return self._assign_variant(flag, user)

    def _get_flag(self, key: str) -> Optional[FeatureFlag]:
        """Get feature flag by key (with caching)."""
        cache_key = f"{self.CACHE_PREFIX}{key}"
        flag = cache.get(cache_key)

        if flag is None:
            try:
                flag = FeatureFlag.objects.get(key=key)
                cache.set(cache_key, flag, self.CACHE_TIMEOUT)
            except FeatureFlag.DoesNotExist:
                return None

        return flag

    def _get_override(self, flag: FeatureFlag, user) -> Optional[bool]:
        """Get user-specific override."""
        try:
            override = FeatureFlagOverride.objects.get(flag=flag, user=user)
            return override.value
        except FeatureFlagOverride.DoesNotExist:
            return None

    def _evaluate_flag(
        self,
        flag: FeatureFlag,
        user=None,
        context: Dict = None
    ) -> bool:
        """Evaluate flag based on its type."""
        flag_type = flag.flag_type
        config = flag.config or {}

        if flag_type == FlagType.BOOLEAN.value:
            return flag.default_value

        elif flag_type == FlagType.PERCENTAGE.value:
            percentage = config.get('percentage', 0)
            return self._check_percentage(flag.key, user, percentage)

        elif flag_type == FlagType.USER_LIST.value:
            if not user:
                return flag.default_value
            user_ids = config.get('user_ids', [])
            user_emails = config.get('user_emails', [])
            return user.id in user_ids or user.email in user_emails

        elif flag_type == FlagType.SUBSCRIPTION.value:
            if not user:
                return flag.default_value
            allowed_plans = config.get('plans', [])
            return self._check_subscription(user, allowed_plans)

        elif flag_type == FlagType.DATE_RANGE.value:
            return self._is_in_schedule(flag)

        elif flag_type == FlagType.AB_TEST.value:
            # For A/B tests, is_enabled returns True if user gets any variant
            variant = self._assign_variant(flag, user)
            return variant != 'control'

        return flag.default_value

    def _check_percentage(
        self,
        flag_key: str,
        user,
        percentage: int
    ) -> bool:
        """Check percentage-based rollout."""
        # Use deterministic hash for consistent user experience
        if user:
            identifier = f"{flag_key}:{user.id}"
        else:
            identifier = f"{flag_key}:{random.random()}"

        hash_value = int(hashlib.md5(identifier.encode()).hexdigest(), 16)
        user_percentage = hash_value % 100

        return user_percentage < percentage

    def _check_subscription(self, user, allowed_plans: List[str]) -> bool:
        """Check if user's subscription plan is allowed."""
        try:
            from planandsubscription.models import Subscription

            subscription = Subscription.objects.filter(
                user=user,
                status='active',
                is_delete=False
            ).select_related('plan').first()

            if subscription and subscription.plan:
                plan_name = subscription.plan.name.lower()
                return any(p.lower() in plan_name for p in allowed_plans)

            return False
        except Exception:
            return False

    def _is_in_schedule(self, flag: FeatureFlag) -> bool:
        """Check if current time is within flag's schedule."""
        now = timezone.now()

        if flag.start_date and now < flag.start_date:
            return False
        if flag.end_date and now > flag.end_date:
            return False

        return True

    def _assign_variant(self, flag: FeatureFlag, user) -> str:
        """Assign A/B test variant to user."""
        config = flag.config or {}
        variants = config.get('variants', ['control', 'variant'])
        weights = config.get('weights', [50, 50])

        if not variants:
            return 'control'

        # Deterministic assignment based on user
        if user:
            identifier = f"{flag.key}:{user.id}"
        else:
            identifier = f"{flag.key}:{random.random()}"

        hash_value = int(hashlib.md5(identifier.encode()).hexdigest(), 16)
        user_percentage = hash_value % 100

        # Select variant based on weights
        cumulative = 0
        for variant, weight in zip(variants, weights):
            cumulative += weight
            if user_percentage < cumulative:
                # Record variant assignment
                if user:
                    self._record_variant_assignment(flag, user, variant)
                return variant

        return variants[-1]

    def _record_variant_assignment(
        self,
        flag: FeatureFlag,
        user,
        variant: str
    ):
        """Record A/B test variant assignment."""
        try:
            ABTestResult.objects.get_or_create(
                flag=flag,
                user=user,
                defaults={'variant': variant}
            )
        except Exception as e:
            logger.error(f"Error recording variant assignment: {e}")

    # -------------------------------------------------------------------------
    # Management Methods
    # -------------------------------------------------------------------------

    def create_flag(
        self,
        key: str,
        name: str,
        flag_type: FlagType = FlagType.BOOLEAN,
        config: Dict = None,
        created_by=None,
        **kwargs
    ) -> FeatureFlag:
        """Create a new feature flag."""
        flag = FeatureFlag.objects.create(
            key=key,
            name=name,
            flag_type=flag_type.value,
            config=config or {},
            created_by=created_by,
            **kwargs
        )

        logger.info(f"Feature flag created: {key}")
        return flag

    def update_flag(
        self,
        key: str,
        **updates
    ) -> Optional[FeatureFlag]:
        """Update a feature flag."""
        try:
            flag = FeatureFlag.objects.get(key=key)

            for field, value in updates.items():
                if hasattr(flag, field):
                    setattr(flag, field, value)

            flag.save()

            # Clear cache
            cache.delete(f"{self.CACHE_PREFIX}{key}")

            return flag
        except FeatureFlag.DoesNotExist:
            return None

    def delete_flag(self, key: str) -> bool:
        """Delete a feature flag."""
        try:
            flag = FeatureFlag.objects.get(key=key)
            flag.delete()
            cache.delete(f"{self.CACHE_PREFIX}{key}")
            return True
        except FeatureFlag.DoesNotExist:
            return False

    def set_override(
        self,
        flag_key: str,
        user,
        value: bool,
        variant: str = ''
    ) -> bool:
        """Set user override for a flag."""
        try:
            flag = FeatureFlag.objects.get(key=flag_key)
            FeatureFlagOverride.objects.update_or_create(
                flag=flag,
                user=user,
                defaults={'value': value, 'variant': variant}
            )
            return True
        except FeatureFlag.DoesNotExist:
            return False

    def remove_override(self, flag_key: str, user) -> bool:
        """Remove user override for a flag."""
        try:
            flag = FeatureFlag.objects.get(key=flag_key)
            FeatureFlagOverride.objects.filter(flag=flag, user=user).delete()
            return True
        except FeatureFlag.DoesNotExist:
            return False

    def get_all_flags(self, active_only: bool = True) -> List[FeatureFlag]:
        """Get all feature flags."""
        queryset = FeatureFlag.objects.all()
        if active_only:
            queryset = queryset.filter(status=FlagStatus.ACTIVE.value)
        return list(queryset)

    def get_user_flags(self, user) -> Dict[str, bool]:
        """Get all flag values for a user."""
        flags = self.get_all_flags(active_only=True)
        return {
            flag.key: self.is_enabled(flag.key, user=user)
            for flag in flags
        }

    # -------------------------------------------------------------------------
    # A/B Test Analytics
    # -------------------------------------------------------------------------

    def record_conversion(
        self,
        flag_key: str,
        user,
        event: str = 'conversion'
    ):
        """Record A/B test conversion."""
        try:
            flag = FeatureFlag.objects.get(key=flag_key)
            result = ABTestResult.objects.filter(flag=flag, user=user).first()

            if result and not result.converted:
                result.converted = True
                result.conversion_event = event
                result.converted_at = timezone.now()
                result.save()

        except FeatureFlag.DoesNotExist:
            pass

    def get_ab_test_results(self, flag_key: str) -> Dict:
        """Get A/B test results."""
        try:
            flag = FeatureFlag.objects.get(key=flag_key)
            results = ABTestResult.objects.filter(flag=flag)

            variants = flag.config.get('variants', [])
            stats = {}

            for variant in variants:
                variant_results = results.filter(variant=variant)
                total = variant_results.count()
                converted = variant_results.filter(converted=True).count()

                stats[variant] = {
                    'total': total,
                    'converted': converted,
                    'conversion_rate': round(
                        (converted / max(total, 1)) * 100, 2
                    )
                }

            return {
                'flag_key': flag_key,
                'variants': stats,
                'total_participants': results.count(),
            }

        except FeatureFlag.DoesNotExist:
            return {}


# =============================================================================
# Singleton Instance
# =============================================================================

feature_flags = FeatureFlagService()
