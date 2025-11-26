"""
Swagger/OpenAPI Configuration for MultinotesAI API.

This module provides:
- OpenAPI schema generation
- Swagger UI configuration
- ReDoc configuration
- Custom schema extensions

Setup:
1. Install: pip install drf-spectacular
2. Add to INSTALLED_APPS: 'drf_spectacular'
3. Add to REST_FRAMEWORK settings: 'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'
4. Include URLs from this module
"""

from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


# =============================================================================
# OpenAPI Schema Settings
# =============================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'MultinotesAI API',
    'DESCRIPTION': '''
# MultinotesAI API Documentation

MultinotesAI is an AI-powered note-taking and content generation platform.

## Authentication

All API endpoints (except public ones) require authentication using JWT tokens.

### Obtaining Tokens

1. Register: `POST /api/user/register/`
2. Login: `POST /api/user/login/`

You'll receive:
```json
{
    "access": "eyJ...",
    "refresh": "eyJ..."
}
```

### Using Tokens

Include the access token in the `Authorization` header:
```
Authorization: Bearer eyJ...
```

### Refreshing Tokens

When the access token expires, use the refresh token:
`POST /api/user/token/refresh/`

## Rate Limiting

API requests are rate-limited based on your subscription plan:

| Plan    | AI Generations | General API |
|---------|----------------|-------------|
| Free    | 5/hour         | 100/hour    |
| Basic   | 50/hour        | 500/hour    |
| Pro     | 200/hour       | 2000/hour   |

## Error Responses

All errors follow this format:
```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message",
        "details": {}
    }
}
```

## Webhooks

Register webhooks to receive real-time notifications:
`POST /api/webhooks/`

Supported events:
- `user.*` - User events
- `subscription.*` - Subscription events
- `payment.*` - Payment events
- `note.*` - Content events
- `ai.*` - AI generation events
    ''',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,

    # Contact info
    'CONTACT': {
        'name': 'MultinotesAI Support',
        'email': 'support@multinotesai.com',
        'url': 'https://multinotesai.com/support',
    },

    # License
    'LICENSE': {
        'name': 'Proprietary',
        'url': 'https://multinotesai.com/terms',
    },

    # External docs
    'EXTERNAL_DOCS': {
        'description': 'Full Documentation',
        'url': 'https://docs.multinotesai.com',
    },

    # Servers
    'SERVERS': [
        {'url': 'https://api.multinotesai.com', 'description': 'Production'},
        {'url': 'https://staging-api.multinotesai.com', 'description': 'Staging'},
        {'url': 'http://localhost:8000', 'description': 'Development'},
    ],

    # Tags for organizing endpoints
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication and registration'},
        {'name': 'Users', 'description': 'User profile and settings'},
        {'name': 'Content', 'description': 'Notes, folders, and content management'},
        {'name': 'AI Generation', 'description': 'AI-powered content generation'},
        {'name': 'Subscriptions', 'description': 'Plans and subscriptions'},
        {'name': 'Payments', 'description': 'Payment processing'},
        {'name': 'Export', 'description': 'Content export functionality'},
        {'name': 'Sharing', 'description': 'Content sharing'},
        {'name': 'Admin', 'description': 'Admin dashboard endpoints'},
        {'name': 'Webhooks', 'description': 'Webhook management'},
        {'name': 'Health', 'description': 'Health check endpoints'},
    ],

    # Security schemes
    'SECURITY': [{'BearerAuth': []}],

    # Component security schemes
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'JWT authentication token',
            },
            'ApiKeyAuth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API-Key',
                'description': 'API key for external integrations',
            },
        },
    },

    # Schema settings
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,

    # Enum naming
    'ENUM_NAME_OVERRIDES': {
        'SubscriptionStatusEnum': 'planandsubscription.models.Subscription.status',
        'PaymentStatusEnum': 'planandsubscription.models.Payment.status',
    },

    # Sorting
    'SORT_OPERATIONS': True,
    'SORT_OPERATION_PARAMETERS': True,

    # Extensions
    'EXTENSIONS_INFO': {},

    # Preprocessing hooks
    'PREPROCESSING_HOOKS': [
        'backend.swagger.preprocessing_filter_spec',
    ],

    # Postprocessing hooks
    'POSTPROCESSING_HOOKS': [
        'backend.swagger.postprocessing_add_examples',
    ],

    # Schema path prefix
    'SCHEMA_PATH_PREFIX': '/api',

    # Disable serving schema at /api/schema/ (use /api/docs/schema/ instead)
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],

    # Swagger UI settings
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
        'filter': True,
        'docExpansion': 'none',
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
    },

    # ReDoc settings
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'expandResponses': '200,201',
    },
}


