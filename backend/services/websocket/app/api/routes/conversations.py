from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from uuid import UUID
from typing import Optional
import logging
from enum import Enum

from app.core.connection_manager import connect_websocket_to_manager
from app.core.exceptions import send_socket_error
from app.core.auth.socket_auth import socket_auth
from app.schemas.socket_principal import SocketPrincipal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class SocketRoomType(Enum):
    DASHBOARD = "DASHBOARD"


# -----------------------------------------------------------------------------
# Conversation WebSocket endpoint
# -----------------------------------------------------------------------------
@router.websocket("/conversations/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: UUID,
    lang: Optional[str] = Query(default="en"),
    topics: list[str] = Query(default=["message"]),
    api_key: str = Query(default=""),
):
    """
    WebSocket endpoint for conversation-specific real-time updates.

    Connects to a room specific to the conversation_id for receiving
    messages related to that conversation.
    """

    principal: SocketPrincipal = await socket_auth(
        ["read:in_progress_conversation"], api_key=api_key
    )

    tenant_id = principal.tenant_id
    socket_connection_manager = await connect_websocket_to_manager(
        websocket=websocket,
        room_id=conversation_id,
        user_id=principal.user_id,
        permissions=principal.permissions,
        tenant_id=tenant_id,
        topics=topics,
    )

    try:
        while True:
            data = await websocket.receive_text()
            # logger.debug("Received data: %s", data)
            # Echo back or process received data as needed
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        logger.debug(
            f"WebSocket disconnected for conversation {conversation_id} (tenant: {tenant_id})"
        )
        if socket_connection_manager:
            await socket_connection_manager.disconnect(
                websocket, conversation_id, tenant_id
            )
    except Exception as e:
        logger.exception("Unexpected WebSocket error: %s", e)
        # Attempt to disconnect even if we don't know the exact room/tenant
        if socket_connection_manager:
            try:
                await socket_connection_manager.disconnect(
                    websocket, conversation_id, tenant_id
                )
            except Exception:
                # Fallback: disconnect without room info (searches all rooms)
                await socket_connection_manager.disconnect(websocket, None, None)
        await send_socket_error(websocket, "INTERNAL_ERROR", lang)
        await websocket.close(code=1011)


# -----------------------------------------------------------------------------
# Dashboard WebSocket endpoint
# -----------------------------------------------------------------------------
@router.websocket("/conversations/ws/dashboard/list")
async def websocket_dashboard_endpoint(
    websocket: WebSocket,
    access_token: Optional[str] = Query(default=None),
    api_key: Optional[str] = Query(default=None),
    lang: Optional[str] = Query(default="en"),
    topics: list[str] = Query(default=["message"]),
):
    """
    WebSocket endpoint for dashboard real-time updates.

    Connects to the dashboard room to receive updates about all conversations,
    including new conversations, status changes, and system events.
    """

    principal = await socket_auth(
        required_permissions=["read:in_progress_conversation"],
        access_token=access_token,
        api_key=api_key,
    )

    if principal is None:
        await send_socket_error(websocket, "NOT_AUTHENTICATED", lang)
        await websocket.close(code=1011)
        return

    tenant_id = None

    logger.info(f"Principal: {principal}")
    tenant_id = principal.tenant_id if principal is not None else None

    socket_connection_manager = await connect_websocket_to_manager(
        websocket=websocket,
        room_id=SocketRoomType.DASHBOARD,
        user_id=principal.user_id,
        permissions=principal.permissions,
        tenant_id=tenant_id,
        topics=topics,
    )

    try:
        while True:
            data = await websocket.receive_text()
            # logger.debug("Received data: %s", data)
            # Echo back or process received data as needed
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected for dashboard (tenant: {tenant_id})")
        if socket_connection_manager:
            await socket_connection_manager.disconnect(
                websocket, SocketRoomType.DASHBOARD, tenant_id
            )
    except Exception as e:
        logger.exception("Unexpected WebSocket error: %s", e)
        # Attempt to disconnect even if we don't know the exact room/tenant
        if socket_connection_manager:
            try:
                await socket_connection_manager.disconnect(
                    websocket, SocketRoomType.DASHBOARD, tenant_id
                )
            except Exception:
                # Fallback: disconnect without room info (searches all rooms)
                await socket_connection_manager.disconnect(websocket, None, None)
        await send_socket_error(websocket, "INTERNAL_ERROR", lang)
        await websocket.close(code=1011)
