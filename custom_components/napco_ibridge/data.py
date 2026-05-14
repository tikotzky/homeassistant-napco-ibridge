"""Runtime types for napco_ibridge config entries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import NapcoIbridgeApiClient
    from .coordinator import NapcoIbridgeDataUpdateCoordinator


type NapcoIbridgeConfigEntry = ConfigEntry[NapcoIbridgeData]


@dataclass
class NapcoIbridgeData:
    """Runtime data attached to each config entry."""

    client: NapcoIbridgeApiClient
    coordinator: NapcoIbridgeDataUpdateCoordinator
    integration: Integration
