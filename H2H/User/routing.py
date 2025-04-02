from django.urls import re_path
from User.consumers import DraftConsumer, NotificationConsumer

websocket_urlpatterns = [
    re_path(r'ws/draft/(?P<league_id>\d+)/$', DraftConsumer.as_asgi()),
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),  # New route for notifications

]