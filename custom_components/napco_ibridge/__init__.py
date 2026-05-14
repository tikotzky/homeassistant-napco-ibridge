"""Napco iBridge Home Assistant integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
import homeassistant.helpers.config_validation as cv
from homeassistant.loader import async_get_loaded_integration

from .api import NapcoIbridgeApiClient
from .const import CONF_HOST, DOMAIN
from .coordinator import NapcoIbridgeDataUpdateCoordinator
from .data import NapcoIbridgeData
from .service_actions import async_setup_services

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import NapcoIbridgeConfigEntry

PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the integration's service actions at HA startup."""
    await async_setup_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NapcoIbridgeConfigEntry,
) -> bool:
    """Set up Napco iBridge from a config entry."""
    client = NapcoIbridgeApiClient(host=entry.data[CONF_HOST])
    coordinator = NapcoIbridgeDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        client=client,
    )

    entry.runtime_data = NapcoIbridgeData(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    entry.async_on_unload(coordinator.async_shutdown)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: NapcoIbridgeConfigEntry,
) -> bool:
    """Unload the integration's platforms; coordinator cleanup runs from the unload-hook."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: NapcoIbridgeConfigEntry,
) -> None:
    """Reload entry after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
