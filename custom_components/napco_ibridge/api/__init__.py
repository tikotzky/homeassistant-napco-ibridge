"""
API package for napco_ibridge.

Architecture:
    Three-layer data flow: Entities → Coordinator → API Client.
    Only the coordinator should call the API client. Entities must never
    import or call the API client directly.

Exception hierarchy:
    NapcoIbridgeApiClientError (base)
    ├── NapcoIbridgeApiClientCommunicationError (network/timeout)
    └── NapcoIbridgeApiClientAuthenticationError (401/403)

Coordinator exception mapping:
    ApiClientAuthenticationError → ConfigEntryAuthFailed (triggers reauth)
    ApiClientCommunicationError → UpdateFailed (auto-retry)
    ApiClientError             → UpdateFailed (auto-retry)
"""

from .client import (
    NapcoIbridgeApiClient,
    NapcoIbridgeApiClientAuthenticationError,
    NapcoIbridgeApiClientCommunicationError,
    NapcoIbridgeApiClientError,
)

__all__ = [
    "NapcoIbridgeApiClient",
    "NapcoIbridgeApiClientAuthenticationError",
    "NapcoIbridgeApiClientCommunicationError",
    "NapcoIbridgeApiClientError",
]