# =============================================================================
# Custom Schema Extensions
# =============================================================================

def preprocessing_filter_spec(endpoints, **kwargs):
    """
    Preprocess endpoints before schema generation.

    Filter out internal/admin endpoints from public docs if needed.
    """
    filtered = []
    for (path, path_regex, method, callback) in endpoints:
        # Skip internal endpoints
        if '/internal/' in path:
            continue
        filtered.append((path, path_regex, method, callback))

    return filtered


def postprocessing_add_examples(result, generator, **kwargs):
    """
    Postprocess schema to add examples and additional info.
    """
    # Add example values to common schemas
    if 'components' in result and 'schemas' in result['components']:
        schemas = result['components']['schemas']

        # Add examples for common response formats
        if 'PaginatedResponse' not in schemas:
            schemas['PaginatedResponse'] = {
                'type': 'object',
                'properties': {
                    'count': {'type': 'integer', 'example': 100},
                    'next': {'type': 'string', 'nullable': True, 'example': '/api/notes/?page=2'},
                    'previous': {'type': 'string', 'nullable': True, 'example': None},
                    'results': {'type': 'array', 'items': {}},
                },
            }

        if 'ErrorResponse' not in schemas:
            schemas['ErrorResponse'] = {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {
                        'type': 'object',
                        'properties': {
                            'code': {'type': 'string', 'example': 'AUTH_001'},
                            'message': {'type': 'string', 'example': 'Invalid credentials'},
                            'details': {'type': 'object', 'nullable': True},
                        },
                    },
                },
            }

    return result


# =============================================================================
# URL Patterns
# =============================================================================

def get_swagger_urls():
    """Get URL patterns for API documentation."""
    return [
        # OpenAPI schema (JSON/YAML)
        path(
            'docs/schema/',
            SpectacularAPIView.as_view(),
            name='schema'
        ),

        # Swagger UI
        path(
            'docs/swagger/',
            SpectacularSwaggerView.as_view(url_name='schema'),
            name='swagger-ui'
        ),

        # ReDoc
        path(
            'docs/redoc/',
            SpectacularRedocView.as_view(url_name='schema'),
            name='redoc'
        ),

        # Default docs endpoint (Swagger UI)
        path(
            'docs/',
            SpectacularSwaggerView.as_view(url_name='schema'),
            name='api-docs'
        ),
    ]


# =============================================================================
# Custom OpenAPI Extensions
# =============================================================================

class CustomAutoSchema:
    """
    Custom AutoSchema for additional OpenAPI extensions.

    Usage:
        @extend_schema(
            tags=['Content'],
            operation_id='create_note',
            description='Create a new note',
        )
        def post(self, request):
            ...
    """

    @staticmethod
    def get_operation_id_override(view, method):
        """Generate custom operation IDs."""
        view_name = view.__class__.__name__
        method_lower = method.lower()

        # Map common patterns
        if 'List' in view_name:
            if method_lower == 'get':
                return f"list_{view_name.replace('ListView', '').lower()}"
            elif method_lower == 'post':
                return f"create_{view_name.replace('ListView', '').lower()}"
        elif 'Detail' in view_name:
            if method_lower == 'get':
                return f"get_{view_name.replace('DetailView', '').lower()}"
            elif method_lower in ('put', 'patch'):
                return f"update_{view_name.replace('DetailView', '').lower()}"
            elif method_lower == 'delete':
                return f"delete_{view_name.replace('DetailView', '').lower()}"

        return None


# =============================================================================
# API Documentation Views
# =============================================================================

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class APIRootView(APIView):
    """
    API Root - Entry point for the MultinotesAI API.

    Provides links to documentation and key endpoints.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'name': 'MultinotesAI API',
            'version': '2.0.0',
            'documentation': {
                'swagger': request.build_absolute_uri('/api/docs/swagger/'),
                'redoc': request.build_absolute_uri('/api/docs/redoc/'),
                'schema': request.build_absolute_uri('/api/docs/schema/'),
            },
            'endpoints': {
                'auth': {
                    'register': '/api/user/register/',
                    'login': '/api/user/login/',
                    'refresh': '/api/user/token/refresh/',
                },
                'content': {
                    'notes': '/api/content/',
                    'folders': '/api/folders/',
                },
                'subscriptions': {
                    'plans': '/api/plans/',
                    'subscribe': '/api/subscribe/',
                },
            },
            'status': 'operational',
        })


# Convenience function to add to main urls.py
urlpatterns = get_swagger_urls()
