from django.urls import path
from . import consumers


websocket_urlpatterns = [
    path('ws/sc/<int:user_id>/', consumers.BoardConsumer.as_asgi()),
]









