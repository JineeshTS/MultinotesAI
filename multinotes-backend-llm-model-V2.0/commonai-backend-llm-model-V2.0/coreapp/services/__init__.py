"""
Services package for MultinotesAI.

This package contains business logic services separated from views:
- LLM Service: Multi-provider AI text generation
- Storage Service: File storage and management
- Notification Service: In-app and email notifications
- Webhook Service: Webhook event dispatching
- Search Service: Full-text and semantic search
- Prompt Service: Smart prompt suggestions
- Analytics Service: Usage tracking and metrics
"""

from .llm_service import LLMService, llm_service
from .storage_service import StorageService, storage_service
from .notification_service import NotificationService, notification_service
from .webhook_service import WebhookService, webhook_service
from .search_service import SearchService, search_service
from .prompt_service import PromptSuggestionService, prompt_service
from .analytics_service import AnalyticsService, analytics_service

__all__ = [
    # LLM
    'LLMService',
    'llm_service',
    # Storage
    'StorageService',
    'storage_service',
    # Notifications
    'NotificationService',
    'notification_service',
    # Webhooks
    'WebhookService',
    'webhook_service',
    # Search
    'SearchService',
    'search_service',
    # Prompts
    'PromptSuggestionService',
    'prompt_service',
    # Analytics
    'AnalyticsService',
    'analytics_service',
]
