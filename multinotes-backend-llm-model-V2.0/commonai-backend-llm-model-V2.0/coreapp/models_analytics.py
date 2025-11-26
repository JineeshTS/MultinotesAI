"""
Analytics and metrics models for MultinotesAI.

This module provides:
- UserAnalytics model for tracking user behavior
- PromptTemplate model for reusable prompts
- SystemMetrics model for performance tracking
- APIUsageLog for API usage tracking
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import json


# =============================================================================
# User Analytics Model
# =============================================================================

class UserAnalytics(models.Model):
    """
    Track daily user analytics and engagement metrics.

    Stores aggregated daily statistics per user for:
    - Content creation
    - AI generation usage
    - Feature engagement
    - Session data
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    date = models.DateField(default=timezone.now)

    # Content metrics
    notes_created = models.PositiveIntegerField(default=0)
    notes_edited = models.PositiveIntegerField(default=0)
    notes_deleted = models.PositiveIntegerField(default=0)
    folders_created = models.PositiveIntegerField(default=0)

    # AI usage metrics
    ai_text_generations = models.PositiveIntegerField(default=0)
    ai_image_generations = models.PositiveIntegerField(default=0)
    ai_tokens_used = models.PositiveIntegerField(default=0)
    ai_requests_streamed = models.PositiveIntegerField(default=0)

    # Session metrics
    sessions_count = models.PositiveIntegerField(default=0)
    total_session_duration = models.PositiveIntegerField(default=0)  # seconds
    pages_viewed = models.PositiveIntegerField(default=0)

    # Feature usage (JSON for flexibility)
    feature_usage = models.JSONField(default=dict, blank=True)

    # Sharing metrics
    content_shared = models.PositiveIntegerField(default=0)
    shared_views_received = models.PositiveIntegerField(default=0)

    # API metrics
    api_calls = models.PositiveIntegerField(default=0)
    api_errors = models.PositiveIntegerField(default=0)

    # Storage metrics
    storage_used_bytes = models.BigIntegerField(default=0)
    files_uploaded = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_analytics'
        verbose_name = 'User Analytics'
        verbose_name_plural = 'User Analytics'
        unique_together = ['user', 'date']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['user', '-ai_tokens_used']),
        ]

    def __str__(self):
        return f"Analytics for {self.user} on {self.date}"

    @classmethod
    def get_or_create_today(cls, user):
        """Get or create today's analytics record for user."""
        today = timezone.now().date()
        obj, created = cls.objects.get_or_create(
            user=user,
            date=today,
            defaults={}
        )
        return obj

    def increment(self, field_name, amount=1):
        """Safely increment a field value."""
        current = getattr(self, field_name, 0) or 0
        setattr(self, field_name, current + amount)
        self.save(update_fields=[field_name, 'updated_at'])

    def track_feature(self, feature_name):
        """Track usage of a specific feature."""
        if self.feature_usage is None:
            self.feature_usage = {}
        self.feature_usage[feature_name] = self.feature_usage.get(feature_name, 0) + 1
        self.save(update_fields=['feature_usage', 'updated_at'])


# =============================================================================
# Prompt Template Model
# =============================================================================

class PromptTemplate(models.Model):
    """
    Reusable prompt templates for AI generation.

    Supports:
    - System prompts
    - User prompts with variables
    - Template categories
    - Version history
    """

    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('writing', 'Writing'),
        ('coding', 'Coding'),
        ('analysis', 'Analysis'),
        ('creative', 'Creative'),
        ('business', 'Business'),
        ('education', 'Education'),
        ('custom', 'Custom'),
    ]

    TYPE_CHOICES = [
        ('system', 'System Prompt'),
        ('user', 'User Prompt'),
        ('combined', 'Combined'),
    ]

    # Basic info
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    # Template content
    template_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='user'
    )
    system_prompt = models.TextField(blank=True)
    user_prompt = models.TextField()

    # Classification
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='general'
    )
    tags = models.JSONField(default=list, blank=True)

    # Variables (JSON list of variable names)
    variables = models.JSONField(default=list, blank=True)
    variable_defaults = models.JSONField(default=dict, blank=True)

    # Ownership
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prompt_templates',
        null=True,
        blank=True
    )
    is_public = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)

    # Usage stats
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)

    # LLM configuration
    recommended_model = models.CharField(max_length=100, blank=True)
    temperature = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)]
    )
    max_tokens = models.PositiveIntegerField(default=1000)

    # Versioning
    version = models.PositiveIntegerField(default=1)
    parent_template = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions'
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'prompt_templates'
        verbose_name = 'Prompt Template'
        verbose_name_plural = 'Prompt Templates'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['is_public', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} (v{self.version})"

    def render(self, context=None):
        """
        Render the template with provided context.

        Args:
            context: Dict of variable values

        Returns:
            Dict with rendered system_prompt and user_prompt
        """
        context = context or {}

        # Merge with defaults
        full_context = {**self.variable_defaults, **context}

        # Simple string replacement for variables
        rendered_system = self.system_prompt
        rendered_user = self.user_prompt

        for var_name in self.variables:
            placeholder = f"{{{{{var_name}}}}}"  # {{var_name}}
            value = str(full_context.get(var_name, ''))
            rendered_system = rendered_system.replace(placeholder, value)
            rendered_user = rendered_user.replace(placeholder, value)

        return {
            'system_prompt': rendered_system,
            'user_prompt': rendered_user,
        }

    def record_usage(self):
        """Record template usage."""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])

    def create_version(self, **updates):
        """Create a new version of this template."""
        new_template = PromptTemplate.objects.create(
            name=self.name,
            slug=f"{self.slug}-v{self.version + 1}",
            description=self.description,
            template_type=self.template_type,
            system_prompt=updates.get('system_prompt', self.system_prompt),
            user_prompt=updates.get('user_prompt', self.user_prompt),
            category=self.category,
            tags=self.tags,
            variables=self.variables,
            variable_defaults=self.variable_defaults,
            user=self.user,
            is_public=self.is_public,
            recommended_model=self.recommended_model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            version=self.version + 1,
            parent_template=self,
        )
        return new_template


