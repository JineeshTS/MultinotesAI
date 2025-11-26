"""
Prompt Chaining Service for MultinotesAI.

This module provides:
- Sequential prompt execution with context passing
- Conditional branching based on responses
- Variable substitution and templating
- Chain templates for common workflows
- Error handling and retry logic

WBS Item: 6.1.3 - Prompt chaining (multi-step workflows)
"""

import logging
import re
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Union

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Chain Configuration
# =============================================================================

class StepType(Enum):
    """Types of chain steps."""
    PROMPT = 'prompt'
    CONDITIONAL = 'conditional'
    TRANSFORM = 'transform'
    PARALLEL = 'parallel'
    LOOP = 'loop'
    VALIDATOR = 'validator'


class ChainStatus(Enum):
    """Status of chain execution."""
    PENDING = 'pending'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ChainStep:
    """A single step in the prompt chain."""
    name: str
    step_type: StepType
    prompt_template: Optional[str] = None
    model: str = 'gpt-3.5-turbo'
    max_tokens: int = 1000
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    output_variable: str = 'output'
    condition: Optional[str] = None  # For conditional steps
    transform_fn: Optional[Callable] = None  # For transform steps
    parallel_steps: List['ChainStep'] = field(default_factory=list)
    loop_variable: Optional[str] = None  # For loop steps
    loop_items: Optional[List] = None
    validator_fn: Optional[Callable] = None  # For validator steps
    retry_count: int = 3
    timeout_seconds: int = 120
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'step_type': self.step_type.value,
            'prompt_template': self.prompt_template,
            'model': self.model,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'output_variable': self.output_variable,
            'retry_count': self.retry_count,
            'timeout_seconds': self.timeout_seconds,
        }


@dataclass
class StepResult:
    """Result of executing a chain step."""
    step_name: str
    success: bool
    output: Any
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0
    error: Optional[str] = None
    retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'step_name': self.step_name,
            'success': self.success,
            'output': str(self.output)[:1000] if self.output else None,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'latency_ms': round(self.latency_ms, 2),
            'cost': round(self.cost, 6),
            'error': self.error,
            'retries': self.retries,
        }


@dataclass
class ChainResult:
    """Result of executing a complete chain."""
    chain_id: str
    chain_name: str
    status: ChainStatus
    steps_completed: int
    total_steps: int
    step_results: List[StepResult]
    final_output: Any
    total_tokens: int
    total_cost: float
    total_latency_ms: float
    variables: Dict[str, Any]
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'chain_id': self.chain_id,
            'chain_name': self.chain_name,
            'status': self.status.value,
            'steps_completed': self.steps_completed,
            'total_steps': self.total_steps,
            'step_results': [r.to_dict() for r in self.step_results],
            'final_output': str(self.final_output)[:2000] if self.final_output else None,
            'total_tokens': self.total_tokens,
            'total_cost': round(self.total_cost, 6),
            'total_latency_ms': round(self.total_latency_ms, 2),
            'error': self.error,
            'created_at': self.created_at.isoformat(),
        }


# =============================================================================
# Prompt Chain
# =============================================================================

@dataclass
class PromptChain:
    """A complete prompt chain definition."""
    name: str
    description: str
    steps: List[ChainStep]
    initial_variables: Dict[str, Any] = field(default_factory=dict)
    stop_on_error: bool = True
    max_total_tokens: int = 50000
    max_total_cost: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'steps': [s.to_dict() for s in self.steps],
            'stop_on_error': self.stop_on_error,
            'max_total_tokens': self.max_total_tokens,
            'max_total_cost': self.max_total_cost,
        }


# =============================================================================
# Template Engine
# =============================================================================

