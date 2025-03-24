from django.urls import re_path
from User.consumers import DraftConsumer

websocket_urlpatterns = [
    re_path(r'ws/draft/(?P<league_id>\d+)/$', DraftConsumer.as_asgi()),
]