"""
User Onboarding Models for MultinotesAI.

This module provides:
- Onboarding progress tracking
- User preferences setup
- Feature discovery
- Product tour management
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from django.db import models
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Onboarding Steps
# =============================================================================

ONBOARDING_STEPS = {
    'account_created': {
        'order': 1,
        'title': 'Account Created',
        'description': 'Welcome to MultinotesAI!',
        'auto_complete': True,
    },
    'email_verified': {
        'order': 2,
        'title': 'Email Verified',
        'description': 'Verify your email address',
        'auto_complete': True,
    },
    'profile_completed': {
        'order': 3,
        'title': 'Complete Profile',
        'description': 'Add your name and preferences',
        'required_fields': ['first_name'],
    },
    'first_note_created': {
        'order': 4,
        'title': 'Create First Note',
        'description': 'Create your first AI-powered note',
    },
    'first_ai_generation': {
        'order': 5,
        'title': 'Generate Content',
        'description': 'Use AI to generate content',
    },
    'explore_models': {
        'order': 6,
        'title': 'Explore AI Models',
        'description': 'Try different AI models',
    },
    'create_folder': {
        'order': 7,
        'title': 'Organize Content',
        'description': 'Create a folder to organize your work',
    },
    'explore_templates': {
        'order': 8,
        'title': 'Explore Templates',
        'description': 'Browse prompt templates',
    },
    'subscription_viewed': {
        'order': 9,
        'title': 'View Plans',
        'description': 'Explore subscription options',
    },
    'onboarding_complete': {
        'order': 10,
        'title': 'Onboarding Complete',
        'description': 'You\'re all set!',
        'auto_complete': True,
    },
}


# =============================================================================
# User Onboarding Model
# =============================================================================

class UserOnboarding(models.Model):
    """Track user onboarding progress."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='onboarding'
    )

    # Progress tracking
    completed_steps = models.JSONField(default=list)
    current_step = models.CharField(max_length=50, default='account_created')
    is_complete = models.BooleanField(default=False)

    # Preferences collected during onboarding
    use_case = models.CharField(max_length=100, blank=True)
    primary_goal = models.CharField(max_length=100, blank=True)
    experience_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        default='beginner'
    )
    preferred_model_type = models.CharField(max_length=50, blank=True)

    # Tour and tips
    has_seen_tour = models.BooleanField(default=False)
    dismissed_tips = models.JSONField(default=list)

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_onboarding'

    def __str__(self):
        return f"Onboarding for {self.user.email}"

    @property
    def progress_percentage(self) -> int:
        """Calculate onboarding progress percentage."""
        total_steps = len(ONBOARDING_STEPS)
        completed = len(self.completed_steps)
        return int((completed / total_steps) * 100)

    @property
    def next_step(self) -> Optional[str]:
        """Get the next uncompleted step."""
        for step_key, step_info in sorted(
            ONBOARDING_STEPS.items(),
            key=lambda x: x[1]['order']
        ):
            if step_key not in self.completed_steps:
                return step_key
        return None


