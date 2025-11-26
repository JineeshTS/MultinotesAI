"""
Base classes and utilities for AI generation services.

This module provides common functionality used across all LLM providers:
- Token management
- Prompt/Response recording
- File handling
- Streaming response helpers
"""

import os
import logging
from enum import IntEnum
from abc import ABC, abstractmethod
from typing import Optional, Generator, Any, Tuple
from io import BytesIO

from django.http import StreamingHttpResponse
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

from coreapp.models import LLM, LLM_Tokens, Prompt, PromptResponse, GroupResponse
from planandsubscription.models import Subscription
from authentication.awsservice import uploadImage
from backend.exceptions import (
    LLMModelNotFoundError,
    LLMModelDisconnectedError,
    InsufficientTokensError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

class LLMProvider(IntEnum):
    """LLM Provider source identifiers."""
    TOGETHER = 2
    GEMINI = 3
    OPENAI = 4


class ResponseType(IntEnum):
    """Response type identifiers for prompts/responses."""
    TEXT_TO_TEXT = 2
    IMAGE_TO_TEXT = 3
    TEXT_TO_IMAGE = 4
    TEXT_TO_SPEECH = 5
    SPEECH_TO_TEXT = 6
    CODE = 7
    PROMPT_GENERATION = 8
    VIDEO_TO_TEXT = 9


# Supported file extensions
SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpeg', '.jpg', '.webp', '.heic', '.heif']
SUPPORTED_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.aiff', '.aac', '.ogg', '.flac']
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mpeg', '.mov', '.avi', '.x-flv', '.mpg', '.webm', '.wmv', '.3gpp']


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_llm_instance(model_name: str) -> LLM:
    """
    Get an LLM instance by name.

    Args:
        model_name: Name of the LLM model

    Returns:
        LLM instance

    Raises:
        LLMModelNotFoundError: If model not found
        LLMModelDisconnectedError: If model is not connected
    """
    try:
        llm = LLM.objects.get(
            name=model_name,
            is_enabled=True,
            is_delete=False
        )
    except LLM.DoesNotExist:
        raise LLMModelNotFoundError(f'Model "{model_name}" not found or not enabled.')

    if llm.test_status != 'connected':
        raise LLMModelDisconnectedError(f'Model "{model_name}" is not connected.')

    if not llm.model_string:
        raise LLMModelNotFoundError(f'Model string for "{model_name}" not configured.')

    return llm


def get_user_subscription(user) -> Optional[Subscription]:
    """
    Get user's active subscription, considering cluster membership.

    Args:
        user: CustomUser instance

    Returns:
        Subscription instance or None
    """
    if user.cluster:
        return user.cluster.subscription
    return Subscription.objects.filter(
        user=user.id,
        status__in=['active', 'trial'],
        is_delete=False
    ).first()


def manage_token_usage(user, tokens_used: int = 1) -> bool:
    """
    Deduct text tokens from user's subscription.

    Args:
        user: CustomUser instance
        tokens_used: Number of tokens to deduct

    Returns:
        True if successful

    Raises:
        InsufficientTokensError: If not enough tokens
    """
    subscription = get_user_subscription(user)

    if not subscription:
        raise InsufficientTokensError('No active subscription found.')

    if subscription.balanceToken < tokens_used:
        raise InsufficientTokensError()

    subscription.balanceToken -= tokens_used
    subscription.usedToken += tokens_used
    subscription.save()

    return True


def manage_file_token_usage(user, tokens_used: int = 1) -> bool:
    """
    Deduct file tokens from user's subscription.

    Args:
        user: CustomUser instance
        tokens_used: Number of file tokens to deduct

    Returns:
        True if successful

    Raises:
        InsufficientTokensError: If not enough tokens
    """
    subscription = get_user_subscription(user)

    if not subscription:
        raise InsufficientTokensError('No active subscription found.')

    if subscription.fileToken < tokens_used:
        raise InsufficientTokensError('Insufficient file tokens.')

    subscription.fileToken -= tokens_used
    subscription.usedFileToken += tokens_used
    subscription.save()

    return True


def create_prompt_record(
    user,
    category_id: int,
    response_type: int,
    prompt_text: str = None,
    prompt_audio: str = None,
    group_id: int = None
) -> Prompt:
    """
    Create a Prompt record.

    Args:
        user: CustomUser instance
        category_id: Category ID
        response_type: ResponseType value
        prompt_text: Text prompt (optional)
        prompt_audio: Audio file key (optional)
        group_id: Conversation group ID (optional)

    Returns:
        Prompt instance
    """
    return Prompt.objects.create(
        user_id=user.id,
        prompt_text=prompt_text,
        prompt_audio=prompt_audio,
        category_id=category_id,
        group_id=group_id,
        response_type=response_type,
    )


def create_response_record(
    prompt: Prompt,
    llm: LLM,
    user,
    category_id: int,
    response_type: int,
    response_text: str = None,
    response_image: str = None,
    response_audio: str = None,
    tokens_used: int = 1,
    file_size: int = None
) -> PromptResponse:
    """
    Create a PromptResponse record.

    Args:
        prompt: Prompt instance
        llm: LLM instance
        user: CustomUser instance
        category_id: Category ID
        response_type: ResponseType value
        response_text: Text response (optional)
        response_image: Image file key (optional)
        response_audio: Audio file key (optional)
        tokens_used: Tokens used for generation
        file_size: File size in bytes (optional)

    Returns:
        PromptResponse instance
    """
    return PromptResponse.objects.create(
        llm_id=llm.id,
        prompt_id=prompt.id,
        user_id=user.id,
        category_id=category_id,
        response_type=response_type,
        response_text=response_text,
        response_image=response_image,
        response_audio=response_audio,
        tokenUsed=tokens_used,
        fileSize=file_size,
    )


def create_token_record(
    user,
    llm: LLM,
    prompt: Prompt,
    text_tokens: int = 0,
    file_tokens: int = 0
) -> LLM_Tokens:
    """
    Create an LLM_Tokens record for tracking token usage.

    Args:
        user: CustomUser instance
        llm: LLM instance
        prompt: Prompt instance
        text_tokens: Text tokens used
        file_tokens: File tokens used

    Returns:
        LLM_Tokens instance
    """
    return LLM_Tokens.objects.create(
        user_id=user.id,
        llm_id=llm.id,
        prompt_id=prompt.id,
        token_used=text_tokens,
        file_token_used=file_tokens,
    )


def get_group_name(input_string: str, max_words: int = 4) -> str:
    """
    Extract first N words from a string for group naming.

    Args:
        input_string: Full string
        max_words: Maximum words to extract

    Returns:
        Truncated string
    """
    words = input_string.split()
    return ' '.join(words[:max_words])


def create_or_get_conversation_group(
    user,
    category_id: int,
    llm: LLM,
    prompt_text: str,
    group_id: int = None,
    chatbot: bool = False
) -> Optional[int]:
    """
    Create or retrieve a conversation group for chatbot mode.

    Args:
        user: CustomUser instance
        category_id: Category ID
        llm: LLM instance
        prompt_text: Prompt text for naming
        group_id: Existing group ID (optional)
        chatbot: Whether chatbot mode is enabled

    Returns:
        Group ID or None
    """
    if not chatbot:
        return group_id

    if group_id:
        return group_id

    if not prompt_text:
        return None

    group_name = get_group_name(prompt_text)
    group = GroupResponse.objects.create(
        user_id=user.id,
        category_id=category_id,
        llm_id=llm.id,
        group_name=group_name,
    )

    return group.id


def create_streaming_response(generator: Generator) -> StreamingHttpResponse:
    """
    Create a StreamingHttpResponse for SSE.

    Args:
        generator: Generator yielding SSE data

    Returns:
        StreamingHttpResponse configured for SSE
    """
    response = StreamingHttpResponse(generator)
    response['Content-Type'] = 'text/event-stream'
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    return response


def upload_to_s3(file_data: BytesIO, key: str, content_type: str) -> str:
    """
    Upload file to S3.

    Args:
        file_data: File data as BytesIO
        key: S3 object key
        content_type: MIME type

    Returns:
        S3 object key
    """
    uploadImage(file_data, key, content_type)
    return key


def validate_file_extension(filename: str, allowed_extensions: list) -> Tuple[bool, str]:
    """
    Validate file extension.

    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions

    Returns:
        Tuple of (is_valid, extension)
    """
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    return extension in allowed_extensions, extension


# =============================================================================
# BASE SERVICE CLASS
# =============================================================================

class BaseLLMService(ABC):
    """
    Abstract base class for LLM service implementations.

    Each provider (Together, Gemini, OpenAI) should inherit from this
    class and implement the required methods.
    """

    provider: LLMProvider = None

    def __init__(self, llm: LLM, user):
        """
        Initialize the service.

        Args:
            llm: LLM model instance
            user: CustomUser instance
        """
        self.llm = llm
        self.user = user
        self.model_string = llm.model_string

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        category_id: int,
        prompt_writer: bool = False,
        group_id: int = None
    ) -> Generator:
        """Generate text from prompt. Must be implemented by subclasses."""
        pass

    def supports_capability(self, capability: str) -> bool:
        """
        Check if the LLM supports a specific capability.

        Args:
            capability: Capability name (text, code, image_to_text, etc.)

        Returns:
            True if supported
        """
        return getattr(self.llm, capability, False)

    def get_api_key(self) -> str:
        """Get the API key for this provider."""
        return self.llm.api_key

    def log_generation(self, operation: str, success: bool = True, error: str = None):
        """Log generation operation."""
        if success:
            logger.info(
                f"LLM Generation: provider={self.provider.name}, "
                f"model={self.llm.name}, operation={operation}, user={self.user.id}"
            )
        else:
            logger.error(
                f"LLM Generation Failed: provider={self.provider.name}, "
                f"model={self.llm.name}, operation={operation}, user={self.user.id}, "
                f"error={error}"
            )
