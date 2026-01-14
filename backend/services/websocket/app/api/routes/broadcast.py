"""
Broadcast HTTP API for service-to-service communication
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.connection_manager import SocketConnectionManager, get_connection_manager
from app.core.config.settings import get_settings
from app.core.validations import validate_api_key


logger = logging.getLogger(__name__)
router = APIRouter()


class BroadcastRequest(BaseModel):
    """Request schema for broadcast messages"""

    room_id: str = Field(..., description="Room ID (UUID or string like 'DASHBOARD')")

    msg_type: str = Field(
        ..., description="Message type: message, update, statistics, finalize, takeover"
    )

    current_user_id: str = Field(
        ..., description="UUID of the user sending the message"
    )

    payload: dict = Field(
        default_factory=dict, description="Message payload (JSON object)"
    )

    required_topic: Optional[str] = Field(
        default=None, description="Required topic for filtering (optional)"
    )

    tenant_id: Optional[str] = Field(
        default=None, description="Tenant ID for multi-tenant isolation (optional)"
    )

    class Config:
        schema_extra = {
            "example": {
                "room_id": "12345678-1234-5678-9abc-123456789abc",
                "msg_type": "message",
                "current_user_id": "87654321-4321-8765-cba9-87654321cba9",
                "payload": {"text": "Hello, world!", "sender": "user123"},
                "required_topic": "message",
                "tenant_id": "tenant-1",
            }
        }


class BroadcastResponse(BaseModel):
    """Response schema for broadcast operations"""

    success: bool = Field(..., description="Whether the broadcast was successful")

    message: str = Field(..., description="Status message")

    recipients: int = Field(
        ..., description="Number of recipients the message was sent to"
    )

    room_id: str = Field(..., description="Room ID the message was sent to")

    method: str = Field(..., description="Broadcast method used (redis or local)")


def get_api_key_from_request(request) -> str:
    """
    Extract API key from HTTP request.

    Args:
        request: FastAPI Request object

    Returns:
        str: API key

    Raises:
        HTTPException: If API key is not found
    """
    # Try header first
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key

    # Try query parameter
    api_key = request.query_params.get("api_key")
    if api_key:
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key required in X-API-Key header or api_key query parameter",
    )


async def get_current_service_auth(request) -> dict:
    """
    Dependency for API key authentication.

    Args:
        request: FastAPI Request object

    Returns:
        dict: Authentication payload
    """
    api_key = get_api_key_from_request(request)
    return await validate_api_key(api_key)


@router.post("/broadcast", response_model=BroadcastResponse)
async def broadcast_message(
    request: BroadcastRequest,
    auth_payload: dict = Depends(get_current_service_auth),
    connection_manager: SocketConnectionManager = Depends(get_connection_manager),
):
    """
    Broadcast a message to WebSocket connections.

    This endpoint allows other services to send messages to WebSocket clients
    through the connection manager. Supports both Redis Pub/Sub and local broadcasting.

    Args:
        request: Broadcast message details
        auth_payload: Authentication payload from API key
        connection_manager: WebSocket connection manager instance

    Returns:
        BroadcastResponse: Result of the broadcast operation

    Raises:
        HTTPException: If broadcast fails
    """
    try:
        # Validate current_user_id is a valid UUID
        try:
            user_id = UUID(request.current_user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="current_user_id must be a valid UUID",
            )

        # Validate message type
        valid_msg_types = {"message", "update", "statistics", "finalize", "takeover"}
        if request.msg_type not in valid_msg_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid msg_type. Must be one of: {', '.join(valid_msg_types)}",
            )

        # Get connection statistics before broadcast
        try:
            stats_before = await connection_manager.get_connection_stats()
            total_connections_before = stats_before.get("total_connections", 0)
        except Exception as e:
            logger.warning(f"Failed to get pre-broadcast stats: {e}")
            total_connections_before = 0

        # Perform broadcast
        await connection_manager.broadcast(
            room_id=request.room_id,
            msg_type=request.msg_type,
            current_user_id=user_id,
            payload=request.payload,
            required_topic=request.required_topic,
            tenant_id=request.tenant_id,
        )

        # Get connection statistics after broadcast
        try:
            stats_after = await connection_manager.get_connection_stats()
            total_connections_after = stats_after.get("total_connections", 0)
        except Exception as e:
            logger.warning(f"Failed to get post-broadcast stats: {e}")
            total_connections_after = total_connections_before

        # Determine broadcast method
        settings = get_settings()
        broadcast_method = "redis" if settings.redis.url else "local"

        # Log the broadcast
        logger.info(
            f"Broadcast sent via {broadcast_method}: "
            f"room={request.room_id}, "
            f"type={request.msg_type}, "
            f"user={user_id}, "
            f"tenant={request.tenant_id}, "
            f"topic={request.required_topic}"
        )

        return BroadcastResponse(
            success=True,
            message="Message broadcast successfully",
            recipients=total_connections_after,
            room_id=request.room_id,
            method=broadcast_method,
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Broadcast failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Broadcast failed: {str(e)}",
        )


@router.get("/broadcast/stats")
async def get_broadcast_stats(
    auth_payload: dict = Depends(get_current_service_auth),
    connection_manager: SocketConnectionManager = Depends(get_connection_manager),
):
    """
    Get broadcasting and connection statistics.

    This endpoint provides statistics about current WebSocket connections
    and broadcasting activity for monitoring and debugging purposes.

    Args:
        auth_payload: Authentication payload from API key
        connection_manager: WebSocket connection manager instance

    Returns:
        dict: Connection and broadcast statistics
    """
    try:
        # Get connection statistics
        connection_stats = await connection_manager.get_connection_stats()

        # Get Redis information if available
        redis_info = {}
        settings = get_settings()
        if settings.redis.url:
            try:
                from app.cache.redis_manager import get_redis_manager

                redis_manager = get_redis_manager()
                redis_info = await redis_manager.get_info()
            except Exception as e:
                logger.warning(f"Failed to get Redis info: {e}")
                redis_info = {"error": "Unable to retrieve Redis information"}

        return {
            "service": {
                "name": get_settings().SERVICE_NAME,
                "version": get_settings().SERVICE_VERSION,
            },
            "connections": connection_stats,
            "redis": redis_info,
            "broadcast": {
                "supported_methods": ["redis", "local"],
                "current_method": "redis" if settings.redis.url else "local",
                "message_types": [
                    "message",
                    "update",
                    "statistics",
                    "finalize",
                    "takeover",
                ],
            },
            "authentication": {
                "method": auth_payload.get("auth_method"),
                "api_key": (
                    auth_payload.get("api_key", "redacted")[:8] + "..."
                    if auth_payload.get("api_key")
                    else None
                ),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get broadcast stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}",
        )


@router.post("/broadcast/test")
async def test_broadcast(
    auth_payload: dict = Depends(get_current_service_auth),
    connection_manager: SocketConnectionManager = Depends(get_connection_manager),
):
    """
    Test broadcast functionality.

    This endpoint sends a test message to verify that the
    broadcasting system is working correctly.

    Args:
        auth_payload: Authentication payload from API key
        connection_manager: WebSocket connection manager instance

    Returns:
        dict: Test result
    """
    try:
        # Create test message
        test_request = BroadcastRequest(
            room_id="DASHBOARD",
            msg_type="message",
            current_user_id=str(
                auth_payload.get(
                    "user_id", UUID("00000000-0000-0000-0000-000000000000")
                )
            ),
            payload={
                "type": "test",
                "message": "Test broadcast message",
                "timestamp": "now",
                "sender": "broadcast-api",
            },
            required_topic=None,
            tenant_id=None,
        )

        # Get stats before test
        stats_before = await connection_manager.get_connection_stats()

        # Send test broadcast
        await connection_manager.broadcast(
            room_id=test_request.room_id,
            msg_type=test_request.msg_type,
            current_user_id=UUID(test_request.current_user_id),
            payload=test_request.payload,
            required_topic=test_request.required_topic,
            tenant_id=test_request.tenant_id,
        )

        # Get stats after test
        stats_after = await connection_manager.get_connection_stats()

        logger.info("Test broadcast completed successfully")

        return {
            "success": True,
            "message": "Test broadcast completed successfully",
            "test_message": test_request.dict(),
            "connections_before": stats_before.get("total_connections", 0),
            "connections_after": stats_after.get("total_connections", 0),
            "timestamp": "now",
        }

    except Exception as e:
        logger.error(f"Test broadcast failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test broadcast failed: {str(e)}",
        )
