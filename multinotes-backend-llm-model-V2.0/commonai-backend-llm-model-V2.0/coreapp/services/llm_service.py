"""
LLM Service for MultinotesAI.

This module provides a unified interface for interacting with multiple LLM providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- Together AI
"""

import logging
from typing import Optional, Dict, Any, Generator, List
from abc import ABC, abstractmethod

from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# LLM Provider Interface
# =============================================================================

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_name: str = "base"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Generator[str, None, None]:
        """Generate a streaming response from the LLM."""
        pass

    def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Simple estimation: ~4 characters per token
        return len(text) // 4


# =============================================================================
# OpenAI Provider
# =============================================================================

class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    provider_name = "openai"
    DEFAULT_MODEL = "gpt-4"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', '')
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("OpenAI package not installed. Run: pip install openai")
        return self._client

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a response using OpenAI."""
        model = model or self.DEFAULT_MODEL
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            return {
                'content': response.choices[0].message.content,
                'model': response.model,
                'tokens': {
                    'prompt': response.usage.prompt_tokens,
                    'completion': response.usage.completion_tokens,
                    'total': response.usage.total_tokens,
                },
                'finish_reason': response.choices[0].finish_reason,
            }
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Generator[str, None, None]:
        """Generate a streaming response using OpenAI."""
        model = model or self.DEFAULT_MODEL
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise


# =============================================================================
# Anthropic Provider
# =============================================================================

class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider."""

    provider_name = "anthropic"
    DEFAULT_MODEL = "claude-3-sonnet-20240229"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'ANTHROPIC_API_KEY', '')
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("Anthropic package not installed. Run: pip install anthropic")
        return self._client

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a response using Anthropic Claude."""
        model = model or self.DEFAULT_MODEL

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt if system_prompt else None,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )

            return {
                'content': response.content[0].text,
                'model': response.model,
                'tokens': {
                    'prompt': response.usage.input_tokens,
                    'completion': response.usage.output_tokens,
                    'total': response.usage.input_tokens + response.usage.output_tokens,
                },
                'finish_reason': response.stop_reason,
            }
        except Exception as e:
            logger.error(f"Anthropic generation error: {e}")
            raise

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Generator[str, None, None]:
        """Generate a streaming response using Anthropic Claude."""
        model = model or self.DEFAULT_MODEL

        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt if system_prompt else None,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise


# =============================================================================
# Google Gemini Provider
# =============================================================================

class GoogleProvider(LLMProvider):
    """Google Gemini LLM provider."""

    provider_name = "google"
    DEFAULT_MODEL = "gemini-pro"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'GOOGLE_API_KEY', '')
        self._model = None

    def _get_model(self, model_name: str):
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            return genai.GenerativeModel(model_name)
        except ImportError:
            raise ImportError("Google GenerativeAI package not installed. Run: pip install google-generativeai")

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a response using Google Gemini."""
        model_name = model or self.DEFAULT_MODEL
        genai_model = self._get_model(model_name)

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        try:
            response = genai_model.generate_content(
                full_prompt,
                generation_config={
                    'max_output_tokens': max_tokens,
                    'temperature': temperature,
                }
            )

            return {
                'content': response.text,
                'model': model_name,
                'tokens': {
                    'prompt': self.count_tokens(full_prompt),
                    'completion': self.count_tokens(response.text),
                    'total': self.count_tokens(full_prompt) + self.count_tokens(response.text),
                },
                'finish_reason': 'stop',
            }
        except Exception as e:
            logger.error(f"Google generation error: {e}")
            raise

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Generator[str, None, None]:
        """Generate a streaming response using Google Gemini."""
        model_name = model or self.DEFAULT_MODEL
        genai_model = self._get_model(model_name)

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        try:
            response = genai_model.generate_content(
                full_prompt,
                generation_config={
                    'max_output_tokens': max_tokens,
                    'temperature': temperature,
                },
                stream=True
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Google streaming error: {e}")
            raise


# =============================================================================
# LLM Service
# =============================================================================

class LLMService:
    """
    Unified LLM service for the application.

    Usage:
        service = LLMService()
        response = service.generate(
            prompt="Write a poem",
            provider="openai",
            model="gpt-4"
        )
    """

    PROVIDERS = {
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'google': GoogleProvider,
    }

    def __init__(self):
        self._providers = {}

    def get_provider(self, provider_name: str) -> LLMProvider:
        """Get or create a provider instance."""
        if provider_name not in self._providers:
            provider_class = self.PROVIDERS.get(provider_name)
            if not provider_class:
                raise ValueError(f"Unknown provider: {provider_name}")
            self._providers[provider_name] = provider_class()
        return self._providers[provider_name]

    def generate(
        self,
        prompt: str,
        provider: str = "openai",
        model: str = None,
        system_prompt: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response from the specified provider.

        Args:
            prompt: User prompt
            provider: Provider name (openai, anthropic, google)
            model: Model name (provider-specific)
            system_prompt: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Dict with response content and metadata
        """
        llm_provider = self.get_provider(provider)
        return llm_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

    def generate_stream(
        self,
        prompt: str,
        provider: str = "openai",
        model: str = None,
        system_prompt: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response from the specified provider.

        Args:
            Same as generate()

        Yields:
            Response text chunks
        """
        llm_provider = self.get_provider(provider)
        return llm_provider.generate_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

    def get_available_models(self, provider: str = None) -> Dict[str, List[str]]:
        """Get available models for providers."""
        models = {
            'openai': ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
            'anthropic': ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
            'google': ['gemini-pro', 'gemini-pro-vision'],
        }
        if provider:
            return {provider: models.get(provider, [])}
        return models


# =============================================================================
# Singleton Instance
# =============================================================================

llm_service = LLMService()
