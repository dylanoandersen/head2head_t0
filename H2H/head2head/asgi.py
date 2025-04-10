"""
ASGI config for head2head project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'head2head.settings')
django.setup()

from all_players.scheduler import start_scheduler
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
<<<<<<< HEAD
from User import routing
#from decouple import config


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'head2head.settings')

=======
import User.routing
# from decouple import config
>>>>>>> e4d1f74cfe03888c5c19ba65f135659577c142c9

start_scheduler()
print('hi')
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})