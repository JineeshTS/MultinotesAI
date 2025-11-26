"""
Semantic Search Service for MultinotesAI.

This module provides:
- Full-text search
- Semantic/vector search using embeddings
- Search result ranking and filtering
- Search analytics
"""

import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from django.db.models import Q, F, Value, Case, When, IntegerField
from django.db.models.functions import Coalesce, Greatest
from django.contrib.postgres.search import (
    SearchVector, SearchQuery, SearchRank, TrigramSimilarity
)
from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Search Configuration
# =============================================================================

class SearchConfig:
    """Search configuration settings."""

    # Minimum query length
    MIN_QUERY_LENGTH = 2

    # Maximum results per page
    MAX_RESULTS = 100
    DEFAULT_PAGE_SIZE = 20

    # Ranking weights
    TITLE_WEIGHT = 'A'  # Highest weight
    CONTENT_WEIGHT = 'B'
    TAG_WEIGHT = 'C'

    # Similarity thresholds
    MIN_SIMILARITY = 0.1
    FUZZY_THRESHOLD = 0.3

    # Cache settings
    CACHE_TIMEOUT = 300  # 5 minutes
    CACHE_PREFIX = 'search:'


# =============================================================================
# Search Service
# =============================================================================

class SearchService:
    """
    Unified search service for content discovery.

    Usage:
        service = SearchService()
        results = service.search(
            user=user,
            query="machine learning",
            filters={'folder_id': 123}
        )
    """

    def __init__(self):
        self.config = SearchConfig

    def search(
        self,
        user,
        query: str,
        filters: Dict[str, Any] = None,
        page: int = 1,
        page_size: int = None,
        search_type: str = 'hybrid'
    ) -> Dict[str, Any]:
        """
        Search user's content.

        Args:
            user: User performing search
            query: Search query string
            filters: Optional filters (folder_id, date_range, etc.)
            page: Page number
            page_size: Results per page
            search_type: 'text', 'semantic', or 'hybrid'

        Returns:
            Search results with pagination info
        """
        from coreapp.models import ContentGen

        # Validate query
        query = self._clean_query(query)
        if len(query) < self.config.MIN_QUERY_LENGTH:
            return self._empty_results()

        # Set pagination
        page_size = min(
            page_size or self.config.DEFAULT_PAGE_SIZE,
            self.config.MAX_RESULTS
        )

        # Build base queryset
        queryset = ContentGen.objects.filter(
            user=user,
            is_delete=False
        )

        # Apply filters
        queryset = self._apply_filters(queryset, filters)

        # Perform search based on type
        if search_type == 'text':
            queryset = self._text_search(queryset, query)
        elif search_type == 'semantic':
            queryset = self._semantic_search(queryset, query, user)
        else:  # hybrid
            queryset = self._hybrid_search(queryset, query, user)

        # Get total count
        total = queryset.count()

        # Paginate
        offset = (page - 1) * page_size
        results = list(queryset[offset:offset + page_size])

        # Log search
        self._log_search(user, query, total)

        return {
            'results': [self._serialize_result(r) for r in results],
            'query': query,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size,
            'search_type': search_type,
        }

    def _clean_query(self, query: str) -> str:
        """Clean and normalize search query."""
        if not query:
            return ''

        # Remove excessive whitespace
        query = ' '.join(query.split())

        # Remove special characters that could cause issues
        query = re.sub(r'[<>{}[\]\\]', '', query)

        return query.strip()

    def _apply_filters(self, queryset, filters: Dict) -> Any:
        """Apply search filters to queryset."""
        if not filters:
            return queryset

        # Filter by folder
        if 'folder_id' in filters:
            queryset = queryset.filter(folder_id=filters['folder_id'])

        # Filter by date range
        if 'date_from' in filters:
            queryset = queryset.filter(created_at__gte=filters['date_from'])
        if 'date_to' in filters:
            queryset = queryset.filter(created_at__lte=filters['date_to'])

        # Filter by content type
        if 'content_type' in filters:
            queryset = queryset.filter(content_type=filters['content_type'])

        # Filter by tags
        if 'tags' in filters:
            for tag in filters['tags']:
                queryset = queryset.filter(tags__contains=tag)

        # Filter by favorites
        if filters.get('favorites_only'):
            queryset = queryset.filter(is_favorite=True)

        return queryset

    def _text_search(self, queryset, query: str) -> Any:
        """Perform full-text search."""
        # Simple text search using icontains
        search_filter = Q(title__icontains=query) | Q(generatedResponse__icontains=query)

        # Also search in userPrompt if exists
        if hasattr(queryset.model, 'userPrompt'):
            search_filter |= Q(userPrompt__icontains=query)

        return queryset.filter(search_filter).order_by('-updated_at')

    def _semantic_search(self, queryset, query: str, user) -> Any:
        """
        Perform semantic search using embeddings.

        This requires a vector database (pgvector) or embedding storage.
        Falls back to text search if embeddings not available.
        """
        try:
            # Check if semantic search is available
            if not self._is_semantic_available():
                logger.debug("Semantic search not available, falling back to text search")
                return self._text_search(queryset, query)

            # Get query embedding
            embedding = self._get_embedding(query)
            if not embedding:
                return self._text_search(queryset, query)

            # Find similar content (requires pgvector extension)
            from coreapp.models import ContentEmbedding

            # Get content IDs sorted by similarity
            similar_ids = ContentEmbedding.objects.filter(
                content__user=user,
                content__is_delete=False
            ).annotate(
                similarity=1 - F('embedding').cosine_distance(embedding)
            ).filter(
                similarity__gte=self.config.MIN_SIMILARITY
            ).order_by('-similarity').values_list('content_id', flat=True)

            # Preserve order using CASE WHEN
            ordering = Case(
                *[When(pk=pk, then=pos) for pos, pk in enumerate(similar_ids)],
                output_field=IntegerField()
            )

            return queryset.filter(id__in=similar_ids).annotate(
                search_order=ordering
            ).order_by('search_order')

        except Exception as e:
            logger.warning(f"Semantic search failed: {e}, falling back to text search")
            return self._text_search(queryset, query)

    def _hybrid_search(self, queryset, query: str, user) -> Any:
        """
        Combine text and semantic search for best results.
        """
        # Perform text search
        text_results = set(
            self._text_search(queryset, query).values_list('id', flat=True)[:100]
        )

        # Try semantic search
        try:
            if self._is_semantic_available():
                semantic_queryset = self._semantic_search(queryset, query, user)
                semantic_results = set(
                    semantic_queryset.values_list('id', flat=True)[:100]
                )

                # Combine results, prioritizing items that appear in both
                combined_ids = list(text_results | semantic_results)

                # Score by appearance in both result sets
                def score(item_id):
                    score = 0
                    if item_id in text_results:
                        score += 1
                    if item_id in semantic_results:
                        score += 1
                    return score

                combined_ids.sort(key=score, reverse=True)

                # Return queryset with preserved order
                ordering = Case(
                    *[When(pk=pk, then=pos) for pos, pk in enumerate(combined_ids)],
                    output_field=IntegerField()
                )

                return queryset.filter(id__in=combined_ids).annotate(
                    search_order=ordering
                ).order_by('search_order')

        except Exception as e:
            logger.warning(f"Hybrid search semantic component failed: {e}")

        # Fall back to text search results
        ordering = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(text_results)],
            output_field=IntegerField()
        )
        return queryset.filter(id__in=text_results).annotate(
            search_order=ordering
        ).order_by('search_order')

    def _is_semantic_available(self) -> bool:
        """Check if semantic search is available."""
        return getattr(settings, 'SEMANTIC_SEARCH_ENABLED', False)

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding vector for text using LLM service."""
        try:
            from coreapp.services.llm_service import llm_service

            embedding = llm_service.get_embedding(text)
            return embedding

        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return None

    def _serialize_result(self, content) -> Dict:
        """Serialize search result."""
        return {
            'id': content.id,
            'title': content.title,
            'snippet': self._get_snippet(content),
            'folder_id': content.folder_id,
            'created_at': content.created_at.isoformat() if content.created_at else None,
            'updated_at': content.updated_at.isoformat() if content.updated_at else None,
            'is_favorite': getattr(content, 'is_favorite', False),
        }

    def _get_snippet(self, content, max_length: int = 200) -> str:
        """Get content snippet for search results."""
        text = getattr(content, 'generatedResponse', '') or ''
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(' ', 1)[0] + '...'

    def _log_search(self, user, query: str, result_count: int):
        """Log search for analytics."""
        try:
            from coreapp.models_analytics import SearchLog

            SearchLog.objects.create(
                user=user,
                query=query,
                result_count=result_count
            )
        except Exception:
            pass  # Don't fail search if logging fails

    def _empty_results(self) -> Dict:
        """Return empty results structure."""
        return {
            'results': [],
            'query': '',
            'total': 0,
            'page': 1,
            'page_size': self.config.DEFAULT_PAGE_SIZE,
            'pages': 0,
        }

    # -------------------------------------------------------------------------
    # Quick Search
    # -------------------------------------------------------------------------

    def quick_search(
        self,
        user,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Fast search for autocomplete/suggestions.

        Args:
            user: User performing search
            query: Search query
            limit: Maximum results

        Returns:
            List of matching items
        """
        from coreapp.models import ContentGen

        if len(query) < 2:
            return []

        results = ContentGen.objects.filter(
            user=user,
            is_delete=False,
            title__icontains=query
        ).values('id', 'title')[:limit]

        return list(results)

    # -------------------------------------------------------------------------
    # Search Suggestions
    # -------------------------------------------------------------------------

    def get_suggestions(self, user, partial_query: str, limit: int = 5) -> List[str]:
        """
        Get search suggestions based on partial query.

        Args:
            user: User
            partial_query: Partial search string
            limit: Max suggestions

        Returns:
            List of suggestion strings
        """
        from coreapp.models import ContentGen

        if len(partial_query) < 2:
            return []

        # Get matching titles
        titles = ContentGen.objects.filter(
            user=user,
            is_delete=False,
            title__istartswith=partial_query
        ).values_list('title', flat=True).distinct()[:limit]

        return list(titles)

    def get_recent_searches(self, user, limit: int = 10) -> List[str]:
        """Get user's recent search queries."""
        try:
            from coreapp.models_analytics import SearchLog

            searches = SearchLog.objects.filter(
                user=user
            ).order_by('-created_at').values_list('query', flat=True)[:limit]

            return list(dict.fromkeys(searches))  # Remove duplicates, preserve order
        except Exception:
            return []

    def get_popular_searches(self, limit: int = 10) -> List[Dict]:
        """Get globally popular search queries."""
        try:
            from coreapp.models_analytics import SearchLog
            from django.db.models import Count

            popular = SearchLog.objects.filter(
                created_at__gte=datetime.now() - timedelta(days=7)
            ).values('query').annotate(
                count=Count('id')
            ).order_by('-count')[:limit]

            return list(popular)
        except Exception:
            return []


