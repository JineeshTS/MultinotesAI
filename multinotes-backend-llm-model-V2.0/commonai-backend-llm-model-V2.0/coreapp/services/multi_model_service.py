"""
Multi-Model Comparison Service for MultinotesAI.

This module provides:
- Running prompts across multiple AI models simultaneously
- Comparing responses from different models
- Performance and cost analysis across models
- Model recommendation based on task type

WBS Item: 6.1.1 - Multi-model comparison (run same prompt on 3 models)
"""

import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Model Configuration
# =============================================================================

class ModelProvider(Enum):
    """Supported AI model providers."""
    OPENAI = 'openai'
    ANTHROPIC = 'anthropic'
    GOOGLE = 'google'
    COHERE = 'cohere'
    MISTRAL = 'mistral'


@dataclass
class ModelConfig:
    """Configuration for an AI model."""
    model_id: str
    provider: ModelProvider
    display_name: str
    max_tokens: int = 4096
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    supports_streaming: bool = True
    supports_functions: bool = False
    context_window: int = 8192
    is_available: bool = True


# Available models for comparison
AVAILABLE_MODELS: Dict[str, ModelConfig] = {
    # OpenAI models
    'gpt-4': ModelConfig(
        model_id='gpt-4',
        provider=ModelProvider.OPENAI,
        display_name='GPT-4',
        max_tokens=8192,
        input_cost_per_1k=0.03,
        output_cost_per_1k=0.06,
        supports_functions=True,
        context_window=8192,
    ),
    'gpt-4-turbo': ModelConfig(
        model_id='gpt-4-turbo-preview',
        provider=ModelProvider.OPENAI,
        display_name='GPT-4 Turbo',
        max_tokens=4096,
        input_cost_per_1k=0.01,
        output_cost_per_1k=0.03,
        supports_functions=True,
        context_window=128000,
    ),
    'gpt-3.5-turbo': ModelConfig(
        model_id='gpt-3.5-turbo',
        provider=ModelProvider.OPENAI,
        display_name='GPT-3.5 Turbo',
        max_tokens=4096,
        input_cost_per_1k=0.0005,
        output_cost_per_1k=0.0015,
        supports_functions=True,
        context_window=16385,
    ),
    # Anthropic models
    'claude-3-opus': ModelConfig(
        model_id='claude-3-opus-20240229',
        provider=ModelProvider.ANTHROPIC,
        display_name='Claude 3 Opus',
        max_tokens=4096,
        input_cost_per_1k=0.015,
        output_cost_per_1k=0.075,
        context_window=200000,
    ),
    'claude-3-sonnet': ModelConfig(
        model_id='claude-3-sonnet-20240229',
        provider=ModelProvider.ANTHROPIC,
        display_name='Claude 3 Sonnet',
        max_tokens=4096,
        input_cost_per_1k=0.003,
        output_cost_per_1k=0.015,
        context_window=200000,
    ),
    'claude-3-haiku': ModelConfig(
        model_id='claude-3-haiku-20240307',
        provider=ModelProvider.ANTHROPIC,
        display_name='Claude 3 Haiku',
        max_tokens=4096,
        input_cost_per_1k=0.00025,
        output_cost_per_1k=0.00125,
        context_window=200000,
    ),
    # Google models
    'gemini-pro': ModelConfig(
        model_id='gemini-pro',
        provider=ModelProvider.GOOGLE,
        display_name='Gemini Pro',
        max_tokens=8192,
        input_cost_per_1k=0.0005,
        output_cost_per_1k=0.0015,
        context_window=32768,
    ),
    'gemini-1.5-pro': ModelConfig(
        model_id='gemini-1.5-pro',
        provider=ModelProvider.GOOGLE,
        display_name='Gemini 1.5 Pro',
        max_tokens=8192,
        input_cost_per_1k=0.00125,
        output_cost_per_1k=0.005,
        context_window=1000000,
    ),
    # Mistral models
    'mistral-large': ModelConfig(
        model_id='mistral-large-latest',
        provider=ModelProvider.MISTRAL,
        display_name='Mistral Large',
        max_tokens=4096,
        input_cost_per_1k=0.008,
        output_cost_per_1k=0.024,
        context_window=32768,
    ),
    'mistral-medium': ModelConfig(
        model_id='mistral-medium-latest',
        provider=ModelProvider.MISTRAL,
        display_name='Mistral Medium',
        max_tokens=4096,
        input_cost_per_1k=0.0027,
        output_cost_per_1k=0.0081,
        context_window=32768,
    ),
}


