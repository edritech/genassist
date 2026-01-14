from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import httpx
import websockets
from websockets.exceptions import WebSocketException, ConnectionClosed
from dotenv import load_dotenv
import os
import uvicorn
import logging
import asyncio
import json

logger = logging.getLogger(__name__)

# Gateway for forwarding requests to the core and websocket services
app = FastAPI(
    title="GenAssist Gateway",
    version="1.0.0",
    description="Gateway for forwarding requests to the core and websocket services",
)
tags_metadata = [
    {
        "name": "core",
        "description": "Core service",
    },
    {
        "name": "websocket",
        "description": "Websocket service",
    },
]

# Load environment variables
load_dotenv()


# HTTP: Forward request to the service
async def forward_request(
    service_url: str,
    method: str,
    path: str,
    body=None,
    params=None,
    headers=None,
    files=None,
    data=None,
):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Add origin host header to the request
        host = service_url.split("://")[1].split("/")[0]
        headers["host"] = host.lower()

        url = f"{service_url}{path}"

        # Prepare request kwargs - only include parameters that are actually set
        request_kwargs = {
            "method": method,
            "url": url,
            "params": params,
            "headers": headers,
        }

        # Only add body parameters if they're set (httpx doesn't like None values)
        if files is not None:
            # Multipart form data with files
            request_kwargs["files"] = files
            if data is not None:
                request_kwargs["data"] = data
        elif data is not None:
            # URL-encoded form data
            request_kwargs["data"] = data
        elif body is not None:
            # JSON body
            request_kwargs["json"] = body

        response = await client.request(**request_kwargs)
        return response


