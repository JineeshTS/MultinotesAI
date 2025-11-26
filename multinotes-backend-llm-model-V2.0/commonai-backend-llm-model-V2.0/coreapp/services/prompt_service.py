"""
Prompt Suggestion Service for MultinotesAI.

This module provides:
- Smart prompt suggestions based on context
- Prompt templates management
- Prompt history and favorites
- Category-based prompt organization
"""

import logging
import random
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

from django.db import models
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt Categories
# =============================================================================

class PromptCategory(Enum):
    """Prompt category constants."""

    # Writing
    WRITING_BLOG = 'writing.blog'
    WRITING_ARTICLE = 'writing.article'
    WRITING_STORY = 'writing.story'
    WRITING_ESSAY = 'writing.essay'
    WRITING_EMAIL = 'writing.email'
    WRITING_SOCIAL = 'writing.social'

    # Business
    BUSINESS_PROPOSAL = 'business.proposal'
    BUSINESS_PLAN = 'business.plan'
    BUSINESS_REPORT = 'business.report'
    BUSINESS_PRESENTATION = 'business.presentation'

    # Academic
    ACADEMIC_RESEARCH = 'academic.research'
    ACADEMIC_SUMMARY = 'academic.summary'
    ACADEMIC_ANALYSIS = 'academic.analysis'
    ACADEMIC_REVIEW = 'academic.review'

    # Creative
    CREATIVE_BRAINSTORM = 'creative.brainstorm'
    CREATIVE_POETRY = 'creative.poetry'
    CREATIVE_DIALOGUE = 'creative.dialogue'
    CREATIVE_SCRIPT = 'creative.script'

    # Technical
    TECHNICAL_DOCS = 'technical.docs'
    TECHNICAL_CODE = 'technical.code'
    TECHNICAL_DEBUG = 'technical.debug'
    TECHNICAL_EXPLAIN = 'technical.explain'

    # Productivity
    PRODUCTIVITY_TODO = 'productivity.todo'
    PRODUCTIVITY_MEETING = 'productivity.meeting'
    PRODUCTIVITY_NOTES = 'productivity.notes'
    PRODUCTIVITY_PLAN = 'productivity.plan'

    # Other
    OTHER_TRANSLATE = 'other.translate'
    OTHER_REWRITE = 'other.rewrite'
    OTHER_EXPAND = 'other.expand'
    OTHER_SUMMARIZE = 'other.summarize'


# =============================================================================
# Prompt Templates
# =============================================================================

PROMPT_TEMPLATES = {
    # Writing templates
    PromptCategory.WRITING_BLOG: [
        "Write a blog post about {topic} targeting {audience}",
        "Create an engaging blog article on {topic} with a {tone} tone",
        "Draft a {length} blog post explaining {topic} for beginners",
        "Write a listicle: Top {number} tips for {topic}",
    ],
    PromptCategory.WRITING_EMAIL: [
        "Write a professional email to {recipient} about {subject}",
        "Draft a follow-up email regarding {topic}",
        "Create an email template for {purpose}",
        "Write a polite request email for {request}",
    ],
    PromptCategory.WRITING_SOCIAL: [
        "Create a {platform} post about {topic}",
        "Write an engaging caption for a {type} post about {topic}",
        "Draft a social media announcement for {event}",
        "Create {number} tweet variations about {topic}",
    ],

    # Business templates
    PromptCategory.BUSINESS_PROPOSAL: [
        "Write a project proposal for {project}",
        "Create a business proposal outline for {service}",
        "Draft a partnership proposal for {company}",
    ],
    PromptCategory.BUSINESS_REPORT: [
        "Create an executive summary for {topic}",
        "Write a status report for {project}",
        "Draft a quarterly review for {department}",
    ],

    # Academic templates
    PromptCategory.ACADEMIC_SUMMARY: [
        "Summarize the key points of {topic}",
        "Create a concise summary of {content}",
        "Write an abstract for a paper about {topic}",
    ],
    PromptCategory.ACADEMIC_ANALYSIS: [
        "Analyze the main arguments in {topic}",
        "Provide a critical analysis of {subject}",
        "Compare and contrast {item1} and {item2}",
    ],

    # Creative templates
    PromptCategory.CREATIVE_BRAINSTORM: [
        "Generate {number} ideas for {topic}",
        "Brainstorm creative solutions for {problem}",
        "List unique approaches to {challenge}",
    ],

    # Technical templates
    PromptCategory.TECHNICAL_DOCS: [
        "Write documentation for {feature}",
        "Create a README for {project}",
        "Document the API endpoint for {endpoint}",
    ],
    PromptCategory.TECHNICAL_EXPLAIN: [
        "Explain {concept} in simple terms",
        "Break down how {technology} works",
        "Describe the process of {process}",
    ],

    # Productivity templates
    PromptCategory.PRODUCTIVITY_MEETING: [
        "Create an agenda for a meeting about {topic}",
        "Write meeting notes summary for {meeting}",
        "Draft action items from {discussion}",
    ],

    # Other templates
    PromptCategory.OTHER_SUMMARIZE: [
        "Summarize this text in {length} words",
        "Create bullet points from this content",
        "Extract key takeaways from this",
    ],
    PromptCategory.OTHER_REWRITE: [
        "Rewrite this in a {tone} tone",
        "Make this more {adjective}",
        "Simplify this for a {audience} audience",
    ],
}


