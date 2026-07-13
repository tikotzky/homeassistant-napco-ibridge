"""DataUpdateCoordinator for napco_ibridge.

The protocol is push-driven: a long-lived TCP connection emits status frames
continuously. We adapt that into HA's coordinator pattern by relaying each
client update via async_set_updated_data().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.napco_ibridge.api import NapcoIbridgeApiClient, NapcoIbridgeApiClientError, NapcoStatus
from custom_components.napco_ibridge.const import DOMAIN, LOGGER
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from custom_components.napco_ibridge.data import NapcoIbridgeConfigEntry
    from homeassistant.core import HomeAssistant


class NapcoIbridgeDataUpdateCoordinator(DataUpdateCoordinator[NapcoStatus]):
    """Coordinator that owns the lifetime of the Napco TCP client."""

    config_entry: NapcoIbridgeConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: NapcoIbridgeConfigEntry,
        client: NapcoIbridgeApiClient,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=None,  # Push-driven from the client's read loop
            always_update=False,
        )
        self.client = client
        self._remove_listener = client.add_listener(self._handle_push)
        self._remove_connection_listener = client.add_connection_listener(
            self._handle_connection_change,
        )

    def _handle_push(self, status: NapcoStatus) -> None:
        self.async_set_updated_data(status)

    def _handle_connection_change(self, connected: bool) -> None:
        """Mark entities unavailable while the panel link is down."""
        if connected:
            # Re-seed state explicitly: push callbacks only fire on changes, and
            # the panel state may be identical to before the reconnect.
            self.async_set_updated_data(self.client.status)
        else:
            self.async_set_update_error(UpdateFailed("Connection to Napco panel lost"))

    async def _async_setup(self) -> None:
        try:
            await self.client.async_connect()
        except NapcoIbridgeApiClientError as err:
            msg = f"Unable to connect to Napco panel: {err}"
            raise UpdateFailed(msg) from err
        # Seed coordinator data with whatever the connect handshake produced.
        self.data = self.client.status

    async def _async_update_data(self) -> NapcoStatus:
        # Should not be called (update_interval is None), but keep safe.
        return self.client.status

    async def async_shutdown(self) -> None:
        self._remove_listener()
        self._remove_connection_listener()
        await self.client.async_disconnect()
        await super().async_shutdown()
