"""
ASGI config for MultinotesAI backend.

This module provides:
- ASGI application for async request handling
- WebSocket routing with JWT authentication
- HTTP protocol routing
- Middleware configuration

Deployment options:
- Daphne: daphne backend.asgi:application -b 0.0.0.0 -p 8000
- Uvicorn: uvicorn backend.asgi:application --host 0.0.0.0 --port 8000
- Hypercorn: hypercorn backend.asgi:application

For more information on ASGI, see:
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
import logging

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import coreapp.routing

logger = logging.getLogger(__name__)


# =============================================================================
# JWT Authentication Middleware for WebSocket
# =============================================================================

class JWTAuthMiddleware:
    """
    Custom middleware for JWT authentication in WebSocket connections.

    Usage:
        The JWT token should be passed in the query string:
        ws://example.com/ws/endpoint/?token=eyJ...
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        from urllib.parse import parse_qs
        from django.contrib.auth.models import AnonymousUser

        # Get token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if token:
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                from django.contrib.auth import get_user_model
                from channels.db import database_sync_to_async

                User = get_user_model()

                # Validate token
                access_token = AccessToken(token)
                user_id = access_token['user_id']

                # Get user
                @database_sync_to_async
                def get_user(uid):
                    try:
                        return User.objects.get(id=uid)
                    except User.DoesNotExist:
                        return AnonymousUser()

                scope['user'] = await get_user(user_id)
            except Exception as e:
                logger.warning(f"WebSocket JWT auth failed: {e}")
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()

        return await self.app(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Convenience wrapper for JWT auth middleware."""
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))


# =============================================================================
# ASGI Application
# =============================================================================

application = ProtocolTypeRouter({
    # HTTP requests -> Django
    'http': django_asgi_app,

    # WebSocket requests -> Channels with JWT auth
    'websocket': AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(
                coreapp.routing.websocket_urlpatterns
            )
        )
    ),
})


# =============================================================================
# Uvicorn/Daphne Configuration Helpers
# =============================================================================

def get_uvicorn_config():
    """Get Uvicorn configuration for development/production."""
    from django.conf import settings

    is_debug = getattr(settings, 'DEBUG', False)

    return {
        'app': 'backend.asgi:application',
        'host': '0.0.0.0',
        'port': int(os.environ.get('PORT', 8000)),
        'workers': 1 if is_debug else int(os.environ.get('WEB_WORKERS', 4)),
        'log_level': 'debug' if is_debug else 'info',
        'reload': is_debug,
        'access_log': True,
        'proxy_headers': True,
        'forwarded_allow_ips': '*',
    }


if __name__ == '__main__':
    import uvicorn
    config = get_uvicorn_config()
    uvicorn.run(**config)
