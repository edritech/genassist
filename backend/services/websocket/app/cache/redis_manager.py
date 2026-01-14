"""
Lightweight Redis Manager for WebSocket Pub/Sub functionality
"""

import logging
from typing import Optional
import asyncio
from redis.asyncio import Redis, ConnectionPool


logger = logging.getLogger(__name__)


class RedisManager:
    """
    Lightweight Redis manager focused on Pub/Sub functionality for WebSocket connections.

    Simplified version that removes unnecessary features and focuses on:
    - Connection management
    - Pub/Sub operations
    - Basic health checking
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_connections: int = 10,
        socket_timeout: int = 5,
    ):
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout

        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection for Pub/Sub operations"""
        if self._initialized:
            return

        try:
            # Create lightweight connection pool optimized for Pub/Sub
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=self.max_connections,
                retry_on_timeout=True,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_timeout,
            )

            # Create Redis client with the pool
            self._redis = Redis(connection_pool=self._pool)

            # Test connection
            await self._redis.ping()

            self._initialized = True
            logger.info("Redis manager initialized for Pub/Sub operations")

        except Exception as e:
            logger.error(f"Failed to initialize Redis manager: {e}")
            self._initialized = False
            raise

    async def get_redis(self) -> Redis:
        """Get Redis client for Pub/Sub operations"""
        if not self._initialized:
            await self.initialize()

        if self._redis is None:
            raise RuntimeError("Redis connection not initialized")

        return self._redis

    async def publish(self, channel: str, message: str) -> None:
        """
        Publish a message to a Redis channel.

        Args:
            channel: Redis channel name
            message: Message to publish
        """
        redis_client = await self.get_redis()
        try:
            await redis_client.publish(channel, message)
            logger.debug(f"Published message to channel: {channel}")
        except Exception as e:
            logger.error(f"Failed to publish to channel {channel}: {e}")
            raise

    async def subscribe(self, *channels: str):
        """
        Create a Pub/Sub subscription for the specified channels.

        Args:
            *channels: Channel names to subscribe to

        Returns:
            Redis PubSub object
        """
        redis_client = await self.get_redis()
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(*channels)
            logger.debug(f"Subscribed to channels: {channels}")
            return pubsub
        except Exception as e:
            logger.error(f"Failed to subscribe to channels {channels}: {e}")
            raise

    async def psubscribe(self, *patterns: str):
        """
        Create a PubSub subscription for the specified patterns.

        Args:
            *patterns: Channel patterns to subscribe to

        Returns:
            Redis PubSub object
        """
        redis_client = await self.get_redis()
        try:
            pubsub = redis_client.pubsub()
            await pubsub.psubscribe(*patterns)
            logger.debug(f"Subscribed to patterns: {patterns}")
            return pubsub
        except Exception as e:
            logger.error(f"Failed to subscribe to patterns {patterns}: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self._initialized or self._redis is None:
                return False
            await self._redis.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False

    async def get_info(self) -> dict:
        """
        Get basic Redis information.

        Returns:
            Dict with basic Redis info
        """
        try:
            if not self._initialized or self._redis is None:
                return {"status": "not_initialized"}

            info = await self._redis.info()
            return {
                "status": "connected",
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
            }
        except Exception as e:
            logger.error(f"Error getting Redis info: {e}")
            return {"status": "error", "error": str(e)}

    async def close(self) -> None:
        """Close Redis connection and cleanup resources"""
        try:
            if self._redis:
                await self._redis.close()
                self._redis = None

            if self._pool:
                await self._pool.disconnect()
                self._pool = None

            self._initialized = False
            logger.info("Redis manager closed")

        except Exception as e:
            logger.error(f"Error closing Redis manager: {e}")


# Global Redis manager instance
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """
    Get global Redis manager instance.

    In a real application, this would be initialized with actual configuration
    from environment variables.
    """
    global _redis_manager

    if _redis_manager is None:
        # These should come from environment variables in production
        redis_url = (
            "redis://localhost:6379"  # os.getenv("REDIS_URL", "redis://localhost:6379")
        )
        max_connections = 10  # int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
        socket_timeout = 5  # int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))

        _redis_manager = RedisManager(
            redis_url=redis_url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
        )

    return _redis_manager


async def initialize_redis_manager() -> None:
    """
    Initialize the global Redis manager.

    This should be called during application startup.
    """
    redis_manager = get_redis_manager()
    await redis_manager.initialize()


async def shutdown_redis_manager() -> None:
    """
    Shutdown the global Redis manager.

    This should be called during application shutdown.
    """
    global _redis_manager

    if _redis_manager:
        await _redis_manager.close()
        _redis_manager = None
