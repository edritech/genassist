"""
Health Check API for WebSocket service
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.connection_manager import get_connection_manager
from app.cache.redis_manager import get_redis_manager
from app.core.config.settings import get_settings


logger = logging.getLogger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str = "healthy"
    service: str
    version: str
    redis_connected: bool
    active_connections: int


class DetailedHealthResponse(BaseModel):
    """Detailed health check response with additional information"""

    status: str
    service: str
    version: str
    environment: str
    redis_connected: bool
    redis_details: Dict[str, Any]
    active_connections: int
    connection_details: Dict[str, Any]
    uptime_seconds: float


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.

    Returns the overall health status of the WebSocket service,
    including Redis connectivity and active connection count.

    Returns:
        HealthResponse: Basic health information

    Response Schema:
        {
            "status": "healthy",
            "service": "websocket",
            "redis_connected": true,
            "active_connections": 42
        }
    """
    settings = get_settings()

    try:
        # Check Redis connectivity
        redis_connected = await check_redis_health()

        # Get active connections count
        active_connections = await get_active_connections_count()

        # Determine overall status
        overall_status = "healthy" if redis_connected else "degraded"

        return HealthResponse(
            status=overall_status,
            service=settings.SERVICE_NAME,
            version=settings.SERVICE_VERSION,
            redis_connected=redis_connected,
            active_connections=active_connections,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        # Return unhealthy status on error
        return HealthResponse(
            status="unhealthy",
            service=settings.SERVICE_NAME,
            version=settings.SERVICE_VERSION,
            redis_connected=False,
            active_connections=0,
        )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Detailed health check endpoint with comprehensive service information.

    Returns detailed health information including Redis details,
    connection statistics, and service metadata.

    Returns:
        DetailedHealthResponse: Comprehensive health information
    """
    try:
        settings = get_settings()

        # Check Redis health and get details
        redis_connected, redis_details = await check_redis_health_detailed()

        # Get connection statistics
        active_connections, connection_details = await get_connection_details()

        # Determine overall status
        if not redis_connected:
            overall_status = "degraded"
        elif active_connections == 0:
            overall_status = "healthy"  # No connections is normal
        else:
            overall_status = "healthy"

        # Calculate uptime (simplified - in production, track actual start time)
        uptime_seconds = 0.0  # Would be calculated from actual start time

        return DetailedHealthResponse(
            status=overall_status,
            service=settings.SERVICE_NAME,
            version=settings.SERVICE_VERSION,
            environment=settings.ENV,
            redis_connected=redis_connected,
            redis_details=redis_details,
            active_connections=active_connections,
            connection_details=connection_details,
            uptime_seconds=uptime_seconds,
        )

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}", exc_info=True)
        return DetailedHealthResponse(
            status="unhealthy",
            service=settings.SERVICE_NAME,
            version=settings.SERVICE_VERSION,
            environment=settings.ENV,
            redis_connected=False,
            redis_details={"error": str(e)},
            active_connections=0,
            connection_details={"error": str(e)},
            uptime_seconds=0.0,
        )


@router.get("/health/redis")
async def redis_health_check():
    """
    Redis-specific health check endpoint.

    Returns detailed Redis connectivity and performance information.

    Returns:
        dict: Redis health information
    """
    try:
        redis_connected, redis_details = await check_redis_health_detailed()

        return {
            "status": "connected" if redis_connected else "disconnected",
            "redis": redis_details,
        }

    except Exception as e:
        logger.error(f"Redis health check failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e), "redis": {"connected": False}}


@router.get("/health/connections")
async def connections_health_check():
    """
    WebSocket connections health check endpoint.

    Returns detailed information about active WebSocket connections.

    Returns:
        dict: Connection health information
    """
    try:
        active_connections, connection_details = await get_connection_details()

        return {
            "status": "healthy",
            "active_connections": active_connections,
            "connections": connection_details,
        }

    except Exception as e:
        logger.error(f"Connections health check failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e), "active_connections": 0}


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes/container orchestration.

    Returns whether the service is ready to accept traffic.
    Service is ready when:
    - Redis is connected (if configured)
    - Connection manager is initialized

    Returns:
        dict: Readiness status
    """
    try:
        # Check if Redis is available (if configured)
        settings = get_settings()
        if settings.redis.url:
            redis_connected = await check_redis_health()
            if not redis_connected:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service not ready: Redis not connected",
                )

        # Check if connection manager is available
        connection_manager = get_connection_manager()
        if connection_manager is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready: Connection manager not initialized",
            )

        return {
            "status": "ready",
            "service": settings.SERVICE_NAME,
            "version": settings.SERVICE_VERSION,
            "environment": settings.ENV,
            "checks": {
                "redis": (
                    "pass"
                    if not settings.redis.url or await check_redis_health()
                    else "fail"
                ),
                "connection_manager": "pass",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}",
        )


@router.get("/live")
async def liveness_check():
    """
    Liveness check endpoint for Kubernetes/container orchestration.

    Returns whether the service is alive and responding.
    This is a simple check that always returns success if the service is running.

    Returns:
        dict: Liveness status
    """
    return {"status": "alive", "service": "websocket"}


async def check_redis_health() -> bool:
    """
    Check Redis connectivity health.

    Returns:
        bool: True if Redis is healthy, False otherwise
    """
    try:
        settings = get_settings()
        if not settings.redis.url:
            # Redis is not configured, consider this healthy
            return True

        redis_manager = get_redis_manager()
        return await redis_manager.health_check()

    except Exception as e:
        logger.warning(f"Redis health check error: {e}")
        return False


async def check_redis_health_detailed() -> tuple[bool, Dict[str, Any]]:
    """
    Check Redis connectivity and get detailed information.

    Returns:
        tuple: (is_healthy, redis_details)
    """
    try:
        settings = get_settings()
        if not settings.redis.url:
            return True, {"configured": False, "message": "Redis not configured"}

        redis_manager = get_redis_manager()
        is_healthy = await redis_manager.health_check()

        if is_healthy:
            redis_info = await redis_manager.get_info()
            return True, redis_info
        else:
            return False, {"connected": False, "message": "Redis connection failed"}

    except Exception as e:
        logger.warning(f"Redis detailed health check error: {e}")
        return False, {"error": str(e), "connected": False}


async def get_active_connections_count() -> int:
    """
    Get the number of active WebSocket connections.

    Returns:
        int: Number of active connections
    """
    try:
        connection_manager = get_connection_manager()
        if connection_manager is None:
            return 0

        stats = await connection_manager.get_connection_stats()
        return stats.get("total_connections", 0)

    except Exception as e:
        logger.warning(f"Failed to get active connections count: {e}")
        return 0


async def get_connection_details() -> tuple[int, Dict[str, Any]]:
    """
    Get detailed connection information.

    Returns:
        tuple: (active_connections, connection_details)
    """
    try:
        connection_manager = get_connection_manager()
        if connection_manager is None:
            return 0, {"error": "Connection manager not initialized"}

        stats = await connection_manager.get_connection_stats()
        active_connections = stats.get("total_connections", 0)

        # Extract relevant connection details
        connection_details = {
            "rooms_count": stats.get("rooms_count", 0),
            "connections_by_tenant": stats.get("connections_by_tenant", {}),
            "connections_by_user": stats.get("connections_by_user", {}),
        }

        return active_connections, connection_details

    except Exception as e:
        logger.warning(f"Failed to get connection details: {e}")
        return 0, {"error": str(e)}
