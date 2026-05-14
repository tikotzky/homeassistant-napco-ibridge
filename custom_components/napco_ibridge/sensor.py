"""Sensor platform for Napco iBridge."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import EntityCategory

from .const import ARM_STATES, PARALLEL_UPDATES as _PARALLEL_UPDATES
from .entity import NapcoIbridgeEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import NapcoIbridgeConfigEntry

PARALLEL_UPDATES = _PARALLEL_UPDATES


_DISPLAY = SensorEntityDescription(
    key="display",
    translation_key="display",
    entity_category=EntityCategory.DIAGNOSTIC,
    icon="mdi:monitor-dashboard",
)

_ARM_STATE = SensorEntityDescription(
    key="arm_state",
    translation_key="arm_state",
    device_class=SensorDeviceClass.ENUM,
    options=[s.lower() for s in ARM_STATES],
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NapcoIbridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            NapcoDisplaySensor(coordinator, _DISPLAY),
            NapcoArmStateSensor(coordinator, _ARM_STATE),
        ],
    )


class NapcoDisplaySensor(NapcoIbridgeEntity, SensorEntity):
    @property
    def native_value(self) -> str | None:
        status = self.coordinator.data
        if status is None:
            return None
        return f"{status.text_line_1.rstrip()} / {status.text_line_2.rstrip()}".strip(" /")


class NapcoArmStateSensor(NapcoIbridgeEntity, SensorEntity):
    @property
    def native_value(self) -> str | None:
        status = self.coordinator.data
        if status is None:
            return None
        return status.arm_status.lower()
