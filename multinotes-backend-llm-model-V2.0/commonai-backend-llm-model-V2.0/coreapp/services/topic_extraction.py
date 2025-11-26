"""
Topic Extraction Service for MultinotesAI.

This module provides:
- Automatic topic extraction from conversations
- Keyword extraction
- Topic categorization
- Semantic clustering of related topics

WBS Item: 4.4.3 - Add topic extraction from conversations
"""

import re
import logging
from collections import Counter
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from django.conf import settings
from django.db.models import Count

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Common English stop words to filter out
STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought',
    'used', 'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
    'she', 'we', 'they', 'what', 'which', 'who', 'whom', 'when', 'where',
    'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
    'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there', 'then',
    'once', 'if', 'unless', 'until', 'while', 'about', 'after', 'before',
    'between', 'into', 'through', 'during', 'above', 'below', 'up', 'down',
    'out', 'off', 'over', 'under', 'again', 'further', 'any', 'your', 'my',
    'his', 'her', 'our', 'their', 'me', 'him', 'us', 'them', 'myself',
    'yourself', 'himself', 'herself', 'itself', 'ourselves', 'themselves',
    'am', 'being', 'having', 'doing', 'get', 'got', 'getting', 'make',
    'made', 'making', 'say', 'said', 'saying', 'go', 'going', 'gone',
    'come', 'coming', 'came', 'see', 'seeing', 'seen', 'know', 'knowing',
    'known', 'think', 'thinking', 'thought', 'take', 'taking', 'taken',
    'want', 'wanting', 'wanted', 'use', 'using', 'try', 'trying', 'tried',
    'please', 'thank', 'thanks', 'yes', 'no', 'ok', 'okay', 'like', 'well',
    'let', 'lets', "let's", 'dont', "don't", 'cant', "can't", 'wont', "won't",
    'im', "i'm", 'youre', "you're", 'hes', "he's", 'shes', "she's", 'its',
    "it's", 'were', "we're", 'theyre', "they're", 'ive', "i've", 'youve',
    "you've", 'weve', "we've", 'theyve', "they've",
}

# Technical/programming related topics
TECH_TOPICS = {
    'python': 'Programming',
    'javascript': 'Programming',
    'java': 'Programming',
    'typescript': 'Programming',
    'react': 'Frontend',
    'vue': 'Frontend',
    'angular': 'Frontend',
    'node': 'Backend',
    'django': 'Backend',
    'flask': 'Backend',
    'api': 'Backend',
    'database': 'Database',
    'sql': 'Database',
    'mongodb': 'Database',
    'postgresql': 'Database',
    'mysql': 'Database',
    'redis': 'Database',
    'docker': 'DevOps',
    'kubernetes': 'DevOps',
    'aws': 'Cloud',
    'azure': 'Cloud',
    'gcp': 'Cloud',
    'machine learning': 'AI/ML',
    'deep learning': 'AI/ML',
    'neural network': 'AI/ML',
    'nlp': 'AI/ML',
    'ai': 'AI/ML',
    'css': 'Frontend',
    'html': 'Frontend',
    'git': 'DevOps',
    'testing': 'Testing',
    'security': 'Security',
    'authentication': 'Security',
    'encryption': 'Security',
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ExtractedTopic:
    """Represents an extracted topic."""
    name: str
    score: float  # Relevance score (0-1)
    category: Optional[str] = None
    keywords: List[str] = None
    frequency: int = 1

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'score': round(self.score, 3),
            'category': self.category,
            'keywords': self.keywords,
            'frequency': self.frequency,
        }


@dataclass
class TopicExtractionResult:
    """Result of topic extraction."""
    topics: List[ExtractedTopic]
    keywords: List[Tuple[str, int]]  # (keyword, count)
    categories: Dict[str, int]  # category -> count
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'topics': [t.to_dict() for t in self.topics],
            'keywords': [{'keyword': k, 'count': c} for k, c in self.keywords],
            'categories': self.categories,
            'summary': self.summary,
        }


# =============================================================================
# Topic Extractor
# =============================================================================

