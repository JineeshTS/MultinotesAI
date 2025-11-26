"""
Smart Conversation Compression Service for MultinotesAI.

This module provides:
- Intelligent context window management
- Conversation history compression
- Key information extraction and preservation
- Token-efficient summarization

WBS Item: 6.1.10 - Smart conversation compression
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class CompressionStrategy(Enum):
    """Compression strategies."""
    TRUNCATE = 'truncate'  # Simply remove old messages
    SUMMARIZE = 'summarize'  # Summarize old messages
    SLIDING_WINDOW = 'sliding_window'  # Keep recent + summarize old
    IMPORTANCE_BASED = 'importance_based'  # Keep important messages
    HYBRID = 'hybrid'  # Combine strategies


@dataclass
class CompressionConfig:
    """Configuration for conversation compression."""
    max_tokens: int = 4096  # Target context size
    min_messages_to_keep: int = 4  # Always keep last N messages
    summary_ratio: float = 0.3  # Compress to this ratio
    importance_threshold: float = 0.5  # Threshold for importance-based
    preserve_system: bool = True  # Always preserve system messages
    preserve_first_user: bool = True  # Preserve first user message


@dataclass
class Message:
    """A conversation message."""
    role: str
    content: str
    tokens: int = 0
    importance: float = 0.5
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.tokens == 0:
            self.tokens = estimate_tokens(self.content)
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CompressionResult:
    """Result of conversation compression."""
    messages: List[Dict[str, str]]
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    summary: Optional[str] = None
    removed_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'messages': self.messages,
            'original_tokens': self.original_tokens,
            'compressed_tokens': self.compressed_tokens,
            'compression_ratio': round(self.compression_ratio, 3),
            'summary': self.summary,
            'removed_count': self.removed_count,
        }


# =============================================================================
# Token Estimation
# =============================================================================

def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.

    Uses a simple heuristic: ~4 characters per token for English.
    For more accuracy, use tiktoken library.
    """
    if not text:
        return 0

    # Simple estimation: words + punctuation
    # Average English word is ~5 chars, average token is ~4 chars
    # So roughly 1.25 tokens per word
    words = len(text.split())
    chars = len(text)

    # Use character-based estimate with word adjustment
    return max(int(chars / 4), int(words * 1.3))


def count_message_tokens(messages: List[Dict[str, str]]) -> int:
    """Count total tokens in message list."""
    total = 0
    for msg in messages:
        # Account for message structure overhead (~4 tokens per message)
        total += 4
        total += estimate_tokens(msg.get('content', ''))
    return total


# =============================================================================
# Importance Scoring
# =============================================================================

class ImportanceScorer:
    """Score message importance for compression decisions."""

    # Keywords that indicate important content
    IMPORTANT_KEYWORDS = {
        'important', 'critical', 'must', 'required', 'never', 'always',
        'remember', 'note', 'key', 'essential', 'crucial', 'warning',
        'error', 'bug', 'fix', 'solution', 'answer', 'result', 'conclusion',
    }

    # Patterns that indicate code or technical content
    CODE_PATTERNS = [
        r'```[\s\S]*?```',  # Code blocks
        r'`[^`]+`',  # Inline code
        r'def\s+\w+',  # Python functions
        r'function\s+\w+',  # JS functions
        r'class\s+\w+',  # Classes
    ]

    def score(self, message: Message) -> float:
        """
        Score message importance (0-1).

        Args:
            message: Message to score

        Returns:
            Importance score between 0 and 1
        """
        score = 0.5  # Base score

        content = message.content.lower()

        # Role-based scoring
        if message.role == 'system':
            score += 0.3  # System messages are important
        elif message.role == 'user':
            score += 0.1  # User messages slightly more important

        # Keyword-based scoring
        keyword_count = sum(1 for kw in self.IMPORTANT_KEYWORDS if kw in content)
        score += min(keyword_count * 0.05, 0.2)

        # Code content scoring
        has_code = any(re.search(pattern, message.content) for pattern in self.CODE_PATTERNS)
        if has_code:
            score += 0.15

        # Length-based scoring (very short or very long messages might be less important)
        if message.tokens < 10:
            score -= 0.1
        elif message.tokens > 500:
            score -= 0.05

        # Question scoring (questions often drive conversation)
        if '?' in content:
            score += 0.1

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))


