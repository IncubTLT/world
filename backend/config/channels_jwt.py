import urllib.parse

from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from channels.auth import AuthMiddlewareStack
from django.utils.functional import cached_property


class JwtAuthMiddleware(BaseMiddleware):
    """
    Middleware для аутентификации WebSocket-подключений по JWT.
    Токен ждём в querystring: ?token=<access_token>.
    """

    @cached_property
    def jwt_auth(self):
        from rest_framework_simplejwt.authentication import JWTAuthentication

        return JWTAuthentication()

    @cached_property
    def anonymous_user_class(self):
        from django.contrib.auth.models import AnonymousUser

        return AnonymousUser

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = urllib.parse.parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        if not token:
            scope["user"] = self.anonymous_user_class()
            return await super().__call__(scope, receive, send)

        try:
            validated_token = self.jwt_auth.get_validated_token(token)
            user = await database_sync_to_async(self.jwt_auth.get_user)(
                validated_token
            )
            scope["user"] = user
        except Exception:
            scope["user"] = self.anonymous_user_class()

        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    """
    Оборачиваем стандартный AuthMiddlewareStack, чтобы сессии тоже продолжали работать
    (если вдруг где-то используешь).
    """
    return JwtAuthMiddleware(AuthMiddlewareStack(inner))
