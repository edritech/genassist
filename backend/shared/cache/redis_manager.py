"""
Unified Redis Connection Manager for both Pub/Sub and general caching operations.

This manager combines features from both core and websocket implementations:
- Connection pooling for efficient resource management
- Pub/Sub operations for message broadcasting
- Health checking and monitoring
- Flexible initialization (singleton or instance-based)
"""

import logging
from typing import Optional
import asyncio
from redis.asyncio import Redis, ConnectionPool

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Unified Redis connection manager with support for both Pub/Sub and general caching.

    Features:
    - Connection pooling for efficient resource management
    - Pub/Sub operations for WebSocket message broadcasting
    - General caching operations (get, set, delete, etc.)
    - Health checking and connection monitoring
    - Flexible initialization patterns

    Usage:
        # Instance-based usage
        manager = RedisManager(
            redis_url="redis://localhost:6379",
            max_connections=20,
            socket_timeout=5,
            health_check_interval=30
        )
        await manager.initialize()
        redis_client = await manager.get_redis()

        # Or use singleton pattern (optional)
        manager = await RedisManager.get_instance()
    """

    # Singleton instance support
    _instance: Optional["RedisManager"] = None
    _lock = asyncio.Lock()

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_connections: int = 20,
        socket_timeout: int = 5,
        health_check_interval: int = 30,
    ):
        """
        Initialize Redis manager.

        Args:
            redis_url: Redis connection URL
            max_connections: Maximum number of connections in pool
            socket_timeout: Socket timeout in seconds
            health_check_interval: Health check interval in seconds
        """
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.health_check_interval = health_check_interval

        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self._initialized = False

    @classmethod
    async def get_instance(
        cls,
        redis_url: Optional[str] = None,
        max_connections: int = 20,
        socket_timeout: int = 5,
        health_check_interval: int = 30,
    ) -> "RedisManager":
        """
        Get singleton instance with thread-safe initialization.

        Args:
            redis_url: Redis connection URL (uses default if None)
            max_connections: Maximum number of connections in pool
            socket_timeout: Socket timeout in seconds
            health_check_interval: Health check interval in seconds

        Returns:
            RedisManager singleton instance
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    kwargs = {
                        "max_connections": max_connections,
                        "socket_timeout": socket_timeout,
                        "health_check_interval": health_check_interval,
                    }
                    if redis_url:
                        kwargs["redis_url"] = redis_url
                    cls._instance = RedisManager(**kwargs)
                    await cls._instance.initialize()
        return cls._instance

    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        if self._initialized:
            return

        try:
            # Create connection pool with configurable settings
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=self.max_connections,
                retry_on_timeout=True,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_timeout,
                health_check_interval=self.health_check_interval,
            )

            # Create Redis client with the pool
            self._redis = Redis(connection_pool=self._pool)

            # Test connection
            await self._redis.ping()

            self._initialized = True
            logger.info(
                f"Redis connection pool initialized successfully: {self.redis_url}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Redis connection pool: {e}")
            self._initialized = False
            raise

    async def get_redis(self) -> Redis:
        """
        Get Redis client from connection pool.

        Returns:
            Redis client instance

        Raises:
            RuntimeError: If Redis connection is not initialized
        """
        if not self._initialized:
            await self.initialize()

        if self._redis is None:
            raise RuntimeError("Redis connection not initialized")

        return self._redis

    # Pub/Sub operations (for WebSocket broadcasting)

    async def publish(self, channel: str, message: str) -> None:
        """
        Publish a message to a Redis channel.

        Args:
            channel: Redis channel name
            message: Message to publish (will be JSON-encoded if needed)

        Raises:
            RuntimeError: If Redis is not initialized
            Exception: If publish fails
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

        Raises:
            RuntimeError: If Redis is not initialized
            Exception: If subscription fails
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
            *patterns: Channel patterns to subscribe to (e.g., "websocket:*")

        Returns:
            Redis PubSub object

        Raises:
            RuntimeError: If Redis is not initialized
            Exception: If subscription fails
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

    # General caching operations

    async def get(self, key: str) -> Optional[str]:
        """
        Get a value from Redis cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        redis_client = await self.get_redis()
        return await redis_client.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set a value in Redis cache.

        Args:
            key: Cache key
            value: Value to cache
            ex: Optional expiration time in seconds

        Returns:
            True if successful
        """
        redis_client = await self.get_redis()
        return await redis_client.set(key, value, ex=ex)

    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys from Redis.

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        redis_client = await self.get_redis()
        return await redis_client.delete(*keys)

    # Health checking and monitoring

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

    async def get_connection_info(self) -> dict:
        """
        Get connection pool and Redis server information.

        Returns:
            Dictionary with connection info and statistics
        """
        if self._pool is None:
            return {"status": "not_initialized"}

        try:
            info = await self._redis.info()
            # Get pool statistics (attributes may vary by Redis version)
            pool_stats = {}
            try:
                pool_stats["pool_created_connections"] = getattr(
                    self._pool, "created_connections", "N/A"
                )
                pool_stats["pool_max_connections"] = getattr(
                    self._pool, "max_connections", "N/A"
                )
                # These attributes might not exist in all Redis versions
                available_conns = getattr(self._pool, "_available_connections", None)
                in_use_conns = getattr(self._pool, "_in_use_connections", None)
                pool_stats["pool_available_connections"] = (
                    len(available_conns) if available_conns else "N/A"
                )
                pool_stats["pool_in_use_connections"] = (
                    len(in_use_conns) if in_use_conns else "N/A"
                )
            except Exception as e:
                logger.debug(f"Could not get detailed pool stats: {e}")
                pool_stats = {"pool_info": "Limited stats available"}

            return {
                "status": "connected",
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                **pool_stats,
            }
        except Exception as e:
            logger.error(f"Error getting connection info: {e}")
            return {"status": "error", "error": str(e)}

    async def get_info(self) -> dict:
        """
        Get basic Redis server information (alias for get_connection_info).

        Returns:
            Dictionary with basic Redis info
        """
        return await self.get_connection_info()

    # Cleanup

    async def close(self) -> None:
        """Close Redis connection pool and cleanup resources."""
        try:
            if self._redis:
                await self._redis.close()
                self._redis = None

            if self._pool:
                await self._pool.disconnect()
                self._pool = None

            self._initialized = False
            logger.info("Redis connection pool closed")

        except Exception as e:
            logger.error(f"Error closing Redis connection pool: {e}")

    @classmethod
    async def reset_instance(cls) -> None:
        """
        Reset singleton instance (useful for testing).

        This closes the current instance and clears it, allowing a new one to be created.
        """
        async with cls._lock:
            if cls._instance:
                await cls._instance.close()
                cls._instance = None

    # Convenience methods for singleton pattern

    @classmethod
    def get_manager(cls) -> Optional["RedisManager"]:
        """
        Get the current singleton instance without initialization.

        Returns:
            Current singleton instance or None
        """
        return cls._instance


# Convenience functions for backward compatibility

_global_manager: Optional[RedisManager] = None


def get_redis_manager() -> Optional[RedisManager]:
    """
    Get global Redis manager instance (backward compatibility function).

    Note: Prefer using RedisManager.get_instance() or creating an instance directly.

    Returns:
        Global RedisManager instance or None
    """
    return _global_manager


async def initialize_redis_manager(
    redis_url: str = "redis://localhost:6379",
    max_connections: int = 20,
    socket_timeout: int = 5,
    health_check_interval: int = 30,
) -> None:
    """
    Initialize the global Redis manager (backward compatibility function).

    This should be called during application startup.

    Args:
        redis_url: Redis connection URL
        max_connections: Maximum number of connections in pool
        socket_timeout: Socket timeout in seconds
        health_check_interval: Health check interval in seconds
    """
    global _global_manager

    if _global_manager is None:
        _global_manager = RedisManager(
            redis_url=redis_url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            health_check_interval=health_check_interval,
        )
        await _global_manager.initialize()


async def shutdown_redis_manager() -> None:
    """
    Shutdown the global Redis manager (backward compatibility function).

    This should be called during application shutdown.
    """
    global _global_manager

    if _global_manager:
        await _global_manager.close()
        _global_manager = None
