from __future__ import annotations

import asyncio
import logging

import redis.asyncio as aioredis
from django.conf import settings
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class AsyncRedisClient:
    _client: Redis = None  # pyright: ignore[reportAssignmentType]

    @classmethod
    async def initialize(cls):
        if cls._client is None:
            cls._client = await aioredis.from_url(
                f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                max_connections=120,
                encoding="utf8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            logger.info("AsyncRedisClient is setting...")
        return cls._client

    @classmethod
    def get_client(cls):
        if cls._client is None:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    logger.info("Event loop is already running. Initializing Redis client asynchronously.")
                    asyncio.create_task(cls.initialize())
                else:
                    logger.info("Event loop is not running. Initializing Redis client synchronously.")
                    loop.run_until_complete(cls.initialize())
            except RuntimeError:
                logger.info("No event loop found. Creating a new event loop.")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(cls.initialize())
        return cls._client


async def set_async_redis_client():
    return await AsyncRedisClient.initialize()
