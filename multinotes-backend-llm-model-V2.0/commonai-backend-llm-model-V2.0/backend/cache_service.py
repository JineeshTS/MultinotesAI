"""
Redis caching service for MultinotesAI.

This module provides centralized caching functionality for:
- LLM model lists
- User subscriptions
- Folder hierarchies
- Category data
- Session data
"""

from django.core.cache import cache
from django.conf import settings
from functools import wraps
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Cache Key Prefixes
# =============================================================================

class CacheKeys:
    """Centralized cache key management."""

    # Prefixes
    LLM_MODEL = "llm_model"
    LLM_LIST = "llm_list"
    USER_SUBSCRIPTION = "user_sub"
    USER_FOLDERS = "user_folders"
    USER_STORAGE = "user_storage"
    CATEGORIES = "categories"
    PLAN_LIST = "plan_list"
    CONTENT = "content"
    SHARE = "share"

    @classmethod
    def llm_model(cls, model_id: int) -> str:
        """Cache key for a specific LLM model."""
        return f"{cls.LLM_MODEL}:{model_id}"

    @classmethod
    def llm_list(cls, user_id: int = None, provider: str = None) -> str:
        """Cache key for LLM model list."""
        key = cls.LLM_LIST
        if user_id:
            key += f":user:{user_id}"
        if provider:
            key += f":provider:{provider}"
        return key

    @classmethod
    def user_subscription(cls, user_id: int) -> str:
        """Cache key for user subscription."""
        return f"{cls.USER_SUBSCRIPTION}:{user_id}"

    @classmethod
    def user_folders(cls, user_id: int, folder_id: int = None) -> str:
        """Cache key for user folders."""
        key = f"{cls.USER_FOLDERS}:{user_id}"
        if folder_id:
            key += f":folder:{folder_id}"
        return key

    @classmethod
    def user_storage(cls, user_id: int) -> str:
        """Cache key for user storage usage."""
        return f"{cls.USER_STORAGE}:{user_id}"

    @classmethod
    def categories(cls, category_type: str = None) -> str:
        """Cache key for categories."""
        if category_type:
            return f"{cls.CATEGORIES}:{category_type}"
        return cls.CATEGORIES

    @classmethod
    def plan_list(cls) -> str:
        """Cache key for subscription plans."""
        return cls.PLAN_LIST

    @classmethod
    def content(cls, content_id: int) -> str:
        """Cache key for content item."""
        return f"{cls.CONTENT}:{content_id}"

    @classmethod
    def share(cls, share_code: str) -> str:
        """Cache key for shared content."""
        return f"{cls.SHARE}:{share_code}"


# =============================================================================
# Cache Timeouts (in seconds)
# =============================================================================

class CacheTimeout:
    """Centralized cache timeout configuration."""

    SHORT = 60 * 5           # 5 minutes
    MEDIUM = 60 * 15         # 15 minutes
    STANDARD = 60 * 30       # 30 minutes
    LONG = 60 * 60           # 1 hour
    VERY_LONG = 60 * 60 * 6  # 6 hours
    DAY = 60 * 60 * 24       # 24 hours

    # Specific timeouts
    LLM_MODEL = LONG
    LLM_LIST = MEDIUM
    SUBSCRIPTION = STANDARD
    FOLDERS = MEDIUM
    STORAGE = SHORT
    CATEGORIES = VERY_LONG
    PLANS = DAY
    CONTENT = MEDIUM
    SHARE = LONG


# =============================================================================
# Cache Service Class
# =============================================================================

