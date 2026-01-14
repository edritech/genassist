import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


async def send_socket_error(websocket: WebSocket, error_key: str, lang: str = "en"):
    """
    Send an error message to a WebSocket client.

    This function sends a standardized error message format to the connected
    WebSocket client. Errors are sent in a JSON format with error details.

    Args:
        websocket: The WebSocket connection to send the error to
        error_key: The error key identifier (e.g., "INTERNAL_ERROR")
        lang: Language code for the error message (default: "en")

    Note:
        This function silently ignores any exceptions that occur during
        error sending to prevent cascading failures.
    """
    error_message = {
        "type": "error",
        "payload": {
            "error_key": error_key,
            "message": f"Error: {error_key}",
            "lang": lang,
        },
    }
    try:
        await websocket.send_text(json.dumps(error_message))
    except Exception as e:
        logger.warning(f"Failed to send socket error: {e}")
        # Ignore errors during error sending to prevent cascading failures
