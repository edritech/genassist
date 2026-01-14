"""
Core Auth Gateway for delegating authentication to the core service.

This gateway allows other microservices (e.g., websocket service) to delegate
authentication to the core AuthService via HTTP instead of duplicating auth logic.
"""

import logging
from typing import Optional, Tuple, Any
from uuid import UUID
from enum import Enum
import httpx

from shared.http.internal_service_client import (
    InternalServiceClient,
    get_core_api_client,
)


logger = logging.getLogger(__name__)


class CoreAuthGatewayError(Exception):
    """Base exception for CoreAuthGateway errors."""

    pass


class CoreAuthGateway:
    """
    Gateway for authenticating WebSocket connections via the core auth service.

    This gateway calls the core service's internal websocket-introspect endpoint
    to validate tokens and API keys, returning normalized authentication data.

    Example:
        gateway = CoreAuthGateway(
            core_base_url="http://localhost:8000",
            internal_api_key="internal-secret-key"
        )
        return await gateway.authenticate_websocket(
            access_token="eyJ...",
            tenant_id="tenant-123"
        )
    """

    def __init__(
        self,
        core_base_url: str = "http://localhost:8000",
        internal_api_key: Optional[str] = None,
        timeout: float = 5.0,
    ):
        """
        Initialize CoreAuthGateway.

        Args:
            core_base_url: Base URL of the core service (default: "http://localhost:8000")
            internal_api_key: API key for internal service-to-service auth
            timeout: Request timeout in seconds (default: 5.0)
        """
        self.core_base_url = core_base_url.rstrip("/")
        self.internal_api_key = internal_api_key
        self.timeout = timeout
        self._client: Optional[InternalServiceClient] = None

    def _get_client(self) -> InternalServiceClient:
        """Get or create internal service client."""
        if self._client is None:
            self._client = get_core_api_client(
                base_url=self.core_base_url, api_key=self.internal_api_key
            )
        return self._client

    async def authenticate_websocket(
        self,
        access_token: Optional[str] = None,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Tuple[Any, UUID, list[str]]:
        """
        Authenticate WebSocket connection via core auth service.

        This method calls the core service's `/api/auth/internal/websocket-introspect`
        endpoint to validate credentials and retrieve user information.

        Args:
            access_token: JWT access token (optional if api_key provided)
            api_key: API key string (optional if access_token provided)
            tenant_id: Optional tenant ID for multi-tenant context

        Returns:
            Tuple of (principal, user_id, permissions):
            - principal: Dict containing user/auth info (for SocketPrincipal)
            - user_id: UUID of the authenticated user
            - permissions: List of permission strings

        Raises:
            CoreAuthGatewayError: If authentication fails or service is unavailable
            AuthValidationError: If credentials are invalid or expired
        """
        if not access_token and not api_key:
            raise CoreAuthGatewayError(
                "Missing credentials: access_token or api_key required"
            )

        try:
            # add X-API-Key
            headers = (
                {"X-Internal-API": self.internal_api_key}
                if self.internal_api_key
                else {}
            )

            # add X-Tenant-Id if tenant_id is provided
            if tenant_id:
                headers["X-Tenant-Id"] = tenant_id

            client = self._get_client()

            # Build query parameters
            params = {}
            if access_token:
                params["access_token"] = access_token
            if api_key:
                params["api_key"] = api_key

            response = await client.post(
                f"/api/auth/socket_auth",
                params=params,
                headers=headers,
            )

            data = response.json()

            # Extract and validate response fields
            principal = data.get("principal", {})
            user_id_str = data.get("user_id")
            permissions = data.get("permissions", [])

            if not user_id_str:
                raise CoreAuthGatewayError(
                    "Core auth service returned invalid response: missing user_id"
                )

            try:
                user_id = UUID(user_id_str)
            except (ValueError, TypeError) as e:
                raise CoreAuthGatewayError(
                    f"Core auth service returned invalid user_id: {user_id_str}"
                ) from e

            if not isinstance(permissions, list):
                raise CoreAuthGatewayError(
                    f"Core auth service returned invalid permissions: {permissions}"
                )

            logger.debug(
                f"Authenticated user {user_id} via core auth service "
                f"(mode: {data.get('auth_mode', 'unknown')})"
            )

            return principal, user_id, permissions

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            error_detail = None
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", str(e))
            except Exception:
                error_detail = e.response.text or str(e)

            if status_code == 401:
                raise CoreAuthGatewayError(
                    f"Authentication failed: {error_detail}"
                ) from e
            elif status_code == 403:
                raise CoreAuthGatewayError(
                    f"Authorization failed: {error_detail}"
                ) from e
            elif status_code == 400:
                raise CoreAuthGatewayError(f"Invalid request: {error_detail}") from e
            else:
                raise CoreAuthGatewayError(
                    f"Core auth service error ({status_code}): {error_detail}"
                ) from e

        except httpx.RequestError as e:
            logger.error(f"Failed to connect to core auth service: {e}")
            raise CoreAuthGatewayError(
                f"Core auth service unavailable: {str(e)}"
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error in core auth gateway: {e}", exc_info=True)
            raise CoreAuthGatewayError(f"Authentication error: {str(e)}") from e

    async def close(self):
        """Close the internal HTTP client."""
        if self._client:
            # InternalServiceClient doesn't expose close, but httpx client does
            # We'll let it be managed by the client lifecycle
            self._client = None


# Factory function for creating gateway instances
_core_auth_gateway: Optional[CoreAuthGateway] = None


def get_core_auth_gateway(
    core_base_url: Optional[str] = None,
    internal_api_key: Optional[str] = None,
) -> CoreAuthGateway:
    """
    Get or create a singleton CoreAuthGateway instance.

    Args:
        core_base_url: Optional override for core service URL
        internal_api_key: Optional override for internal API key

    Returns:
        CoreAuthGateway instance
    """
    global _core_auth_gateway

    if _core_auth_gateway is None or core_base_url or internal_api_key:
        _core_auth_gateway = CoreAuthGateway(
            core_base_url=core_base_url or "http://localhost:8000",
            internal_api_key=internal_api_key,
        )

    return _core_auth_gateway
