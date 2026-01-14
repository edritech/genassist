from fastapi import APIRouter
from fastapi import WebSocket, WebSocketDisconnect
from uuid import UUID
import logging
from app.core.connection_manager import connect_websocket_to_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/test")
async def websocket_test_endpoint(websocket: WebSocket):
    """
    Simple test WebSocket endpoint without authentication for debugging.
    This endpoint tracks connections in the connection manager for health checks.
    """
    # Use special test identifiers for unauthenticated test connections
    test_room_id = "TEST_ROOM"
    test_user_id = UUID(int=1)  # Generate a unique ID for this test connection
    test_tenant_id = None

    # Connect to the test room to track this connection
    connection_manager = await connect_websocket_to_manager(
        websocket=websocket,
        room_id=test_room_id,
        user_id=test_user_id,
        permissions=["test:connection"],
        tenant_id=test_tenant_id,
        topics=["test"],
    )

    try:
        while True:
            data = await websocket.receive_text()
            logger.info("Received test data: %s", data)
            await websocket.send_text(f"Test Echo: {data}")
    except WebSocketDisconnect:
        logger.info("Test WebSocket disconnected")
    except Exception as e:
        logger.exception("Test WebSocket error: %s", e)
        await websocket.close(code=1011)
    finally:
        # Ensure we disconnect from the connection manager
        if connection_manager:
            await connection_manager.disconnect(websocket, test_room_id, test_tenant_id)
