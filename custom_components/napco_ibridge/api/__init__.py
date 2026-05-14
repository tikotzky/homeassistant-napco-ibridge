"""API package for napco_ibridge.

Exposes the async TCP client and discovery helper for the Napco iBridge
protocol. Only the coordinator should drive the client; entities read state
through the coordinator.
"""

from __future__ import annotations

from .client import (
    BUTTONS,
    DIGIT_BUTTONS,
    NapcoIbridgeApiClient,
    NapcoIbridgeApiClientAuthenticationError,
    NapcoIbridgeApiClientCommunicationError,
    NapcoIbridgeApiClientError,
    NapcoStatus,
    async_discover_panel,
)

__all__ = [
    "BUTTONS",
    "DIGIT_BUTTONS",
    "NapcoIbridgeApiClient",
    "NapcoIbridgeApiClientAuthenticationError",
    "NapcoIbridgeApiClientCommunicationError",
    "NapcoIbridgeApiClientError",
    "NapcoStatus",
    "async_discover_panel",
]
