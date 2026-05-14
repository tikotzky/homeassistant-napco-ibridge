"""Diagnostics for napco_ibridge."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.redact import async_redact_data

from .const import CONF_CODE

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import NapcoIbridgeConfigEntry

TO_REDACT = {CONF_CODE}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: NapcoIbridgeConfigEntry,
) -> dict[str, Any]:
    coordinator = entry.runtime_data.coordinator
    status = coordinator.data
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "status": asdict(status) if status is not None else None,
        "client": {
            "host": entry.runtime_data.client.host,
            "connected": entry.runtime_data.client.is_connected,
        },
    }
