"""
AI Services Package for MultinotesAI.

This package provides modular AI generation services for different providers:
- Together AI
- Google Gemini
- OpenAI

Each service handles specific AI capabilities like text generation,
image generation, speech synthesis, and transcription.
"""

from .base import (
    BaseLLMService,
    LLMProvider,
    ResponseType,
    get_llm_instance,
    manage_token_usage,
    manage_file_token_usage,
    create_prompt_record,
    create_response_record,
    create_token_record,
    get_group_name,
    create_streaming_response,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_AUDIO_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
)

__all__ = [
    'BaseLLMService',
    'LLMProvider',
    'ResponseType',
    'get_llm_instance',
    'manage_token_usage',
    'manage_file_token_usage',
    'create_prompt_record',
    'create_response_record',
    'create_token_record',
    'get_group_name',
    'create_streaming_response',
    'SUPPORTED_IMAGE_EXTENSIONS',
    'SUPPORTED_AUDIO_EXTENSIONS',
    'SUPPORTED_VIDEO_EXTENSIONS',
]