class TopicExtractor:
    """
    Extract topics from text using keyword analysis and pattern matching.

    Usage:
        extractor = TopicExtractor()
        result = extractor.extract_topics("Your text here...")
        print(result.topics)
    """

    def __init__(self):
        self.stop_words = STOP_WORDS
        self.tech_topics = TECH_TOPICS
        self.min_word_length = 3
        self.max_topics = 10
        self.min_keyword_frequency = 2

    def extract_topics(
        self,
        text: str,
        max_topics: int = None,
        include_keywords: bool = True
    ) -> TopicExtractionResult:
        """
        Extract topics from text.

        Args:
            text: Input text to analyze
            max_topics: Maximum number of topics to return
            include_keywords: Whether to include keyword list

        Returns:
            TopicExtractionResult with extracted topics
        """
        max_topics = max_topics or self.max_topics

        # Preprocess text
        cleaned_text = self._preprocess_text(text)

        # Extract keywords
        keywords = self._extract_keywords(cleaned_text)

        # Extract n-grams for compound topics
        bigrams = self._extract_ngrams(cleaned_text, n=2)
        trigrams = self._extract_ngrams(cleaned_text, n=3)

        # Identify topics
        topics = self._identify_topics(keywords, bigrams, trigrams)

        # Categorize topics
        categories = self._categorize_topics(topics)

        # Score and rank topics
        scored_topics = self._score_topics(topics, keywords)

        # Limit topics
        top_topics = sorted(scored_topics, key=lambda t: t.score, reverse=True)[:max_topics]

        return TopicExtractionResult(
            topics=top_topics,
            keywords=keywords[:20] if include_keywords else [],
            categories=categories,
        )

    def extract_from_conversation(
        self,
        messages: List[Dict[str, str]],
        max_topics: int = None
    ) -> TopicExtractionResult:
        """
        Extract topics from a conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_topics: Maximum topics to return

        Returns:
            TopicExtractionResult
        """
        # Combine all messages
        combined_text = "\n".join(
            msg.get('content', '') for msg in messages
        )

        # Weight user messages more heavily
        user_text = "\n".join(
            msg.get('content', '') for msg in messages
            if msg.get('role') == 'user'
        )

        # Extract from combined text
        result = self.extract_topics(combined_text, max_topics)

        # Boost topics that appear in user messages
        user_keywords = set(word.lower() for word in self._tokenize(user_text))

        for topic in result.topics:
            topic_words = set(topic.name.lower().split())
            if topic_words & user_keywords:
                topic.score = min(topic.score * 1.2, 1.0)

        # Re-sort after boosting
        result.topics = sorted(result.topics, key=lambda t: t.score, reverse=True)

        return result

    def _preprocess_text(self, text: str) -> str:
        """Clean and preprocess text."""
        # Convert to lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)

        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)

        # Remove code blocks (markdown)
        text = re.sub(r'```[\s\S]*?```', '', text)

        # Remove inline code
        text = re.sub(r'`[^`]+`', '', text)

        # Keep alphanumeric and spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        words = text.split()
        return [
            word for word in words
            if len(word) >= self.min_word_length
            and word not in self.stop_words
            and not word.isdigit()
        ]

    def _extract_keywords(self, text: str) -> List[Tuple[str, int]]:
        """Extract keywords with frequency counts."""
        words = self._tokenize(text)
        word_counts = Counter(words)

        # Filter by minimum frequency
        keywords = [
            (word, count) for word, count in word_counts.most_common()
            if count >= self.min_keyword_frequency or count == max(word_counts.values())
        ]

        return keywords

    def _extract_ngrams(self, text: str, n: int = 2) -> List[Tuple[str, int]]:
        """Extract n-grams from text."""
        words = self._tokenize(text)

        if len(words) < n:
            return []

        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i + n])
            ngrams.append(ngram)

        ngram_counts = Counter(ngrams)

        return [
            (ngram, count) for ngram, count in ngram_counts.most_common()
            if count >= 2
        ]

    def _identify_topics(
        self,
        keywords: List[Tuple[str, int]],
        bigrams: List[Tuple[str, int]],
        trigrams: List[Tuple[str, int]]
    ) -> List[ExtractedTopic]:
        """Identify topics from keywords and n-grams."""
        topics = []

        # Check for known tech topics
        keyword_set = {kw for kw, _ in keywords}

        for tech_term, category in self.tech_topics.items():
            if tech_term in keyword_set:
                count = next((c for kw, c in keywords if kw == tech_term), 1)
                topics.append(ExtractedTopic(
                    name=tech_term.title(),
                    score=0.8,
                    category=category,
                    keywords=[tech_term],
                    frequency=count
                ))

        # Add significant bigrams as topics
        for bigram, count in bigrams[:10]:
            words = bigram.split()
            # Skip if all words are already in topics
            if not any(word in [t.name.lower() for t in topics] for word in words):
                topics.append(ExtractedTopic(
                    name=bigram.title(),
                    score=0.6,
                    category=self._guess_category(bigram),
                    keywords=words,
                    frequency=count
                ))

        # Add top single keywords as topics
        for keyword, count in keywords[:15]:
            if keyword not in [t.name.lower() for t in topics]:
                topics.append(ExtractedTopic(
                    name=keyword.title(),
                    score=0.5,
                    category=self._guess_category(keyword),
                    keywords=[keyword],
                    frequency=count
                ))

        return topics

    def _guess_category(self, text: str) -> Optional[str]:
        """Guess category for a topic."""
        text_lower = text.lower()

        for term, category in self.tech_topics.items():
            if term in text_lower:
                return category

        return None

    def _categorize_topics(self, topics: List[ExtractedTopic]) -> Dict[str, int]:
        """Count topics by category."""
        categories = Counter()
        for topic in topics:
            if topic.category:
                categories[topic.category] += 1
        return dict(categories)

    def _score_topics(
        self,
        topics: List[ExtractedTopic],
        keywords: List[Tuple[str, int]]
    ) -> List[ExtractedTopic]:
        """Score topics based on relevance."""
        if not keywords:
            return topics

        max_freq = max(count for _, count in keywords) if keywords else 1

        for topic in topics:
            # Base score from initial assignment
            score = topic.score

            # Boost based on frequency
            freq_boost = (topic.frequency / max_freq) * 0.3
            score += freq_boost

            # Boost if has category
            if topic.category:
                score += 0.1

            # Normalize to 0-1
            topic.score = min(score, 1.0)

        return topics


