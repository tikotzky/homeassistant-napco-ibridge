"""Button platform for Napco iBridge — panic shortcuts only.

Arm/disarm and the other keypad shortcuts are exposed via the
alarm_control_panel entity and the napco_ibridge.send_keys service action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription

from .api import BUTTONS
from .const import PARALLEL_UPDATES as _PARALLEL_UPDATES
from .entity import NapcoIbridgeEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import NapcoIbridgeConfigEntry

PARALLEL_UPDATES = _PARALLEL_UPDATES


@dataclass(frozen=True, kw_only=True)
class NapcoButtonDescription(ButtonEntityDescription):
    """Bind an HA button to a single Napco keypad button."""

    keypad_button: str


_DESCRIPTIONS: tuple[NapcoButtonDescription, ...] = (
    NapcoButtonDescription(
        key="panic_fire",
        translation_key="panic_fire",
        icon="mdi:fire",
        keypad_button="ButtonF",
    ),
    NapcoButtonDescription(
        key="panic_ambulance",
        translation_key="panic_ambulance",
        icon="mdi:ambulance",
        keypad_button="ButtonA",
    ),
    NapcoButtonDescription(
        key="panic_police",
        translation_key="panic_police",
        icon="mdi:police-badge",
        keypad_button="ButtonP",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NapcoIbridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(NapcoButton(coordinator, description) for description in _DESCRIPTIONS)


class NapcoButton(NapcoIbridgeEntity, ButtonEntity):
    entity_description: NapcoButtonDescription

    async def async_press(self) -> None:
        code = BUTTONS[self.entity_description.keypad_button]
        await self.coordinator.client.async_send_keys([code])