class OnboardingEvent(models.Model):
    """Track onboarding-related events."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='onboarding_events'
    )
    event_type = models.CharField(max_length=50)
    event_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'onboarding_events'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
        ]
        ordering = ['-created_at']


class FeatureTip(models.Model):
    """Feature tips shown to users."""

    key = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    target_element = models.CharField(max_length=100, blank=True)
    placement = models.CharField(max_length=20, default='bottom')

    # Targeting
    show_to_new_users = models.BooleanField(default=True)
    required_step = models.CharField(max_length=50, blank=True)
    min_usage_days = models.IntegerField(default=0)

    # Display settings
    priority = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'feature_tips'
        ordering = ['-priority', 'key']

    def __str__(self):
        return self.key


# =============================================================================
# Onboarding Service
# =============================================================================

class OnboardingService:
    """
    Service for managing user onboarding.

    Usage:
        service = OnboardingService()
        service.start_onboarding(user)
        service.complete_step(user, 'first_note_created')
    """

    def start_onboarding(self, user) -> UserOnboarding:
        """Start onboarding for a new user."""
        onboarding, created = UserOnboarding.objects.get_or_create(
            user=user,
            defaults={
                'completed_steps': ['account_created'],
                'current_step': 'email_verified',
            }
        )

        if created:
            self._log_event(user, 'onboarding_started')

        return onboarding

    def get_onboarding(self, user) -> Optional[UserOnboarding]:
        """Get user's onboarding progress."""
        try:
            return UserOnboarding.objects.get(user=user)
        except UserOnboarding.DoesNotExist:
            return None

    def complete_step(self, user, step: str) -> bool:
        """
        Mark an onboarding step as complete.

        Args:
            user: User
            step: Step key to complete

        Returns:
            True if step was completed
        """
        if step not in ONBOARDING_STEPS:
            return False

        onboarding = self.get_onboarding(user)
        if not onboarding:
            onboarding = self.start_onboarding(user)

        if step in onboarding.completed_steps:
            return False  # Already completed

        # Add to completed steps
        onboarding.completed_steps.append(step)

        # Update current step
        next_step = onboarding.next_step
        if next_step:
            onboarding.current_step = next_step
        else:
            # All steps complete
            onboarding.is_complete = True
            onboarding.completed_at = timezone.now()
            onboarding.current_step = 'onboarding_complete'

        onboarding.save()

        # Log event
        self._log_event(user, 'step_completed', {'step': step})

        # Check if onboarding is now complete
        if onboarding.is_complete:
            self._log_event(user, 'onboarding_completed')

        return True

    def get_progress(self, user) -> Dict:
        """Get onboarding progress for a user."""
        onboarding = self.get_onboarding(user)

        if not onboarding:
            return {
                'is_complete': False,
                'progress': 0,
                'current_step': None,
                'completed_steps': [],
                'remaining_steps': list(ONBOARDING_STEPS.keys()),
            }

        remaining = [
            step for step in ONBOARDING_STEPS.keys()
            if step not in onboarding.completed_steps
        ]

        return {
            'is_complete': onboarding.is_complete,
            'progress': onboarding.progress_percentage,
            'current_step': onboarding.current_step,
            'completed_steps': onboarding.completed_steps,
            'remaining_steps': remaining,
            'steps_detail': self._get_steps_detail(onboarding),
        }

    def _get_steps_detail(self, onboarding: UserOnboarding) -> List[Dict]:
        """Get detailed step information."""
        steps = []
        for key, info in sorted(
            ONBOARDING_STEPS.items(),
            key=lambda x: x[1]['order']
        ):
            steps.append({
                'key': key,
                'title': info['title'],
                'description': info['description'],
                'order': info['order'],
                'is_completed': key in onboarding.completed_steps,
                'is_current': key == onboarding.current_step,
            })
        return steps

    def update_preferences(
        self,
        user,
        use_case: str = None,
        primary_goal: str = None,
        experience_level: str = None,
        preferred_model_type: str = None
    ) -> UserOnboarding:
        """Update onboarding preferences."""
        onboarding = self.get_onboarding(user)
        if not onboarding:
            onboarding = self.start_onboarding(user)

        if use_case:
            onboarding.use_case = use_case
        if primary_goal:
            onboarding.primary_goal = primary_goal
        if experience_level:
            onboarding.experience_level = experience_level
        if preferred_model_type:
            onboarding.preferred_model_type = preferred_model_type

        onboarding.save()
        return onboarding

    def mark_tour_seen(self, user) -> bool:
        """Mark product tour as seen."""
        onboarding = self.get_onboarding(user)
        if onboarding:
            onboarding.has_seen_tour = True
            onboarding.save()
            self._log_event(user, 'tour_completed')
            return True
        return False

    def dismiss_tip(self, user, tip_key: str) -> bool:
        """Dismiss a feature tip."""
        onboarding = self.get_onboarding(user)
        if onboarding and tip_key not in onboarding.dismissed_tips:
            onboarding.dismissed_tips.append(tip_key)
            onboarding.save()
            return True
        return False

    def get_tips_for_user(self, user) -> List[FeatureTip]:
        """Get relevant tips for a user."""
        onboarding = self.get_onboarding(user)
        if not onboarding:
            return []

        # Get active tips not dismissed by user
        tips = FeatureTip.objects.filter(is_active=True).exclude(
            key__in=onboarding.dismissed_tips
        )

        # Filter by targeting
        result = []
        for tip in tips:
            # Check new user requirement
            if tip.show_to_new_users:
                days_since_signup = (timezone.now() - onboarding.started_at).days
                if days_since_signup > 14:  # Not a new user after 2 weeks
                    continue

            # Check required step
            if tip.required_step and tip.required_step not in onboarding.completed_steps:
                continue

            # Check minimum usage days
            if tip.min_usage_days > 0:
                days_active = (timezone.now() - onboarding.started_at).days
                if days_active < tip.min_usage_days:
                    continue

            result.append(tip)

        return result

    def _log_event(self, user, event_type: str, data: Dict = None):
        """Log an onboarding event."""
        OnboardingEvent.objects.create(
            user=user,
            event_type=event_type,
            event_data=data or {}
        )

    # -------------------------------------------------------------------------
    # Auto-completion Hooks
    # -------------------------------------------------------------------------

    def on_email_verified(self, user):
        """Called when user verifies email."""
        self.complete_step(user, 'email_verified')

    def on_profile_updated(self, user):
        """Called when user updates profile."""
        if user.first_name:
            self.complete_step(user, 'profile_completed')

    def on_note_created(self, user):
        """Called when user creates first note."""
        self.complete_step(user, 'first_note_created')

    def on_ai_generation(self, user):
        """Called when user uses AI generation."""
        self.complete_step(user, 'first_ai_generation')

    def on_folder_created(self, user):
        """Called when user creates a folder."""
        self.complete_step(user, 'create_folder')

    def on_template_used(self, user):
        """Called when user uses a template."""
        self.complete_step(user, 'explore_templates')

    def on_plans_viewed(self, user):
        """Called when user views subscription plans."""
        self.complete_step(user, 'subscription_viewed')

    # -------------------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------------------

    def get_onboarding_analytics(self, days: int = 30) -> Dict:
        """Get onboarding analytics."""
        since = timezone.now() - timedelta(days=days)

        total_started = UserOnboarding.objects.filter(
            started_at__gte=since
        ).count()

        total_completed = UserOnboarding.objects.filter(
            started_at__gte=since,
            is_complete=True
        ).count()

        # Step completion rates
        step_completion = {}
        for step in ONBOARDING_STEPS.keys():
            count = UserOnboarding.objects.filter(
                started_at__gte=since,
                completed_steps__contains=[step]
            ).count()
            step_completion[step] = {
                'count': count,
                'rate': round((count / max(total_started, 1)) * 100, 2)
            }

        return {
            'total_started': total_started,
            'total_completed': total_completed,
            'completion_rate': round(
                (total_completed / max(total_started, 1)) * 100, 2
            ),
            'step_completion': step_completion,
        }


# =============================================================================
# Singleton Instance
# =============================================================================

onboarding_service = OnboardingService()