# =============================================================================
# Response Data Classes
# =============================================================================

@dataclass
class ModelResponse:
    """Response from a single model."""
    model_id: str
    model_name: str
    provider: str
    response_text: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_id': self.model_id,
            'model_name': self.model_name,
            'provider': self.provider,
            'response_text': self.response_text,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'latency_ms': round(self.latency_ms, 2),
            'cost': round(self.cost, 6),
            'success': self.success,
            'error': self.error,
            'metadata': self.metadata,
        }


@dataclass
class ComparisonResult:
    """Result of multi-model comparison."""
    prompt: str
    responses: List[ModelResponse]
    total_latency_ms: float
    total_cost: float
    fastest_model: Optional[str] = None
    cheapest_model: Optional[str] = None
    best_value_model: Optional[str] = None
    comparison_id: str = ''
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'comparison_id': self.comparison_id,
            'prompt': self.prompt[:500] + '...' if len(self.prompt) > 500 else self.prompt,
            'responses': [r.to_dict() for r in self.responses],
            'summary': {
                'total_models': len(self.responses),
                'successful': sum(1 for r in self.responses if r.success),
                'failed': sum(1 for r in self.responses if not r.success),
                'total_latency_ms': round(self.total_latency_ms, 2),
                'total_cost': round(self.total_cost, 6),
                'fastest_model': self.fastest_model,
                'cheapest_model': self.cheapest_model,
                'best_value_model': self.best_value_model,
            },
            'created_at': self.created_at.isoformat(),
        }


# =============================================================================
# Model Adapters
# =============================================================================

class BaseModelAdapter:
    """Base class for model adapters."""

    def __init__(self, config: ModelConfig):
        self.config = config

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> ModelResponse:
        """Generate response from model."""
        raise NotImplementedError


class OpenAIAdapter(BaseModelAdapter):
    """Adapter for OpenAI models."""

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> ModelResponse:
        start_time = time.time()

        try:
            import openai

            client = openai.OpenAI(
                api_key=settings.OPENAI_API_KEY
            )

            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})

            response = client.chat.completions.create(
                model=self.config.model_id,
                messages=messages,
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=temperature,
            )

            latency_ms = (time.time() - start_time) * 1000

            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens

            # Calculate cost
            cost = (
                (input_tokens / 1000) * self.config.input_cost_per_1k +
                (output_tokens / 1000) * self.config.output_cost_per_1k
            )

            return ModelResponse(
                model_id=self.config.model_id,
                model_name=self.config.display_name,
                provider=self.config.provider.value,
                response_text=response.choices[0].message.content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                latency_ms=latency_ms,
                cost=cost,
                success=True,
                metadata={
                    'finish_reason': response.choices[0].finish_reason,
                }
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"OpenAI API error for {self.config.model_id}: {e}")
            return ModelResponse(
                model_id=self.config.model_id,
                model_name=self.config.display_name,
                provider=self.config.provider.value,
                response_text='',
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )


class AnthropicAdapter(BaseModelAdapter):
    """Adapter for Anthropic Claude models."""

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> ModelResponse:
        start_time = time.time()

        try:
            import anthropic

            client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )

            message = client.messages.create(
                model=self.config.model_id,
                max_tokens=max_tokens or self.config.max_tokens,
                system=system_prompt or '',
                messages=[
                    {'role': 'user', 'content': prompt}
                ],
                temperature=temperature,
            )

            latency_ms = (time.time() - start_time) * 1000

            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens

            # Calculate cost
            cost = (
                (input_tokens / 1000) * self.config.input_cost_per_1k +
                (output_tokens / 1000) * self.config.output_cost_per_1k
            )

            response_text = ''
            for block in message.content:
                if block.type == 'text':
                    response_text += block.text

            return ModelResponse(
                model_id=self.config.model_id,
                model_name=self.config.display_name,
                provider=self.config.provider.value,
                response_text=response_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                latency_ms=latency_ms,
                cost=cost,
                success=True,
                metadata={
                    'stop_reason': message.stop_reason,
                }
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Anthropic API error for {self.config.model_id}: {e}")
            return ModelResponse(
                model_id=self.config.model_id,
                model_name=self.config.display_name,
                provider=self.config.provider.value,
                response_text='',
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )


class GoogleAdapter(BaseModelAdapter):
    """Adapter for Google Gemini models."""

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> ModelResponse:
        start_time = time.time()

        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GOOGLE_API_KEY)

            model = genai.GenerativeModel(
                model_name=self.config.model_id,
                system_instruction=system_prompt,
            )

            generation_config = genai.GenerationConfig(
                max_output_tokens=max_tokens or self.config.max_tokens,
                temperature=temperature,
            )

            response = model.generate_content(
                prompt,
                generation_config=generation_config,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Token counting for Gemini
            input_tokens = model.count_tokens(prompt).total_tokens
            output_tokens = model.count_tokens(response.text).total_tokens if response.text else 0

            # Calculate cost
            cost = (
                (input_tokens / 1000) * self.config.input_cost_per_1k +
                (output_tokens / 1000) * self.config.output_cost_per_1k
            )

            return ModelResponse(
                model_id=self.config.model_id,
                model_name=self.config.display_name,
                provider=self.config.provider.value,
                response_text=response.text if response.text else '',
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                latency_ms=latency_ms,
                cost=cost,
                success=True,
                metadata={
                    'safety_ratings': str(response.prompt_feedback) if hasattr(response, 'prompt_feedback') else None,
                }
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Google API error for {self.config.model_id}: {e}")
            return ModelResponse(
                model_id=self.config.model_id,
                model_name=self.config.display_name,
                provider=self.config.provider.value,
                response_text='',
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )


class MistralAdapter(BaseModelAdapter):
    """Adapter for Mistral models."""

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> ModelResponse:
        start_time = time.time()

        try:
            from mistralai.client import MistralClient
            from mistralai.models.chat_completion import ChatMessage

            client = MistralClient(
                api_key=settings.MISTRAL_API_KEY
            )

            messages = []
            if system_prompt:
                messages.append(ChatMessage(role='system', content=system_prompt))
            messages.append(ChatMessage(role='user', content=prompt))

            response = client.chat(
                model=self.config.model_id,
                messages=messages,
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=temperature,
            )

            latency_ms = (time.time() - start_time) * 1000

            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens

            # Calculate cost
            cost = (
                (input_tokens / 1000) * self.config.input_cost_per_1k +
                (output_tokens / 1000) * self.config.output_cost_per_1k
            )

            return ModelResponse(
                model_id=self.config.model_id,
                model_name=self.config.display_name,
                provider=self.config.provider.value,
                response_text=response.choices[0].message.content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                latency_ms=latency_ms,
                cost=cost,
                success=True,
                metadata={
                    'finish_reason': response.choices[0].finish_reason,
                }
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Mistral API error for {self.config.model_id}: {e}")
            return ModelResponse(
                model_id=self.config.model_id,
                model_name=self.config.display_name,
                provider=self.config.provider.value,
                response_text='',
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )


# =============================================================================
# Multi-Model Comparison Service
# =============================================================================

class MultiModelService:
    """
    Service for running prompts across multiple AI models.

    Usage:
        service = MultiModelService()
        result = service.compare(
            prompt="Explain quantum computing",
            models=['gpt-4', 'claude-3-sonnet', 'gemini-pro']
        )
    """

    # Adapter mapping
    ADAPTERS = {
        ModelProvider.OPENAI: OpenAIAdapter,
        ModelProvider.ANTHROPIC: AnthropicAdapter,
        ModelProvider.GOOGLE: GoogleAdapter,
        ModelProvider.MISTRAL: MistralAdapter,
    }

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self._executor = None

    @property
    def executor(self):
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self._executor

    # -------------------------------------------------------------------------
    # Model Information
    # -------------------------------------------------------------------------

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models for comparison."""
        return [
            {
                'id': model_id,
                'name': config.display_name,
                'provider': config.provider.value,
                'max_tokens': config.max_tokens,
                'context_window': config.context_window,
                'input_cost_per_1k': config.input_cost_per_1k,
                'output_cost_per_1k': config.output_cost_per_1k,
                'supports_streaming': config.supports_streaming,
                'supports_functions': config.supports_functions,
                'is_available': config.is_available,
            }
            for model_id, config in AVAILABLE_MODELS.items()
            if config.is_available
        ]

    def get_model_by_task(self, task_type: str) -> List[str]:
        """Get recommended models for a task type."""
        task_recommendations = {
            'creative_writing': ['gpt-4', 'claude-3-opus', 'gemini-1.5-pro'],
            'code_generation': ['gpt-4-turbo', 'claude-3-opus', 'mistral-large'],
            'summarization': ['gpt-3.5-turbo', 'claude-3-haiku', 'gemini-pro'],
            'analysis': ['gpt-4', 'claude-3-sonnet', 'gemini-1.5-pro'],
            'translation': ['gpt-4', 'claude-3-sonnet', 'mistral-large'],
            'chat': ['gpt-3.5-turbo', 'claude-3-haiku', 'gemini-pro'],
            'reasoning': ['gpt-4', 'claude-3-opus', 'gemini-1.5-pro'],
        }

        return task_recommendations.get(task_type, ['gpt-4', 'claude-3-sonnet', 'gemini-pro'])

    # -------------------------------------------------------------------------
    # Comparison Methods
    # -------------------------------------------------------------------------

    def compare(
        self,
        prompt: str,
        models: List[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        parallel: bool = True,
    ) -> ComparisonResult:
        """
        Run prompt on multiple models and compare results.

        Args:
            prompt: The prompt to send to all models
            models: List of model IDs to use (default: gpt-4, claude-3-sonnet, gemini-pro)
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens for response
            temperature: Temperature for generation
            parallel: Whether to run models in parallel

        Returns:
            ComparisonResult with all responses
        """
        import uuid

        # Default models
        if not models:
            models = ['gpt-4', 'claude-3-sonnet', 'gemini-pro']

        # Validate models
        valid_models = [m for m in models if m in AVAILABLE_MODELS]
        if not valid_models:
            raise ValueError(f"No valid models provided. Available: {list(AVAILABLE_MODELS.keys())}")

        start_time = time.time()

        # Run comparisons
        if parallel:
            responses = self._run_parallel(
                valid_models, prompt, system_prompt, max_tokens, temperature
            )
        else:
            responses = self._run_sequential(
                valid_models, prompt, system_prompt, max_tokens, temperature
            )

        total_latency = (time.time() - start_time) * 1000
        total_cost = sum(r.cost for r in responses)

        # Analyze results
        successful_responses = [r for r in responses if r.success]

        fastest_model = None
        cheapest_model = None
        best_value_model = None

        if successful_responses:
            # Fastest model
            fastest = min(successful_responses, key=lambda r: r.latency_ms)
            fastest_model = fastest.model_name

            # Cheapest model
            cheapest = min(successful_responses, key=lambda r: r.cost)
            cheapest_model = cheapest.model_name

            # Best value (quality per cost - approximated by tokens per dollar)
            best_value = max(
                successful_responses,
                key=lambda r: r.output_tokens / max(r.cost, 0.0001)
            )
            best_value_model = best_value.model_name

        return ComparisonResult(
            prompt=prompt,
            responses=responses,
            total_latency_ms=total_latency,
            total_cost=total_cost,
            fastest_model=fastest_model,
            cheapest_model=cheapest_model,
            best_value_model=best_value_model,
            comparison_id=str(uuid.uuid4()),
        )

    def _run_parallel(
        self,
        models: List[str],
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: Optional[int],
        temperature: float,
    ) -> List[ModelResponse]:
        """Run models in parallel using thread pool."""
        responses = []
        futures = {}

        for model_id in models:
            config = AVAILABLE_MODELS[model_id]
            adapter_class = self.ADAPTERS.get(config.provider)

            if adapter_class:
                adapter = adapter_class(config)
                future = self.executor.submit(
                    adapter.generate,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                futures[future] = model_id

        for future in as_completed(futures):
            try:
                response = future.result(timeout=120)
                responses.append(response)
            except Exception as e:
                model_id = futures[future]
                config = AVAILABLE_MODELS[model_id]
                responses.append(ModelResponse(
                    model_id=model_id,
                    model_name=config.display_name,
                    provider=config.provider.value,
                    response_text='',
                    success=False,
                    error=f"Timeout or error: {str(e)}",
                ))

        return responses

    def _run_sequential(
        self,
        models: List[str],
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: Optional[int],
        temperature: float,
    ) -> List[ModelResponse]:
        """Run models sequentially."""
        responses = []

        for model_id in models:
            config = AVAILABLE_MODELS[model_id]
            adapter_class = self.ADAPTERS.get(config.provider)

            if adapter_class:
                adapter = adapter_class(config)
                response = adapter.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                responses.append(response)

        return responses

    # -------------------------------------------------------------------------
    # Quick Comparison
    # -------------------------------------------------------------------------

    def quick_compare(
        self,
        prompt: str,
        task_type: str = 'general',
    ) -> ComparisonResult:
        """
        Quick comparison using recommended models for task type.

        Args:
            prompt: The prompt to test
            task_type: Type of task (creative_writing, code_generation, etc.)

        Returns:
            ComparisonResult
        """
        models = self.get_model_by_task(task_type)
        return self.compare(prompt, models=models)

    # -------------------------------------------------------------------------
    # Cost Comparison
    # -------------------------------------------------------------------------

    def estimate_costs(
        self,
        prompt: str,
        models: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Estimate costs for running prompt on different models.

        Args:
            prompt: The prompt to estimate
            models: Models to compare (default: all)

        Returns:
            List of cost estimates sorted by cost
        """
        from coreapp.services.token_service import token_estimator

        if not models:
            models = list(AVAILABLE_MODELS.keys())

        estimates = []
        input_tokens = token_estimator.estimate_tokens(prompt)

        for model_id in models:
            if model_id not in AVAILABLE_MODELS:
                continue

            config = AVAILABLE_MODELS[model_id]

            # Estimate output tokens (approximate)
            output_tokens = token_estimator.estimate_response_tokens(input_tokens)

            input_cost = (input_tokens / 1000) * config.input_cost_per_1k
            output_cost = (output_tokens / 1000) * config.output_cost_per_1k
            total_cost = input_cost + output_cost

            estimates.append({
                'model_id': model_id,
                'model_name': config.display_name,
                'provider': config.provider.value,
                'input_tokens': input_tokens,
                'estimated_output_tokens': output_tokens,
                'input_cost': round(input_cost, 6),
                'output_cost': round(output_cost, 6),
                'total_cost': round(total_cost, 6),
                'currency': 'USD',
            })

        # Sort by total cost
        estimates.sort(key=lambda x: x['total_cost'])

        return estimates

    # -------------------------------------------------------------------------
    # Response Quality Analysis
    # -------------------------------------------------------------------------

    def analyze_responses(
        self,
        result: ComparisonResult,
    ) -> Dict[str, Any]:
        """
        Analyze and compare response quality.

        Args:
            result: ComparisonResult from comparison

        Returns:
            Analysis dict
        """
        successful = [r for r in result.responses if r.success]

        if not successful:
            return {'error': 'No successful responses to analyze'}

        # Basic statistics
        latencies = [r.latency_ms for r in successful]
        costs = [r.cost for r in successful]
        output_lengths = [len(r.response_text) for r in successful]
        token_counts = [r.output_tokens for r in successful]

        analysis = {
            'models_compared': len(result.responses),
            'successful': len(successful),
            'failed': len(result.responses) - len(successful),
            'latency': {
                'min_ms': round(min(latencies), 2),
                'max_ms': round(max(latencies), 2),
                'avg_ms': round(sum(latencies) / len(latencies), 2),
            },
            'cost': {
                'min': round(min(costs), 6),
                'max': round(max(costs), 6),
                'total': round(sum(costs), 6),
            },
            'response_length': {
                'min_chars': min(output_lengths),
                'max_chars': max(output_lengths),
                'avg_chars': round(sum(output_lengths) / len(output_lengths), 0),
            },
            'tokens': {
                'min': min(token_counts),
                'max': max(token_counts),
                'avg': round(sum(token_counts) / len(token_counts), 0),
            },
            'rankings': {
                'fastest': result.fastest_model,
                'cheapest': result.cheapest_model,
                'best_value': result.best_value_model,
            },
        }

        # Response similarity analysis (if multiple responses)
        if len(successful) > 1:
            similarities = self._calculate_similarities(successful)
            analysis['similarity'] = similarities

        return analysis

    def _calculate_similarities(
        self,
        responses: List[ModelResponse],
    ) -> Dict[str, Any]:
        """Calculate response similarities using word overlap."""
        def get_words(text: str) -> set:
            return set(text.lower().split())

        # Calculate pairwise similarities
        similarities = []
        for i, r1 in enumerate(responses):
            for j, r2 in enumerate(responses):
                if i < j:
                    words1 = get_words(r1.response_text)
                    words2 = get_words(r2.response_text)

                    if words1 and words2:
                        intersection = len(words1 & words2)
                        union = len(words1 | words2)
                        jaccard = intersection / union if union > 0 else 0

                        similarities.append({
                            'models': [r1.model_name, r2.model_name],
                            'jaccard_similarity': round(jaccard, 3),
                        })

        # Calculate average similarity
        avg_similarity = 0
        if similarities:
            avg_similarity = sum(s['jaccard_similarity'] for s in similarities) / len(similarities)

        return {
            'pairwise': similarities,
            'average_similarity': round(avg_similarity, 3),
        }


# =============================================================================
# Async Multi-Model Service
# =============================================================================

class AsyncMultiModelService:
    """
    Async version of multi-model service for better performance.
    """

    async def compare(
        self,
        prompt: str,
        models: List[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> ComparisonResult:
        """
        Async version of compare.
        """
        import uuid

        if not models:
            models = ['gpt-4', 'claude-3-sonnet', 'gemini-pro']

        valid_models = [m for m in models if m in AVAILABLE_MODELS]
        if not valid_models:
            raise ValueError("No valid models provided")

        start_time = time.time()

        # Create tasks
        tasks = []
        for model_id in valid_models:
            task = asyncio.create_task(
                self._async_generate(
                    model_id, prompt, system_prompt, max_tokens, temperature
                )
            )
            tasks.append(task)

        # Wait for all tasks
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process responses
        processed_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                model_id = valid_models[i]
                config = AVAILABLE_MODELS[model_id]
                processed_responses.append(ModelResponse(
                    model_id=model_id,
                    model_name=config.display_name,
                    provider=config.provider.value,
                    response_text='',
                    success=False,
                    error=str(response),
                ))
            else:
                processed_responses.append(response)

        total_latency = (time.time() - start_time) * 1000
        total_cost = sum(r.cost for r in processed_responses if r.success)

        successful = [r for r in processed_responses if r.success]
        fastest_model = min(successful, key=lambda r: r.latency_ms).model_name if successful else None
        cheapest_model = min(successful, key=lambda r: r.cost).model_name if successful else None

        return ComparisonResult(
            prompt=prompt,
            responses=processed_responses,
            total_latency_ms=total_latency,
            total_cost=total_cost,
            fastest_model=fastest_model,
            cheapest_model=cheapest_model,
            comparison_id=str(uuid.uuid4()),
        )

    async def _async_generate(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: Optional[int],
        temperature: float,
    ) -> ModelResponse:
        """Run generation in executor for async compatibility."""
        loop = asyncio.get_event_loop()
        config = AVAILABLE_MODELS[model_id]
        adapter_class = MultiModelService.ADAPTERS.get(config.provider)

        if not adapter_class:
            return ModelResponse(
                model_id=model_id,
                model_name=config.display_name,
                provider=config.provider.value,
                response_text='',
                success=False,
                error='No adapter available for provider',
            )

        adapter = adapter_class(config)
        return await loop.run_in_executor(
            None,
            lambda: adapter.generate(prompt, system_prompt, max_tokens, temperature)
        )


# =============================================================================
# Singleton Instances
# =============================================================================

multi_model_service = MultiModelService()
async_multi_model_service = AsyncMultiModelService()