class TemplateEngine:
    """
    Simple template engine for variable substitution.

    Supports:
    - {{variable}} - Simple substitution
    - {{variable|default:value}} - Default values
    - {{variable|upper}} - Filters
    - {{#if condition}}...{{/if}} - Conditionals
    """

    VARIABLE_PATTERN = re.compile(r'\{\{([^}]+)\}\}')
    CONDITIONAL_PATTERN = re.compile(
        r'\{\{#if\s+([^}]+)\}\}(.*?)\{\{/if\}\}',
        re.DOTALL
    )

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """Render template with variables."""
        if not template:
            return ''

        # Process conditionals first
        result = self._process_conditionals(template, variables)

        # Then process variables
        result = self._process_variables(result, variables)

        return result

    def _process_conditionals(self, template: str, variables: Dict[str, Any]) -> str:
        """Process {{#if}}...{{/if}} blocks."""
        def replace_conditional(match):
            condition = match.group(1).strip()
            content = match.group(2)

            # Evaluate condition
            try:
                # Support simple variable checks
                if condition in variables:
                    if variables[condition]:
                        return content
                    return ''

                # Support comparisons
                if '==' in condition:
                    parts = condition.split('==')
                    left = self._get_value(parts[0].strip(), variables)
                    right = self._get_value(parts[1].strip(), variables)
                    if left == right:
                        return content

                return ''
            except Exception:
                return ''

        return self.CONDITIONAL_PATTERN.sub(replace_conditional, template)

    def _process_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """Process {{variable}} substitutions."""
        def replace_variable(match):
            expression = match.group(1).strip()

            # Check for filters
            if '|' in expression:
                parts = expression.split('|')
                var_name = parts[0].strip()
                filters = parts[1:]
                value = self._get_value(var_name, variables)
                return self._apply_filters(value, filters, variables)

            return str(self._get_value(expression, variables))

        return self.VARIABLE_PATTERN.sub(replace_variable, template)

    def _get_value(self, key: str, variables: Dict[str, Any]) -> Any:
        """Get value from variables, supporting dot notation."""
        # Remove quotes for string literals
        if key.startswith('"') and key.endswith('"'):
            return key[1:-1]
        if key.startswith("'") and key.endswith("'"):
            return key[1:-1]

        # Handle dot notation
        parts = key.split('.')
        value = variables

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, '')
            else:
                return ''

        return value

    def _apply_filters(
        self,
        value: Any,
        filters: List[str],
        variables: Dict[str, Any]
    ) -> str:
        """Apply filters to value."""
        for filter_expr in filters:
            filter_expr = filter_expr.strip()

            # Default filter
            if filter_expr.startswith('default:'):
                if not value:
                    value = filter_expr[8:].strip()
                continue

            # String filters
            if filter_expr == 'upper':
                value = str(value).upper()
            elif filter_expr == 'lower':
                value = str(value).lower()
            elif filter_expr == 'capitalize':
                value = str(value).capitalize()
            elif filter_expr == 'strip':
                value = str(value).strip()
            elif filter_expr == 'json':
                value = json.dumps(value)

            # Length filter
            elif filter_expr == 'length':
                value = len(value) if value else 0

            # Truncate filter
            elif filter_expr.startswith('truncate:'):
                try:
                    max_len = int(filter_expr[9:])
                    value = str(value)[:max_len]
                except ValueError:
                    pass

        return str(value)


# =============================================================================
# Prompt Chaining Service
# =============================================================================

