import logging
import os

from asgiref.compatibility import guarantee_single_callable
from channels.routing import ProtocolTypeRouter, URLRouter
from config.async_redis import set_async_redis_client
from config.channels_jwt import JwtAuthMiddlewareStack
from config.taskiq_app import scheduler, taskiq_broker
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
logger = logging.getLogger('config.asgi')

application = get_asgi_application()


async def startup():
    """Действия при старте приложения."""
    await set_async_redis_client()

    if not taskiq_broker.is_worker_process:
        await scheduler.startup()
    logger.info("Taskiq планировщик запущен.")


async def shutdown():
    """Действия при завершении приложения."""
    if taskiq_broker.is_worker_process:
        await scheduler.shutdown()
    logger.info("Taskiq is shutdown.")


def get_application():
    from apps.ai.routing import websocket_urlpatterns as ai_urlpatterns
    from apps.messaging.routing import \
        websocket_urlpatterns as messaging_urlpatterns

    class LifespanMiddleware:
        def __init__(self, app):
            self.app = guarantee_single_callable(app)

        async def __call__(self, scope, receive, send):
            if scope['type'] == 'lifespan':
                await self.handle_lifespan(receive, send)
            else:
                await self.app(scope, receive, send)

        async def handle_lifespan(self, receive, send):
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    try:
                        await startup()
                        await send({'type': 'lifespan.startup.complete'})
                    except Exception as e:
                        logger.error("Startup failed: %s", e, exc_info=True)
                        await send({
                            'type': 'lifespan.startup.failed',
                            'message': str(e),
                        })
                        return

                elif message['type'] == 'lifespan.shutdown':
                    try:
                        await shutdown()
                        await send({'type': 'lifespan.shutdown.complete'})
                    except Exception as e:
                        logger.error("Shutdown failed: %s", e, exc_info=True)
                        await send({
                            'type': 'lifespan.shutdown.failed',
                            'message': str(e),
                        })
                        return

    return LifespanMiddleware(ProtocolTypeRouter({
        'http': application,
        'websocket': JwtAuthMiddlewareStack(
            URLRouter(
                messaging_urlpatterns + ai_urlpatterns
            )
        ),
    }))


application = get_application()
