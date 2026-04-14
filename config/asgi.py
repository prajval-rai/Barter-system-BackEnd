# config/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

from chat.routing import websocket_urlpatterns
from config.ws_middleware import JWTAuthMiddleware

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # ✅ No AllowedHostsOriginValidator — it does a literal string match
        #    against ALLOWED_HOSTS and rejects "*", causing every WS from
        #    localhost:3000 to get REJECT before auth even runs.
        "websocket": JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        ),
    }
)