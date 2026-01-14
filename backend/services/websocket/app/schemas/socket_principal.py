from dataclasses import dataclass
from shared.schemas.api_key import ApiKeyInternal
from shared.schemas.user import UserReadAuth


@dataclass(slots=True)
class SocketPrincipal:
    """Return value of the auth dependency."""

    principal: ApiKeyInternal | UserReadAuth
    user_id: str
    permissions: list[str]
    tenant_id: str | None = None  # Tenant identifier for multi-tenant support