# =============================================================================
# System Metrics Model
# =============================================================================

class SystemMetrics(models.Model):
    """
    Track system-wide performance metrics.

    Used for:
    - API response times
    - Error rates
    - Resource utilization
    - Provider health
    """

    METRIC_TYPES = [
        ('response_time', 'Response Time'),
        ('error_rate', 'Error Rate'),
        ('throughput', 'Throughput'),
        ('availability', 'Availability'),
        ('resource', 'Resource Usage'),
        ('custom', 'Custom'),
    ]

    # Metric identification
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    metric_name = models.CharField(max_length=255)
    component = models.CharField(max_length=100, blank=True)  # e.g., 'openai', 'database'

    # Values
    value = models.FloatField()
    unit = models.CharField(max_length=50, blank=True)  # e.g., 'ms', 'percent', 'count'

    # Context
    tags = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamp
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'system_metrics'
        verbose_name = 'System Metric'
        verbose_name_plural = 'System Metrics'
        indexes = [
            models.Index(fields=['metric_type', 'recorded_at']),
            models.Index(fields=['metric_name', 'recorded_at']),
            models.Index(fields=['component', 'recorded_at']),
            models.Index(fields=['-recorded_at']),
        ]

    def __str__(self):
        return f"{self.metric_name}: {self.value}{self.unit} at {self.recorded_at}"

    @classmethod
    def record(cls, metric_type, metric_name, value, **kwargs):
        """
        Record a new metric.

        Args:
            metric_type: Type of metric
            metric_name: Name of the metric
            value: Metric value
            **kwargs: Additional fields (component, unit, tags, metadata)
        """
        return cls.objects.create(
            metric_type=metric_type,
            metric_name=metric_name,
            value=value,
            component=kwargs.get('component', ''),
            unit=kwargs.get('unit', ''),
            tags=kwargs.get('tags', {}),
            metadata=kwargs.get('metadata', {}),
        )


# =============================================================================
# API Usage Log Model
# =============================================================================

class APIUsageLog(models.Model):
    """
    Detailed log of API usage for billing and analytics.

    Tracks:
    - Individual API calls
    - Token consumption
    - Costs
    - Response times
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_usage_logs'
    )

    # Request info
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    request_id = models.CharField(max_length=100, blank=True)

    # LLM specific
    llm_provider = models.CharField(max_length=50, blank=True)
    llm_model = models.CharField(max_length=100, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)

    # Cost tracking
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    # Performance
    response_time_ms = models.PositiveIntegerField(default=0)
    status_code = models.PositiveIntegerField(default=200)
    is_error = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_usage_logs'
        verbose_name = 'API Usage Log'
        verbose_name_plural = 'API Usage Logs'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['endpoint', '-created_at']),
            models.Index(fields=['llm_provider', '-created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_error', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user} - {self.endpoint} at {self.created_at}"

    @classmethod
    def log_request(cls, user, endpoint, method, **kwargs):
        """
        Log an API request.

        Args:
            user: User making the request
            endpoint: API endpoint called
            method: HTTP method
            **kwargs: Additional fields
        """
        return cls.objects.create(
            user=user,
            endpoint=endpoint,
            method=method,
            **kwargs
        )


# =============================================================================
# Daily Aggregation Model
# =============================================================================

class DailyAggregation(models.Model):
    """
    Aggregated daily statistics for the entire platform.

    Used for:
    - Admin dashboards
    - Trend analysis
    - Capacity planning
    """

    date = models.DateField(unique=True)

    # User metrics
    total_users = models.PositiveIntegerField(default=0)
    new_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    churned_users = models.PositiveIntegerField(default=0)

    # Content metrics
    total_notes = models.PositiveIntegerField(default=0)
    notes_created = models.PositiveIntegerField(default=0)
    notes_edited = models.PositiveIntegerField(default=0)

    # AI metrics
    ai_generations = models.PositiveIntegerField(default=0)
    total_tokens = models.BigIntegerField(default=0)
    ai_cost_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Revenue metrics
    new_subscriptions = models.PositiveIntegerField(default=0)
    canceled_subscriptions = models.PositiveIntegerField(default=0)
    revenue_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Performance metrics
    avg_response_time_ms = models.FloatField(default=0)
    error_rate = models.FloatField(default=0)
    uptime_percent = models.FloatField(default=100)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_aggregations'
        verbose_name = 'Daily Aggregation'
        verbose_name_plural = 'Daily Aggregations'
        indexes = [
            models.Index(fields=['-date']),
        ]

    def __str__(self):
        return f"Aggregation for {self.date}"

    @classmethod
    def get_or_create_today(cls):
        """Get or create today's aggregation record."""
        today = timezone.now().date()
        obj, created = cls.objects.get_or_create(date=today)
        return obj
