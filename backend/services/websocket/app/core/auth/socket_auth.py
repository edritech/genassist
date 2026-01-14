import logging
from typing import Optional
from shared.gateways.core_gateway.auth import CoreAuthGateway
from app.core.config.settings import get_settings
from app.schemas.socket_principal import SocketPrincipal

logger = logging.getLogger(__name__)

# Initialize settings and gateway
_settings = get_settings()
_gateway: Optional[CoreAuthGateway] = None


def _get_gateway() -> CoreAuthGateway:
    """Get or create CoreAuthGateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = CoreAuthGateway(
            core_base_url=_settings.core_service.base_url,
            internal_api_key=_settings.core_service.internal_api_key,
            timeout=_settings.core_service.timeout,
        )

        logger.info(
            f"CoreAuthGateway initialized with base URL: {_settings.core_service.base_url}"
        )
    return _gateway


def validate_permissions(
    principal_permissions: list[str], required_permissions: list[str]
) -> bool:
    """
    Validate the permissions. If the principal has all the required permissions, return True, otherwise return False.
    """
    if not principal_permissions:
        return False
    for permission in required_permissions:
        if permission not in principal_permissions:
            return False
    return True


async def socket_auth(
    required_permissions: list[str],
    access_token: Optional[str] = None,
    api_key: Optional[str] = None,
) -> SocketPrincipal | None:
    """
    Create socket_auth dependency configured for websocket service.

    Delegates authentication to the core auth service via CoreAuthGateway
    instead of validating JWTs locally. This ensures a single source of
    truth for authentication and permissions.
    """
    logger.info(f"Socket auth required permissions: {required_permissions}")

    async def auth_callback(
        access_token: Optional[str], api_key: Optional[str]
    ) -> SocketPrincipal | None:
        """
        Unified auth callback that delegates to core auth service.

        This callback is called by authenticate_websocket_internal with
        the extracted token/api_key. It calls the core service to validate
        credentials and retrieve user info and permissions.
        """
        gateway = _get_gateway()

        try:
            # Extract tenant_id from websocket if needed (for future enhancement)
            # For now, we'll pass None and let the core service handle tenant context
            tenant_id = None

            principal, user_id, permissions = await gateway.authenticate_websocket(
                access_token=access_token,
                api_key=api_key,
                tenant_id=tenant_id,
            )

            logger.debug(
                f"Authenticated user {user_id} via socket auth "
                f"(permissions: {len(permissions)} granted)"
            )

            # Validate the permissions
            is_valid_permissions = validate_permissions(
                permissions, required_permissions
            )
            if not is_valid_permissions:
                return None

            return SocketPrincipal(principal, user_id, permissions)

        except Exception as e:
            logger.error(f"Socket auth failed: {e}", exc_info=True)
            return None

    return await auth_callback(access_token, api_key)