# =============================================================================
# User Prompt History Model
# =============================================================================

class UserPromptHistory(models.Model):
    """Track user's prompt usage for personalized suggestions."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prompt_history'
    )
    prompt_text = models.TextField()
    category = models.CharField(max_length=50, blank=True)
    is_favorite = models.BooleanField(default=False)
    use_count = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_prompt_history'
        indexes = [
            models.Index(fields=['user', '-last_used_at']),
            models.Index(fields=['user', 'is_favorite']),
            models.Index(fields=['user', 'category']),
        ]

    def __str__(self):
        return f"{self.user.email}: {self.prompt_text[:50]}"


class PromptTemplate(models.Model):
    """Custom prompt templates (system and user-created)."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    template = models.TextField()
    category = models.CharField(max_length=50)
    variables = models.JSONField(default=list)  # List of variable names

    # Ownership
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='custom_templates'
    )
    is_system = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)

    # Stats
    use_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_delete = models.BooleanField(default=False)

    class Meta:
        db_table = 'prompt_templates'
        indexes = [
            models.Index(fields=['category', 'is_system']),
            models.Index(fields=['user', '-use_count']),
        ]

    def __str__(self):
        return self.name


# =============================================================================
# Prompt Suggestion Service
# =============================================================================

class PromptSuggestionService:
    """
    Smart prompt suggestion service.

    Usage:
        service = PromptSuggestionService()
        suggestions = service.get_suggestions(
            user=user,
            context={'topic': 'AI', 'type': 'blog'}
        )
    """

    def __init__(self):
        self.templates = PROMPT_TEMPLATES

    # -------------------------------------------------------------------------
    # Suggestion Generation
    # -------------------------------------------------------------------------

    def get_suggestions(
        self,
        user=None,
        category: str = None,
        context: Dict = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get prompt suggestions.

        Args:
            user: User (for personalized suggestions)
            category: Filter by category
            context: Context for filling templates
            limit: Maximum suggestions

        Returns:
            List of prompt suggestions
        """
        suggestions = []

        # Get template suggestions
        template_suggestions = self._get_template_suggestions(
            category=category,
            context=context,
            limit=limit
        )
        suggestions.extend(template_suggestions)

        # Get personalized suggestions for user
        if user:
            personalized = self._get_personalized_suggestions(
                user=user,
                category=category,
                limit=limit // 2
            )
            suggestions.extend(personalized)

        # Deduplicate and limit
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            text = s.get('prompt', '').lower()
            if text not in seen:
                seen.add(text)
                unique_suggestions.append(s)

        return unique_suggestions[:limit]

    def _get_template_suggestions(
        self,
        category: str = None,
        context: Dict = None,
        limit: int = 5
    ) -> List[Dict]:
        """Get suggestions from templates."""
        suggestions = []
        context = context or {}

        # Get relevant categories
        if category:
            categories = [
                c for c in PromptCategory
                if c.value.startswith(category) or c.value == category
            ]
        else:
            categories = list(PromptCategory)

        # Sample templates
        for cat in categories:
            templates = self.templates.get(cat, [])
            for template in templates:
                try:
                    # Fill in context variables
                    prompt = self._fill_template(template, context)
                    suggestions.append({
                        'prompt': prompt,
                        'template': template,
                        'category': cat.value,
                        'type': 'template',
                    })
                except Exception:
                    continue

        # Shuffle and limit
        random.shuffle(suggestions)
        return suggestions[:limit]

    def _get_personalized_suggestions(
        self,
        user,
        category: str = None,
        limit: int = 3
    ) -> List[Dict]:
        """Get personalized suggestions based on user history."""
        queryset = UserPromptHistory.objects.filter(user=user)

        if category:
            queryset = queryset.filter(category__startswith=category)

        # Get recent and frequently used prompts
        recent = queryset.order_by('-last_used_at')[:limit]
        frequent = queryset.order_by('-use_count')[:limit]

        suggestions = []
        seen = set()

        for prompt in list(recent) + list(frequent):
            if prompt.prompt_text not in seen:
                seen.add(prompt.prompt_text)
                suggestions.append({
                    'prompt': prompt.prompt_text,
                    'category': prompt.category,
                    'type': 'history',
                    'use_count': prompt.use_count,
                    'is_favorite': prompt.is_favorite,
                })

        return suggestions[:limit]

    def _fill_template(self, template: str, context: Dict) -> str:
        """Fill template variables with context values."""
        import re

        # Find all {variable} patterns
        variables = re.findall(r'\{(\w+)\}', template)

        result = template
        for var in variables:
            if var in context:
                result = result.replace(f'{{{var}}}', str(context[var]))
            else:
                # Leave unfilled variables as placeholders
                result = result.replace(f'{{{var}}}', f'[{var}]')

        return result

    # -------------------------------------------------------------------------
    # Quick Suggestions
    # -------------------------------------------------------------------------

    def get_quick_suggestions(
        self,
        partial_text: str,
        limit: int = 5
    ) -> List[str]:
        """
        Get quick suggestions for autocomplete.

        Args:
            partial_text: Partial prompt text
            limit: Maximum suggestions

        Returns:
            List of completion suggestions
        """
        if len(partial_text) < 3:
            return []

        completions = []
        partial_lower = partial_text.lower()

        # Search through all templates
        for category, templates in self.templates.items():
            for template in templates:
                if partial_lower in template.lower():
                    completions.append(template)

        return completions[:limit]

    def get_starter_prompts(self, category: str = None) -> List[Dict]:
        """Get starter prompts for new users."""
        starters = [
            {
                'prompt': 'Write a blog post about...',
                'category': 'writing.blog',
                'icon': 'pencil',
            },
            {
                'prompt': 'Summarize this text...',
                'category': 'other.summarize',
                'icon': 'compress',
            },
            {
                'prompt': 'Explain this concept in simple terms...',
                'category': 'technical.explain',
                'icon': 'lightbulb',
            },
            {
                'prompt': 'Generate ideas for...',
                'category': 'creative.brainstorm',
                'icon': 'brain',
            },
            {
                'prompt': 'Write a professional email about...',
                'category': 'writing.email',
                'icon': 'envelope',
            },
            {
                'prompt': 'Create a todo list for...',
                'category': 'productivity.todo',
                'icon': 'list',
            },
        ]

        if category:
            return [s for s in starters if s['category'].startswith(category)]
        return starters

    # -------------------------------------------------------------------------
    # Prompt History Management
    # -------------------------------------------------------------------------

    def record_prompt_usage(
        self,
        user,
        prompt_text: str,
        category: str = None
    ) -> UserPromptHistory:
        """Record a prompt usage for history."""
        # Try to update existing
        existing = UserPromptHistory.objects.filter(
            user=user,
            prompt_text=prompt_text
        ).first()

        if existing:
            existing.use_count += 1
            existing.last_used_at = timezone.now()
            if category:
                existing.category = category
            existing.save()
            return existing

        # Create new
        return UserPromptHistory.objects.create(
            user=user,
            prompt_text=prompt_text,
            category=category or self._detect_category(prompt_text)
        )

    def _detect_category(self, prompt_text: str) -> str:
        """Auto-detect prompt category from text."""
        text_lower = prompt_text.lower()

        # Simple keyword matching
        keywords = {
            'writing.blog': ['blog', 'article', 'post'],
            'writing.email': ['email', 'mail', 'message'],
            'writing.social': ['tweet', 'instagram', 'social', 'caption'],
            'business.proposal': ['proposal', 'pitch'],
            'business.report': ['report', 'summary', 'review'],
            'academic.research': ['research', 'paper', 'study'],
            'creative.brainstorm': ['ideas', 'brainstorm', 'generate'],
            'technical.docs': ['document', 'readme', 'api'],
            'technical.code': ['code', 'function', 'script'],
            'productivity.meeting': ['meeting', 'agenda', 'minutes'],
            'other.summarize': ['summarize', 'summary', 'brief'],
            'other.rewrite': ['rewrite', 'rephrase', 'improve'],
        }

        for category, words in keywords.items():
            if any(word in text_lower for word in words):
                return category

        return 'other'

    def get_user_history(
        self,
        user,
        limit: int = 20,
        favorites_only: bool = False
    ) -> List[UserPromptHistory]:
        """Get user's prompt history."""
        queryset = UserPromptHistory.objects.filter(user=user)

        if favorites_only:
            queryset = queryset.filter(is_favorite=True)

        return list(queryset.order_by('-last_used_at')[:limit])

    def toggle_favorite(self, user, prompt_id: int) -> bool:
        """Toggle favorite status for a prompt."""
        try:
            prompt = UserPromptHistory.objects.get(id=prompt_id, user=user)
            prompt.is_favorite = not prompt.is_favorite
            prompt.save()
            return prompt.is_favorite
        except UserPromptHistory.DoesNotExist:
            return False

    def delete_from_history(self, user, prompt_id: int) -> bool:
        """Delete prompt from history."""
        try:
            UserPromptHistory.objects.filter(id=prompt_id, user=user).delete()
            return True
        except Exception:
            return False

    def clear_history(self, user) -> int:
        """Clear all prompt history for user."""
        deleted, _ = UserPromptHistory.objects.filter(user=user).delete()
        return deleted

    # -------------------------------------------------------------------------
    # Template Management
    # -------------------------------------------------------------------------

    def create_template(
        self,
        user,
        name: str,
        template: str,
        category: str,
        description: str = '',
        is_public: bool = False
    ) -> PromptTemplate:
        """Create a custom prompt template."""
        import re

        # Extract variables from template
        variables = re.findall(r'\{(\w+)\}', template)

        return PromptTemplate.objects.create(
            user=user,
            name=name,
            template=template,
            category=category,
            description=description,
            variables=variables,
            is_public=is_public,
        )

    def get_user_templates(self, user, limit: int = 50) -> List[PromptTemplate]:
        """Get user's custom templates."""
        return list(PromptTemplate.objects.filter(
            user=user,
            is_delete=False
        ).order_by('-use_count')[:limit])

    def get_public_templates(
        self,
        category: str = None,
        limit: int = 20
    ) -> List[PromptTemplate]:
        """Get public templates."""
        queryset = PromptTemplate.objects.filter(
            is_public=True,
            is_delete=False
        )

        if category:
            queryset = queryset.filter(category__startswith=category)

        return list(queryset.order_by('-use_count')[:limit])

    def get_categories(self) -> List[Dict]:
        """Get all prompt categories."""
        categories = {}

        for cat in PromptCategory:
            parts = cat.value.split('.')
            main = parts[0]
            sub = parts[1] if len(parts) > 1 else None

            if main not in categories:
                categories[main] = {
                    'name': main.title(),
                    'subcategories': []
                }

            if sub:
                categories[main]['subcategories'].append({
                    'value': cat.value,
                    'name': sub.replace('_', ' ').title()
                })

        return list(categories.values())


# =============================================================================
# Singleton Instance
# =============================================================================

prompt_service = PromptSuggestionService()
