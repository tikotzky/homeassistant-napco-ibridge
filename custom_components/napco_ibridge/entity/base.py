"""Base entity for napco_ibridge."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import CONF_HOST, DOMAIN, MANUFACTURER, MODEL
from ..coordinator import NapcoIbridgeDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription


class NapcoIbridgeEntity(CoordinatorEntity[NapcoIbridgeDataUpdateCoordinator]):
    """Common base: shared device + unique id derived from the config entry."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NapcoIbridgeDataUpdateCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = entity_description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=f"http://{entry.data.get(CONF_HOST, '')}",
        )
