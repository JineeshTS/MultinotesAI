"""
Response Variations Generator for MultinotesAI.

This module provides:
- Generate multiple variations of AI responses
- Different tones, styles, and lengths
- A/B testing response quality
- Best variation selection

WBS Item: 6.1.7 - Response variations generator
"""

import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Variation Configuration
# =============================================================================

class VariationType(Enum):
    """Types of response variations."""
    TONE = 'tone'
    LENGTH = 'length'
    STYLE = 'style'
    FORMALITY = 'formality'
    CREATIVITY = 'creativity'
    PERSPECTIVE = 'perspective'
    CUSTOM = 'custom'


class ToneVariant(Enum):
    """Tone variations."""
    PROFESSIONAL = 'professional'
    CASUAL = 'casual'
    FRIENDLY = 'friendly'
    FORMAL = 'formal'
    ENTHUSIASTIC = 'enthusiastic'
    EMPATHETIC = 'empathetic'
    AUTHORITATIVE = 'authoritative'
    HUMOROUS = 'humorous'


class LengthVariant(Enum):
    """Length variations."""
    CONCISE = 'concise'
    STANDARD = 'standard'
    DETAILED = 'detailed'
    COMPREHENSIVE = 'comprehensive'


class StyleVariant(Enum):
    """Style variations."""
    NARRATIVE = 'narrative'
    BULLET_POINTS = 'bullet_points'
    STEP_BY_STEP = 'step_by_step'
    FAQ = 'faq'
    CONVERSATIONAL = 'conversational'
    TECHNICAL = 'technical'
    EDUCATIONAL = 'educational'


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class VariationConfig:
    """Configuration for generating a variation."""
    variation_type: VariationType
    variant_value: str
    system_modifier: str = ''
    temperature_modifier: float = 0.0
    max_tokens_modifier: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'variation_type': self.variation_type.value,
            'variant_value': self.variant_value,
        }


@dataclass
class ResponseVariation:
    """A single response variation."""
    variation_id: str
    config: VariationConfig
    response_text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0
    quality_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'variation_id': self.variation_id,
            'variation_type': self.config.variation_type.value,
            'variant_value': self.config.variant_value,
            'response_text': self.response_text,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'latency_ms': round(self.latency_ms, 2),
            'cost': round(self.cost, 6),
            'quality_score': self.quality_score,
            'word_count': len(self.response_text.split()),
            'char_count': len(self.response_text),
        }


@dataclass
class VariationResult:
    """Result of generating variations."""
    request_id: str
    prompt: str
    variations: List[ResponseVariation]
    total_latency_ms: float
    total_cost: float
    best_variation_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'request_id': self.request_id,
            'prompt': self.prompt[:200] + '...' if len(self.prompt) > 200 else self.prompt,
            'variation_count': len(self.variations),
            'variations': [v.to_dict() for v in self.variations],
            'total_latency_ms': round(self.total_latency_ms, 2),
            'total_cost': round(self.total_cost, 6),
            'best_variation_id': self.best_variation_id,
            'created_at': self.created_at.isoformat(),
        }


# =============================================================================
# Variation Modifiers
# =============================================================================

TONE_MODIFIERS = {
    ToneVariant.PROFESSIONAL: "Respond in a professional and business-like tone.",
    ToneVariant.CASUAL: "Respond in a casual and relaxed tone.",
    ToneVariant.FRIENDLY: "Respond in a warm and friendly tone.",
    ToneVariant.FORMAL: "Respond in a formal and structured tone.",
    ToneVariant.ENTHUSIASTIC: "Respond with enthusiasm and energy.",
    ToneVariant.EMPATHETIC: "Respond with empathy and understanding.",
    ToneVariant.AUTHORITATIVE: "Respond with authority and expertise.",
    ToneVariant.HUMOROUS: "Respond with appropriate humor when suitable.",
}

LENGTH_MODIFIERS = {
    LengthVariant.CONCISE: ("Keep your response brief and to the point. Maximum 2-3 sentences.", -500),
    LengthVariant.STANDARD: ("Provide a standard-length response.", 0),
    LengthVariant.DETAILED: ("Provide a detailed response with examples.", 500),
    LengthVariant.COMPREHENSIVE: ("Provide a comprehensive response covering all aspects.", 1000),
}

