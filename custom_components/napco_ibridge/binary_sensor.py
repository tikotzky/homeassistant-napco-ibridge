"""Binary sensor platform for Napco iBridge."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .api import NapcoStatus
from .const import PARALLEL_UPDATES as _PARALLEL_UPDATES
from .entity import NapcoIbridgeEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import NapcoIbridgeConfigEntry

PARALLEL_UPDATES = _PARALLEL_UPDATES


def _led_on(value: str) -> bool:
    return value not in (None, "", "Off")


@dataclass(frozen=True, kw_only=True)
class NapcoBinaryDescription(BinarySensorEntityDescription):
    """Adds an `is_on` function picking out the right field from the status."""

    value_fn: Callable[[NapcoStatus], bool]


_DESCRIPTIONS: tuple[NapcoBinaryDescription, ...] = (
    NapcoBinaryDescription(
        key="trouble",
        translation_key="trouble",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda s: _led_on(s.trouble_led),
    ),
    NapcoBinaryDescription(
        key="fire",
        translation_key="fire",
        device_class=BinarySensorDeviceClass.SMOKE,
        value_fn=lambda s: _led_on(s.fire_led),
    ),
    NapcoBinaryDescription(
        key="fire_trouble",
        translation_key="fire_trouble",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda s: _led_on(s.fire_trouble_led),
    ),
    NapcoBinaryDescription(
        key="bypass",
        translation_key="bypass",
        value_fn=lambda s: _led_on(s.bypass_led),
    ),
    NapcoBinaryDescription(
        key="sounder",
        translation_key="sounder",
        device_class=BinarySensorDeviceClass.SOUND,
        value_fn=lambda s: _led_on(s.sounder),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NapcoIbridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(NapcoBinarySensor(coordinator, description) for description in _DESCRIPTIONS)


class NapcoBinarySensor(NapcoIbridgeEntity, BinarySensorEntity):
    entity_description: NapcoBinaryDescription

    @property
    def is_on(self) -> bool | None:
        status = self.coordinator.data
        if status is None:
            return None
        return self.entity_description.value_fn(status)
