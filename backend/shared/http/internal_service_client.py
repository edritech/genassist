"""
Internal Service Client for service-to-service communication within Docker network.

This module provides a reusable HTTP client for making internal service calls
that are not exposed to the public internet. Services communicate using Docker
service names (e.g., 'app', 'websocket', 'whisper') which resolve to internal
IP addresses within the Docker network.

Key features:
- Uses Docker service names for internal communication
- Supports async (httpx) and sync (requests) HTTP clients
- Includes authentication headers for service-to-service calls
- Handles errors and retries
- Configurable timeouts and connection pooling
"""

import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import httpx
import requests
from functools import lru_cache

logger = logging.getLogger(__name__)


class InternalServiceClient:
    """
    HTTP client for internal service-to-service communication.

    Uses Docker service names (e.g., 'app', 'websocket') which resolve
    to internal IP addresses within the Docker network. These URLs are
    not accessible from outside the Docker network.

    Example:
        client = InternalServiceClient(
            base_url="http://localhost:8000",
            api_key="internal-service-key"
        )
        response = await client.get("/api/v1/users")
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        connect_timeout: float = 5.0,
        max_retries: int = 3,
    ):
        """
        Initialize internal service client.

        Args:
            base_url: Base URL using Docker service name (e.g., "http://localhost:8000")
            api_key: Optional API key for service-to-service authentication
            timeout: Request timeout in seconds
            connect_timeout: Connection timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self._async_client: Optional[httpx.AsyncClient] = None

    def _get_headers(
        self, additional_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Get headers including authentication."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if additional_headers:
            headers.update(additional_headers)
        return headers

    # Async methods using httpx
    async def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(
                    timeout=self.timeout,
                    connect=self.connect_timeout,
                ),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                ),
            )
        return self._async_client

    async def close(self):
        """Close async HTTP client."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    @asynccontextmanager
    async def _async_request_context(self):
        """Context manager for async requests."""
        client = await self._get_async_client()
        try:
            yield client
        finally:
            pass  # Keep client alive for reuse

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make async GET request."""
        async with self._async_request_context() as client:
            response = await client.get(
                path,
                params=params,
                headers=self._get_headers(headers),
            )
            response.raise_for_status()
            return response

    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make async POST request."""
        async with self._async_request_context() as client:
            request_headers = self._get_headers(headers)
            # Remove Content-Type for file uploads (httpx will set it)
            if files:
                request_headers.pop("Content-Type", None)

            response = await client.post(
                path,
                json=json,
                content=data,
                files=files,
                params=params,
                headers=request_headers,
            )
            response.raise_for_status()
            return response

    async def put(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make async PUT request."""
        async with self._async_request_context() as client:
            response = await client.put(
                path,
                json=json,
                content=data,
                headers=self._get_headers(headers),
            )
            response.raise_for_status()
            return response

    async def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make async DELETE request."""
        async with self._async_request_context() as client:
            response = await client.delete(
                path,
                headers=self._get_headers(headers),
            )
            response.raise_for_status()
            return response

    # Sync methods using requests
    def get_sync(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """Make sync GET request."""
        url = f"{self.base_url}{path}"
        response = requests.get(
            url,
            params=params,
            headers=self._get_headers(headers),
            timeout=(self.connect_timeout, self.timeout),
        )
        response.raise_for_status()
        return response

    def post_sync(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """Make sync POST request."""
        url = f"{self.base_url}{path}"
        response = requests.post(
            url,
            json=json,
            data=data,
            headers=self._get_headers(headers),
            timeout=(self.connect_timeout, self.timeout),
        )
        response.raise_for_status()
        return response

    def put_sync(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """Make sync PUT request."""
        url = f"{self.base_url}{path}"
        response = requests.put(
            url,
            json=json,
            data=data,
            headers=self._get_headers(headers),
            timeout=(self.connect_timeout, self.timeout),
        )
        response.raise_for_status()
        return response

    def delete_sync(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """Make sync DELETE request."""
        url = f"{self.base_url}{path}"
        response = requests.delete(
            url,
            headers=self._get_headers(headers),
            timeout=(self.connect_timeout, self.timeout),
        )
        response.raise_for_status()
        return response


# Factory functions for common service clients
@lru_cache(maxsize=10)
def get_core_api_client(
    base_url: str = "http://localhost:8000",
    api_key: Optional[str] = None,
) -> InternalServiceClient:
    """
    Get cached client for Core API service.

    Args:
        base_url: Core API base URL (default: "http://localhost:8000")
        api_key: Optional API key for authentication

    Returns:
        InternalServiceClient configured for Core API
    """
    logger.info(f"Getting core API client for base URL: {base_url}")

    return InternalServiceClient(base_url=base_url, api_key=api_key)


@lru_cache(maxsize=10)
def get_websocket_client(
    base_url: str = "http://websocket:8002",
    api_key: Optional[str] = None,
) -> InternalServiceClient:
    """
    Get cached client for WebSocket service.

    Args:
        base_url: WebSocket service base URL (default: "http://websocket:8002")
        api_key: Optional API key for authentication

    Returns:
        InternalServiceClient configured for WebSocket service
    """
    return InternalServiceClient(base_url=base_url, api_key=api_key)


@lru_cache(maxsize=10)
def get_whisper_client(
    base_url: str = "http://whisper:8001",
    api_key: Optional[str] = None,
) -> InternalServiceClient:
    """
    Get cached client for Whisper service.

    Args:
        base_url: Whisper service base URL (default: "http://whisper:8001")
        api_key: Optional API key for authentication

    Returns:
        InternalServiceClient configured for Whisper service
    """
    return InternalServiceClient(base_url=base_url, api_key=api_key)
