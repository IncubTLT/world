import asyncio
import logging
import os

import django
from django.conf import settings
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker, ListRedisScheduleSource, RedisAsyncResultBackend

from config.async_redis import set_async_redis_client

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()]
)

# logging.getLogger("taskiq.schedule_sources.list_schedule_source").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TASKIQ_PROCESS = os.getenv("TASKIQ_PROCESS")


async def init_dependencies():
    await set_async_redis_client()
    logger.info("Redis client initialized in scheduler.")


if TASKIQ_PROCESS == "1":
    django.setup()
    loop = asyncio.get_event_loop()
    loop.create_task(init_dependencies())

result_backend = RedisAsyncResultBackend(settings.REDIS_URL)


def create_scheduler(queue_name: str, schedule_prefix: str, pool_size: int = 1) -> tuple[ListQueueBroker, TaskiqScheduler]:
    broker = ListQueueBroker(
        url=settings.REDIS_URL,
        queue_name=queue_name,
        max_connection_pool_size=pool_size,
    ).with_result_backend(result_backend)

    redis_source = ListRedisScheduleSource(
        url=settings.REDIS_URL,
        prefix=schedule_prefix,
        max_connection_pool_size=pool_size,
    )

    scheduler = TaskiqScheduler(
        broker=broker,
        sources=(redis_source, LabelScheduleSource(broker))
    )

    return broker, scheduler, redis_source

taskiq_broker, scheduler, redis_source = create_scheduler("taskiq", "schedule", pool_size=10)


__all__ = [
    "taskiq_broker",
    "scheduler",
    "redis_source",
]