# WebSocket (WS): Forward WebSocket connection to the service
async def forward_websocket(service_url: str, path: str, client_ws: WebSocket):
    """
    Proxy WebSocket connection from client to backend service.

    Args:
        service_url: Base URL of the backend service
        path: Path to forward to
        client_ws: Client WebSocket connection
    """
    # Accept the client connection
    await client_ws.accept()

    # Build the target WebSocket URL
    # Convert http:// to ws:// or https:// to wss://
    if service_url.startswith("https://"):
        ws_url = service_url.replace("https://", "wss://", 1)
    elif service_url.startswith("http://"):
        ws_url = service_url.replace("http://", "ws://", 1)
    else:
        # Assume it's already a WebSocket URL
        ws_url = service_url

    target_url = f"{ws_url}{path}"

    # Get headers from client, excluding hop-by-hop headers
    headers = {}
    for key, value in client_ws.headers.items():
        # Skip hop-by-hop headers that shouldn't be forwarded
        if key.lower() not in [
            "connection",
            "upgrade",
            "sec-websocket-key",
            "sec-websocket-version",
            "sec-websocket-extensions",
            "sec-websocket-protocol",
            "host",
        ]:
            headers[key] = value

    backend_ws = None
    try:
        # Connect to the backend WebSocket service using websockets library
        # Convert headers dict to a format websockets library expects

        logger.info(f"Connecting to backend WebSocket: {target_url}")
        logger.debug(f"Forwarding headers: {list(headers.keys())}")

        async with websockets.connect(
            target_url,
            ping_interval=20,  # Send ping every 20 seconds to keep connection alive
            ping_timeout=10,  # Wait 10 seconds for pong
            close_timeout=10,  # Wait 10 seconds when closing
        ) as backend_ws:
            logger.info(f"WebSocket proxy established: {target_url}")
            logger.info(
                f"Connection state - client: {client_ws.client_state}, backend: {backend_ws.state if hasattr(backend_ws, 'state') else 'connected'}"
            )

            # Use an event to signal when one side disconnects
            client_disconnected = asyncio.Event()
            backend_disconnected = asyncio.Event()

            async def forward_client_to_backend():
                """Forward messages from client to backend"""
                try:
                    while True:
                        # Check if we should stop
                        if (
                            client_disconnected.is_set()
                            or backend_disconnected.is_set()
                        ):
                            break

                        # Receive from client
                        try:
                            data = await client_ws.receive()

                            # Handle different message types
                            if "text" in data:
                                await backend_ws.send(data["text"])
                            elif "bytes" in data:
                                await backend_ws.send(data["bytes"])
                            elif "json" in data:
                                await backend_ws.send(json.dumps(data["json"]))
                            elif data.get("type") == "websocket.disconnect":
                                logger.info("Client disconnected")
                                client_disconnected.set()
                                break
                        except WebSocketDisconnect:
                            logger.info("Client disconnected")
                            client_disconnected.set()
                            break
                        except Exception as e:
                            logger.error(
                                f"Error forwarding client to backend: {e}",
                                exc_info=True,
                            )
                            client_disconnected.set()
                            break
                except Exception as e:
                    logger.error(
                        f"Error in client-to-backend forwarder: {e}", exc_info=True
                    )
                    client_disconnected.set()

            async def forward_backend_to_client():
                """Forward messages from backend to client"""
                try:
                    while True:
                        # Check if we should stop
                        if (
                            client_disconnected.is_set()
                            or backend_disconnected.is_set()
                        ):
                            break

                        # Receive from backend (websockets library)
                        try:
                            message = await backend_ws.recv()

                            # websockets library returns str or bytes
                            if isinstance(message, str):
                                await client_ws.send_text(message)
                            elif isinstance(message, bytes):
                                await client_ws.send_bytes(message)
                        except ConnectionClosed:
                            logger.info("Backend disconnected")
                            backend_disconnected.set()
                            break
                        except Exception as e:
                            logger.error(
                                f"Error receiving from backend: {e}", exc_info=True
                            )
                            backend_disconnected.set()
                            break
                except Exception as e:
                    logger.error(
                        f"Error in backend-to-client forwarder: {e}", exc_info=True
                    )
                    backend_disconnected.set()

            # Create both forwarding tasks
            client_task = asyncio.create_task(forward_client_to_backend())
            backend_task = asyncio.create_task(forward_backend_to_client())

            # Wait for both tasks to complete (they will complete when disconnected)
            # Use gather to wait for both, but they'll exit when disconnection events are set
            try:
                await asyncio.gather(client_task, backend_task, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error in gather: {e}", exc_info=True)

            # Close the other connection if one side disconnected
            if client_disconnected.is_set() and backend_ws:
                try:
                    await backend_ws.close()
                except Exception as e:
                    logger.debug(f"Error closing backend connection: {e}")

            if backend_disconnected.is_set():
                try:
                    await client_ws.close(code=1000, reason="Backend disconnected")
                except Exception as e:
                    logger.debug(f"Error closing client connection: {e}")

    except websockets.exceptions.InvalidURI as e:
        logger.error(f"Invalid WebSocket URI: {e}")
        try:
            await client_ws.close(code=1008, reason="Invalid URI")
        except Exception:
            pass
    except websockets.exceptions.InvalidHandshake as e:
        logger.error(f"WebSocket handshake failed: {e}")
        try:
            await client_ws.close(code=1002, reason="Handshake failed")
        except Exception:
            pass
    except ConnectionClosed as e:
        logger.error(f"Backend connection closed: {e}")
        try:
            await client_ws.close(code=1011, reason="Backend connection closed")
        except Exception:
            pass
    except WebSocketException as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await client_ws.close(code=1011, reason="WebSocket error")
        except Exception:
            pass
    except Exception as e:
        logger.error(f"WebSocket proxy error: {e}", exc_info=True)
        try:
            await client_ws.close(code=1011, reason="Proxy error")
        except Exception:
            pass


# Load GenAssist Services
def load_services():
    return {
        "core": os.getenv("CORE_SERVICE_BASE_URL"),
        "websocket": os.getenv("WEBSOCKET_SERVICE_BASE_URL"),
    }


# Root endpoint
@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "GenAssist Gateway",
        "version": "1.0.0",
        "endpoints": {
            "core": os.getenv("CORE_SERVICE_BASE_URL"),
            "websocket": os.getenv("WEBSOCKET_SERVICE_BASE_URL"),
            "health": "/health",
            "docs": "/docs",
        },
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "GenAssist Gateway", "version": "1.0.0"}


