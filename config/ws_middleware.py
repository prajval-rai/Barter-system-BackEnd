# config/ws_middleware.py
#
# Django Channels does NOT run DRF middleware.
# This middleware reads the "access" JWT cookie (matching CookieJWTAuthentication)
# and populates scope["user"] before the consumer runs.

from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()

# ✅ Matches exactly what CookieJWTAuthentication uses: request.COOKIES.get("access")
COOKIE_NAME = "access"


def _parse_cookies(headers: list) -> dict:
    cookies: dict = {}
    for key, value in headers:
        if key == b"cookie":
            for part in value.decode("latin1").split(";"):
                part = part.strip()
                if "=" in part:
                    name, _, val = part.partition("=")
                    cookies[name.strip()] = val.strip()
    return cookies


def _get_token(scope: dict) -> str | None:
    # 1. Cookie (primary — matches CookieJWTAuthentication exactly)
    cookies = _parse_cookies(scope.get("headers", []))
    if cookies.get(COOKIE_NAME):
        return cookies[COOKIE_NAME]

    # 2. Query string fallback: ws://.../?token=<jwt>
    #    Used when the cookie is HttpOnly and JS can't read it,
    #    so the frontend fetches the token from /accounts/token/ and passes it here.
    qs = parse_qs(scope.get("query_string", b"").decode())
    token_list = qs.get("token", [])
    if token_list:
        return token_list[0]

    return None


@database_sync_to_async
def _authenticate(token_str: str):
    try:
        token   = AccessToken(token_str)
        user_id = token["user_id"]
        return User.objects.get(pk=user_id)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            token_str = _get_token(scope)
            scope["user"] = await _authenticate(token_str) if token_str else AnonymousUser()
        return await super().__call__(scope, receive, send)