class CacheService:
    """
    Centralized caching service for the application.

    Usage:
        from backend.cache_service import cache_service

        # Get cached data
        data = cache_service.get_llm_list(user_id=1)

        # Set cached data
        cache_service.set_llm_list(models_data, user_id=1)

        # Invalidate cache
        cache_service.invalidate_llm_list(user_id=1)
    """

    def __init__(self):
        self.cache = cache
        self.enabled = getattr(settings, 'CACHE_ENABLED', True)

    # -------------------------------------------------------------------------
    # Generic Methods
    # -------------------------------------------------------------------------

    def get(self, key: str, default=None):
        """Get value from cache."""
        if not self.enabled:
            return default
        try:
            return self.cache.get(key, default)
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return default

    def set(self, key: str, value, timeout: int = CacheTimeout.STANDARD):
        """Set value in cache."""
        if not self.enabled:
            return False
        try:
            self.cache.set(key, value, timeout)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str):
        """Delete value from cache."""
        try:
            self.cache.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern."""
        try:
            # For Redis backend
            if hasattr(self.cache, 'delete_pattern'):
                self.cache.delete_pattern(pattern)
            # For other backends, we can't do pattern matching
            return True
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return False

    # -------------------------------------------------------------------------
    # LLM Model Methods
    # -------------------------------------------------------------------------

    def get_llm_model(self, model_id: int):
        """Get cached LLM model."""
        return self.get(CacheKeys.llm_model(model_id))

    def set_llm_model(self, model_id: int, data):
        """Cache LLM model."""
        return self.set(CacheKeys.llm_model(model_id), data, CacheTimeout.LLM_MODEL)

    def invalidate_llm_model(self, model_id: int):
        """Invalidate LLM model cache."""
        return self.delete(CacheKeys.llm_model(model_id))

    def get_llm_list(self, user_id: int = None, provider: str = None):
        """Get cached LLM model list."""
        return self.get(CacheKeys.llm_list(user_id, provider))

    def set_llm_list(self, data, user_id: int = None, provider: str = None):
        """Cache LLM model list."""
        return self.set(
            CacheKeys.llm_list(user_id, provider),
            data,
            CacheTimeout.LLM_LIST
        )

    def invalidate_llm_list(self, user_id: int = None):
        """Invalidate LLM model list cache."""
        self.delete_pattern(f"{CacheKeys.LLM_LIST}:*")
        if user_id:
            self.delete(CacheKeys.llm_list(user_id))

    # -------------------------------------------------------------------------
    # Subscription Methods
    # -------------------------------------------------------------------------

    def get_subscription(self, user_id: int):
        """Get cached user subscription."""
        return self.get(CacheKeys.user_subscription(user_id))

    def set_subscription(self, user_id: int, data):
        """Cache user subscription."""
        return self.set(
            CacheKeys.user_subscription(user_id),
            data,
            CacheTimeout.SUBSCRIPTION
        )

    def invalidate_subscription(self, user_id: int):
        """Invalidate user subscription cache."""
        return self.delete(CacheKeys.user_subscription(user_id))

    # -------------------------------------------------------------------------
    # Folder Methods
    # -------------------------------------------------------------------------

    def get_folders(self, user_id: int, folder_id: int = None):
        """Get cached user folders."""
        return self.get(CacheKeys.user_folders(user_id, folder_id))

    def set_folders(self, user_id: int, data, folder_id: int = None):
        """Cache user folders."""
        return self.set(
            CacheKeys.user_folders(user_id, folder_id),
            data,
            CacheTimeout.FOLDERS
        )

    def invalidate_folders(self, user_id: int):
        """Invalidate all folder caches for user."""
        self.delete_pattern(f"{CacheKeys.USER_FOLDERS}:{user_id}:*")
        return self.delete(CacheKeys.user_folders(user_id))

    # -------------------------------------------------------------------------
    # Storage Methods
    # -------------------------------------------------------------------------

    def get_storage(self, user_id: int):
        """Get cached user storage usage."""
        return self.get(CacheKeys.user_storage(user_id))

    def set_storage(self, user_id: int, data):
        """Cache user storage usage."""
        return self.set(
            CacheKeys.user_storage(user_id),
            data,
            CacheTimeout.STORAGE
        )

    def invalidate_storage(self, user_id: int):
        """Invalidate user storage cache."""
        return self.delete(CacheKeys.user_storage(user_id))

    # -------------------------------------------------------------------------
    # Category Methods
    # -------------------------------------------------------------------------

    def get_categories(self, category_type: str = None):
        """Get cached categories."""
        return self.get(CacheKeys.categories(category_type))

    def set_categories(self, data, category_type: str = None):
        """Cache categories."""
        return self.set(
            CacheKeys.categories(category_type),
            data,
            CacheTimeout.CATEGORIES
        )

    def invalidate_categories(self):
        """Invalidate all category caches."""
        return self.delete_pattern(f"{CacheKeys.CATEGORIES}:*")

    # -------------------------------------------------------------------------
    # Plan Methods
    # -------------------------------------------------------------------------

    def get_plans(self):
        """Get cached subscription plans."""
        return self.get(CacheKeys.plan_list())

    def set_plans(self, data):
        """Cache subscription plans."""
        return self.set(CacheKeys.plan_list(), data, CacheTimeout.PLANS)

    def invalidate_plans(self):
        """Invalidate plans cache."""
        return self.delete(CacheKeys.plan_list())

    # -------------------------------------------------------------------------
    # Content Methods
    # -------------------------------------------------------------------------

    def get_content(self, content_id: int):
        """Get cached content item."""
        return self.get(CacheKeys.content(content_id))

    def set_content(self, content_id: int, data):
        """Cache content item."""
        return self.set(CacheKeys.content(content_id), data, CacheTimeout.CONTENT)

    def invalidate_content(self, content_id: int):
        """Invalidate content cache."""
        return self.delete(CacheKeys.content(content_id))

    # -------------------------------------------------------------------------
    # Share Methods
    # -------------------------------------------------------------------------

    def get_share(self, share_code: str):
        """Get cached shared content."""
        return self.get(CacheKeys.share(share_code))

    def set_share(self, share_code: str, data):
        """Cache shared content."""
        return self.set(CacheKeys.share(share_code), data, CacheTimeout.SHARE)

    def invalidate_share(self, share_code: str):
        """Invalidate share cache."""
        return self.delete(CacheKeys.share(share_code))

    # -------------------------------------------------------------------------
    # User-level Invalidation
    # -------------------------------------------------------------------------

    def invalidate_user_caches(self, user_id: int):
        """Invalidate all caches for a user."""
        self.invalidate_subscription(user_id)
        self.invalidate_folders(user_id)
        self.invalidate_storage(user_id)
        self.invalidate_llm_list(user_id)


# =============================================================================
# Decorators
# =============================================================================

def cached(key_func, timeout=CacheTimeout.STANDARD):
    """
    Decorator to cache function results.

    Usage:
        @cached(lambda user_id: f"my_data:{user_id}", timeout=300)
        def get_my_data(user_id):
            return expensive_computation()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = key_func(*args, **kwargs)
            result = cache_service.get(cache_key)

            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache_service.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def cache_response(key_prefix: str, timeout: int = CacheTimeout.STANDARD,
                   user_specific: bool = False):
    """
    Decorator for caching API view responses.

    Usage:
        class MyView(APIView):
            @cache_response('my_endpoint', timeout=300, user_specific=True)
            def get(self, request):
                return Response(data)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Build cache key
            cache_key = key_prefix
            if user_specific and request.user.is_authenticated:
                cache_key += f":user:{request.user.id}"

            # Add query params to key
            if request.query_params:
                params_hash = hashlib.md5(
                    json.dumps(dict(request.query_params), sort_keys=True).encode()
                ).hexdigest()[:8]
                cache_key += f":params:{params_hash}"

            # Check cache
            cached_response = cache_service.get(cache_key)
            if cached_response is not None:
                return cached_response

            # Get fresh response
            response = func(self, request, *args, **kwargs)

            # Cache successful responses
            if response.status_code == 200:
                cache_service.set(cache_key, response, timeout)

            return response
        return wrapper
    return decorator


# =============================================================================
# Singleton Instance
# =============================================================================

cache_service = CacheService()