@app.api_route(
    "/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def gateway(service: str, path: str, request: Request):
    services = load_services()
    if service not in services:
        raise HTTPException(status_code=404, detail="Service not found")

    service_url = services[service]

    # Get query parameters
    try:
        params = request.query_params
    except Exception:
        params = None

    # Get headers
    headers = dict(request.headers)

    # Check content type to determine how to read the body
    content_type = headers.get("content-type", "").lower()
    body = None
    files = None
    data = None

    # Handle multipart/form-data (includes file uploads)
    if "multipart/form-data" in content_type:
        try:
            form = await request.form()
            # Convert FormData to separate files and data for httpx
            files_dict = {}
            data_dict = {}

            for key, value in form.items():
                # Check if it's a file (UploadFile)
                if hasattr(value, "read"):
                    # It's a file upload - read the file content
                    file_content = await value.read()
                    # httpx expects: (filename, file_content, content_type) or (filename, file_content)
                    if value.content_type:
                        files_dict[key] = (
                            value.filename or key,
                            file_content,
                            value.content_type,
                        )
                    else:
                        files_dict[key] = (value.filename or key, file_content)
                else:
                    # Regular form field
                    data_dict[key] = value

            # Set files and data for httpx
            files = files_dict if files_dict else None
            data = data_dict if data_dict else None

            # Remove Content-Type and Content-Length headers for multipart
            # httpx will set them correctly with the proper boundary
            if "content-type" in headers:
                del headers["content-type"]
            if "content-length" in headers:
                del headers["content-length"]
        except Exception as e:
            logger.warning(f"Failed to parse form data: {e}", exc_info=True)
            files = None
            data = None

    # Handle JSON body (only if not multipart)
    elif "application/json" in content_type:
        try:
            body = await request.json()
            # Remove Content-Length header - httpx will recalculate it
            if "content-length" in headers:
                del headers["content-length"]
        except Exception:
            body = None

    # Handle application/x-www-form-urlencoded
    elif "application/x-www-form-urlencoded" in content_type:
        try:
            form = await request.form()
            data = dict(form)
            # Remove Content-Length header - httpx will recalculate it
            if "content-length" in headers:
                del headers["content-length"]
        except Exception:
            data = None

    response = await forward_request(
        service_url, request.method, f"/{path}", body, params, headers, files, data
    )

    # Handle response content - check if it's JSON or empty
    content_type = response.headers.get("content-type", "").lower()

    # Filter out hop-by-hop headers that shouldn't be forwarded
    response_headers = {}
    hop_by_hop_headers = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
    for key, value in response.headers.items():
        if key.lower() not in hop_by_hop_headers:
            response_headers[key] = value

    # Try to parse JSON if content-type indicates JSON or if there's content
    if response.content:
        try:
            # Try to parse as JSON first
            content = response.json()
        except (json.JSONDecodeError, ValueError):
            # If JSON parsing fails, check content type
            if "application/json" in content_type:
                # Expected JSON but parsing failed - return error info
                content = {"error": "Invalid JSON response", "text": response.text}
            else:
                # Not JSON, return as text wrapped in dict for JSONResponse
                content = {"text": response.text} if response.text else {}
    else:
        # No content (e.g., 204 No Content, 307 redirect after following)
        content = {}

    # Return response with appropriate headers
    return JSONResponse(
        status_code=response.status_code, content=content, headers=response_headers
    )


@app.websocket("/{service}/{path:path}")
async def websocket_gateway(service: str, path: str, websocket: WebSocket):
    """
    WebSocket gateway endpoint that forwards WebSocket connections to backend services.

    Usage:
        ws://gateway-url/websocket/conversations/ws/{conversation_id}?lang=en&api_key=xxx
    """
    services = load_services()
    if service not in services:
        await websocket.close(code=1008, reason="Service not found")
        return

    service_url = services[service]

    # Get query parameters from the WebSocket URL
    query_string = ""
    if websocket.url.query:
        query_string = f"?{websocket.url.query}"

    # Forward the WebSocket connection with query parameters
    await forward_websocket(service_url, f"/{path}{query_string}", websocket)


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()

    PORT = os.getenv("PORT", 8000)

    # Run the application directly
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        log_level="info",
        access_log=True,
    )