class PromptChainingService:
    """
    Service for executing multi-step prompt chains.

    Usage:
        chain = PromptChain(
            name="Research Chain",
            steps=[
                ChainStep(
                    name="research",
                    step_type=StepType.PROMPT,
                    prompt_template="Research the topic: {{topic}}",
                    output_variable="research_output"
                ),
                ChainStep(
                    name="summarize",
                    step_type=StepType.PROMPT,
                    prompt_template="Summarize: {{research_output}}",
                    output_variable="summary"
                )
            ]
        )

        result = prompt_chaining_service.execute(chain, {'topic': 'AI'})
    """

    def __init__(self):
        self.template_engine = TemplateEngine()
        self._active_chains: Dict[str, ChainResult] = {}

    # -------------------------------------------------------------------------
    # Chain Execution
    # -------------------------------------------------------------------------

    def execute(
        self,
        chain: PromptChain,
        initial_variables: Dict[str, Any] = None,
        on_step_complete: Optional[Callable] = None,
    ) -> ChainResult:
        """
        Execute a prompt chain.

        Args:
            chain: The chain to execute
            initial_variables: Starting variables
            on_step_complete: Callback after each step

        Returns:
            ChainResult with all outputs
        """
        import uuid

        chain_id = str(uuid.uuid4())
        start_time = time.time()

        # Initialize variables
        variables = {**chain.initial_variables, **(initial_variables or {})}

        # Track results
        step_results = []
        total_tokens = 0
        total_cost = 0.0
        final_output = None
        error = None
        status = ChainStatus.RUNNING

        # Store active chain
        result = ChainResult(
            chain_id=chain_id,
            chain_name=chain.name,
            status=status,
            steps_completed=0,
            total_steps=len(chain.steps),
            step_results=[],
            final_output=None,
            total_tokens=0,
            total_cost=0.0,
            total_latency_ms=0.0,
            variables=variables,
        )
        self._active_chains[chain_id] = result

        try:
            for i, step in enumerate(chain.steps):
                # Check limits
                if total_tokens >= chain.max_total_tokens:
                    error = f"Token limit exceeded: {total_tokens}"
                    status = ChainStatus.FAILED
                    break

                if total_cost >= chain.max_total_cost:
                    error = f"Cost limit exceeded: ${total_cost:.4f}"
                    status = ChainStatus.FAILED
                    break

                # Execute step
                step_result = self._execute_step(step, variables)
                step_results.append(step_result)

                # Update totals
                total_tokens += step_result.input_tokens + step_result.output_tokens
                total_cost += step_result.cost

                # Update variables with output
                if step_result.success:
                    variables[step.output_variable] = step_result.output
                    final_output = step_result.output
                else:
                    if chain.stop_on_error:
                        error = f"Step '{step.name}' failed: {step_result.error}"
                        status = ChainStatus.FAILED
                        break

                # Callback
                if on_step_complete:
                    on_step_complete(step, step_result, variables)

                # Update active chain
                result.steps_completed = i + 1
                result.step_results = step_results
                result.variables = variables

            if status == ChainStatus.RUNNING:
                status = ChainStatus.COMPLETED

        except Exception as e:
            logger.exception(f"Chain execution error: {e}")
            error = str(e)
            status = ChainStatus.FAILED

        total_latency = (time.time() - start_time) * 1000

        # Final result
        result = ChainResult(
            chain_id=chain_id,
            chain_name=chain.name,
            status=status,
            steps_completed=len(step_results),
            total_steps=len(chain.steps),
            step_results=step_results,
            final_output=final_output,
            total_tokens=total_tokens,
            total_cost=total_cost,
            total_latency_ms=total_latency,
            variables=variables,
            error=error,
        )

        # Update cache
        self._active_chains[chain_id] = result

        return result

    def _execute_step(
        self,
        step: ChainStep,
        variables: Dict[str, Any],
    ) -> StepResult:
        """Execute a single chain step."""
        if step.step_type == StepType.PROMPT:
            return self._execute_prompt_step(step, variables)
        elif step.step_type == StepType.CONDITIONAL:
            return self._execute_conditional_step(step, variables)
        elif step.step_type == StepType.TRANSFORM:
            return self._execute_transform_step(step, variables)
        elif step.step_type == StepType.PARALLEL:
            return self._execute_parallel_step(step, variables)
        elif step.step_type == StepType.LOOP:
            return self._execute_loop_step(step, variables)
        elif step.step_type == StepType.VALIDATOR:
            return self._execute_validator_step(step, variables)
        else:
            return StepResult(
                step_name=step.name,
                success=False,
                output=None,
                error=f"Unknown step type: {step.step_type}",
            )

    def _execute_prompt_step(
        self,
        step: ChainStep,
        variables: Dict[str, Any],
    ) -> StepResult:
        """Execute a prompt step with LLM."""
        start_time = time.time()
        retries = 0

        while retries <= step.retry_count:
            try:
                # Render template
                prompt = self.template_engine.render(step.prompt_template, variables)
                system_prompt = None
                if step.system_prompt:
                    system_prompt = self.template_engine.render(
                        step.system_prompt, variables
                    )

                # Call LLM
                from coreapp.services.llm_service import llm_service

                response = llm_service.generate(
                    prompt=prompt,
                    model=step.model,
                    max_tokens=step.max_tokens,
                    temperature=step.temperature,
                    system_prompt=system_prompt,
                )

                latency_ms = (time.time() - start_time) * 1000

                return StepResult(
                    step_name=step.name,
                    success=True,
                    output=response.get('text', ''),
                    input_tokens=response.get('input_tokens', 0),
                    output_tokens=response.get('output_tokens', 0),
                    latency_ms=latency_ms,
                    cost=response.get('cost', 0.0),
                    retries=retries,
                    metadata={
                        'model': step.model,
                        'prompt_length': len(prompt),
                    }
                )

            except Exception as e:
                retries += 1
                if retries > step.retry_count:
                    latency_ms = (time.time() - start_time) * 1000
                    return StepResult(
                        step_name=step.name,
                        success=False,
                        output=None,
                        latency_ms=latency_ms,
                        error=str(e),
                        retries=retries - 1,
                    )
                time.sleep(1 * retries)  # Exponential backoff

        return StepResult(
            step_name=step.name,
            success=False,
            output=None,
            error="Max retries exceeded",
        )

    def _execute_conditional_step(
        self,
        step: ChainStep,
        variables: Dict[str, Any],
    ) -> StepResult:
        """Execute a conditional step."""
        start_time = time.time()

        try:
            # Evaluate condition
            condition = self.template_engine.render(step.condition, variables)

            # Simple boolean evaluation
            condition_met = False
            condition_lower = condition.lower().strip()

            if condition_lower in ('true', 'yes', '1'):
                condition_met = True
            elif condition_lower in ('false', 'no', '0', ''):
                condition_met = False
            else:
                # Try to evaluate as expression
                try:
                    condition_met = bool(eval(condition, {'__builtins__': {}}, variables))
                except Exception:
                    condition_met = bool(condition)

            latency_ms = (time.time() - start_time) * 1000

            return StepResult(
                step_name=step.name,
                success=True,
                output=condition_met,
                latency_ms=latency_ms,
                metadata={'condition': step.condition, 'result': condition_met},
            )

        except Exception as e:
            return StepResult(
                step_name=step.name,
                success=False,
                output=None,
                error=str(e),
            )

    def _execute_transform_step(
        self,
        step: ChainStep,
        variables: Dict[str, Any],
    ) -> StepResult:
        """Execute a transform step."""
        start_time = time.time()

        try:
            if step.transform_fn:
                result = step.transform_fn(variables)
            else:
                # Default transform: extract from template
                result = self.template_engine.render(
                    step.prompt_template or '', variables
                )

            latency_ms = (time.time() - start_time) * 1000

            return StepResult(
                step_name=step.name,
                success=True,
                output=result,
                latency_ms=latency_ms,
            )

        except Exception as e:
            return StepResult(
                step_name=step.name,
                success=False,
                output=None,
                error=str(e),
            )

    def _execute_parallel_step(
        self,
        step: ChainStep,
        variables: Dict[str, Any],
    ) -> StepResult:
        """Execute multiple steps in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        start_time = time.time()
        results = []

        try:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(self._execute_step, sub_step, variables.copy()): sub_step
                    for sub_step in step.parallel_steps
                }

                for future in as_completed(futures):
                    sub_result = future.result()
                    results.append(sub_result)

            latency_ms = (time.time() - start_time) * 1000

            # Combine results
            combined_output = {r.step_name: r.output for r in results}
            all_success = all(r.success for r in results)

            return StepResult(
                step_name=step.name,
                success=all_success,
                output=combined_output,
                input_tokens=sum(r.input_tokens for r in results),
                output_tokens=sum(r.output_tokens for r in results),
                latency_ms=latency_ms,
                cost=sum(r.cost for r in results),
                metadata={'parallel_results': [r.to_dict() for r in results]},
            )

        except Exception as e:
            return StepResult(
                step_name=step.name,
                success=False,
                output=None,
                error=str(e),
            )

    def _execute_loop_step(
        self,
        step: ChainStep,
        variables: Dict[str, Any],
    ) -> StepResult:
        """Execute a step multiple times with different inputs."""
        start_time = time.time()
        results = []

        try:
            # Get loop items
            items = step.loop_items
            if step.loop_variable and step.loop_variable in variables:
                items = variables[step.loop_variable]

            if not items:
                return StepResult(
                    step_name=step.name,
                    success=True,
                    output=[],
                    latency_ms=0,
                    metadata={'iterations': 0},
                )

            for i, item in enumerate(items):
                # Create iteration variables
                iter_vars = {
                    **variables,
                    'item': item,
                    'index': i,
                }

                # Execute prompt
                prompt = self.template_engine.render(step.prompt_template, iter_vars)

                from coreapp.services.llm_service import llm_service

                response = llm_service.generate(
                    prompt=prompt,
                    model=step.model,
                    max_tokens=step.max_tokens,
                    temperature=step.temperature,
                )

                results.append({
                    'item': item,
                    'output': response.get('text', ''),
                    'tokens': response.get('output_tokens', 0),
                })

            latency_ms = (time.time() - start_time) * 1000

            return StepResult(
                step_name=step.name,
                success=True,
                output=results,
                input_tokens=sum(r.get('tokens', 0) for r in results),
                output_tokens=sum(r.get('tokens', 0) for r in results),
                latency_ms=latency_ms,
                metadata={'iterations': len(results)},
            )

        except Exception as e:
            return StepResult(
                step_name=step.name,
                success=False,
                output=None,
                error=str(e),
            )

    def _execute_validator_step(
        self,
        step: ChainStep,
        variables: Dict[str, Any],
    ) -> StepResult:
        """Execute a validation step."""
        start_time = time.time()

        try:
            if step.validator_fn:
                is_valid = step.validator_fn(variables)
            else:
                # Default: check if output_variable exists and is truthy
                is_valid = bool(variables.get(step.output_variable))

            latency_ms = (time.time() - start_time) * 1000

            return StepResult(
                step_name=step.name,
                success=is_valid,
                output=is_valid,
                latency_ms=latency_ms,
                error=None if is_valid else 'Validation failed',
            )

        except Exception as e:
            return StepResult(
                step_name=step.name,
                success=False,
                output=False,
                error=str(e),
            )

    # -------------------------------------------------------------------------
    # Chain Management
    # -------------------------------------------------------------------------

    def get_chain_status(self, chain_id: str) -> Optional[ChainResult]:
        """Get status of a running or completed chain."""
        return self._active_chains.get(chain_id)

    def cancel_chain(self, chain_id: str) -> bool:
        """Cancel a running chain."""
        if chain_id in self._active_chains:
            result = self._active_chains[chain_id]
            if result.status == ChainStatus.RUNNING:
                result.status = ChainStatus.CANCELLED
                return True
        return False

    def list_active_chains(self) -> List[Dict[str, Any]]:
        """List all active chains."""
        return [
            {
                'chain_id': chain_id,
                'chain_name': result.chain_name,
                'status': result.status.value,
                'progress': f"{result.steps_completed}/{result.total_steps}",
            }
            for chain_id, result in self._active_chains.items()
            if result.status == ChainStatus.RUNNING
        ]


# =============================================================================
# Chain Templates
# =============================================================================

class ChainTemplates:
    """Pre-built chain templates for common workflows."""

    @staticmethod
    def research_and_summarize() -> PromptChain:
        """Chain for researching a topic and summarizing findings."""
        return PromptChain(
            name="Research and Summarize",
            description="Research a topic, extract key points, and summarize",
            steps=[
                ChainStep(
                    name="research",
                    step_type=StepType.PROMPT,
                    prompt_template="""Research the following topic comprehensively:
Topic: {{topic}}

Provide detailed information covering:
1. Overview and background
2. Key concepts and terminology
3. Current state and trends
4. Important considerations""",
                    model="gpt-4",
                    max_tokens=2000,
                    output_variable="research_output",
                ),
                ChainStep(
                    name="extract_key_points",
                    step_type=StepType.PROMPT,
                    prompt_template="""Extract the key points from this research:

{{research_output}}

List the 5-10 most important takeaways.""",
                    model="gpt-3.5-turbo",
                    max_tokens=500,
                    output_variable="key_points",
                ),
                ChainStep(
                    name="summarize",
                    step_type=StepType.PROMPT,
                    prompt_template="""Create a concise executive summary based on:

Research:
{{research_output}}

Key Points:
{{key_points}}

Write a 2-3 paragraph summary suitable for busy professionals.""",
                    model="gpt-3.5-turbo",
                    max_tokens=500,
                    output_variable="summary",
                ),
            ],
        )

    @staticmethod
    def content_creation() -> PromptChain:
        """Chain for creating and refining content."""
        return PromptChain(
            name="Content Creation",
            description="Create, review, and refine content",
            steps=[
                ChainStep(
                    name="outline",
                    step_type=StepType.PROMPT,
                    prompt_template="""Create an outline for content about:
Topic: {{topic}}
Type: {{content_type|default:article}}
Target audience: {{audience|default:general}}

Provide a detailed structure with main sections and subsections.""",
                    model="gpt-3.5-turbo",
                    max_tokens=500,
                    output_variable="outline",
                ),
                ChainStep(
                    name="draft",
                    step_type=StepType.PROMPT,
                    prompt_template="""Write the full content based on this outline:

{{outline}}

Topic: {{topic}}
Tone: {{tone|default:professional}}
Length: {{length|default:medium}}""",
                    model="gpt-4",
                    max_tokens=3000,
                    output_variable="draft",
                ),
                ChainStep(
                    name="review",
                    step_type=StepType.PROMPT,
                    prompt_template="""Review this content for improvements:

{{draft}}

Check for:
1. Clarity and readability
2. Accuracy and completeness
3. Engagement and flow
4. Grammar and style

Provide specific suggestions.""",
                    model="gpt-4",
                    max_tokens=1000,
                    output_variable="review",
                ),
                ChainStep(
                    name="refine",
                    step_type=StepType.PROMPT,
                    prompt_template="""Incorporate the review feedback into the content:

Original:
{{draft}}

Feedback:
{{review}}

Produce the improved final version.""",
                    model="gpt-4",
                    max_tokens=3000,
                    output_variable="final_content",
                ),
            ],
        )

    @staticmethod
    def code_review() -> PromptChain:
        """Chain for reviewing and improving code."""
        return PromptChain(
            name="Code Review",
            description="Review code for issues and suggest improvements",
            steps=[
                ChainStep(
                    name="analyze",
                    step_type=StepType.PROMPT,
                    prompt_template="""Analyze this code for potential issues:

```{{language|default:python}}
{{code}}
```

Check for:
1. Bugs and logic errors
2. Security vulnerabilities
3. Performance issues
4. Code style and best practices""",
                    model="gpt-4",
                    max_tokens=1500,
                    output_variable="analysis",
                ),
                ChainStep(
                    name="suggest_improvements",
                    step_type=StepType.PROMPT,
                    prompt_template="""Based on this analysis:

{{analysis}}

Suggest specific code improvements with examples.""",
                    model="gpt-4",
                    max_tokens=1500,
                    output_variable="improvements",
                ),
                ChainStep(
                    name="rewrite",
                    step_type=StepType.PROMPT,
                    prompt_template="""Rewrite the original code with improvements:

Original:
```{{language|default:python}}
{{code}}
```

Improvements to apply:
{{improvements}}

Provide the improved code with comments explaining changes.""",
                    model="gpt-4",
                    max_tokens=2000,
                    output_variable="improved_code",
                ),
            ],
        )

    @staticmethod
    def translation_and_localization() -> PromptChain:
        """Chain for translating and localizing content."""
        return PromptChain(
            name="Translation and Localization",
            description="Translate content with cultural adaptation",
            steps=[
                ChainStep(
                    name="translate",
                    step_type=StepType.PROMPT,
                    prompt_template="""Translate this content:

{{content}}

From: {{source_language|default:English}}
To: {{target_language}}

Maintain the original meaning and tone.""",
                    model="gpt-4",
                    max_tokens=2000,
                    output_variable="translation",
                ),
                ChainStep(
                    name="localize",
                    step_type=StepType.PROMPT,
                    prompt_template="""Adapt this translation for the {{target_region|default:target}} audience:

{{translation}}

Consider:
1. Cultural references
2. Idioms and expressions
3. Formatting conventions
4. Local context""",
                    model="gpt-4",
                    max_tokens=2000,
                    output_variable="localized_content",
                ),
                ChainStep(
                    name="review_translation",
                    step_type=StepType.PROMPT,
                    prompt_template="""Review this localized translation:

Original:
{{content}}

Localized:
{{localized_content}}

Check for accuracy and cultural appropriateness.
Suggest any corrections needed.""",
                    model="gpt-4",
                    max_tokens=1000,
                    output_variable="review_notes",
                ),
            ],
        )

    @staticmethod
    def data_analysis() -> PromptChain:
        """Chain for analyzing data and generating insights."""
        return PromptChain(
            name="Data Analysis",
            description="Analyze data and generate actionable insights",
            steps=[
                ChainStep(
                    name="understand_data",
                    step_type=StepType.PROMPT,
                    prompt_template="""Analyze this data:

{{data}}

Provide:
1. Data structure overview
2. Key statistics
3. Notable patterns
4. Data quality observations""",
                    model="gpt-4",
                    max_tokens=1500,
                    output_variable="data_overview",
                ),
                ChainStep(
                    name="identify_insights",
                    step_type=StepType.PROMPT,
                    prompt_template="""Based on this data analysis:

{{data_overview}}

Identify:
1. Key trends and patterns
2. Anomalies or outliers
3. Correlations
4. Actionable insights""",
                    model="gpt-4",
                    max_tokens=1500,
                    output_variable="insights",
                ),
                ChainStep(
                    name="recommendations",
                    step_type=StepType.PROMPT,
                    prompt_template="""Based on these insights:

{{insights}}

Provide:
1. Strategic recommendations
2. Action items with priorities
3. Potential risks to consider
4. Success metrics to track""",
                    model="gpt-4",
                    max_tokens=1500,
                    output_variable="recommendations",
                ),
            ],
        )


# =============================================================================
# Singleton Instance
# =============================================================================

prompt_chaining_service = PromptChainingService()
chain_templates = ChainTemplates()