# =============================================================================
# Conversation Compressor
# =============================================================================

class ConversationCompressor:
    """
    Compress conversation history to fit within token limits.

    Usage:
        compressor = ConversationCompressor()
        result = compressor.compress(
            messages=[...],
            max_tokens=4096,
            strategy=CompressionStrategy.HYBRID
        )
    """

    def __init__(self):
        self.scorer = ImportanceScorer()
        self.config = CompressionConfig()

    def compress(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = None,
        strategy: CompressionStrategy = CompressionStrategy.HYBRID,
        config: CompressionConfig = None
    ) -> CompressionResult:
        """
        Compress conversation to fit within token limit.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens for result
            strategy: Compression strategy to use
            config: Optional configuration override

        Returns:
            CompressionResult with compressed messages
        """
        config = config or self.config
        max_tokens = max_tokens or config.max_tokens

        # Convert to Message objects
        msg_objects = [
            Message(
                role=m.get('role', 'user'),
                content=m.get('content', ''),
            )
            for m in messages
        ]

        # Score importance
        for msg in msg_objects:
            msg.importance = self.scorer.score(msg)

        # Calculate original tokens
        original_tokens = sum(m.tokens for m in msg_objects)

        # Check if compression needed
        if original_tokens <= max_tokens:
            return CompressionResult(
                messages=messages,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                removed_count=0,
            )

        # Apply compression strategy
        if strategy == CompressionStrategy.TRUNCATE:
            result = self._truncate(msg_objects, max_tokens, config)
        elif strategy == CompressionStrategy.SLIDING_WINDOW:
            result = self._sliding_window(msg_objects, max_tokens, config)
        elif strategy == CompressionStrategy.IMPORTANCE_BASED:
            result = self._importance_based(msg_objects, max_tokens, config)
        elif strategy == CompressionStrategy.SUMMARIZE:
            result = self._summarize(msg_objects, max_tokens, config)
        else:  # HYBRID
            result = self._hybrid(msg_objects, max_tokens, config)

        # Calculate compression ratio
        compressed_tokens = count_message_tokens(result['messages'])
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

        return CompressionResult(
            messages=result['messages'],
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            summary=result.get('summary'),
            removed_count=result.get('removed_count', 0),
        )

    def _truncate(
        self,
        messages: List[Message],
        max_tokens: int,
        config: CompressionConfig
    ) -> Dict[str, Any]:
        """Simple truncation - keep most recent messages."""
        kept = []
        current_tokens = 0
        removed_count = 0

        # Always keep system message if present
        if config.preserve_system and messages and messages[0].role == 'system':
            kept.append(messages[0])
            current_tokens += messages[0].tokens
            messages = messages[1:]

        # Keep from the end
        for msg in reversed(messages):
            if current_tokens + msg.tokens <= max_tokens:
                kept.insert(0 if not kept else 1, msg)
                current_tokens += msg.tokens
            else:
                removed_count += 1

        return {
            'messages': [{'role': m.role, 'content': m.content} for m in kept],
            'removed_count': removed_count,
        }

    def _sliding_window(
        self,
        messages: List[Message],
        max_tokens: int,
        config: CompressionConfig
    ) -> Dict[str, Any]:
        """Keep recent messages, summarize old ones."""
        if len(messages) <= config.min_messages_to_keep:
            return {
                'messages': [{'role': m.role, 'content': m.content} for m in messages],
                'removed_count': 0,
            }

        # Separate into old and recent
        split_point = len(messages) - config.min_messages_to_keep
        old_messages = messages[:split_point]
        recent_messages = messages[split_point:]

        # Calculate token budget
        recent_tokens = sum(m.tokens for m in recent_messages)
        summary_budget = max_tokens - recent_tokens - 100  # Reserve for summary

        if summary_budget <= 0:
            # Not enough budget, just truncate
            return self._truncate(messages, max_tokens, config)

        # Create summary of old messages
        summary = self._create_summary(old_messages, summary_budget)

        # Build result
        result_messages = []

        # Add system message if present
        if config.preserve_system and old_messages and old_messages[0].role == 'system':
            result_messages.append({
                'role': 'system',
                'content': old_messages[0].content
            })

        # Add summary as system message
        if summary:
            result_messages.append({
                'role': 'system',
                'content': f"[Conversation Summary]\n{summary}"
            })

        # Add recent messages
        for msg in recent_messages:
            result_messages.append({
                'role': msg.role,
                'content': msg.content
            })

        return {
            'messages': result_messages,
            'summary': summary,
            'removed_count': len(old_messages) - (1 if config.preserve_system else 0),
        }

    def _importance_based(
        self,
        messages: List[Message],
        max_tokens: int,
        config: CompressionConfig
    ) -> Dict[str, Any]:
        """Keep messages based on importance scores."""
        # Sort by importance (keep indices for ordering)
        indexed = [(i, msg) for i, msg in enumerate(messages)]
        indexed.sort(key=lambda x: x[1].importance, reverse=True)

        # Select messages within budget
        kept_indices = set()
        current_tokens = 0

        for idx, msg in indexed:
            if current_tokens + msg.tokens <= max_tokens:
                kept_indices.add(idx)
                current_tokens += msg.tokens

        # Ensure minimum recent messages
        for i in range(len(messages) - 1, max(0, len(messages) - config.min_messages_to_keep) - 1, -1):
            if i not in kept_indices:
                msg = messages[i]
                if current_tokens + msg.tokens <= max_tokens * 1.1:  # Allow slight overflow
                    kept_indices.add(i)
                    current_tokens += msg.tokens

        # Build result in original order
        result_messages = []
        for i, msg in enumerate(messages):
            if i in kept_indices:
                result_messages.append({
                    'role': msg.role,
                    'content': msg.content
                })

        return {
            'messages': result_messages,
            'removed_count': len(messages) - len(result_messages),
        }

    def _summarize(
        self,
        messages: List[Message],
        max_tokens: int,
        config: CompressionConfig
    ) -> Dict[str, Any]:
        """Summarize entire conversation."""
        summary = self._create_summary(messages, int(max_tokens * config.summary_ratio))

        result_messages = []

        # Keep system message
        if config.preserve_system and messages and messages[0].role == 'system':
            result_messages.append({
                'role': 'system',
                'content': messages[0].content
            })

        # Add summary
        if summary:
            result_messages.append({
                'role': 'system',
                'content': f"[Conversation Summary]\n{summary}"
            })

        # Keep last few messages
        recent = messages[-config.min_messages_to_keep:]
        for msg in recent:
            result_messages.append({
                'role': msg.role,
                'content': msg.content
            })

        return {
            'messages': result_messages,
            'summary': summary,
            'removed_count': len(messages) - config.min_messages_to_keep,
        }

    def _hybrid(
        self,
        messages: List[Message],
        max_tokens: int,
        config: CompressionConfig
    ) -> Dict[str, Any]:
        """
        Hybrid approach combining multiple strategies.

        1. Keep system messages
        2. Keep highly important messages
        3. Summarize middle section
        4. Keep recent messages
        """
        if len(messages) <= config.min_messages_to_keep * 2:
            return self._truncate(messages, max_tokens, config)

        result_messages = []
        current_tokens = 0

        # 1. Keep system message
        if config.preserve_system and messages and messages[0].role == 'system':
            result_messages.append({
                'role': 'system',
                'content': messages[0].content
            })
            current_tokens += messages[0].tokens
            messages = messages[1:]

        # 2. Identify highly important messages
        important_indices = set()
        for i, msg in enumerate(messages[:-config.min_messages_to_keep]):
            if msg.importance >= config.importance_threshold:
                important_indices.add(i)

        # 3. Calculate budget for summary
        recent_messages = messages[-config.min_messages_to_keep:]
        recent_tokens = sum(m.tokens for m in recent_messages)
        important_tokens = sum(
            messages[i].tokens for i in important_indices
        )
        summary_budget = max_tokens - current_tokens - recent_tokens - important_tokens - 100

        # 4. Create summary of remaining messages
        summarize_messages = [
            messages[i] for i in range(len(messages) - config.min_messages_to_keep)
            if i not in important_indices
        ]

        if summarize_messages and summary_budget > 50:
            summary = self._create_summary(summarize_messages, summary_budget)
            if summary:
                result_messages.append({
                    'role': 'system',
                    'content': f"[Summary of earlier conversation]\n{summary}"
                })

        # 5. Add important messages (in order)
        for i in sorted(important_indices):
            result_messages.append({
                'role': messages[i].role,
                'content': messages[i].content
            })

        # 6. Add recent messages
        for msg in recent_messages:
            result_messages.append({
                'role': msg.role,
                'content': msg.content
            })

        return {
            'messages': result_messages,
            'summary': summary if summarize_messages else None,
            'removed_count': len(summarize_messages),
        }

    def _create_summary(self, messages: List[Message], max_tokens: int) -> str:
        """
        Create a summary of messages.

        This is a simple extractive summary. For better results,
        use an LLM-based summarization.
        """
        if not messages:
            return ""

        # Extract key points
        key_points = []

        for msg in messages:
            # Extract questions
            questions = re.findall(r'[^.!?]*\?', msg.content)
            for q in questions[:2]:
                key_points.append(f"- Question: {q.strip()}")

            # Extract sentences with important keywords
            sentences = re.split(r'[.!?]+', msg.content)
            for sentence in sentences:
                if any(kw in sentence.lower() for kw in ['important', 'must', 'should', 'key', 'note']):
                    if len(sentence.strip()) > 10:
                        key_points.append(f"- {sentence.strip()}")

        # Build summary
        if not key_points:
            # Fallback: first sentence of first few messages
            for msg in messages[:3]:
                first_sentence = msg.content.split('.')[0]
                if len(first_sentence) > 20:
                    key_points.append(f"- {first_sentence.strip()}")

        # Limit to token budget
        summary_parts = []
        current_tokens = 0

        for point in key_points:
            point_tokens = estimate_tokens(point)
            if current_tokens + point_tokens <= max_tokens:
                summary_parts.append(point)
                current_tokens += point_tokens
            else:
                break

        return "\n".join(summary_parts) if summary_parts else "Previous conversation context available."