# =============================================================================
# Search Index Service
# =============================================================================

class SearchIndexService:
    """
    Service for managing search indexes and embeddings.
    """

    def index_content(self, content) -> bool:
        """
        Index content for search.

        Args:
            content: ContentGen instance

        Returns:
            True if successful
        """
        try:
            # Create text index (MySQL FULLTEXT)
            # This is handled automatically by MySQL if FULLTEXT index exists

            # Create embedding for semantic search
            if getattr(settings, 'SEMANTIC_SEARCH_ENABLED', False):
                self._create_embedding(content)

            return True
        except Exception as e:
            logger.error(f"Failed to index content {content.id}: {e}")
            return False

    def _create_embedding(self, content):
        """Create embedding for content."""
        try:
            from coreapp.services.llm_service import llm_service
            from coreapp.models import ContentEmbedding

            # Combine title and content for embedding
            text = f"{content.title}\n\n{content.generatedResponse or ''}"
            text = text[:8000]  # Limit text length

            embedding = llm_service.get_embedding(text)

            if embedding:
                ContentEmbedding.objects.update_or_create(
                    content=content,
                    defaults={'embedding': embedding}
                )
        except Exception as e:
            logger.warning(f"Failed to create embedding: {e}")

    def reindex_all(self, user=None) -> int:
        """Reindex all content."""
        from coreapp.models import ContentGen

        queryset = ContentGen.objects.filter(is_delete=False)
        if user:
            queryset = queryset.filter(user=user)

        count = 0
        for content in queryset.iterator():
            if self.index_content(content):
                count += 1

        logger.info(f"Reindexed {count} content items")
        return count

    def remove_index(self, content_id: int):
        """Remove content from search index."""
        try:
            from coreapp.models import ContentEmbedding

            ContentEmbedding.objects.filter(content_id=content_id).delete()
        except Exception:
            pass


# =============================================================================
# Singleton Instances
# =============================================================================

search_service = SearchService()
search_index_service = SearchIndexService()
