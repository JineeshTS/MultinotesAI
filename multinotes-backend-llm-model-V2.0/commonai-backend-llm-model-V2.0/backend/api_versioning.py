"""
API Versioning for MultinotesAI.

This module provides:
- API version detection and routing
- Version-specific view handling
- Deprecation warnings
- Version negotiation
"""

import logging
import re
from typing import Optional, Tuple
from functools import wraps

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


# =============================================================================
# Version Configuration
# =============================================================================

class APIVersionConfig:
    """API version configuration."""

    # Supported API versions
    SUPPORTED_VERSIONS = ['v1', 'v2']
    DEFAULT_VERSION = 'v2'
    LATEST_VERSION = 'v2'

    # Deprecated versions (will show warning)
    DEPRECATED_VERSIONS = ['v1']

    # Sunset versions (will be removed soon)
    SUNSET_VERSIONS = []

    # Version header name
    VERSION_HEADER = 'X-API-Version'

    # Accept header pattern
    ACCEPT_PATTERN = r'application/vnd\.multinotesai\.v(\d+)\+json'


# =============================================================================
# Version Detection
# =============================================================================

class APIVersionDetector:
    """Detect API version from request."""

    def __init__(self, config=None):
        self.config = config or APIVersionConfig

    def get_version(self, request) -> Tuple[str, str]:
        """
        Detect API version from request.

        Returns:
            Tuple of (version, detection_method)
        """
        # 1. Check URL path
        version = self._get_version_from_path(request.path)
        if version:
            return version, 'url'

        # 2. Check custom header
        version = self._get_version_from_header(request)
        if version:
            return version, 'header'

        # 3. Check Accept header
        version = self._get_version_from_accept(request)
        if version:
            return version, 'accept'

        # 4. Check query parameter
        version = self._get_version_from_query(request)
        if version:
            return version, 'query'

        # Default version
        return self.config.DEFAULT_VERSION, 'default'

    def _get_version_from_path(self, path: str) -> Optional[str]:
        """Extract version from URL path."""
        match = re.match(r'^/api/(v\d+)/', path)
        if match:
            version = match.group(1)
            if version in self.config.SUPPORTED_VERSIONS:
                return version
        return None

    def _get_version_from_header(self, request) -> Optional[str]:
        """Extract version from custom header."""
        version = request.META.get(
            f'HTTP_{self.config.VERSION_HEADER.upper().replace("-", "_")}'
        )
        if version and version in self.config.SUPPORTED_VERSIONS:
            return version
        return None

    def _get_version_from_accept(self, request) -> Optional[str]:
        """Extract version from Accept header."""
        accept = request.META.get('HTTP_ACCEPT', '')
        match = re.search(self.config.ACCEPT_PATTERN, accept)
        if match:
            version = f'v{match.group(1)}'
            if version in self.config.SUPPORTED_VERSIONS:
                return version
        return None

    def _get_version_from_query(self, request) -> Optional[str]:
        """Extract version from query parameter."""
        version = request.GET.get('api_version')
        if version and version in self.config.SUPPORTED_VERSIONS:
            return version
        return None


# =============================================================================
# Version Middleware
# =============================================================================

