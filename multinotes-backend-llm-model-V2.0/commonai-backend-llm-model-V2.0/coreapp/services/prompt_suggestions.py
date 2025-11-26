"""
Prompt Suggestion Generator for MultinotesAI.

This module provides:
- Contextual prompt suggestions based on user activity
- Template-based prompt generation
- Follow-up prompt recommendations
- Popular prompts discovery

WBS Item: 4.4.4 - Create prompt suggestion generator
"""

import random
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt Templates
# =============================================================================

PROMPT_TEMPLATES = {
    'writing': [
        "Write a {tone} {content_type} about {topic}",
        "Help me improve this text: {text}",
        "Summarize the following in {length} words: {text}",
        "Rewrite this in a more {style} tone: {text}",
        "Create an outline for {topic}",
        "Write a compelling introduction for {topic}",
        "Generate {count} headlines for {topic}",
    ],
    'coding': [
        "Write a {language} function that {task}",
        "Debug this code: {code}",
        "Explain this code: {code}",
        "Optimize this code for {metric}: {code}",
        "Convert this code from {source_lang} to {target_lang}",
        "Write unit tests for: {code}",
        "Add comments to explain: {code}",
        "Refactor this code to be more {quality}: {code}",
    ],
    'analysis': [
        "Analyze the pros and cons of {topic}",
        "Compare {item1} and {item2}",
        "What are the key trends in {industry}?",
        "Explain {concept} in simple terms",
        "What are the implications of {topic}?",
        "Provide a SWOT analysis for {subject}",
    ],
    'creative': [
        "Write a short story about {topic}",
        "Create a poem about {subject}",
        "Generate creative names for {thing}",
        "Write dialogue between {character1} and {character2}",
        "Describe {scene} in vivid detail",
        "Create a metaphor explaining {concept}",
    ],
    'business': [
        "Write a professional email about {topic}",
        "Create a business proposal for {project}",
        "Draft a meeting agenda for {purpose}",
        "Write a project status update for {project}",
        "Create talking points for {presentation}",
        "Summarize key metrics from {report}",
    ],
    'learning': [
        "Explain {topic} like I'm a beginner",
        "What are the fundamentals of {subject}?",
        "Create a study guide for {topic}",
        "Quiz me on {subject}",
        "What are common misconceptions about {topic}?",
        "Recommend resources for learning {skill}",
    ],
}

FOLLOW_UP_TEMPLATES = {
    'expand': [
        "Can you elaborate on {point}?",
        "Tell me more about {topic}",
        "What are some examples of {concept}?",
        "Can you provide more details on {aspect}?",
    ],
    'clarify': [
        "What do you mean by {term}?",
        "Can you explain {concept} differently?",
        "I don't understand {part}. Can you clarify?",
        "Can you simplify this explanation?",
    ],
    'apply': [
        "How can I apply this to {situation}?",
        "What would be a practical example?",
        "How does this work in real-world scenarios?",
        "Can you show me how to implement this?",
    ],
    'compare': [
        "How does this compare to {alternative}?",
        "What are the differences between this and {other}?",
        "Which approach is better for {use_case}?",
    ],
    'next_steps': [
        "What should I do next?",
        "What are the next steps?",
        "How do I continue from here?",
        "What else should I consider?",
    ],
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PromptSuggestion:
    """A prompt suggestion."""
    text: str
    category: str
    relevance_score: float
    source: str  # 'template', 'history', 'popular', 'followup'
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'category': self.category,
            'relevance_score': round(self.relevance_score, 3),
            'source': self.source,
            'metadata': self.metadata or {},
        }


# =============================================================================
# Prompt Suggestion Generator
# =============================================================================

