"""
Conversation Summarization Service for MultinotesAI.

This module provides:
- Conversation summarization
- Key point extraction
- Topic detection
- Context compression
"""

import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Summarization Configuration
# =============================================================================

class SummarizationConfig:
    """Configuration for summarization."""

    # Length limits
    MAX_INPUT_TOKENS = 8000
    MIN_INPUT_LENGTH = 100
    DEFAULT_SUMMARY_LENGTH = 200  # words
    MAX_SUMMARY_LENGTH = 500

    # Extraction settings
    MAX_KEY_POINTS = 5
    MAX_TOPICS = 3
    MAX_ACTION_ITEMS = 5

    # Cache
    CACHE_TIMEOUT = 3600  # 1 hour


# =============================================================================
# Summarization Service
# =============================================================================

class SummarizationService:
    """
    Service for summarizing conversations and content.

    Usage:
        service = SummarizationService()
        summary = service.summarize_conversation(messages)
        key_points = service.extract_key_points(text)
    """

    def __init__(self):
        self.config = SummarizationConfig

    # -------------------------------------------------------------------------
    # Conversation Summarization
    # -------------------------------------------------------------------------

    def summarize_conversation(
        self,
        messages: List[Dict],
        max_length: int = None,
        style: str = 'concise'  # 'concise', 'detailed', 'bullet'
    ) -> Dict:
        """
        Summarize a conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_length: Maximum summary length in words
            style: Summary style

        Returns:
            Summary dict with text and metadata
        """
        if not messages:
            return {'summary': '', 'metadata': {}}

        # Format conversation
        conversation_text = self._format_conversation(messages)

        if len(conversation_text) < self.config.MIN_INPUT_LENGTH:
            return {
                'summary': conversation_text,
                'metadata': {'too_short': True}
            }

        # Check cache
        cache_key = self._get_cache_key(conversation_text, style)
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Generate summary based on style
        if style == 'bullet':
            summary = self._generate_bullet_summary(conversation_text, max_length)
        elif style == 'detailed':
            summary = self._generate_detailed_summary(conversation_text, max_length)
        else:
            summary = self._generate_concise_summary(conversation_text, max_length)

        result = {
            'summary': summary,
            'metadata': {
                'original_length': len(conversation_text),
                'summary_length': len(summary),
                'compression_ratio': round(len(summary) / max(len(conversation_text), 1), 2),
                'message_count': len(messages),
                'style': style,
            }
        }

        # Cache result
        cache.set(cache_key, result, self.config.CACHE_TIMEOUT)

        return result

    def _format_conversation(self, messages: List[Dict]) -> str:
        """Format messages into readable conversation."""
        formatted = []
        for msg in messages:
            role = msg.get('role', 'user').title()
            content = msg.get('content', '')
            formatted.append(f"{role}: {content}")
        return "\n\n".join(formatted)

    def _generate_concise_summary(self, text: str, max_length: int = None) -> str:
        """Generate a concise summary using extractive approach."""
        max_length = max_length or self.config.DEFAULT_SUMMARY_LENGTH

        # Split into sentences
        sentences = self._split_sentences(text)

        if len(sentences) <= 3:
            return text

        # Score sentences by importance
        scored = []
        for i, sentence in enumerate(sentences):
            score = self._score_sentence(sentence, i, len(sentences))
            scored.append((sentence, score))

        # Sort by score and select top sentences
        scored.sort(key=lambda x: x[1], reverse=True)

        summary_sentences = []
        word_count = 0

        for sentence, score in scored:
            words = len(sentence.split())
            if word_count + words <= max_length:
                summary_sentences.append(sentence)
                word_count += words
            else:
                break

        # Reorder by original position
        original_order = {s: i for i, s in enumerate(sentences)}
        summary_sentences.sort(key=lambda s: original_order.get(s, 0))

        return ' '.join(summary_sentences)

    def _generate_detailed_summary(self, text: str, max_length: int = None) -> str:
        """Generate a more detailed summary."""
        max_length = max_length or self.config.MAX_SUMMARY_LENGTH

        # Extract key information
        key_points = self.extract_key_points(text)
        topics = self.detect_topics(text)

        # Build structured summary
        parts = []

        if topics:
            parts.append(f"Topics discussed: {', '.join(topics[:3])}")

        if key_points:
            parts.append("Key points:")
            for point in key_points[:5]:
                parts.append(f"• {point}")

        # Add concise summary
        concise = self._generate_concise_summary(text, max_length // 2)
        parts.append(f"\nSummary: {concise}")

        return '\n'.join(parts)

    def _generate_bullet_summary(self, text: str, max_length: int = None) -> str:
        """Generate bullet-point summary."""
        key_points = self.extract_key_points(text, limit=7)

        bullets = []
        for point in key_points:
            bullets.append(f"• {point}")

        return '\n'.join(bullets)

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _score_sentence(self, sentence: str, position: int, total: int) -> float:
        """Score sentence importance."""
        score = 0.0

        # Position score (first and last sentences often important)
        if position == 0:
            score += 2.0
        elif position == total - 1:
            score += 1.5
        elif position < 3:
            score += 1.0

        # Length score (medium length preferred)
        words = len(sentence.split())
        if 10 <= words <= 30:
            score += 1.0
        elif words < 5:
            score -= 0.5

        # Keyword presence
        important_patterns = [
            r'\b(important|key|main|significant|crucial)\b',
            r'\b(conclusion|summary|result|finding)\b',
            r'\b(should|must|need|require)\b',
            r'\b(because|therefore|thus|hence)\b',
        ]

        for pattern in important_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                score += 0.5

        # Question handling
        if sentence.strip().endswith('?'):
            score += 0.5

        return score

    # -------------------------------------------------------------------------
    # Key Point Extraction
    # -------------------------------------------------------------------------

    def extract_key_points(
        self,
        text: str,
        limit: int = None
    ) -> List[str]:
        """
        Extract key points from text.

        Args:
            text: Text to analyze
            limit: Maximum key points

        Returns:
            List of key point strings
        """
        limit = limit or self.config.MAX_KEY_POINTS

        sentences = self._split_sentences(text)
        key_points = []

        # Score and rank sentences
        scored = []
        for sentence in sentences:
            score = self._score_as_key_point(sentence)
            if score > 0.5:
                scored.append((sentence, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Clean and deduplicate
        seen_content = set()
        for sentence, score in scored:
            cleaned = self._clean_key_point(sentence)
            # Simple deduplication
            content_hash = cleaned.lower()[:50]
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                key_points.append(cleaned)

            if len(key_points) >= limit:
                break

        return key_points

    def _score_as_key_point(self, sentence: str) -> float:
        """Score how likely a sentence is a key point."""
        score = 0.5  # Base score

        # Check for key point indicators
        indicators = [
            (r'^\d+[\.\)]\s', 0.5),  # Numbered list
            (r'^[-•*]\s', 0.5),  # Bullet point
            (r'\b(first|second|third|finally)\b', 0.3),
            (r'\b(key|main|important|crucial|essential)\b', 0.4),
            (r'\b(note|remember|consider)\b', 0.3),
            (r'\b(should|must|need to|have to)\b', 0.3),
        ]

        for pattern, weight in indicators:
            if re.search(pattern, sentence, re.IGNORECASE):
                score += weight

        # Penalize questions and very short sentences
        if sentence.strip().endswith('?'):
            score -= 0.3

        words = len(sentence.split())
        if words < 5:
            score -= 0.5
        elif words > 50:
            score -= 0.2

        return max(0, score)

    def _clean_key_point(self, text: str) -> str:
        """Clean a key point for presentation."""
        # Remove leading bullets/numbers
        text = re.sub(r'^[\d\.\)\-•*]+\s*', '', text.strip())
        # Ensure proper capitalization
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        return text

    # -------------------------------------------------------------------------
    # Topic Detection
    # -------------------------------------------------------------------------

    def detect_topics(
        self,
        text: str,
        limit: int = None
    ) -> List[str]:
        """
        Detect main topics in text.

        Args:
            text: Text to analyze
            limit: Maximum topics

        Returns:
            List of topic strings
        """
        limit = limit or self.config.MAX_TOPICS

        # Simple keyword-based topic detection
        text_lower = text.lower()
        words = re.findall(r'\b[a-z]{4,}\b', text_lower)

        # Count word frequencies
        word_freq = {}
        for word in words:
            if word not in self._get_stop_words():
                word_freq[word] = word_freq.get(word, 0) + 1

        # Get top words as topics
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        topics = [word.title() for word, count in sorted_words[:limit * 2] if count > 1]

        # Deduplicate similar topics
        unique_topics = []
        for topic in topics:
            if not any(topic.lower() in t.lower() or t.lower() in topic.lower()
                      for t in unique_topics):
                unique_topics.append(topic)
            if len(unique_topics) >= limit:
                break

        return unique_topics

    def _get_stop_words(self) -> set:
        """Get common stop words."""
        return {
            'the', 'and', 'for', 'that', 'this', 'with', 'have', 'from',
            'they', 'will', 'would', 'could', 'should', 'been', 'were',
            'what', 'when', 'where', 'which', 'there', 'their', 'about',
            'into', 'more', 'some', 'just', 'also', 'very', 'like', 'make',
            'being', 'other', 'then', 'than', 'your', 'only', 'well',
        }

    # -------------------------------------------------------------------------
    # Action Item Extraction
    # -------------------------------------------------------------------------

    def extract_action_items(
        self,
        text: str,
        limit: int = None
    ) -> List[Dict]:
        """
        Extract action items from text.

        Args:
            text: Text to analyze
            limit: Maximum action items

        Returns:
            List of action item dicts
        """
        limit = limit or self.config.MAX_ACTION_ITEMS

        sentences = self._split_sentences(text)
        action_items = []

        # Patterns indicating action items
        action_patterns = [
            r'\b(need to|should|must|will|going to|have to)\b',
            r'\b(todo|action|task|follow[\s-]?up)\b',
            r'\b(complete|finish|send|create|update|review|check)\b',
            r'^(please|kindly)\b',
        ]

        for sentence in sentences:
            for pattern in action_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    # Extract the action
                    action = self._clean_key_point(sentence)
                    if action and len(action) > 10:
                        action_items.append({
                            'action': action,
                            'priority': self._detect_priority(sentence),
                        })
                    break

            if len(action_items) >= limit:
                break

        return action_items

    def _detect_priority(self, text: str) -> str:
        """Detect priority level from text."""
        text_lower = text.lower()

        if any(word in text_lower for word in ['urgent', 'asap', 'immediately', 'critical']):
            return 'high'
        elif any(word in text_lower for word in ['important', 'soon', 'priority']):
            return 'medium'
        else:
            return 'normal'

    # -------------------------------------------------------------------------
    # Context Compression
    # -------------------------------------------------------------------------

    def compress_context(
        self,
        messages: List[Dict],
        max_tokens: int = 4000
    ) -> List[Dict]:
        """
        Compress conversation context for continued generation.

        Args:
            messages: Original messages
            max_tokens: Target token limit

        Returns:
            Compressed message list
        """
        if not messages:
            return []

        # Rough token estimation (4 chars ≈ 1 token)
        total_chars = sum(len(m.get('content', '')) for m in messages)
        estimated_tokens = total_chars // 4

        if estimated_tokens <= max_tokens:
            return messages

        # Need to compress
        # Keep system message and recent messages
        compressed = []
        recent_count = 4  # Keep last 4 messages

        # Add system message if present
        if messages and messages[0].get('role') == 'system':
            compressed.append(messages[0])
            messages = messages[1:]

        # Summarize older messages
        older_messages = messages[:-recent_count] if len(messages) > recent_count else []
        recent_messages = messages[-recent_count:] if len(messages) > recent_count else messages

        if older_messages:
            summary_result = self.summarize_conversation(older_messages, style='concise')
            compressed.append({
                'role': 'system',
                'content': f"[Previous conversation summary: {summary_result['summary']}]"
            })

        # Add recent messages
        compressed.extend(recent_messages)

        return compressed

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    def _get_cache_key(self, text: str, style: str) -> str:
        """Generate cache key for summary."""
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        return f"summary:{style}:{text_hash}"


# =============================================================================
# Singleton Instance
# =============================================================================

summarization_service = SummarizationService()
