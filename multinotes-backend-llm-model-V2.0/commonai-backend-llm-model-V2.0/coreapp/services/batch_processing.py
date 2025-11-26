"""
Batch Processing Service for MultinotesAI.

This module provides:
- Batch prompt processing for multiple inputs
- Queue-based job management
- Progress tracking and notifications
- Rate limiting and throttling
- Retry logic and error handling

WBS Item: 6.1.4 - Batch processing
"""

import logging
import time
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Iterator
from queue import Queue, Empty
from threading import Thread, Event

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Batch Configuration
# =============================================================================

class BatchStatus(Enum):
    """Status of a batch job."""
    PENDING = 'pending'
    QUEUED = 'queued'
    PROCESSING = 'processing'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    PARTIAL = 'partial'  # Some items succeeded, some failed


class BatchPriority(Enum):
    """Priority levels for batch jobs."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    max_concurrent: int = 5
    batch_size: int = 10
    retry_count: int = 3
    retry_delay: float = 1.0
    timeout_per_item: float = 120.0
    rate_limit_per_minute: int = 60
    max_items_per_batch: int = 1000
    enable_notifications: bool = True
    cache_results: bool = True
    cache_ttl: int = 3600


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class BatchItem:
    """A single item in a batch."""
    item_id: str
    input_data: Dict[str, Any]
    status: str = 'pending'
    output: Any = None
    error: Optional[str] = None
    retries: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'item_id': self.item_id,
            'input_data': self.input_data,
            'status': self.status,
            'output': str(self.output)[:500] if self.output else None,
            'error': self.error,
            'retries': self.retries,
            'processing_time_ms': round(self.processing_time_ms, 2),
        }


@dataclass
class BatchJob:
    """A batch processing job."""
    job_id: str
    name: str
    user_id: int
    items: List[BatchItem]
    status: BatchStatus = BatchStatus.PENDING
    priority: BatchPriority = BatchPriority.NORMAL
    config: BatchConfig = field(default_factory=BatchConfig)
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.total_items = len(self.items)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'job_id': self.job_id,
            'name': self.name,
            'user_id': self.user_id,
            'status': self.status.value,
            'priority': self.priority.value,
            'progress': round(self.progress, 2),
            'total_items': self.total_items,
            'processed_items': self.processed_items,
            'successful_items': self.successful_items,
            'failed_items': self.failed_items,
            'total_tokens': self.total_tokens,
            'total_cost': round(self.total_cost, 6),
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
        }

    def to_detailed_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result['items'] = [item.to_dict() for item in self.items]
        return result


@dataclass
class BatchResult:
    """Result of a completed batch job."""
    job_id: str
    success: bool
    total_items: int
    successful_items: int
    failed_items: int
    results: List[Dict[str, Any]]
    total_tokens: int
    total_cost: float
    processing_time_ms: float
    errors: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'job_id': self.job_id,
            'success': self.success,
            'total_items': self.total_items,
            'successful_items': self.successful_items,
            'failed_items': self.failed_items,
            'total_tokens': self.total_tokens,
            'total_cost': round(self.total_cost, 6),
            'processing_time_ms': round(self.processing_time_ms, 2),
            'success_rate': round(self.successful_items / max(self.total_items, 1) * 100, 1),
        }


# =============================================================================
# Rate Limiter
# =============================================================================

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: int, per_seconds: int = 60):
        self.rate = rate
        self.per_seconds = per_seconds
        self.tokens = rate
        self.last_update = time.time()

    def acquire(self, timeout: float = None) -> bool:
        """Acquire a token, blocking if necessary."""
        start_time = time.time()

        while True:
            self._refill()

            if self.tokens >= 1:
                self.tokens -= 1
                return True

            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

            # Wait for token to become available
            time.sleep(0.1)

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        tokens_to_add = elapsed * (self.rate / self.per_seconds)
        self.tokens = min(self.rate, self.tokens + tokens_to_add)
        self.last_update = now


# =============================================================================
# Batch Processor
# =============================================================================

class BatchProcessor:
    """
    Core batch processing engine.

    Handles parallel execution, rate limiting, retries, and progress tracking.
    """

    def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()
        self.rate_limiter = RateLimiter(
            rate=self.config.rate_limit_per_minute,
            per_seconds=60
        )
        self._executor: Optional[ThreadPoolExecutor] = None
        self._stop_event = Event()

    @property
    def executor(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self.config.max_concurrent
            )
        return self._executor

    def process(
        self,
        items: List[BatchItem],
        processor_fn: Callable[[Dict[str, Any]], Any],
        on_item_complete: Optional[Callable] = None,
        on_progress: Optional[Callable] = None,
    ) -> BatchResult:
        """
        Process batch items.

        Args:
            items: List of items to process
            processor_fn: Function to process each item
            on_item_complete: Callback after each item
            on_progress: Progress callback

        Returns:
            BatchResult with all outcomes
        """
        start_time = time.time()
        results = []
        errors = []
        total_tokens = 0
        total_cost = 0.0
        successful = 0
        failed = 0

        self._stop_event.clear()

        # Process in batches
        for batch_start in range(0, len(items), self.config.batch_size):
            if self._stop_event.is_set():
                break

            batch_items = items[batch_start:batch_start + self.config.batch_size]

            # Submit batch to executor
            futures = {}
            for item in batch_items:
                if self._stop_event.is_set():
                    break

                # Rate limiting
                self.rate_limiter.acquire(timeout=30)

                item.status = 'processing'
                item.started_at = datetime.now()

                future = self.executor.submit(
                    self._process_item,
                    item,
                    processor_fn,
                )
                futures[future] = item

            # Collect results
            for future in as_completed(futures, timeout=self.config.timeout_per_item * len(batch_items)):
                item = futures[future]

                try:
                    result = future.result(timeout=self.config.timeout_per_item)

                    item.output = result.get('output')
                    item.status = 'completed'
                    item.completed_at = datetime.now()
                    item.processing_time_ms = result.get('processing_time_ms', 0)

                    total_tokens += result.get('tokens', 0)
                    total_cost += result.get('cost', 0.0)
                    successful += 1

                    results.append({
                        'item_id': item.item_id,
                        'output': item.output,
                    })

                except Exception as e:
                    item.status = 'failed'
                    item.error = str(e)
                    item.completed_at = datetime.now()
                    failed += 1

                    errors.append({
                        'item_id': item.item_id,
                        'error': str(e),
                    })

                if on_item_complete:
                    on_item_complete(item)

            # Progress update
            if on_progress:
                progress = (batch_start + len(batch_items)) / len(items) * 100
                on_progress(progress, successful, failed)

        processing_time = (time.time() - start_time) * 1000

        return BatchResult(
            job_id='',
            success=failed == 0,
            total_items=len(items),
            successful_items=successful,
            failed_items=failed,
            results=results,
            total_tokens=total_tokens,
            total_cost=total_cost,
            processing_time_ms=processing_time,
            errors=errors,
        )

    def _process_item(
        self,
        item: BatchItem,
        processor_fn: Callable,
    ) -> Dict[str, Any]:
        """Process a single item with retries."""
        retries = 0
        last_error = None

        while retries <= self.config.retry_count:
            try:
                start_time = time.time()
                result = processor_fn(item.input_data)
                processing_time = (time.time() - start_time) * 1000

                return {
                    'output': result.get('output') if isinstance(result, dict) else result,
                    'tokens': result.get('tokens', 0) if isinstance(result, dict) else 0,
                    'cost': result.get('cost', 0.0) if isinstance(result, dict) else 0.0,
                    'processing_time_ms': processing_time,
                }

            except Exception as e:
                retries += 1
                item.retries = retries
                last_error = e

                if retries <= self.config.retry_count:
                    time.sleep(self.config.retry_delay * retries)

        raise last_error or Exception("Processing failed")

    def stop(self):
        """Stop processing."""
        self._stop_event.set()


# =============================================================================
# Batch Processing Service
# =============================================================================

class BatchProcessingService:
    """
    Service for managing batch processing jobs.

    Usage:
        service = BatchProcessingService()
        job = service.create_job(
            user_id=1,
            name="Summarize Articles",
            items=[{'text': 'Article 1...'}, {'text': 'Article 2...'}],
            prompt_template="Summarize: {{text}}"
        )
        result = service.execute_job(job.job_id)
    """

    def __init__(self):
        self._jobs: Dict[str, BatchJob] = {}
        self._processors: Dict[str, BatchProcessor] = {}
        self._job_queue: Queue = Queue()
        self._worker_thread: Optional[Thread] = None
        self._running = False

    # -------------------------------------------------------------------------
    # Job Creation
    # -------------------------------------------------------------------------

    def create_job(
        self,
        user_id: int,
        name: str,
        items: List[Dict[str, Any]],
        prompt_template: Optional[str] = None,
        model: str = 'gpt-3.5-turbo',
        max_tokens: int = 1000,
        temperature: float = 0.7,
        priority: BatchPriority = BatchPriority.NORMAL,
        config: BatchConfig = None,
        processor_type: str = 'llm',
        custom_processor: Optional[Callable] = None,
    ) -> BatchJob:
        """
        Create a new batch job.

        Args:
            user_id: User creating the job
            name: Job name
            items: List of input data dicts
            prompt_template: Template for LLM prompts
            model: LLM model to use
            max_tokens: Max tokens per request
            temperature: Generation temperature
            priority: Job priority
            config: Batch configuration
            processor_type: 'llm' or 'custom'
            custom_processor: Custom processing function

        Returns:
            Created BatchJob
        """
        config = config or BatchConfig()

        if len(items) > config.max_items_per_batch:
            raise ValueError(
                f"Too many items: {len(items)} > {config.max_items_per_batch}"
            )

        job_id = str(uuid.uuid4())

        # Create batch items
        batch_items = [
            BatchItem(
                item_id=str(uuid.uuid4()),
                input_data=item,
            )
            for item in items
        ]

        job = BatchJob(
            job_id=job_id,
            name=name,
            user_id=user_id,
            items=batch_items,
            priority=priority,
            config=config,
            metadata={
                'prompt_template': prompt_template,
                'model': model,
                'max_tokens': max_tokens,
                'temperature': temperature,
                'processor_type': processor_type,
            }
        )

        self._jobs[job_id] = job

        # Cache job
        self._cache_job(job)

        logger.info(f"Created batch job {job_id} with {len(items)} items")

        return job

    # -------------------------------------------------------------------------
    # Job Execution
    # -------------------------------------------------------------------------

    def execute_job(
        self,
        job_id: str,
        async_execution: bool = False,
        on_progress: Optional[Callable] = None,
    ) -> Optional[BatchResult]:
        """
        Execute a batch job.

        Args:
            job_id: Job ID to execute
            async_execution: Run in background
            on_progress: Progress callback

        Returns:
            BatchResult if sync, None if async
        """
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if job.status not in [BatchStatus.PENDING, BatchStatus.PAUSED]:
            raise ValueError(f"Job cannot be executed: {job.status}")

        if async_execution:
            self._queue_job(job)
            return None

        return self._execute_job_sync(job, on_progress)

    def _execute_job_sync(
        self,
        job: BatchJob,
        on_progress: Optional[Callable] = None,
    ) -> BatchResult:
        """Execute job synchronously."""
        job.status = BatchStatus.PROCESSING
        job.started_at = datetime.now()

        processor = BatchProcessor(job.config)
        self._processors[job.job_id] = processor

        # Create processor function
        processor_fn = self._create_processor_fn(job)

        def progress_callback(progress, successful, failed):
            job.progress = progress
            job.processed_items = successful + failed
            job.successful_items = successful
            job.failed_items = failed

            if on_progress:
                on_progress(job)

            # Send notification
            if job.config.enable_notifications:
                self._send_progress_notification(job)

        try:
            result = processor.process(
                items=job.items,
                processor_fn=processor_fn,
                on_item_complete=lambda item: self._on_item_complete(job, item),
                on_progress=progress_callback,
            )

            result.job_id = job.job_id
            job.total_tokens = result.total_tokens
            job.total_cost = result.total_cost

            if result.failed_items > 0 and result.successful_items > 0:
                job.status = BatchStatus.PARTIAL
            elif result.failed_items == result.total_items:
                job.status = BatchStatus.FAILED
            else:
                job.status = BatchStatus.COMPLETED

            job.completed_at = datetime.now()
            job.progress = 100.0

            # Cache results
            if job.config.cache_results:
                self._cache_result(result)

            # Final notification
            if job.config.enable_notifications:
                self._send_completion_notification(job, result)

            return result

        except Exception as e:
            logger.exception(f"Batch job {job.job_id} failed: {e}")
            job.status = BatchStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now()

            raise

        finally:
            if job.job_id in self._processors:
                del self._processors[job.job_id]

    def _create_processor_fn(self, job: BatchJob) -> Callable:
        """Create processor function based on job type."""
        metadata = job.metadata
        processor_type = metadata.get('processor_type', 'llm')

        if processor_type == 'llm':
            prompt_template = metadata.get('prompt_template', '{{input}}')
            model = metadata.get('model', 'gpt-3.5-turbo')
            max_tokens = metadata.get('max_tokens', 1000)
            temperature = metadata.get('temperature', 0.7)

            def llm_processor(input_data: Dict[str, Any]) -> Dict[str, Any]:
                from coreapp.services.llm_service import llm_service
                from coreapp.services.prompt_chaining import TemplateEngine

                engine = TemplateEngine()
                prompt = engine.render(prompt_template, input_data)

                response = llm_service.generate(
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                return {
                    'output': response.get('text', ''),
                    'tokens': response.get('output_tokens', 0),
                    'cost': response.get('cost', 0.0),
                }

            return llm_processor

        elif processor_type == 'custom':
            custom_fn = metadata.get('custom_processor')
            if custom_fn:
                return custom_fn

        # Default: pass through
        return lambda x: {'output': x}

    def _on_item_complete(self, job: BatchJob, item: BatchItem):
        """Handle item completion."""
        job.processed_items = sum(
            1 for i in job.items if i.status in ['completed', 'failed']
        )
        job.successful_items = sum(
            1 for i in job.items if i.status == 'completed'
        )
        job.failed_items = sum(
            1 for i in job.items if i.status == 'failed'
        )
        job.progress = (job.processed_items / job.total_items) * 100

    # -------------------------------------------------------------------------
    # Job Queue (Background Processing)
    # -------------------------------------------------------------------------

    def _queue_job(self, job: BatchJob):
        """Add job to queue for background processing."""
        job.status = BatchStatus.QUEUED
        self._job_queue.put((job.priority.value, job.job_id))

        # Start worker if not running
        if not self._running:
            self.start_worker()

    def start_worker(self):
        """Start background worker thread."""
        if self._running:
            return

        self._running = True
        self._worker_thread = Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Batch processing worker started")

    def stop_worker(self):
        """Stop background worker."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info("Batch processing worker stopped")

    def _worker_loop(self):
        """Background worker loop."""
        while self._running:
            try:
                # Get next job (with timeout)
                try:
                    priority, job_id = self._job_queue.get(timeout=1)
                except Empty:
                    continue

                job = self.get_job(job_id)
                if not job:
                    continue

                if job.status == BatchStatus.CANCELLED:
                    continue

                # Execute job
                try:
                    self._execute_job_sync(job)
                except Exception as e:
                    logger.error(f"Background job {job_id} failed: {e}")

            except Exception as e:
                logger.error(f"Worker loop error: {e}")

    # -------------------------------------------------------------------------
    # Job Management
    # -------------------------------------------------------------------------

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get job by ID."""
        # Check memory first
        if job_id in self._jobs:
            return self._jobs[job_id]

        # Check cache
        cached = cache.get(f"batch_job:{job_id}")
        if cached:
            return cached

        return None

    def list_jobs(
        self,
        user_id: Optional[int] = None,
        status: Optional[BatchStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List jobs with optional filters."""
        jobs = list(self._jobs.values())

        if user_id:
            jobs = [j for j in jobs if j.user_id == user_id]

        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return [j.to_dict() for j in jobs[:limit]]

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        job = self.get_job(job_id)
        if not job:
            return False

        if job.status in [BatchStatus.COMPLETED, BatchStatus.FAILED]:
            return False

        job.status = BatchStatus.CANCELLED

        # Stop processor if running
        if job_id in self._processors:
            self._processors[job_id].stop()

        logger.info(f"Cancelled batch job {job_id}")
        return True

    def pause_job(self, job_id: str) -> bool:
        """Pause a running job."""
        job = self.get_job(job_id)
        if not job:
            return False

        if job.status != BatchStatus.PROCESSING:
            return False

        job.status = BatchStatus.PAUSED

        if job_id in self._processors:
            self._processors[job_id].stop()

        return True

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = self.get_job(job_id)
        if not job:
            return False

        if job.status != BatchStatus.PAUSED:
            return False

        # Re-queue job
        self._queue_job(job)
        return True

    def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            cache.delete(f"batch_job:{job_id}")
            cache.delete(f"batch_result:{job_id}")
            return True
        return False

    # -------------------------------------------------------------------------
    # Results
    # -------------------------------------------------------------------------

    def get_results(self, job_id: str) -> Optional[BatchResult]:
        """Get results for a completed job."""
        # Check cache
        cached = cache.get(f"batch_result:{job_id}")
        if cached:
            return cached

        job = self.get_job(job_id)
        if not job:
            return None

        if job.status not in [BatchStatus.COMPLETED, BatchStatus.PARTIAL]:
            return None

        # Build result from job
        results = [
            {
                'item_id': item.item_id,
                'output': item.output,
            }
            for item in job.items
            if item.status == 'completed'
        ]

        errors = [
            {
                'item_id': item.item_id,
                'error': item.error,
            }
            for item in job.items
            if item.status == 'failed'
        ]

        return BatchResult(
            job_id=job_id,
            success=job.status == BatchStatus.COMPLETED,
            total_items=job.total_items,
            successful_items=job.successful_items,
            failed_items=job.failed_items,
            results=results,
            total_tokens=job.total_tokens,
            total_cost=job.total_cost,
            processing_time_ms=0,
            errors=errors,
        )

    def get_item_result(
        self,
        job_id: str,
        item_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get result for a specific item."""
        job = self.get_job(job_id)
        if not job:
            return None

        for item in job.items:
            if item.item_id == item_id:
                return item.to_dict()

        return None

    # -------------------------------------------------------------------------
    # Caching
    # -------------------------------------------------------------------------

    def _cache_job(self, job: BatchJob):
        """Cache job state."""
        cache.set(
            f"batch_job:{job.job_id}",
            job,
            timeout=job.config.cache_ttl,
        )

    def _cache_result(self, result: BatchResult):
        """Cache job result."""
        cache.set(
            f"batch_result:{result.job_id}",
            result,
            timeout=3600,
        )

    # -------------------------------------------------------------------------
    # Notifications
    # -------------------------------------------------------------------------

    def _send_progress_notification(self, job: BatchJob):
        """Send progress notification via WebSocket."""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"batch_user_{job.user_id}",
                    {
                        'type': 'batch.progress',
                        'job_id': job.job_id,
                        'progress': job.progress,
                        'processed': job.processed_items,
                        'total': job.total_items,
                        'status': job.status.value,
                    }
                )
        except Exception as e:
            logger.debug(f"Progress notification failed: {e}")

    def _send_completion_notification(self, job: BatchJob, result: BatchResult):
        """Send completion notification."""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"batch_user_{job.user_id}",
                    {
                        'type': 'batch.completed',
                        'job_id': job.job_id,
                        'status': job.status.value,
                        'successful': result.successful_items,
                        'failed': result.failed_items,
                        'total_cost': result.total_cost,
                    }
                )
        except Exception as e:
            logger.debug(f"Completion notification failed: {e}")


# =============================================================================
# Batch Templates
# =============================================================================

class BatchTemplates:
    """Pre-built batch job templates."""

    @staticmethod
    def summarize_documents(
        documents: List[Dict[str, str]],
        user_id: int,
    ) -> BatchJob:
        """Create batch job for summarizing documents."""
        service = batch_processing_service

        return service.create_job(
            user_id=user_id,
            name="Document Summarization",
            items=documents,
            prompt_template="""Summarize the following document in 3-5 sentences:

Title: {{title}}
Content: {{content}}

Summary:""",
            model='gpt-3.5-turbo',
            max_tokens=500,
        )

    @staticmethod
    def translate_texts(
        texts: List[Dict[str, str]],
        target_language: str,
        user_id: int,
    ) -> BatchJob:
        """Create batch job for translation."""
        service = batch_processing_service

        items = [
            {'text': t['text'], 'target_language': target_language}
            for t in texts
        ]

        return service.create_job(
            user_id=user_id,
            name=f"Translation to {target_language}",
            items=items,
            prompt_template="""Translate the following text to {{target_language}}:

{{text}}

Translation:""",
            model='gpt-4',
            max_tokens=1000,
        )

    @staticmethod
    def classify_content(
        items: List[Dict[str, str]],
        categories: List[str],
        user_id: int,
    ) -> BatchJob:
        """Create batch job for content classification."""
        service = batch_processing_service

        categories_str = ', '.join(categories)
        items_with_categories = [
            {**item, 'categories': categories_str}
            for item in items
        ]

        return service.create_job(
            user_id=user_id,
            name="Content Classification",
            items=items_with_categories,
            prompt_template="""Classify the following content into one of these categories: {{categories}}

Content: {{content}}

Respond with only the category name.""",
            model='gpt-3.5-turbo',
            max_tokens=50,
        )

    @staticmethod
    def extract_entities(
        texts: List[Dict[str, str]],
        entity_types: List[str],
        user_id: int,
    ) -> BatchJob:
        """Create batch job for entity extraction."""
        service = batch_processing_service

        entity_str = ', '.join(entity_types)
        items = [
            {'text': t['text'], 'entity_types': entity_str}
            for t in texts
        ]

        return service.create_job(
            user_id=user_id,
            name="Entity Extraction",
            items=items,
            prompt_template="""Extract the following entity types from the text: {{entity_types}}

Text: {{text}}

Return a JSON object with entity types as keys and lists of extracted entities as values.""",
            model='gpt-4',
            max_tokens=500,
        )

    @staticmethod
    def generate_embeddings(
        texts: List[Dict[str, str]],
        user_id: int,
    ) -> BatchJob:
        """Create batch job for generating embeddings."""
        service = batch_processing_service

        def embedding_processor(input_data: Dict[str, Any]) -> Dict[str, Any]:
            from coreapp.services.llm_service import llm_service

            embedding = llm_service.get_embedding(input_data['text'])

            return {
                'output': embedding,
                'tokens': len(input_data['text'].split()) // 4,
                'cost': 0.0001,
            }

        return service.create_job(
            user_id=user_id,
            name="Embedding Generation",
            items=texts,
            processor_type='custom',
            config=BatchConfig(
                max_concurrent=10,
                rate_limit_per_minute=3000,
            ),
            metadata={
                'processor_type': 'custom',
                'custom_processor': embedding_processor,
            }
        )


# =============================================================================
# Singleton Instance
# =============================================================================

batch_processing_service = BatchProcessingService()
batch_templates = BatchTemplates()