class APIVersionMiddleware:
    """
    Middleware to handle API versioning.

    Adds version info to request and handles deprecation warnings.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.detector = APIVersionDetector()
        self.config = APIVersionConfig

    def __call__(self, request):
        # Only process API requests
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        # Detect version
        version, method = self.detector.get_version(request)
        request.api_version = version
        request.api_version_method = method

        # Get response
        response = self.get_response(request)

        # Add version headers
        response['X-API-Version'] = version
        response['X-API-Latest-Version'] = self.config.LATEST_VERSION

        # Add deprecation warning if needed
        if version in self.config.DEPRECATED_VERSIONS:
            response['X-API-Deprecation-Warning'] = (
                f'API version {version} is deprecated. '
                f'Please migrate to {self.config.LATEST_VERSION}'
            )
            response['Deprecation'] = 'true'

        # Add sunset warning if needed
        if version in self.config.SUNSET_VERSIONS:
            response['Sunset'] = 'true'
            response['X-API-Sunset-Warning'] = (
                f'API version {version} will be removed soon. '
                f'Please migrate to {self.config.LATEST_VERSION} immediately.'
            )

        return response


# =============================================================================
# Version Decorators
# =============================================================================

def api_version(*versions):
    """
    Decorator to restrict view to specific API versions.

    Usage:
        @api_version('v2')
        def my_view(request):
            ...

        @api_version('v1', 'v2')
        def compatible_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            current_version = getattr(request, 'api_version', APIVersionConfig.DEFAULT_VERSION)

            if current_version not in versions:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'VERSION_NOT_SUPPORTED',
                        'message': f'This endpoint requires API version: {", ".join(versions)}',
                        'current_version': current_version,
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def deprecated_in(version, alternative=None):
    """
    Decorator to mark a view as deprecated in a specific version.

    Usage:
        @deprecated_in('v2', alternative='/api/v2/new-endpoint/')
        def old_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            current_version = getattr(request, 'api_version', APIVersionConfig.DEFAULT_VERSION)

            response = view_func(request, *args, **kwargs)

            if current_version >= version:
                warning = f'This endpoint is deprecated in API {version}'
                if alternative:
                    warning += f'. Use {alternative} instead.'

                if hasattr(response, '__setitem__'):
                    response['X-Deprecation-Warning'] = warning

                logger.warning(f"Deprecated endpoint called: {request.path}")

            return response
        return wrapper
    return decorator


def minimum_version(version):
    """
    Decorator to require minimum API version.

    Usage:
        @minimum_version('v2')
        def new_feature_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            current_version = getattr(request, 'api_version', APIVersionConfig.DEFAULT_VERSION)

            # Simple version comparison
            current_num = int(current_version.replace('v', ''))
            required_num = int(version.replace('v', ''))

            if current_num < required_num:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'VERSION_TOO_OLD',
                        'message': f'This endpoint requires API version {version} or higher',
                        'current_version': current_version,
                        'minimum_required': version,
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Versioned API View Base
# =============================================================================

class VersionedAPIView(APIView):
    """
    Base API view with version-aware method dispatching.

    Usage:
        class MyView(VersionedAPIView):
            def get_v1(self, request):
                return Response({'version': 'v1'})

            def get_v2(self, request):
                return Response({'version': 'v2', 'new_field': 'value'})
    """

    supported_versions = APIVersionConfig.SUPPORTED_VERSIONS

    def dispatch(self, request, *args, **kwargs):
        # Get API version
        version = getattr(request, 'api_version', APIVersionConfig.DEFAULT_VERSION)

        # Try version-specific handler first
        method = request.method.lower()
        versioned_handler = getattr(self, f'{method}_{version}', None)

        if versioned_handler:
            return versioned_handler(request, *args, **kwargs)

        # Fall back to default handler
        return super().dispatch(request, *args, **kwargs)


# =============================================================================
# Version Information Endpoint
# =============================================================================

class APIVersionInfoView(APIView):
    """
    Get API version information.

    GET /api/version/
    """
    permission_classes = []

    def get(self, request):
        config = APIVersionConfig

        return Response({
            'current_version': getattr(request, 'api_version', config.DEFAULT_VERSION),
            'latest_version': config.LATEST_VERSION,
            'supported_versions': config.SUPPORTED_VERSIONS,
            'deprecated_versions': config.DEPRECATED_VERSIONS,
            'detection_method': getattr(request, 'api_version_method', 'unknown'),
        })


# =============================================================================
# Version Router
# =============================================================================

class VersionRouter:
    """
    Router for version-specific URL patterns.

    Usage:
        router = VersionRouter()
        router.register('users/', UserViewV1, version='v1')
        router.register('users/', UserViewV2, version='v2')
        urlpatterns = router.get_urls()
    """

    def __init__(self):
        self.registry = {}

    def register(self, prefix: str, viewset, version: str = None, basename: str = None):
        """Register a viewset for a specific version."""
        version = version or APIVersionConfig.DEFAULT_VERSION

        if version not in self.registry:
            self.registry[version] = []

        self.registry[version].append({
            'prefix': prefix,
            'viewset': viewset,
            'basename': basename,
        })

    def get_urls(self):
        """Generate URL patterns for all versions."""
        from django.urls import path, include
        from rest_framework.routers import DefaultRouter

        urlpatterns = []

        for version, routes in self.registry.items():
            router = DefaultRouter()

            for route in routes:
                router.register(
                    route['prefix'],
                    route['viewset'],
                    basename=route['basename']
                )

            urlpatterns.append(
                path(f'{version}/', include(router.urls))
            )

        return urlpatterns


# =============================================================================
# Singleton Instances
# =============================================================================

version_detector = APIVersionDetector()
version_router = VersionRouter()
