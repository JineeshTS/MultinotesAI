"""
Scheduled Generations Service for MultinotesAI.

This module provides:
- Scheduled prompt execution (cron-like scheduling)
- Recurring AI generations
- Schedule management and monitoring
- Timezone-aware scheduling
- Webhook/notification on completion

WBS Item: 6.1.5 - Scheduled generations
"""

import logging
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from threading import Thread, Event
import time

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Schedule Configuration
# =============================================================================

class ScheduleStatus(Enum):
    """Status of a scheduled generation."""
    ACTIVE = 'active'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'


class RepeatInterval(Enum):
    """Predefined repeat intervals."""
    ONCE = 'once'
    HOURLY = 'hourly'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    CUSTOM = 'custom'


class DayOfWeek(Enum):
    """Days of the week."""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass
class CronSchedule:
    """Cron-like schedule specification."""
    minute: str = '*'  # 0-59 or *
    hour: str = '*'  # 0-23 or *
    day_of_month: str = '*'  # 1-31 or *
    month: str = '*'  # 1-12 or *
    day_of_week: str = '*'  # 0-6 (Mon-Sun) or *

    def matches(self, dt: datetime) -> bool:
        """Check if datetime matches this schedule."""
        if not self._matches_field(self.minute, dt.minute, 0, 59):
            return False
        if not self._matches_field(self.hour, dt.hour, 0, 23):
            return False
        if not self._matches_field(self.day_of_month, dt.day, 1, 31):
            return False
        if not self._matches_field(self.month, dt.month, 1, 12):
            return False
        if not self._matches_field(self.day_of_week, dt.weekday(), 0, 6):
            return False
        return True

    def _matches_field(self, pattern: str, value: int, min_val: int, max_val: int) -> bool:
        """Check if value matches cron pattern."""
        if pattern == '*':
            return True

        # Handle comma-separated values
        if ',' in pattern:
            values = [int(v.strip()) for v in pattern.split(',')]
            return value in values

        # Handle range
        if '-' in pattern:
            parts = pattern.split('-')
            start, end = int(parts[0]), int(parts[1])
            return start <= value <= end

        # Handle step
        if '/' in pattern:
            parts = pattern.split('/')
            if parts[0] == '*':
                step = int(parts[1])
                return (value - min_val) % step == 0
            else:
                start = int(parts[0])
                step = int(parts[1])
                return value >= start and (value - start) % step == 0

        # Single value
        try:
            return int(pattern) == value
        except ValueError:
            return False

    def next_run(self, after: datetime = None) -> datetime:
        """Calculate next run time after given datetime."""
        if after is None:
            after = timezone.now()

        # Start from next minute
        dt = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Find next matching time (max 366 days ahead)
        for _ in range(366 * 24 * 60):
            if self.matches(dt):
                return dt
            dt += timedelta(minutes=1)

        raise ValueError("Could not find next run time within a year")

    def to_string(self) -> str:
        """Convert to cron string."""
        return f"{self.minute} {self.hour} {self.day_of_month} {self.month} {self.day_of_week}"

    @classmethod
    def from_string(cls, cron_str: str) -> 'CronSchedule':
        """Parse cron string."""
        parts = cron_str.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron format: {cron_str}")

        return cls(
            minute=parts[0],
            hour=parts[1],
            day_of_month=parts[2],
            month=parts[3],
            day_of_week=parts[4],
        )


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class GenerationConfig:
    """Configuration for AI generation."""
    prompt_template: str
    model: str = 'gpt-3.5-turbo'
    max_tokens: int = 1000
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of a scheduled execution."""
    execution_id: str
    schedule_id: str
    status: str
    output: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    error: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'schedule_id': self.schedule_id,
            'status': self.status,
            'output': self.output[:500] if self.output else None,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'cost': round(self.cost, 6),
            'latency_ms': round(self.latency_ms, 2),
            'error': self.error,
            'executed_at': self.executed_at.isoformat(),
        }


@dataclass
class ScheduledGeneration:
    """A scheduled generation job."""
    schedule_id: str
    user_id: int
    name: str
    description: str
    generation_config: GenerationConfig
    schedule: CronSchedule
    repeat_interval: RepeatInterval = RepeatInterval.ONCE
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    timezone: str = 'UTC'
    max_executions: Optional[int] = None
    expires_at: Optional[datetime] = None
    execution_count: int = 0
    last_execution: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    last_result: Optional[ExecutionResult] = None
    webhook_url: Optional[str] = None
    notify_on_completion: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.next_execution is None:
            self.next_execution = self.schedule.next_run()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'schedule_id': self.schedule_id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'prompt_template': self.generation_config.prompt_template[:200] + '...' if len(self.generation_config.prompt_template) > 200 else self.generation_config.prompt_template,
            'model': self.generation_config.model,
            'schedule': self.schedule.to_string(),
            'repeat_interval': self.repeat_interval.value,
            'status': self.status.value,
            'timezone': self.timezone,
            'execution_count': self.execution_count,
            'last_execution': self.last_execution.isoformat() if self.last_execution else None,
            'next_execution': self.next_execution.isoformat() if self.next_execution else None,
            'created_at': self.created_at.isoformat(),
        }

    def to_detailed_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result['generation_config'] = {
            'prompt_template': self.generation_config.prompt_template,
            'model': self.generation_config.model,
            'max_tokens': self.generation_config.max_tokens,
            'temperature': self.generation_config.temperature,
            'system_prompt': self.generation_config.system_prompt,
            'variables': self.generation_config.variables,
        }
        result['max_executions'] = self.max_executions
        result['expires_at'] = self.expires_at.isoformat() if self.expires_at else None
        result['webhook_url'] = self.webhook_url
        result['last_result'] = self.last_result.to_dict() if self.last_result else None
        return result


# =============================================================================
# Schedule Manager
# =============================================================================

class ScheduleManager:
    """
    Manager for scheduled generation jobs.

    Handles CRUD operations and schedule validation.
    """

    def __init__(self):
        self._schedules: Dict[str, ScheduledGeneration] = {}

    def create(
        self,
        user_id: int,
        name: str,
        prompt_template: str,
        schedule: str,
        description: str = '',
        model: str = 'gpt-3.5-turbo',
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        variables: Dict[str, Any] = None,
        repeat_interval: RepeatInterval = RepeatInterval.CUSTOM,
        timezone_str: str = 'UTC',
        max_executions: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        webhook_url: Optional[str] = None,
        notify_on_completion: bool = True,
    ) -> ScheduledGeneration:
        """Create a new scheduled generation."""
        schedule_id = str(uuid.uuid4())

        # Parse cron schedule
        cron_schedule = CronSchedule.from_string(schedule)

        generation_config = GenerationConfig(
            prompt_template=prompt_template,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
            variables=variables or {},
        )

        scheduled_gen = ScheduledGeneration(
            schedule_id=schedule_id,
            user_id=user_id,
            name=name,
            description=description,
            generation_config=generation_config,
            schedule=cron_schedule,
            repeat_interval=repeat_interval,
            timezone=timezone_str,
            max_executions=max_executions,
            expires_at=expires_at,
            webhook_url=webhook_url,
            notify_on_completion=notify_on_completion,
        )

        self._schedules[schedule_id] = scheduled_gen

        # Cache schedule
        self._cache_schedule(scheduled_gen)

        logger.info(f"Created scheduled generation {schedule_id}")

        return scheduled_gen

    def get(self, schedule_id: str) -> Optional[ScheduledGeneration]:
        """Get schedule by ID."""
        if schedule_id in self._schedules:
            return self._schedules[schedule_id]

        # Check cache
        cached = cache.get(f"schedule:{schedule_id}")
        if cached:
            self._schedules[schedule_id] = cached
            return cached

        return None

    def list(
        self,
        user_id: Optional[int] = None,
        status: Optional[ScheduleStatus] = None,
        limit: int = 50,
    ) -> List[ScheduledGeneration]:
        """List schedules with optional filters."""
        schedules = list(self._schedules.values())

        if user_id:
            schedules = [s for s in schedules if s.user_id == user_id]

        if status:
            schedules = [s for s in schedules if s.status == status]

        # Sort by next execution
        schedules.sort(key=lambda s: s.next_execution or datetime.max)

        return schedules[:limit]

    def update(
        self,
        schedule_id: str,
        **kwargs,
    ) -> Optional[ScheduledGeneration]:
        """Update schedule properties."""
        schedule = self.get(schedule_id)
        if not schedule:
            return None

        # Update allowed fields
        if 'name' in kwargs:
            schedule.name = kwargs['name']
        if 'description' in kwargs:
            schedule.description = kwargs['description']
        if 'schedule' in kwargs:
            schedule.schedule = CronSchedule.from_string(kwargs['schedule'])
            schedule.next_execution = schedule.schedule.next_run()
        if 'prompt_template' in kwargs:
            schedule.generation_config.prompt_template = kwargs['prompt_template']
        if 'model' in kwargs:
            schedule.generation_config.model = kwargs['model']
        if 'max_tokens' in kwargs:
            schedule.generation_config.max_tokens = kwargs['max_tokens']
        if 'temperature' in kwargs:
            schedule.generation_config.temperature = kwargs['temperature']
        if 'variables' in kwargs:
            schedule.generation_config.variables = kwargs['variables']
        if 'webhook_url' in kwargs:
            schedule.webhook_url = kwargs['webhook_url']
        if 'max_executions' in kwargs:
            schedule.max_executions = kwargs['max_executions']
        if 'expires_at' in kwargs:
            schedule.expires_at = kwargs['expires_at']

        schedule.updated_at = datetime.now()

        self._cache_schedule(schedule)

        return schedule

    def pause(self, schedule_id: str) -> bool:
        """Pause a schedule."""
        schedule = self.get(schedule_id)
        if not schedule:
            return False

        if schedule.status == ScheduleStatus.ACTIVE:
            schedule.status = ScheduleStatus.PAUSED
            schedule.updated_at = datetime.now()
            self._cache_schedule(schedule)
            return True

        return False

    def resume(self, schedule_id: str) -> bool:
        """Resume a paused schedule."""
        schedule = self.get(schedule_id)
        if not schedule:
            return False

        if schedule.status == ScheduleStatus.PAUSED:
            schedule.status = ScheduleStatus.ACTIVE
            schedule.next_execution = schedule.schedule.next_run()
            schedule.updated_at = datetime.now()
            self._cache_schedule(schedule)
            return True

        return False

    def cancel(self, schedule_id: str) -> bool:
        """Cancel a schedule."""
        schedule = self.get(schedule_id)
        if not schedule:
            return False

        schedule.status = ScheduleStatus.CANCELLED
        schedule.next_execution = None
        schedule.updated_at = datetime.now()
        self._cache_schedule(schedule)

        logger.info(f"Cancelled schedule {schedule_id}")
        return True

    def delete(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            cache.delete(f"schedule:{schedule_id}")
            cache.delete(f"schedule_history:{schedule_id}")
            return True
        return False

    def _cache_schedule(self, schedule: ScheduledGeneration):
        """Cache schedule state."""
        cache.set(f"schedule:{schedule.schedule_id}", schedule, timeout=86400)


# =============================================================================
# Scheduled Generation Service
# =============================================================================

class ScheduledGenerationService:
    """
    Service for executing scheduled generations.

    Usage:
        service = ScheduledGenerationService()
        schedule = service.create_schedule(
            user_id=1,
            name="Daily Summary",
            prompt_template="Generate a summary for {{date}}",
            schedule="0 9 * * *"  # Every day at 9 AM
        )
        service.start()
    """

    def __init__(self):
        self.manager = ScheduleManager()
        self._executor_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._execution_history: Dict[str, List[ExecutionResult]] = {}

    # -------------------------------------------------------------------------
    # Schedule Management (delegated to manager)
    # -------------------------------------------------------------------------

    def create_schedule(self, **kwargs) -> ScheduledGeneration:
        """Create a new scheduled generation."""
        return self.manager.create(**kwargs)

    def get_schedule(self, schedule_id: str) -> Optional[ScheduledGeneration]:
        """Get schedule by ID."""
        return self.manager.get(schedule_id)

    def list_schedules(
        self,
        user_id: Optional[int] = None,
        status: Optional[ScheduleStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List schedules."""
        schedules = self.manager.list(user_id, status, limit)
        return [s.to_dict() for s in schedules]

    def update_schedule(self, schedule_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a schedule."""
        schedule = self.manager.update(schedule_id, **kwargs)
        return schedule.to_dict() if schedule else None

    def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a schedule."""
        return self.manager.pause(schedule_id)

    def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a schedule."""
        return self.manager.resume(schedule_id)

    def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel a schedule."""
        return self.manager.cancel(schedule_id)

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        return self.manager.delete(schedule_id)

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    def execute_now(self, schedule_id: str) -> Optional[ExecutionResult]:
        """Execute a schedule immediately (manual trigger)."""
        schedule = self.manager.get(schedule_id)
        if not schedule:
            return None

        return self._execute_schedule(schedule)

    def _execute_schedule(self, schedule: ScheduledGeneration) -> ExecutionResult:
        """Execute a scheduled generation."""
        execution_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            from coreapp.services.llm_service import llm_service
            from coreapp.services.prompt_chaining import TemplateEngine

            # Render prompt with variables
            engine = TemplateEngine()
            variables = {
                **schedule.generation_config.variables,
                'date': timezone.now().strftime('%Y-%m-%d'),
                'time': timezone.now().strftime('%H:%M:%S'),
                'datetime': timezone.now().isoformat(),
                'execution_count': schedule.execution_count + 1,
            }

            prompt = engine.render(
                schedule.generation_config.prompt_template,
                variables
            )

            system_prompt = None
            if schedule.generation_config.system_prompt:
                system_prompt = engine.render(
                    schedule.generation_config.system_prompt,
                    variables
                )

            # Call LLM
            response = llm_service.generate(
                prompt=prompt,
                model=schedule.generation_config.model,
                max_tokens=schedule.generation_config.max_tokens,
                temperature=schedule.generation_config.temperature,
                system_prompt=system_prompt,
            )

            latency_ms = (time.time() - start_time) * 1000

            result = ExecutionResult(
                execution_id=execution_id,
                schedule_id=schedule.schedule_id,
                status='success',
                output=response.get('text', ''),
                input_tokens=response.get('input_tokens', 0),
                output_tokens=response.get('output_tokens', 0),
                cost=response.get('cost', 0.0),
                latency_ms=latency_ms,
                metadata={
                    'model': schedule.generation_config.model,
                    'prompt_length': len(prompt),
                }
            )

        except Exception as e:
            logger.exception(f"Scheduled execution {execution_id} failed: {e}")

            latency_ms = (time.time() - start_time) * 1000

            result = ExecutionResult(
                execution_id=execution_id,
                schedule_id=schedule.schedule_id,
                status='error',
                error=str(e),
                latency_ms=latency_ms,
            )

        # Update schedule
        schedule.execution_count += 1
        schedule.last_execution = datetime.now()
        schedule.last_result = result

        # Check if schedule should complete
        if self._should_complete(schedule):
            schedule.status = ScheduleStatus.COMPLETED
            schedule.next_execution = None
        else:
            # Calculate next execution
            schedule.next_execution = schedule.schedule.next_run(datetime.now())

        # Store history
        self._store_execution_result(result)

        # Send notifications
        if schedule.notify_on_completion:
            self._send_completion_notification(schedule, result)

        if schedule.webhook_url:
            self._call_webhook(schedule, result)

        # Cache updates
        self.manager._cache_schedule(schedule)

        return result

    def _should_complete(self, schedule: ScheduledGeneration) -> bool:
        """Check if schedule should be marked complete."""
        # One-time schedule
        if schedule.repeat_interval == RepeatInterval.ONCE:
            return True

        # Max executions reached
        if schedule.max_executions and schedule.execution_count >= schedule.max_executions:
            return True

        # Expired
        if schedule.expires_at and datetime.now() >= schedule.expires_at:
            return True

        return False

    # -------------------------------------------------------------------------
    # Scheduler Loop
    # -------------------------------------------------------------------------

    def start(self):
        """Start the scheduler."""
        if self._executor_thread and self._executor_thread.is_alive():
            logger.warning("Scheduler already running")
            return

        self._stop_event.clear()
        self._executor_thread = Thread(target=self._scheduler_loop, daemon=True)
        self._executor_thread.start()
        logger.info("Scheduled generation service started")

    def stop(self):
        """Stop the scheduler."""
        self._stop_event.set()
        if self._executor_thread:
            self._executor_thread.join(timeout=5)
        logger.info("Scheduled generation service stopped")

    def _scheduler_loop(self):
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            try:
                now = datetime.now()

                # Get all active schedules
                schedules = self.manager.list(status=ScheduleStatus.ACTIVE)

                for schedule in schedules:
                    # Check if due for execution
                    if schedule.next_execution and schedule.next_execution <= now:
                        logger.info(f"Executing schedule {schedule.schedule_id}")

                        try:
                            self._execute_schedule(schedule)
                        except Exception as e:
                            logger.error(
                                f"Failed to execute schedule {schedule.schedule_id}: {e}"
                            )

                # Sleep for a minute before next check
                for _ in range(60):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(10)

    # -------------------------------------------------------------------------
    # Execution History
    # -------------------------------------------------------------------------

    def _store_execution_result(self, result: ExecutionResult):
        """Store execution result in history."""
        schedule_id = result.schedule_id

        if schedule_id not in self._execution_history:
            self._execution_history[schedule_id] = []

        self._execution_history[schedule_id].append(result)

        # Keep only last 100 results
        if len(self._execution_history[schedule_id]) > 100:
            self._execution_history[schedule_id] = \
                self._execution_history[schedule_id][-100:]

        # Cache history
        cache.set(
            f"schedule_history:{schedule_id}",
            self._execution_history[schedule_id],
            timeout=86400,
        )

    def get_execution_history(
        self,
        schedule_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get execution history for a schedule."""
        # Check memory
        if schedule_id in self._execution_history:
            history = self._execution_history[schedule_id]
        else:
            # Check cache
            history = cache.get(f"schedule_history:{schedule_id}") or []

        # Sort by executed_at descending
        history.sort(key=lambda r: r.executed_at, reverse=True)

        return [r.to_dict() for r in history[:limit]]

    def get_execution_stats(
        self,
        schedule_id: str,
    ) -> Dict[str, Any]:
        """Get execution statistics for a schedule."""
        history = self._execution_history.get(schedule_id, [])

        if not history:
            return {
                'total_executions': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0,
            }

        successful = sum(1 for r in history if r.status == 'success')
        failed = sum(1 for r in history if r.status == 'error')

        latencies = [r.latency_ms for r in history if r.status == 'success']
        costs = [r.cost for r in history if r.status == 'success']

        return {
            'total_executions': len(history),
            'successful': successful,
            'failed': failed,
            'success_rate': round(successful / len(history) * 100, 1),
            'avg_latency_ms': round(sum(latencies) / len(latencies), 2) if latencies else 0,
            'total_cost': round(sum(costs), 6),
            'avg_cost': round(sum(costs) / len(costs), 6) if costs else 0,
        }

    # -------------------------------------------------------------------------
    # Notifications
    # -------------------------------------------------------------------------

    def _send_completion_notification(
        self,
        schedule: ScheduledGeneration,
        result: ExecutionResult,
    ):
        """Send completion notification via WebSocket."""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"schedule_user_{schedule.user_id}",
                    {
                        'type': 'schedule.executed',
                        'schedule_id': schedule.schedule_id,
                        'schedule_name': schedule.name,
                        'status': result.status,
                        'execution_id': result.execution_id,
                        'output_preview': result.output[:200] if result.output else None,
                        'error': result.error,
                    }
                )
        except Exception as e:
            logger.debug(f"Notification failed: {e}")

    def _call_webhook(
        self,
        schedule: ScheduledGeneration,
        result: ExecutionResult,
    ):
        """Call webhook URL with execution result."""
        import requests

        try:
            payload = {
                'schedule_id': schedule.schedule_id,
                'schedule_name': schedule.name,
                'execution_id': result.execution_id,
                'status': result.status,
                'output': result.output,
                'error': result.error,
                'executed_at': result.executed_at.isoformat(),
            }

            response = requests.post(
                schedule.webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )

            logger.info(
                f"Webhook called for {schedule.schedule_id}: "
                f"status={response.status_code}"
            )

        except Exception as e:
            logger.error(f"Webhook call failed: {e}")


# =============================================================================
# Schedule Templates
# =============================================================================

class ScheduleTemplates:
    """Pre-built schedule templates."""

    @staticmethod
    def daily_summary(
        user_id: int,
        hour: int = 9,
        prompt: str = "Generate a summary of key AI news and developments.",
    ) -> ScheduledGeneration:
        """Create daily summary schedule."""
        service = scheduled_generation_service

        return service.create_schedule(
            user_id=user_id,
            name="Daily AI Summary",
            description=f"Generated daily at {hour}:00",
            prompt_template=f"{prompt}\n\nDate: {{{{date}}}}",
            schedule=f"0 {hour} * * *",
            repeat_interval=RepeatInterval.DAILY,
            model='gpt-4',
            max_tokens=1500,
        )

    @staticmethod
    def weekly_report(
        user_id: int,
        day_of_week: DayOfWeek = DayOfWeek.MONDAY,
        hour: int = 8,
        topics: List[str] = None,
    ) -> ScheduledGeneration:
        """Create weekly report schedule."""
        service = scheduled_generation_service
        topics = topics or ['productivity', 'technology', 'business']

        return service.create_schedule(
            user_id=user_id,
            name="Weekly Report",
            description=f"Generated every {day_of_week.name} at {hour}:00",
            prompt_template=f"""Generate a weekly report covering:
Topics: {', '.join(topics)}

Date: {{{{date}}}}
Week number: {{{{execution_count}}}}

Include:
1. Key highlights
2. Trends to watch
3. Recommendations""",
            schedule=f"0 {hour} * * {day_of_week.value}",
            repeat_interval=RepeatInterval.WEEKLY,
            model='gpt-4',
            max_tokens=2000,
        )

    @staticmethod
    def hourly_monitoring(
        user_id: int,
        prompt: str = "Check system status and report any anomalies.",
    ) -> ScheduledGeneration:
        """Create hourly monitoring schedule."""
        service = scheduled_generation_service

        return service.create_schedule(
            user_id=user_id,
            name="Hourly Monitoring",
            description="Runs every hour",
            prompt_template=f"{prompt}\n\nTimestamp: {{{{datetime}}}}",
            schedule="0 * * * *",
            repeat_interval=RepeatInterval.HOURLY,
            model='gpt-3.5-turbo',
            max_tokens=500,
        )

    @staticmethod
    def content_generation(
        user_id: int,
        content_type: str,
        schedule: str,
        topics: List[str],
    ) -> ScheduledGeneration:
        """Create content generation schedule."""
        service = scheduled_generation_service

        return service.create_schedule(
            user_id=user_id,
            name=f"{content_type.title()} Generation",
            description=f"Automated {content_type} generation",
            prompt_template=f"""Generate a {content_type} about one of these topics:
{', '.join(topics)}

Requirements:
- Engaging and informative
- SEO-friendly
- Include call-to-action

Date: {{{{date}}}}
Article number: {{{{execution_count}}}}""",
            schedule=schedule,
            repeat_interval=RepeatInterval.CUSTOM,
            model='gpt-4',
            max_tokens=2000,
            variables={'content_type': content_type, 'topics': topics},
        )


# =============================================================================
# Celery Tasks Integration
# =============================================================================

def register_celery_tasks():
    """Register Celery tasks for scheduled generations."""
    try:
        from celery import shared_task

        @shared_task(name='execute_scheduled_generation')
        def execute_scheduled_generation_task(schedule_id: str):
            """Celery task to execute a scheduled generation."""
            service = scheduled_generation_service
            result = service.execute_now(schedule_id)
            return result.to_dict() if result else None

        @shared_task(name='check_due_schedules')
        def check_due_schedules_task():
            """Celery task to check and execute due schedules."""
            service = scheduled_generation_service
            now = datetime.now()

            schedules = service.manager.list(status=ScheduleStatus.ACTIVE)
            executed = 0

            for schedule in schedules:
                if schedule.next_execution and schedule.next_execution <= now:
                    execute_scheduled_generation_task.delay(schedule.schedule_id)
                    executed += 1

            return {'executed': executed}

        logger.info("Registered Celery tasks for scheduled generations")

    except ImportError:
        logger.debug("Celery not available, skipping task registration")


# =============================================================================
# Singleton Instance
# =============================================================================

scheduled_generation_service = ScheduledGenerationService()
schedule_templates = ScheduleTemplates()

# Register Celery tasks if available
register_celery_tasks()
