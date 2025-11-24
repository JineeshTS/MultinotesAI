"""
Custom middleware for MultinotesAI.

This module provides:
- Performance monitoring middleware
- Request logging middleware
- Security headers middleware
- CORS handling
"""

import time
import uuid
import logging
import json
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)
performance_logger = logging.getLogger('performance')


# =============================================================================
# Performance Monitoring Middleware
# =============================================================================

class PerformanceMiddleware(MiddlewareMixin):
    """
    Middleware to track request performance metrics.

    Logs:
    - Request duration
    - Response size
    - Database query count
    - Memory usage (optional)

    Adds X-Request-Time header to responses.
    """

    # Paths to exclude from detailed logging
    EXCLUDED_PATHS = [
        '/health/',
        '/metrics/',
        '/favicon.ico',
        '/static/',
        '/media/',
    ]

    # Slow request threshold (milliseconds)
    SLOW_REQUEST_THRESHOLD = 1000

    def process_request(self, request):
        """Store request start time."""
        request._start_time = time.time()
        request._request_id = str(uuid.uuid4())[:8]

        # Track database queries in debug mode
        if settings.DEBUG:
            from django.db import connection
            request._initial_queries = len(connection.queries)

    def process_response(self, request, response):
        """Calculate and log request duration."""
        if not hasattr(request, '_start_time'):
            return response

        # Calculate duration
        duration_ms = (time.time() - request._start_time) * 1000

        # Add timing header
        response['X-Request-Time'] = f"{duration_ms:.2f}ms"
        response['X-Request-ID'] = getattr(request, '_request_id', 'unknown')

        # Skip logging for excluded paths
        path = request.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return response

        # Prepare log data
        log_data = {
            'request_id': getattr(request, '_request_id', 'unknown'),
            'method': request.method,
            'path': path,
            'status_code': response.status_code,
            'duration_ms': round(duration_ms, 2),
            'response_size': len(response.content) if hasattr(response, 'content') else 0,
            'user_id': request.user.id if request.user.is_authenticated else None,
            'ip': self._get_client_ip(request),
        }

        # Add query count in debug mode
        if settings.DEBUG:
            from django.db import connection
            query_count = len(connection.queries) - getattr(request, '_initial_queries', 0)
            log_data['query_count'] = query_count

        # Log based on duration
        if duration_ms > self.SLOW_REQUEST_THRESHOLD:
            performance_logger.warning(f"Slow request: {json.dumps(log_data)}")
        else:
            performance_logger.info(json.dumps(log_data))

        return response

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


# =============================================================================
# Request Logging Middleware
# =============================================================================

class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log incoming requests for debugging and auditing.

    Logs request details including:
    - HTTP method and path
    - Query parameters
    - Request body (for POST/PUT/PATCH)
    - User agent
    """

    # Sensitive fields to mask in logs
    SENSITIVE_FIELDS = ['password', 'token', 'secret', 'api_key', 'authorization']

    # Max body size to log (bytes)
    MAX_BODY_SIZE = 10000

    def process_request(self, request):
        """Log incoming request details."""
        if not getattr(settings, 'LOG_REQUESTS', False):
            return

        log_data = {
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.GET),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'content_type': request.content_type,
        }

        # Log request body for mutations
        if request.method in ['POST', 'PUT', 'PATCH']:
            body = self._get_safe_body(request)
            if body:
                log_data['body'] = body

        logger.debug(f"Incoming request: {json.dumps(log_data)}")

    def _get_safe_body(self, request):
        """Get request body with sensitive fields masked."""
        try:
            if len(request.body) > self.MAX_BODY_SIZE:
                return '<body too large>'

            body = json.loads(request.body)
            return self._mask_sensitive(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return '<non-json body>'

    def _mask_sensitive(self, data):
        """Recursively mask sensitive fields."""
        if isinstance(data, dict):
            return {
                k: '***MASKED***' if k.lower() in self.SENSITIVE_FIELDS else self._mask_sensitive(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._mask_sensitive(item) for item in data]
        return data


# =============================================================================
# Security Headers Middleware
# =============================================================================

class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to responses.

    Adds:
    - Content-Security-Policy
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """

    def process_response(self, request, response):
        """Add security headers to response."""
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'

        # Enable XSS filter (legacy browsers)
        response['X-XSS-Protection'] = '1; mode=block'

        # Control referrer information
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Restrict browser features
        response['Permissions-Policy'] = (
            'accelerometer=(), camera=(), geolocation=(), gyroscope=(), '
            'magnetometer=(), microphone=(), payment=(), usb=()'
        )

        # Content Security Policy (customize based on your needs)
        if not settings.DEBUG:
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                "connect-src 'self' https://api.razorpay.com",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]
            response['Content-Security-Policy'] = '; '.join(csp_directives)

        return response


