"""Button platform for Napco iBridge — single-press keypad shortcuts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription

from .api import BUTTONS, DIGIT_BUTTONS
from .const import CONF_CODE, PARALLEL_UPDATES as _PARALLEL_UPDATES
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


@dataclass(frozen=True, kw_only=True)
class NapcoArmButtonDescription(ButtonEntityDescription):
    """Bind an HA button to a fixed keypad sequence (no user code)."""

    sequence: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class NapcoDisarmButtonDescription(ButtonEntityDescription):
    """Bind an HA button to a code + terminator key sequence."""

    terminator: str


# Single-press shortcuts available regardless of whether a code is saved.
_KEY_DESCRIPTIONS: tuple[NapcoButtonDescription, ...] = (
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


# Arm shortcuts — no user code required, always available.
_ARM_DESCRIPTIONS: tuple[NapcoArmButtonDescription, ...] = (
    NapcoArmButtonDescription(
        key="arm_away",
        translation_key="arm_away",
        icon="mdi:shield-lock",
        sequence=("ButtonInstantAwayLong",),
    ),
    NapcoArmButtonDescription(
        key="arm_home",
        translation_key="arm_home",
        icon="mdi:shield-home",
        sequence=("ButtonInteriorStayLong",),
    ),
    NapcoArmButtonDescription(
        key="arm_night",
        translation_key="arm_night",
        icon="mdi:shield-moon",
        sequence=("ButtonInteriorStayLong", "ButtonInteriorStayLong"),
    ),
)

# Disarm — needs the saved user code, so only emitted when one is stored.
_DISARM_DESCRIPTION = NapcoDisarmButtonDescription(
    key="disarm",
    translation_key="disarm",
    icon="mdi:shield-off",
    terminator="ButtonOnOffEnter",
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: NapcoIbridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[ButtonEntity] = [
        NapcoButton(coordinator, description) for description in _KEY_DESCRIPTIONS
    ]
    entities.extend(
        NapcoArmButton(coordinator, description)
        for description in _ARM_DESCRIPTIONS
    )
    if entry.data.get(CONF_CODE):
        entities.append(NapcoDisarmButton(coordinator, _DISARM_DESCRIPTION, entry))
    async_add_entities(entities)


class NapcoButton(NapcoIbridgeEntity, ButtonEntity):
    entity_description: NapcoButtonDescription

    async def async_press(self) -> None:
        code = BUTTONS[self.entity_description.keypad_button]
        await self.coordinator.client.async_send_keys([code])


class NapcoArmButton(NapcoIbridgeEntity, ButtonEntity):
    """Arm via a fixed long-press sequence (no user code required)."""

    entity_description: NapcoArmButtonDescription

    async def async_press(self) -> None:
        keys = [BUTTONS[name] for name in self.entity_description.sequence]
        await self.coordinator.client.async_send_keys(keys)


class NapcoDisarmButton(NapcoIbridgeEntity, ButtonEntity):
    """Disarm with the saved user code in a single press."""

    entity_description: NapcoDisarmButtonDescription

    def __init__(self, coordinator, description, entry: NapcoIbridgeConfigEntry) -> None:  # noqa: ANN001
        super().__init__(coordinator, description)
        self._entry = entry

    async def async_press(self) -> None:
        code: str | None = self._entry.data.get(CONF_CODE)
        if not code:
            # Code was cleared via options flow after the entity was created;
            # the entry will reload shortly. Quietly no-op.
            return
        sequence = [BUTTONS[DIGIT_BUTTONS[int(d)]] for d in code]
        sequence.append(BUTTONS[self.entity_description.terminator])
        await self.coordinator.client.async_send_keys(sequence)