class PromptSuggestionGenerator:
    """
    Generate contextual prompt suggestions.

    Usage:
        generator = PromptSuggestionGenerator()
        suggestions = generator.get_suggestions(user_id=123)
    """

    def __init__(self):
        self.templates = PROMPT_TEMPLATES
        self.follow_up_templates = FOLLOW_UP_TEMPLATES

    def get_suggestions(
        self,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
        context: Optional[str] = None,
        limit: int = 10
    ) -> List[PromptSuggestion]:
        """
        Get prompt suggestions.

        Args:
            user_id: User ID for personalized suggestions
            category: Filter by category
            context: Current context/conversation for follow-ups
            limit: Maximum suggestions to return

        Returns:
            List of PromptSuggestion objects
        """
        suggestions = []

        # Get template-based suggestions
        template_suggestions = self._get_template_suggestions(category, limit // 2)
        suggestions.extend(template_suggestions)

        # Get history-based suggestions if user provided
        if user_id:
            history_suggestions = self._get_history_based_suggestions(
                user_id, category, limit // 3
            )
            suggestions.extend(history_suggestions)

        # Get popular suggestions
        popular_suggestions = self._get_popular_suggestions(category, limit // 3)
        suggestions.extend(popular_suggestions)

        # Get follow-up suggestions if context provided
        if context:
            follow_up_suggestions = self._get_follow_up_suggestions(context, limit // 3)
            suggestions.extend(follow_up_suggestions)

        # Sort by relevance and limit
        suggestions.sort(key=lambda s: s.relevance_score, reverse=True)
        return suggestions[:limit]

    def get_follow_ups(
        self,
        previous_response: str,
        conversation_context: Optional[List[Dict]] = None,
        limit: int = 5
    ) -> List[PromptSuggestion]:
        """
        Get follow-up prompt suggestions.

        Args:
            previous_response: The AI's previous response
            conversation_context: Full conversation history
            limit: Maximum suggestions

        Returns:
            List of follow-up suggestions
        """
        suggestions = []

        # Extract key terms from response for context
        key_terms = self._extract_key_terms(previous_response)

        # Generate follow-ups from templates
        for category, templates in self.follow_up_templates.items():
            template = random.choice(templates)

            # Fill in template with context
            if key_terms:
                filled = self._fill_template_smart(template, key_terms)
            else:
                filled = template.replace('{', '').replace('}', '')

            suggestions.append(PromptSuggestion(
                text=filled,
                category=category,
                relevance_score=0.7 + random.random() * 0.2,
                source='followup',
                metadata={'original_template': template}
            ))

        # Add generic follow-ups
        generic_followups = [
            "Can you explain that in more detail?",
            "What are the potential challenges with this approach?",
            "Are there any alternatives I should consider?",
            "Can you provide a specific example?",
            "How would you recommend getting started?",
        ]

        for followup in random.sample(generic_followups, min(2, len(generic_followups))):
            suggestions.append(PromptSuggestion(
                text=followup,
                category='general',
                relevance_score=0.5,
                source='followup'
            ))

        return suggestions[:limit]

    def get_by_category(
        self,
        category: str,
        limit: int = 10
    ) -> List[PromptSuggestion]:
        """
        Get suggestions for a specific category.

        Args:
            category: Category name
            limit: Maximum suggestions

        Returns:
            List of suggestions
        """
        if category not in self.templates:
            return []

        suggestions = []
        templates = self.templates[category]

        for template in templates:
            # Create a partial suggestion with placeholders indicated
            display_text = self._create_display_text(template)

            suggestions.append(PromptSuggestion(
                text=display_text,
                category=category,
                relevance_score=0.8,
                source='template',
                metadata={'template': template, 'requires_input': True}
            ))

        return suggestions[:limit]

    def get_starter_prompts(self, limit: int = 6) -> List[PromptSuggestion]:
        """
        Get starter prompts for new users.

        Returns a diverse set of easy-to-use prompts.
        """
        starters = [
            PromptSuggestion(
                text="Help me write a professional email",
                category='business',
                relevance_score=0.9,
                source='template'
            ),
            PromptSuggestion(
                text="Explain a complex topic in simple terms",
                category='learning',
                relevance_score=0.9,
                source='template'
            ),
            PromptSuggestion(
                text="Help me debug my code",
                category='coding',
                relevance_score=0.85,
                source='template'
            ),
            PromptSuggestion(
                text="Generate creative ideas for my project",
                category='creative',
                relevance_score=0.85,
                source='template'
            ),
            PromptSuggestion(
                text="Summarize a long document",
                category='writing',
                relevance_score=0.8,
                source='template'
            ),
            PromptSuggestion(
                text="Compare options and help me decide",
                category='analysis',
                relevance_score=0.8,
                source='template'
            ),
            PromptSuggestion(
                text="Create a study plan for learning something new",
                category='learning',
                relevance_score=0.75,
                source='template'
            ),
            PromptSuggestion(
                text="Write a creative story",
                category='creative',
                relevance_score=0.75,
                source='template'
            ),
        ]

        return random.sample(starters, min(limit, len(starters)))

    def _get_template_suggestions(
        self,
        category: Optional[str],
        limit: int
    ) -> List[PromptSuggestion]:
        """Get suggestions from templates."""
        suggestions = []

        categories = [category] if category else list(self.templates.keys())

        for cat in categories:
            if cat not in self.templates:
                continue

            templates = random.sample(
                self.templates[cat],
                min(2, len(self.templates[cat]))
            )

            for template in templates:
                display_text = self._create_display_text(template)
                suggestions.append(PromptSuggestion(
                    text=display_text,
                    category=cat,
                    relevance_score=0.6 + random.random() * 0.2,
                    source='template',
                    metadata={'template': template}
                ))

        return suggestions[:limit]

    def _get_history_based_suggestions(
        self,
        user_id: int,
        category: Optional[str],
        limit: int
    ) -> List[PromptSuggestion]:
        """Get suggestions based on user's prompt history."""
        from coreapp.models import Prompt

        try:
            # Get user's recent prompts
            recent_prompts = Prompt.objects.filter(
                user_id=user_id,
                is_delete=False
            ).order_by('-created_at')[:50]

            if not recent_prompts:
                return []

            # Find patterns in prompt types
            prompt_texts = [p.prompt_text for p in recent_prompts]

            # Get common starting phrases
            starts = Counter()
            for text in prompt_texts:
                words = text.split()[:3]
                if len(words) >= 2:
                    starts[' '.join(words)] += 1

            suggestions = []
            for start, count in starts.most_common(limit):
                if count >= 2:
                    suggestions.append(PromptSuggestion(
                        text=f"{start}...",
                        category='history',
                        relevance_score=0.7 + (count / 10),
                        source='history',
                        metadata={'usage_count': count}
                    ))

            return suggestions

        except Exception as e:
            logger.error(f"Failed to get history suggestions: {e}")
            return []

    def _get_popular_suggestions(
        self,
        category: Optional[str],
        limit: int
    ) -> List[PromptSuggestion]:
        """Get popular prompts across all users."""
        # Popular prompt patterns
        popular = [
            ("Explain {topic} in simple terms", 'learning'),
            ("Write a summary of {text}", 'writing'),
            ("Help me improve this code", 'coding'),
            ("Create a professional email", 'business'),
            ("Compare {option1} vs {option2}", 'analysis'),
            ("Generate ideas for {project}", 'creative'),
        ]

        if category:
            popular = [p for p in popular if p[1] == category]

        suggestions = []
        for text, cat in popular[:limit]:
            display_text = self._create_display_text(text)
            suggestions.append(PromptSuggestion(
                text=display_text,
                category=cat,
                relevance_score=0.75,
                source='popular'
            ))

        return suggestions

    def _get_follow_up_suggestions(
        self,
        context: str,
        limit: int
    ) -> List[PromptSuggestion]:
        """Get follow-up suggestions based on context."""
        key_terms = self._extract_key_terms(context)

        suggestions = []
        for category, templates in self.follow_up_templates.items():
            template = random.choice(templates)
            filled = self._fill_template_smart(template, key_terms)

            suggestions.append(PromptSuggestion(
                text=filled,
                category=category,
                relevance_score=0.65,
                source='followup'
            ))

        return suggestions[:limit]

    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text."""
        # Simple keyword extraction
        words = text.lower().split()

        # Filter stop words and short words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'could', 'should', 'may', 'might', 'must', 'can',
                      'this', 'that', 'these', 'those', 'it', 'its', 'to', 'of',
                      'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'or',
                      'and', 'but', 'if', 'then', 'so', 'than', 'too', 'very'}

        key_terms = [
            word for word in words
            if len(word) > 3 and word not in stop_words and word.isalpha()
        ]

        # Return unique terms
        seen = set()
        unique_terms = []
        for term in key_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)

        return unique_terms[:10]

    def _fill_template_smart(self, template: str, terms: List[str]) -> str:
        """Fill template placeholders with relevant terms."""
        import re

        placeholders = re.findall(r'\{(\w+)\}', template)

        filled = template
        for i, placeholder in enumerate(placeholders):
            if i < len(terms):
                filled = filled.replace(f'{{{placeholder}}}', terms[i], 1)
            else:
                filled = filled.replace(f'{{{placeholder}}}', f'[{placeholder}]', 1)

        return filled

    def _create_display_text(self, template: str) -> str:
        """Create display text from template with placeholder indicators."""
        import re

        # Replace {placeholder} with [placeholder]
        display = re.sub(r'\{(\w+)\}', r'[\1]', template)
        return display


# =============================================================================
# Prompt Discovery Service
# =============================================================================

class PromptDiscoveryService:
    """
    Service for discovering and recommending prompts.
    """

    def __init__(self):
        self.generator = PromptSuggestionGenerator()

    def get_trending_prompts(
        self,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get trending prompts based on recent usage.

        Args:
            days: Number of days to look back
            limit: Maximum results

        Returns:
            List of trending prompt data
        """
        from coreapp.models import Prompt

        try:
            cutoff = timezone.now() - timedelta(days=days)

            # Get most used prompt patterns
            prompts = Prompt.objects.filter(
                created_at__gte=cutoff,
                is_delete=False
            ).values('prompt_text').annotate(
                usage_count=Count('id')
            ).order_by('-usage_count')[:limit * 2]

            trending = []
            seen_patterns = set()

            for p in prompts:
                # Normalize prompt for deduplication
                normalized = self._normalize_prompt(p['prompt_text'])
                if normalized in seen_patterns:
                    continue
                seen_patterns.add(normalized)

                # Truncate for display
                display_text = p['prompt_text'][:100]
                if len(p['prompt_text']) > 100:
                    display_text += '...'

                trending.append({
                    'text': display_text,
                    'usage_count': p['usage_count'],
                    'category': self._guess_category(p['prompt_text']),
                })

            return trending[:limit]

        except Exception as e:
            logger.error(f"Failed to get trending prompts: {e}")
            return []

    def get_recommended_for_user(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[PromptSuggestion]:
        """
        Get personalized prompt recommendations.

        Args:
            user_id: User ID
            limit: Maximum recommendations

        Returns:
            List of recommendations
        """
        return self.generator.get_suggestions(user_id=user_id, limit=limit)

    def get_categories(self) -> List[Dict[str, Any]]:
        """Get available prompt categories."""
        return [
            {'id': 'writing', 'name': 'Writing', 'icon': '✍️'},
            {'id': 'coding', 'name': 'Coding', 'icon': '💻'},
            {'id': 'analysis', 'name': 'Analysis', 'icon': '📊'},
            {'id': 'creative', 'name': 'Creative', 'icon': '🎨'},
            {'id': 'business', 'name': 'Business', 'icon': '💼'},
            {'id': 'learning', 'name': 'Learning', 'icon': '📚'},
        ]

    def _normalize_prompt(self, text: str) -> str:
        """Normalize prompt text for comparison."""
        # Lowercase and remove extra whitespace
        normalized = ' '.join(text.lower().split())

        # Remove common variations
        for prefix in ['please ', 'can you ', 'could you ', 'help me ']:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]

        return normalized[:50]  # Compare first 50 chars

    def _guess_category(self, text: str) -> str:
        """Guess category from prompt text."""
        text_lower = text.lower()

        if any(word in text_lower for word in ['code', 'function', 'debug', 'program', 'api']):
            return 'coding'
        elif any(word in text_lower for word in ['write', 'draft', 'compose', 'summarize']):
            return 'writing'
        elif any(word in text_lower for word in ['analyze', 'compare', 'evaluate', 'pros cons']):
            return 'analysis'
        elif any(word in text_lower for word in ['creative', 'story', 'poem', 'imagine']):
            return 'creative'
        elif any(word in text_lower for word in ['email', 'business', 'proposal', 'meeting']):
            return 'business'
        elif any(word in text_lower for word in ['explain', 'learn', 'teach', 'understand']):
            return 'learning'

        return 'general'


# =============================================================================
# Singleton Instances
# =============================================================================

prompt_generator = PromptSuggestionGenerator()
prompt_discovery = PromptDiscoveryService()