# =============================================================================
# Maintenance Mode Middleware
# =============================================================================

class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Middleware to enable maintenance mode.

    When enabled, returns 503 for all requests except:
    - Health check endpoint
    - Admin users
    - Whitelisted IPs
    """

    ALLOWED_PATHS = ['/health/', '/api/health/']
    ALLOWED_IPS = []  # Add whitelisted IPs here

    def process_request(self, request):
        """Check if maintenance mode is enabled."""
        if not getattr(settings, 'MAINTENANCE_MODE', False):
            return None

        # Allow health checks
        if request.path in self.ALLOWED_PATHS:
            return None

        # Allow whitelisted IPs
        client_ip = self._get_client_ip(request)
        if client_ip in self.ALLOWED_IPS:
            return None

        # Allow admin users
        if request.user.is_authenticated and request.user.is_staff:
            return None

        return JsonResponse(
            {
                'status': 503,
                'message': 'Service temporarily unavailable for maintenance',
                'retry_after': 3600,
            },
            status=503,
            headers={'Retry-After': '3600'}
        )

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


# =============================================================================
# API Version Middleware
# =============================================================================

class APIVersionMiddleware(MiddlewareMixin):
    """
    Middleware to handle API versioning.

    Reads version from:
    1. URL prefix (/api/v1/, /api/v2/)
    2. Accept header (application/vnd.multinotesai+json; version=1)
    3. Custom header (X-API-Version)

    Defaults to latest version.
    """

    DEFAULT_VERSION = '1'
    SUPPORTED_VERSIONS = ['1', '2']

    def process_request(self, request):
        """Extract API version from request."""
        version = None

        # Check URL prefix
        path = request.path
        if path.startswith('/api/v'):
            parts = path.split('/')
            if len(parts) > 2:
                version_part = parts[2]
                if version_part.startswith('v') and version_part[1:] in self.SUPPORTED_VERSIONS:
                    version = version_part[1:]

        # Check Accept header
        if not version:
            accept = request.META.get('HTTP_ACCEPT', '')
            if 'version=' in accept:
                version = accept.split('version=')[1].split(';')[0].strip()

        # Check custom header
        if not version:
            version = request.META.get('HTTP_X_API_VERSION')

        # Validate and set version
        if version not in self.SUPPORTED_VERSIONS:
            version = self.DEFAULT_VERSION

        request.api_version = version


# =============================================================================
# JSON Error Middleware
# =============================================================================

class JSONErrorMiddleware(MiddlewareMixin):
    """
    Middleware to ensure all errors return JSON responses.

    Handles:
    - 404 Not Found
    - 500 Server Error
    - Other exceptions
    """

    def process_exception(self, request, exception):
        """Handle exceptions and return JSON response."""
        # Only handle API requests
        if not request.path.startswith('/api/'):
            return None

        import traceback

        error_data = {
            'status': 500,
            'message': 'Internal server error',
        }

        if settings.DEBUG:
            error_data['debug'] = {
                'exception': str(exception),
                'traceback': traceback.format_exc(),
            }

        logger.error(f"Unhandled exception: {exception}", exc_info=True)

        return JsonResponse(error_data, status=500)


# =============================================================================
# CORS Middleware (if not using django-cors-headers)
# =============================================================================

class SimpleCORSMiddleware(MiddlewareMixin):
    """
    Simple CORS middleware for development.

    For production, use django-cors-headers package instead.
    """

    def process_response(self, request, response):
        """Add CORS headers to response."""
        if not settings.DEBUG:
            return response

        origin = request.META.get('HTTP_ORIGIN', '')
        allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])

        if origin in allowed_origins or '*' in allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '86400'

        return response


# =============================================================================
# Middleware Configuration for settings.py
# =============================================================================

"""
Add to MIDDLEWARE in settings.py:

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'backend.middleware.SecurityHeadersMiddleware',
    'backend.middleware.MaintenanceModeMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # or SimpleCORSMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'backend.middleware.PerformanceMiddleware',
    'backend.middleware.RequestLoggingMiddleware',
    'backend.middleware.APIVersionMiddleware',
    'backend.middleware.JSONErrorMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
"""
