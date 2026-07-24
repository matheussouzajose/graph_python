"""Redis client + producer factories.

Isolated here so the rest of the app doesn't import redis directly. If
you move to SQS/RabbitMQ, only this module and `redis_stream.py` change.
"""

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import settings
from app.core.infrastructure.messaging.events import VIDEO_EVENTS_STREAM
from app.core.infrastructure.messaging.redis_stream import RedisStreamProducer


@lru_cache
def get_redis_client() -> Redis:
    """One shared async Redis client (connection-pooled) for the process."""
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
        # Keep long-lived consumer connections healthy: probe idle
        # connections and enable TCP keepalive so a silently dropped
        # socket surfaces (and reconnects) instead of hanging.
        health_check_interval=30,
        socket_keepalive=True,
    )


@lru_cache
def get_video_event_producer() -> RedisStreamProducer:
    return RedisStreamProducer(get_redis_client(), VIDEO_EVENTS_STREAM)