STYLE_MODIFIERS = {
    StyleVariant.NARRATIVE: "Write in a narrative, story-like format.",
    StyleVariant.BULLET_POINTS: "Use bullet points to organize your response.",
    StyleVariant.STEP_BY_STEP: "Provide a step-by-step guide format.",
    StyleVariant.FAQ: "Format your response as FAQ-style Q&A.",
    StyleVariant.CONVERSATIONAL: "Write in a conversational, dialogue-like manner.",
    StyleVariant.TECHNICAL: "Use technical language and include specific details.",
    StyleVariant.EDUCATIONAL: "Write in an educational, teaching-focused manner.",
}


# =============================================================================
# Response Variations Service
# =============================================================================

class ResponseVariationsService:
    """
    Service for generating response variations.

    Usage:
        service = ResponseVariationsService()
        result = service.generate_variations(
            prompt="Explain machine learning",
            variation_type=VariationType.TONE,
            variants=[ToneVariant.PROFESSIONAL, ToneVariant.CASUAL]
        )
    """

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self._executor = None

    @property
    def executor(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self._executor

    # -------------------------------------------------------------------------
    # Variation Generation
    # -------------------------------------------------------------------------

    def generate_variations(
        self,
        prompt: str,
        variation_type: VariationType,
        variants: List[Any],
        model: str = 'gpt-3.5-turbo',
        base_system_prompt: Optional[str] = None,
        base_temperature: float = 0.7,
        base_max_tokens: int = 1000,
        parallel: bool = True,
    ) -> VariationResult:
        """
        Generate multiple variations of a response.

        Args:
            prompt: The user prompt
            variation_type: Type of variation to generate
            variants: List of variant values
            model: LLM model to use
            base_system_prompt: Base system prompt
            base_temperature: Base temperature
            base_max_tokens: Base max tokens
            parallel: Run generations in parallel

        Returns:
            VariationResult with all variations
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Build variation configs
        configs = []
        for variant in variants:
            config = self._build_config(variation_type, variant)
            configs.append(config)

        # Generate variations
        if parallel:
            variations = self._generate_parallel(
                prompt, configs, model, base_system_prompt,
                base_temperature, base_max_tokens
            )
        else:
            variations = self._generate_sequential(
                prompt, configs, model, base_system_prompt,
                base_temperature, base_max_tokens
            )

        total_latency = (time.time() - start_time) * 1000
        total_cost = sum(v.cost for v in variations)

        # Score and find best variation
        self._score_variations(variations)
        best_id = self._find_best_variation(variations)

        return VariationResult(
            request_id=request_id,
            prompt=prompt,
            variations=variations,
            total_latency_ms=total_latency,
            total_cost=total_cost,
            best_variation_id=best_id,
        )

    def _build_config(
        self,
        variation_type: VariationType,
        variant: Any,
    ) -> VariationConfig:
        """Build variation configuration."""
        if variation_type == VariationType.TONE:
            if isinstance(variant, ToneVariant):
                modifier = TONE_MODIFIERS.get(variant, '')
                return VariationConfig(
                    variation_type=variation_type,
                    variant_value=variant.value,
                    system_modifier=modifier,
                )
            else:
                return VariationConfig(
                    variation_type=variation_type,
                    variant_value=str(variant),
                    system_modifier=f"Respond in a {variant} tone.",
                )

        elif variation_type == VariationType.LENGTH:
            if isinstance(variant, LengthVariant):
                modifier, tokens_mod = LENGTH_MODIFIERS.get(variant, ('', 0))
                return VariationConfig(
                    variation_type=variation_type,
                    variant_value=variant.value,
                    system_modifier=modifier,
                    max_tokens_modifier=tokens_mod,
                )
            else:
                return VariationConfig(
                    variation_type=variation_type,
                    variant_value=str(variant),
                    system_modifier=f"Provide a {variant} response.",
                )

        elif variation_type == VariationType.STYLE:
            if isinstance(variant, StyleVariant):
                modifier = STYLE_MODIFIERS.get(variant, '')
                return VariationConfig(
                    variation_type=variation_type,
                    variant_value=variant.value,
                    system_modifier=modifier,
                )
            else:
                return VariationConfig(
                    variation_type=variation_type,
                    variant_value=str(variant),
                    system_modifier=f"Write in a {variant} style.",
                )

        elif variation_type == VariationType.CREATIVITY:
            temp_mod = float(variant) if isinstance(variant, (int, float)) else 0.0
            return VariationConfig(
                variation_type=variation_type,
                variant_value=str(variant),
                temperature_modifier=temp_mod,
            )

        elif variation_type == VariationType.CUSTOM:
            return VariationConfig(
                variation_type=variation_type,
                variant_value=str(variant),
                system_modifier=str(variant),
            )

        return VariationConfig(
            variation_type=variation_type,
            variant_value=str(variant),
        )

    def _generate_parallel(
        self,
        prompt: str,
        configs: List[VariationConfig],
        model: str,
        base_system_prompt: Optional[str],
        base_temperature: float,
        base_max_tokens: int,
    ) -> List[ResponseVariation]:
        """Generate variations in parallel."""
        variations = []
        futures = {}

        for config in configs:
            future = self.executor.submit(
                self._generate_single,
                prompt, config, model, base_system_prompt,
                base_temperature, base_max_tokens
            )
            futures[future] = config

        for future in as_completed(futures):
            try:
                variation = future.result(timeout=120)
                variations.append(variation)
            except Exception as e:
                config = futures[future]
                logger.error(f"Variation generation failed: {e}")
                variations.append(ResponseVariation(
                    variation_id=str(uuid.uuid4()),
                    config=config,
                    response_text='',
                    metadata={'error': str(e)},
                ))

        return variations

    def _generate_sequential(
        self,
        prompt: str,
        configs: List[VariationConfig],
        model: str,
        base_system_prompt: Optional[str],
        base_temperature: float,
        base_max_tokens: int,
    ) -> List[ResponseVariation]:
        """Generate variations sequentially."""
        variations = []

        for config in configs:
            try:
                variation = self._generate_single(
                    prompt, config, model, base_system_prompt,
                    base_temperature, base_max_tokens
                )
                variations.append(variation)
            except Exception as e:
                logger.error(f"Variation generation failed: {e}")
                variations.append(ResponseVariation(
                    variation_id=str(uuid.uuid4()),
                    config=config,
                    response_text='',
                    metadata={'error': str(e)},
                ))

        return variations

    def _generate_single(
        self,
        prompt: str,
        config: VariationConfig,
        model: str,
        base_system_prompt: Optional[str],
        base_temperature: float,
        base_max_tokens: int,
    ) -> ResponseVariation:
        """Generate a single variation."""
        from coreapp.services.llm_service import llm_service

        start_time = time.time()

        # Build system prompt
        system_parts = []
        if base_system_prompt:
            system_parts.append(base_system_prompt)
        if config.system_modifier:
            system_parts.append(config.system_modifier)
        system_prompt = '\n\n'.join(system_parts) if system_parts else None

        # Adjust parameters
        temperature = min(1.0, max(0.0, base_temperature + config.temperature_modifier))
        max_tokens = max(100, base_max_tokens + config.max_tokens_modifier)

        try:
            response = llm_service.generate(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
            )

            latency_ms = (time.time() - start_time) * 1000

            return ResponseVariation(
                variation_id=str(uuid.uuid4()),
                config=config,
                response_text=response.get('text', ''),
                input_tokens=response.get('input_tokens', 0),
                output_tokens=response.get('output_tokens', 0),
                latency_ms=latency_ms,
                cost=response.get('cost', 0.0),
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            raise

    # -------------------------------------------------------------------------
    # Quality Scoring
    # -------------------------------------------------------------------------

    def _score_variations(self, variations: List[ResponseVariation]):
        """Score variations based on quality heuristics."""
        for variation in variations:
            if not variation.response_text:
                variation.quality_score = 0.0
                continue

            score = 0.0

            # Length score (prefer medium length)
            word_count = len(variation.response_text.split())
            if 50 <= word_count <= 300:
                score += 0.3
            elif 20 <= word_count <= 500:
                score += 0.2
            else:
                score += 0.1

            # Completeness (ends with sentence-ending punctuation)
            if variation.response_text.strip().endswith(('.', '!', '?')):
                score += 0.2

            # Structure (has paragraphs or bullet points)
            if '\n\n' in variation.response_text or '\n- ' in variation.response_text:
                score += 0.2

            # Engagement (questions, examples)
            text_lower = variation.response_text.lower()
            if '?' in variation.response_text:
                score += 0.1
            if 'example' in text_lower or 'for instance' in text_lower:
                score += 0.1

            # Penalize very short responses
            if word_count < 10:
                score *= 0.5

            variation.quality_score = min(1.0, score)

    def _find_best_variation(
        self,
        variations: List[ResponseVariation],
    ) -> Optional[str]:
        """Find the best variation based on quality score."""
        valid = [v for v in variations if v.quality_score is not None and v.response_text]
        if not valid:
            return None

        best = max(valid, key=lambda v: v.quality_score)
        return best.variation_id

    # -------------------------------------------------------------------------
    # Preset Variations
    # -------------------------------------------------------------------------

    def generate_tone_variations(
        self,
        prompt: str,
        tones: List[ToneVariant] = None,
        model: str = 'gpt-3.5-turbo',
        **kwargs,
    ) -> VariationResult:
        """Generate tone variations."""
        if tones is None:
            tones = [ToneVariant.PROFESSIONAL, ToneVariant.CASUAL, ToneVariant.FRIENDLY]

        return self.generate_variations(
            prompt=prompt,
            variation_type=VariationType.TONE,
            variants=tones,
            model=model,
            **kwargs,
        )

    def generate_length_variations(
        self,
        prompt: str,
        lengths: List[LengthVariant] = None,
        model: str = 'gpt-3.5-turbo',
        **kwargs,
    ) -> VariationResult:
        """Generate length variations."""
        if lengths is None:
            lengths = [LengthVariant.CONCISE, LengthVariant.STANDARD, LengthVariant.DETAILED]

        return self.generate_variations(
            prompt=prompt,
            variation_type=VariationType.LENGTH,
            variants=lengths,
            model=model,
            **kwargs,
        )

    def generate_style_variations(
        self,
        prompt: str,
        styles: List[StyleVariant] = None,
        model: str = 'gpt-3.5-turbo',
        **kwargs,
    ) -> VariationResult:
        """Generate style variations."""
        if styles is None:
            styles = [StyleVariant.NARRATIVE, StyleVariant.BULLET_POINTS, StyleVariant.STEP_BY_STEP]

        return self.generate_variations(
            prompt=prompt,
            variation_type=VariationType.STYLE,
            variants=styles,
            model=model,
            **kwargs,
        )

    def generate_creativity_variations(
        self,
        prompt: str,
        temperatures: List[float] = None,
        model: str = 'gpt-3.5-turbo',
        **kwargs,
    ) -> VariationResult:
        """Generate creativity variations using different temperatures."""
        if temperatures is None:
            temperatures = [0.3, 0.7, 1.0]

        return self.generate_variations(
            prompt=prompt,
            variation_type=VariationType.CREATIVITY,
            variants=temperatures,
            model=model,
            base_temperature=0.0,
            **kwargs,
        )

    def generate_all_variations(
        self,
        prompt: str,
        model: str = 'gpt-3.5-turbo',
        **kwargs,
    ) -> Dict[str, VariationResult]:
        """Generate all types of variations."""
        results = {}

        results['tone'] = self.generate_tone_variations(prompt, model=model, **kwargs)
        results['length'] = self.generate_length_variations(prompt, model=model, **kwargs)
        results['style'] = self.generate_style_variations(prompt, model=model, **kwargs)

        return results

    # -------------------------------------------------------------------------
    # A/B Testing Support
    # -------------------------------------------------------------------------

    def ab_test_variations(
        self,
        prompt: str,
        variation_a: VariationConfig,
        variation_b: VariationConfig,
        model: str = 'gpt-3.5-turbo',
        iterations: int = 3,
    ) -> Dict[str, Any]:
        """Run A/B test between two variations."""
        results_a = []
        results_b = []

        for _ in range(iterations):
            var_a = self._generate_single(prompt, variation_a, model, None, 0.7, 1000)
            var_b = self._generate_single(prompt, variation_b, model, None, 0.7, 1000)
            results_a.append(var_a)
            results_b.append(var_b)

        # Calculate averages
        avg_score_a = sum(v.quality_score or 0 for v in results_a) / len(results_a)
        avg_score_b = sum(v.quality_score or 0 for v in results_b) / len(results_b)
        avg_latency_a = sum(v.latency_ms for v in results_a) / len(results_a)
        avg_latency_b = sum(v.latency_ms for v in results_b) / len(results_b)
        avg_cost_a = sum(v.cost for v in results_a) / len(results_a)
        avg_cost_b = sum(v.cost for v in results_b) / len(results_b)

        winner = 'A' if avg_score_a >= avg_score_b else 'B'

        return {
            'variation_a': {
                'config': variation_a.to_dict(),
                'avg_quality_score': round(avg_score_a, 3),
                'avg_latency_ms': round(avg_latency_a, 2),
                'avg_cost': round(avg_cost_a, 6),
                'iterations': iterations,
            },
            'variation_b': {
                'config': variation_b.to_dict(),
                'avg_quality_score': round(avg_score_b, 3),
                'avg_latency_ms': round(avg_latency_b, 2),
                'avg_cost': round(avg_cost_b, 6),
                'iterations': iterations,
            },
            'winner': winner,
            'score_difference': round(abs(avg_score_a - avg_score_b), 3),
        }


# =============================================================================
# Singleton Instance
# =============================================================================

response_variations_service = ResponseVariationsService()