# =============================================================================
# Context Window Manager
# =============================================================================

class ContextWindowManager:
    """
    Manage context window for LLM interactions.

    Usage:
        manager = ContextWindowManager(max_tokens=4096)
        context = manager.prepare_context(
            system_prompt="You are a helpful assistant.",
            messages=[...],
            new_message="User's new message"
        )
    """

    def __init__(self, max_tokens: int = 4096):
        self.max_tokens = max_tokens
        self.compressor = ConversationCompressor()
        self.response_reserve = 1024  # Reserve tokens for response

    def prepare_context(
        self,
        messages: List[Dict[str, str]],
        new_message: Optional[str] = None,
        system_prompt: Optional[str] = None,
        strategy: CompressionStrategy = CompressionStrategy.HYBRID
    ) -> Dict[str, Any]:
        """
        Prepare context for LLM call.

        Args:
            messages: Conversation history
            new_message: New user message to add
            system_prompt: System prompt
            strategy: Compression strategy

        Returns:
            Dict with prepared messages and metadata
        """
        # Start with system prompt
        all_messages = []
        reserved_tokens = self.response_reserve

        if system_prompt:
            all_messages.append({
                'role': 'system',
                'content': system_prompt
            })
            reserved_tokens += estimate_tokens(system_prompt)

        # Add history
        all_messages.extend(messages)

        # Add new message
        if new_message:
            all_messages.append({
                'role': 'user',
                'content': new_message
            })
            reserved_tokens += estimate_tokens(new_message)

        # Calculate available tokens
        available_tokens = self.max_tokens - reserved_tokens

        # Compress if needed
        result = self.compressor.compress(
            messages=all_messages,
            max_tokens=available_tokens,
            strategy=strategy
        )

        return {
            'messages': result.messages,
            'original_tokens': result.original_tokens,
            'final_tokens': result.compressed_tokens,
            'was_compressed': result.compression_ratio < 1.0,
            'compression_ratio': result.compression_ratio,
            'available_for_response': self.max_tokens - result.compressed_tokens,
        }

    def should_compress(self, messages: List[Dict[str, str]]) -> bool:
        """Check if messages need compression."""
        total_tokens = count_message_tokens(messages)
        return total_tokens > (self.max_tokens - self.response_reserve)


# =============================================================================
# Singleton Instances
# =============================================================================

conversation_compressor = ConversationCompressor()
context_manager = ContextWindowManager()
