"""
Additional analytics and feature models for MultinotesAI.

These models support:
- User analytics tracking
- Prompt templates library
- Prompt suggestions
- Product metrics
- User onboarding
"""

from django.db import models
from django.utils import timezone
from authentication.models import CustomUser


class UserAnalytics(models.Model):
    """
    Tracks user engagement and usage analytics.
    Used for retention analysis and product insights.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='analytics'
    )

    # Engagement metrics
    total_sessions = models.IntegerField(default=0)
    total_prompts = models.IntegerField(default=0)
    total_generations = models.IntegerField(default=0)
    total_tokens_used = models.BigIntegerField(default=0)

    # Time metrics
    total_time_spent = models.IntegerField(default=0)  # seconds
    average_session_duration = models.IntegerField(default=0)  # seconds

    # Activity tracking
    last_active = models.DateTimeField(null=True, blank=True)
    last_generation = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)

    # Engagement scoring
    engagement_score = models.FloatField(default=0.0)
    retention_risk = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
        ],
        default='low'
    )

    # Feature usage
    features_used = models.JSONField(default=dict)
    favorite_models = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Analytics'
        verbose_name_plural = 'User Analytics'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['last_active']),
            models.Index(fields=['engagement_score']),
            models.Index(fields=['retention_risk']),
        ]

    def __str__(self):
        return f"Analytics for {self.user.email}"


class PromptTemplate(models.Model):
    """Pre-built prompt templates for common use cases."""
    CATEGORY_CHOICES = [
        ('writing', 'Writing'),
        ('coding', 'Coding'),
        ('analysis', 'Analysis'),
        ('creative', 'Creative'),
        ('business', 'Business'),
        ('education', 'Education'),
        ('marketing', 'Marketing'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    template_text = models.TextField()

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    tags = models.JSONField(default=list)
    variables = models.JSONField(default=list)

    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prompt_templates'
    )
    is_system = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)

    usage_count = models.IntegerField(default=0)
    rating_sum = models.IntegerField(default=0)
    rating_count = models.IntegerField(default=0)

    recommended_model = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-usage_count', '-created_at']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_system', 'is_public']),
            models.Index(fields=['usage_count']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return self.title


class PromptSuggestion(models.Model):
    """AI-generated or curated prompt suggestions."""
    text = models.TextField()
    category = models.CharField(max_length=50, blank=True)

    trigger_keywords = models.JSONField(default=list)
    context_type = models.CharField(
        max_length=50,
        choices=[
            ('general', 'General'),
            ('continuation', 'Continuation'),
            ('refinement', 'Refinement'),
            ('alternative', 'Alternative'),
        ],
        default='general'
    )

    for_new_users = models.BooleanField(default=False)
    for_category = models.CharField(max_length=50, blank=True)

    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_active', 'priority']),
        ]

    def __str__(self):
        return self.text[:50]


class ProductMetrics(models.Model):
    """Daily aggregated product metrics for analytics dashboard."""
    date = models.DateField(unique=True)

    total_users = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    returning_users = models.IntegerField(default=0)

    total_sessions = models.IntegerField(default=0)
    total_prompts = models.IntegerField(default=0)
    total_generations = models.IntegerField(default=0)
    total_tokens_used = models.BigIntegerField(default=0)

    new_subscriptions = models.IntegerField(default=0)
    churned_subscriptions = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mrr = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    feature_usage = models.JSONField(default=dict)
    model_usage = models.JSONField(default=dict)

    error_count = models.IntegerField(default=0)
    api_latency_avg = models.FloatField(default=0)

    d1_retention = models.FloatField(default=0)
    d7_retention = models.FloatField(default=0)
    d30_retention = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Product Metrics'
        verbose_name_plural = 'Product Metrics'
        indexes = [
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"Metrics for {self.date}"


class UserOnboarding(models.Model):
    """Tracks user onboarding progress and feature discovery."""
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='onboarding'
    )

    completed_steps = models.JSONField(default=list)
    current_step = models.CharField(max_length=50, default='welcome')

    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    tours_completed = models.JSONField(default=list)
    tips_dismissed = models.JSONField(default=list)

    selected_use_cases = models.JSONField(default=list)
    experience_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        default='beginner'
    )

    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Onboarding'
        verbose_name_plural = 'User Onboarding'

    def __str__(self):
        return f"Onboarding for {self.user.email}"


class UserFavorite(models.Model):
    """Tracks user favorites for templates, models, and prompts."""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='favorites'
    )

    content_type = models.CharField(
        max_length=50,
        choices=[
            ('template', 'Template'),
            ('model', 'Model'),
            ('prompt', 'Prompt'),
        ]
    )
    content_id = models.IntegerField()
    note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'content_type', 'content_id']
        indexes = [
            models.Index(fields=['user', 'content_type']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.content_type}:{self.content_id}"


class APIKey(models.Model):
    """User-generated API keys for programmatic access."""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )

    name = models.CharField(max_length=100)
    key_prefix = models.CharField(max_length=8)
    key_hash = models.CharField(max_length=128)

    scopes = models.JSONField(default=list)
    rate_limit = models.IntegerField(default=100)

    last_used = models.DateTimeField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['key_prefix']),
        ]

    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"


class Webhook(models.Model):
    """User-configured webhooks for event notifications."""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='webhooks'
    )

    name = models.CharField(max_length=100)
    url = models.URLField()
    secret = models.CharField(max_length=255)

    events = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    last_triggered = models.DateTimeField(null=True, blank=True)
    failure_count = models.IntegerField(default=0)
    last_failure = models.DateTimeField(null=True, blank=True)
    last_failure_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.url[:30]}"
