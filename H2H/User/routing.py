from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/draft/<int:league_id>/', consumers.DraftConsumer.as_asgi()),
]