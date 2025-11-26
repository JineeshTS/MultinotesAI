"""
Advanced AI Features API Views for MultinotesAI.

This module provides REST API endpoints for:
- Multi-model comparison
- Prompt chaining
- Batch processing
- Scheduled generations

WBS Items:
- 6.1.1: Multi-model comparison
- 6.1.3: Prompt chaining
- 6.1.4: Batch processing
- 6.1.5: Scheduled generations
"""

import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


# =============================================================================
# Multi-Model Comparison Views
# =============================================================================

class ModelComparisonView(APIView):
    """
    Compare responses from multiple AI models.

    POST /api/ai/compare/
    {
        "prompt": "Explain quantum computing",
        "models": ["gpt-4", "claude-3-sonnet", "gemini-pro"],
        "system_prompt": "You are a helpful assistant",
        "max_tokens": 1000,
        "temperature": 0.7
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Run comparison across models."""
        from coreapp.services.multi_model_service import multi_model_service

        prompt = request.data.get('prompt', '')
        models = request.data.get('models')
        system_prompt = request.data.get('system_prompt')
        max_tokens = request.data.get('max_tokens')
        temperature = request.data.get('temperature', 0.7)
        parallel = request.data.get('parallel', True)

        if not prompt:
            return Response(
                {'error': 'Prompt is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = multi_model_service.compare(
                prompt=prompt,
                models=models,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                parallel=parallel,
            )

            return Response(result.to_dict())

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Model comparison failed")
            return Response(
                {'error': 'Model comparison failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuickCompareView(APIView):
    """
    Quick comparison using recommended models for task type.

    POST /api/ai/compare/quick/
    {
        "prompt": "Write a function to sort an array",
        "task_type": "code_generation"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Quick comparison based on task type."""
        from coreapp.services.multi_model_service import multi_model_service

        prompt = request.data.get('prompt', '')
        task_type = request.data.get('task_type', 'general')

        if not prompt:
            return Response(
                {'error': 'Prompt is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = multi_model_service.quick_compare(
                prompt=prompt,
                task_type=task_type,
            )

            return Response(result.to_dict())

        except Exception as e:
            logger.exception("Quick comparison failed")
            return Response(
                {'error': 'Comparison failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AvailableModelsView(APIView):
    """
    Get available models for comparison.

    GET /api/ai/compare/models/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List available models."""
        from coreapp.services.multi_model_service import multi_model_service

        models = multi_model_service.get_available_models()
        return Response({'models': models})


class CostEstimationView(APIView):
    """
    Estimate costs for prompt across models.

    POST /api/ai/compare/estimate/
    {
        "prompt": "Your prompt text",
        "models": ["gpt-4", "gpt-3.5-turbo"]
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Estimate costs."""
        from coreapp.services.multi_model_service import multi_model_service

        prompt = request.data.get('prompt', '')
        models = request.data.get('models')

        if not prompt:
            return Response(
                {'error': 'Prompt is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            estimates = multi_model_service.estimate_costs(
                prompt=prompt,
                models=models,
            )

            return Response({'estimates': estimates})

        except Exception as e:
            logger.exception("Cost estimation failed")
            return Response(
                {'error': 'Estimation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Prompt Chaining Views
# =============================================================================

class ExecuteChainView(APIView):
    """
    Execute a prompt chain.

    POST /api/ai/chain/execute/
    {
        "name": "Research Chain",
        "steps": [
            {
                "name": "research",
                "prompt_template": "Research {{topic}}",
                "output_variable": "research_output"
            },
            {
                "name": "summarize",
                "prompt_template": "Summarize: {{research_output}}",
                "output_variable": "summary"
            }
        ],
        "variables": {
            "topic": "artificial intelligence"
        }
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Execute a chain."""
        from coreapp.services.prompt_chaining import (
            prompt_chaining_service,
            PromptChain,
            ChainStep,
            StepType,
        )

        name = request.data.get('name', 'Custom Chain')
        steps_data = request.data.get('steps', [])
        variables = request.data.get('variables', {})
        stop_on_error = request.data.get('stop_on_error', True)

        if not steps_data:
            return Response(
                {'error': 'At least one step is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Build chain steps
            steps = []
            for step_data in steps_data:
                step = ChainStep(
                    name=step_data.get('name', f'step_{len(steps)}'),
                    step_type=StepType.PROMPT,
                    prompt_template=step_data.get('prompt_template', ''),
                    model=step_data.get('model', 'gpt-3.5-turbo'),
                    max_tokens=step_data.get('max_tokens', 1000),
                    temperature=step_data.get('temperature', 0.7),
                    system_prompt=step_data.get('system_prompt'),
                    output_variable=step_data.get('output_variable', 'output'),
                )
                steps.append(step)

            # Create and execute chain
            chain = PromptChain(
                name=name,
                description='User-defined chain',
                steps=steps,
                stop_on_error=stop_on_error,
            )

            result = prompt_chaining_service.execute(chain, variables)

            return Response(result.to_dict())

        except Exception as e:
            logger.exception("Chain execution failed")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChainTemplatesView(APIView):
    """
    Get available chain templates.

    GET /api/ai/chain/templates/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List available chain templates."""
        from coreapp.services.prompt_chaining import chain_templates

        templates = [
            {
                'id': 'research_and_summarize',
                'name': 'Research and Summarize',
                'description': 'Research a topic, extract key points, and summarize',
                'variables': ['topic'],
            },
            {
                'id': 'content_creation',
                'name': 'Content Creation',
                'description': 'Create, review, and refine content',
                'variables': ['topic', 'content_type', 'audience', 'tone', 'length'],
            },
            {
                'id': 'code_review',
                'name': 'Code Review',
                'description': 'Review code for issues and suggest improvements',
                'variables': ['code', 'language'],
            },
            {
                'id': 'translation_and_localization',
                'name': 'Translation and Localization',
                'description': 'Translate content with cultural adaptation',
                'variables': ['content', 'source_language', 'target_language', 'target_region'],
            },
            {
                'id': 'data_analysis',
                'name': 'Data Analysis',
                'description': 'Analyze data and generate actionable insights',
                'variables': ['data'],
            },
        ]

        return Response({'templates': templates})


class ExecuteTemplateChainView(APIView):
    """
    Execute a pre-built chain template.

    POST /api/ai/chain/templates/<template_id>/execute/
    {
        "variables": {
            "topic": "machine learning"
        }
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, template_id):
        """Execute a template chain."""
        from coreapp.services.prompt_chaining import (
            prompt_chaining_service,
            chain_templates,
        )

        variables = request.data.get('variables', {})

        template_map = {
            'research_and_summarize': chain_templates.research_and_summarize,
            'content_creation': chain_templates.content_creation,
            'code_review': chain_templates.code_review,
            'translation_and_localization': chain_templates.translation_and_localization,
            'data_analysis': chain_templates.data_analysis,
        }

        if template_id not in template_map:
            return Response(
                {'error': f'Unknown template: {template_id}'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            chain = template_map[template_id]()
            result = prompt_chaining_service.execute(chain, variables)

            return Response(result.to_dict())

        except Exception as e:
            logger.exception(f"Template chain {template_id} failed")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChainStatusView(APIView):
    """
    Get chain execution status.

    GET /api/ai/chain/<chain_id>/status/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, chain_id):
        """Get chain status."""
        from coreapp.services.prompt_chaining import prompt_chaining_service

        result = prompt_chaining_service.get_chain_status(chain_id)

        if not result:
            return Response(
                {'error': 'Chain not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(result.to_dict())


# =============================================================================
# Batch Processing Views
# =============================================================================

class CreateBatchJobView(APIView):
    """
    Create a batch processing job.

    POST /api/ai/batch/
    {
        "name": "Summarize Articles",
        "items": [
            {"text": "Article 1 content..."},
            {"text": "Article 2 content..."}
        ],
        "prompt_template": "Summarize: {{text}}",
        "model": "gpt-3.5-turbo",
        "priority": "normal"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a batch job."""
        from coreapp.services.batch_processing import (
            batch_processing_service,
            BatchPriority,
            BatchConfig,
        )

        name = request.data.get('name', 'Batch Job')
        items = request.data.get('items', [])
        prompt_template = request.data.get('prompt_template')
        model = request.data.get('model', 'gpt-3.5-turbo')
        max_tokens = request.data.get('max_tokens', 1000)
        temperature = request.data.get('temperature', 0.7)
        priority_str = request.data.get('priority', 'normal')

        if not items:
            return Response(
                {'error': 'Items are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not prompt_template:
            return Response(
                {'error': 'Prompt template is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            priority = BatchPriority[priority_str.upper()]
        except KeyError:
            priority = BatchPriority.NORMAL

        try:
            job = batch_processing_service.create_job(
                user_id=request.user.id,
                name=name,
                items=items,
                prompt_template=prompt_template,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                priority=priority,
            )

            return Response(job.to_dict(), status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Failed to create batch job")
            return Response(
                {'error': 'Failed to create job'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExecuteBatchJobView(APIView):
    """
    Execute a batch job.

    POST /api/ai/batch/<job_id>/execute/
    {
        "async": true
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
        """Execute a batch job."""
        from coreapp.services.batch_processing import batch_processing_service

        async_execution = request.data.get('async', True)

        try:
            job = batch_processing_service.get_job(job_id)
            if not job:
                return Response(
                    {'error': 'Job not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check ownership
            if job.user_id != request.user.id:
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            result = batch_processing_service.execute_job(
                job_id=job_id,
                async_execution=async_execution,
            )

            if async_execution:
                return Response({
                    'message': 'Job queued for execution',
                    'job_id': job_id,
                    'status': 'queued',
                })

            return Response(result.to_dict())

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"Failed to execute batch job {job_id}")
            return Response(
                {'error': 'Execution failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BatchJobStatusView(APIView):
    """
    Get batch job status.

    GET /api/ai/batch/<job_id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        """Get job status."""
        from coreapp.services.batch_processing import batch_processing_service

        job = batch_processing_service.get_job(job_id)
        if not job:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if job.user_id != request.user.id:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response(job.to_dict())


class BatchJobResultsView(APIView):
    """
    Get batch job results.

    GET /api/ai/batch/<job_id>/results/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        """Get job results."""
        from coreapp.services.batch_processing import batch_processing_service

        job = batch_processing_service.get_job(job_id)
        if not job:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if job.user_id != request.user.id:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        result = batch_processing_service.get_results(job_id)
        if not result:
            return Response(
                {'error': 'Results not available yet'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(result.to_dict())


class ListBatchJobsView(APIView):
    """
    List batch jobs.

    GET /api/ai/batch/?status=processing&limit=50
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List jobs."""
        from coreapp.services.batch_processing import (
            batch_processing_service,
            BatchStatus,
        )

        status_str = request.query_params.get('status')
        limit = int(request.query_params.get('limit', 50))

        status_filter = None
        if status_str:
            try:
                status_filter = BatchStatus[status_str.upper()]
            except KeyError:
                pass

        jobs = batch_processing_service.list_jobs(
            user_id=request.user.id,
            status=status_filter,
            limit=limit,
        )

        return Response({'jobs': jobs})


class CancelBatchJobView(APIView):
    """
    Cancel a batch job.

    POST /api/ai/batch/<job_id>/cancel/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
        """Cancel a job."""
        from coreapp.services.batch_processing import batch_processing_service

        job = batch_processing_service.get_job(job_id)
        if not job:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if job.user_id != request.user.id:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        if batch_processing_service.cancel_job(job_id):
            return Response({'message': 'Job cancelled'})

        return Response(
            {'error': 'Cannot cancel job'},
            status=status.HTTP_400_BAD_REQUEST
        )


# =============================================================================
# Scheduled Generation Views
# =============================================================================

class CreateScheduleView(APIView):
    """
    Create a scheduled generation.

    POST /api/ai/schedule/
    {
        "name": "Daily Summary",
        "prompt_template": "Generate a summary for {{date}}",
        "schedule": "0 9 * * *",
        "model": "gpt-4",
        "timezone": "America/New_York"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a schedule."""
        from coreapp.services.scheduled_generations import (
            scheduled_generation_service,
            RepeatInterval,
        )

        name = request.data.get('name', 'Scheduled Generation')
        description = request.data.get('description', '')
        prompt_template = request.data.get('prompt_template')
        schedule = request.data.get('schedule')
        model = request.data.get('model', 'gpt-3.5-turbo')
        max_tokens = request.data.get('max_tokens', 1000)
        temperature = request.data.get('temperature', 0.7)
        system_prompt = request.data.get('system_prompt')
        variables = request.data.get('variables', {})
        timezone_str = request.data.get('timezone', 'UTC')
        repeat_interval_str = request.data.get('repeat_interval', 'custom')
        max_executions = request.data.get('max_executions')
        webhook_url = request.data.get('webhook_url')

        if not prompt_template:
            return Response(
                {'error': 'Prompt template is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not schedule:
            return Response(
                {'error': 'Schedule is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            repeat_interval = RepeatInterval[repeat_interval_str.upper()]
        except KeyError:
            repeat_interval = RepeatInterval.CUSTOM

        try:
            scheduled_gen = scheduled_generation_service.create_schedule(
                user_id=request.user.id,
                name=name,
                description=description,
                prompt_template=prompt_template,
                schedule=schedule,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
                variables=variables,
                timezone_str=timezone_str,
                repeat_interval=repeat_interval,
                max_executions=max_executions,
                webhook_url=webhook_url,
            )

            return Response(scheduled_gen.to_dict(), status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Failed to create schedule")
            return Response(
                {'error': 'Failed to create schedule'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListSchedulesView(APIView):
    """
    List scheduled generations.

    GET /api/ai/schedule/?status=active&limit=50
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List schedules."""
        from coreapp.services.scheduled_generations import (
            scheduled_generation_service,
            ScheduleStatus,
        )

        status_str = request.query_params.get('status')
        limit = int(request.query_params.get('limit', 50))

        status_filter = None
        if status_str:
            try:
                status_filter = ScheduleStatus[status_str.upper()]
            except KeyError:
                pass

        schedules = scheduled_generation_service.list_schedules(
            user_id=request.user.id,
            status=status_filter,
            limit=limit,
        )

        return Response({'schedules': schedules})


class ScheduleDetailView(APIView):
    """
    Get, update, or delete a schedule.

    GET /api/ai/schedule/<schedule_id>/
    PATCH /api/ai/schedule/<schedule_id>/
    DELETE /api/ai/schedule/<schedule_id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, schedule_id):
        """Get schedule details."""
        from coreapp.services.scheduled_generations import scheduled_generation_service

        schedule = scheduled_generation_service.get_schedule(schedule_id)
        if not schedule:
            return Response(
                {'error': 'Schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if schedule.user_id != request.user.id:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response(schedule.to_detailed_dict())

    def patch(self, request, schedule_id):
        """Update schedule."""
        from coreapp.services.scheduled_generations import scheduled_generation_service

        schedule = scheduled_generation_service.get_schedule(schedule_id)
        if not schedule:
            return Response(
                {'error': 'Schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if schedule.user_id != request.user.id:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            updated = scheduled_generation_service.update_schedule(
                schedule_id,
                **request.data
            )

            return Response(updated)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def delete(self, request, schedule_id):
        """Delete schedule."""
        from coreapp.services.scheduled_generations import scheduled_generation_service

        schedule = scheduled_generation_service.get_schedule(schedule_id)
        if not schedule:
            return Response(
                {'error': 'Schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if schedule.user_id != request.user.id:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        scheduled_generation_service.delete_schedule(schedule_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExecuteScheduleNowView(APIView):
    """
    Execute a schedule immediately.

    POST /api/ai/schedule/<schedule_id>/execute/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, schedule_id):
        """Execute schedule now."""
        from coreapp.services.scheduled_generations import scheduled_generation_service

        schedule = scheduled_generation_service.get_schedule(schedule_id)
        if not schedule:
            return Response(
                {'error': 'Schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if schedule.user_id != request.user.id:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            result = scheduled_generation_service.execute_now(schedule_id)
            if result:
                return Response(result.to_dict())

            return Response(
                {'error': 'Execution failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except Exception as e:
            logger.exception(f"Failed to execute schedule {schedule_id}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PauseScheduleView(APIView):
    """
    Pause a schedule.

    POST /api/ai/schedule/<schedule_id>/pause/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, schedule_id):
        """Pause schedule."""
        from coreapp.services.scheduled_generations import scheduled_generation_service

        schedule = scheduled_generation_service.get_schedule(schedule_id)
        if not schedule:
            return Response(
                {'error': 'Schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if schedule.user_id != request.user.id:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        if scheduled_generation_service.pause_schedule(schedule_id):
            return Response({'message': 'Schedule paused'})

        return Response(
            {'error': 'Cannot pause schedule'},
            status=status.HTTP_400_BAD_REQUEST
        )


class ResumeScheduleView(APIView):
    """
    Resume a paused schedule.

    POST /api/ai/schedule/<schedule_id>/resume/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, schedule_id):
        """Resume schedule."""
        from coreapp.services.scheduled_generations import scheduled_generation_service

        schedule = scheduled_generation_service.get_schedule(schedule_id)
        if not schedule:
            return Response(
                {'error': 'Schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if schedule.user_id != request.user.id:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        if scheduled_generation_service.resume_schedule(schedule_id):
            return Response({'message': 'Schedule resumed'})

        return Response(
            {'error': 'Cannot resume schedule'},
            status=status.HTTP_400_BAD_REQUEST
        )


class ScheduleHistoryView(APIView):
    """
    Get schedule execution history.

    GET /api/ai/schedule/<schedule_id>/history/?limit=50
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, schedule_id):
        """Get execution history."""
        from coreapp.services.scheduled_generations import scheduled_generation_service

        schedule = scheduled_generation_service.get_schedule(schedule_id)
        if not schedule:
            return Response(
                {'error': 'Schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if schedule.user_id != request.user.id:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        limit = int(request.query_params.get('limit', 50))

        history = scheduled_generation_service.get_execution_history(
            schedule_id,
            limit=limit,
        )

        stats = scheduled_generation_service.get_execution_stats(schedule_id)

        return Response({
            'history': history,
            'stats': stats,
        })


class ScheduleTemplatesView(APIView):
    """
    Get schedule templates.

    GET /api/ai/schedule/templates/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List schedule templates."""
        templates = [
            {
                'id': 'daily_summary',
                'name': 'Daily Summary',
                'description': 'Generate daily summary at specified hour',
                'default_schedule': '0 9 * * *',
                'variables': ['hour', 'prompt'],
            },
            {
                'id': 'weekly_report',
                'name': 'Weekly Report',
                'description': 'Generate weekly report on specified day',
                'default_schedule': '0 8 * * 1',
                'variables': ['day_of_week', 'hour', 'topics'],
            },
            {
                'id': 'hourly_monitoring',
                'name': 'Hourly Monitoring',
                'description': 'Run hourly checks',
                'default_schedule': '0 * * * *',
                'variables': ['prompt'],
            },
            {
                'id': 'content_generation',
                'name': 'Content Generation',
                'description': 'Automated content creation',
                'default_schedule': '0 10 * * 1,3,5',
                'variables': ['content_type', 'topics'],
            },
        ]

        return Response({'templates': templates})
