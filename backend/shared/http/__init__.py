"""
Shared HTTP client utilities for internal service communication.
"""

from .internal_service_client import (
    InternalServiceClient,
    get_core_api_client,
    get_websocket_client,
    get_whisper_client,
)

__all__ = [
    "InternalServiceClient",
    "get_core_api_client",
    "get_websocket_client",
    "get_whisper_client",
]
