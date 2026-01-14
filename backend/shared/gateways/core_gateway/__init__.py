"""
Shared core service gateway for service-to-service communication.

This module provides gateways for calling core service endpoints from other
microservices (e.g., websocket service).
"""

from .auth import CoreAuthGateway, get_core_auth_gateway

__all__ = [
    "CoreAuthGateway",
    "get_core_auth_gateway",
]