# =============================================================================
# Conversation Topic Analyzer
# =============================================================================

class ConversationTopicAnalyzer:
    """
    Analyze topics across multiple conversations.

    Usage:
        analyzer = ConversationTopicAnalyzer()
        trends = analyzer.get_topic_trends(user_id, days=30)
    """

    def __init__(self):
        self.extractor = TopicExtractor()

    def analyze_conversation(self, prompt_id: int) -> TopicExtractionResult:
        """
        Analyze topics in a specific conversation.

        Args:
            prompt_id: ID of the prompt/conversation

        Returns:
            TopicExtractionResult
        """
        from coreapp.models import Prompt, PromptResponse

        try:
            prompt = Prompt.objects.get(id=prompt_id)
            responses = PromptResponse.objects.filter(
                prompt=prompt,
                is_delete=False
            ).order_by('created_at')

            messages = [{'role': 'user', 'content': prompt.prompt_text}]
            for response in responses:
                messages.append({
                    'role': 'assistant',
                    'content': response.response_text
                })

            return self.extractor.extract_from_conversation(messages)

        except Exception as e:
            logger.error(f"Failed to analyze conversation {prompt_id}: {e}")
            return TopicExtractionResult(topics=[], keywords=[], categories={})

    def get_user_topics(
        self,
        user_id: int,
        limit: int = 100,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get aggregated topics for a user's recent conversations.

        Args:
            user_id: User ID
            limit: Max conversations to analyze
            days: Number of days to look back

        Returns:
            Dict with aggregated topic data
        """
        from django.utils import timezone
        from datetime import timedelta
        from coreapp.models import Prompt

        cutoff_date = timezone.now() - timedelta(days=days)

        prompts = Prompt.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        ).order_by('-created_at')[:limit]

        all_topics = []
        category_counts = Counter()

        for prompt in prompts:
            result = self.analyze_conversation(prompt.id)
            all_topics.extend(result.topics)
            for cat, count in result.categories.items():
                category_counts[cat] += count

        # Aggregate topics
        topic_scores = {}
        for topic in all_topics:
            name = topic.name.lower()
            if name not in topic_scores:
                topic_scores[name] = {
                    'name': topic.name,
                    'total_score': 0,
                    'count': 0,
                    'category': topic.category,
                }
            topic_scores[name]['total_score'] += topic.score
            topic_scores[name]['count'] += 1

        # Calculate average scores
        aggregated_topics = []
        for name, data in topic_scores.items():
            avg_score = data['total_score'] / data['count']
            aggregated_topics.append({
                'name': data['name'],
                'score': round(avg_score, 3),
                'frequency': data['count'],
                'category': data['category'],
            })

        # Sort by frequency * score
        aggregated_topics.sort(
            key=lambda t: t['frequency'] * t['score'],
            reverse=True
        )

        return {
            'topics': aggregated_topics[:20],
            'categories': dict(category_counts),
            'total_conversations': prompts.count(),
            'period_days': days,
        }

    def get_topic_trends(
        self,
        user_id: int,
        days: int = 30,
        interval: str = 'week'
    ) -> List[Dict[str, Any]]:
        """
        Get topic trends over time.

        Args:
            user_id: User ID
            days: Number of days to analyze
            interval: 'day' or 'week'

        Returns:
            List of topic data by time period
        """
        from django.utils import timezone
        from datetime import timedelta
        from coreapp.models import Prompt

        cutoff_date = timezone.now() - timedelta(days=days)

        prompts = Prompt.objects.filter(
            user_id=user_id,
            is_delete=False,
            created_at__gte=cutoff_date
        ).order_by('created_at')

        # Group prompts by interval
        interval_days = 7 if interval == 'week' else 1
        periods = {}

        for prompt in prompts:
            period_start = prompt.created_at.date()
            if interval == 'week':
                # Round to start of week
                period_start = period_start - timedelta(days=period_start.weekday())

            period_key = period_start.isoformat()

            if period_key not in periods:
                periods[period_key] = []
            periods[period_key].append(prompt.id)

        # Analyze each period
        trends = []
        for period_key, prompt_ids in sorted(periods.items()):
            period_topics = []

            for prompt_id in prompt_ids:
                result = self.analyze_conversation(prompt_id)
                period_topics.extend(result.topics)

            # Aggregate topics for this period
            topic_counts = Counter(t.name.lower() for t in period_topics)

            trends.append({
                'period': period_key,
                'conversation_count': len(prompt_ids),
                'top_topics': [
                    {'name': name, 'count': count}
                    for name, count in topic_counts.most_common(5)
                ],
            })

        return trends


# =============================================================================
# Singleton Instances
# =============================================================================

topic_extractor = TopicExtractor()
topic_analyzer = ConversationTopicAnalyzer()
