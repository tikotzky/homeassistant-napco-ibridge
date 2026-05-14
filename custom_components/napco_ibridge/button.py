"""Button platform for Napco iBridge — single-press keypad shortcuts."""

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
    """Description binding an HA button to a single Napco keypad button name."""

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
    NapcoButtonDescription(
        key="bypass",
        translation_key="bypass",
        icon="mdi:shield-off-outline",
        keypad_button="ButtonBypass",
    ),
    NapcoButtonDescription(
        key="function_menu",
        translation_key="function_menu",
        icon="mdi:menu",
        keypad_button="ButtonFunctionMenu",
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
