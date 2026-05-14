"""Alarm control panel platform for Napco iBridge."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityDescription,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.exceptions import HomeAssistantError

from .api import BUTTONS, DIGIT_BUTTONS
from .const import (
    ARM_STATE_ARMING_AWAY,
    ARM_STATE_ARMING_NIGHT,
    ARM_STATE_ARMING_STAY,
    ARM_STATE_AWAY,
    ARM_STATE_DISARM,
    ARM_STATE_NIGHT,
    ARM_STATE_NOT_READY,
    ARM_STATE_STAY,
    CONF_CODE,
    PARALLEL_UPDATES as _PARALLEL_UPDATES,
)
from .coordinator import NapcoIbridgeDataUpdateCoordinator
from .entity import NapcoIbridgeEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import NapcoIbridgeConfigEntry

PARALLEL_UPDATES = _PARALLEL_UPDATES

_STATE_MAP = {
    ARM_STATE_DISARM: AlarmControlPanelState.DISARMED,
    ARM_STATE_STAY: AlarmControlPanelState.ARMED_HOME,
    ARM_STATE_AWAY: AlarmControlPanelState.ARMED_AWAY,
    ARM_STATE_NIGHT: AlarmControlPanelState.ARMED_NIGHT,
    ARM_STATE_ARMING_STAY: AlarmControlPanelState.ARMING,
    ARM_STATE_ARMING_AWAY: AlarmControlPanelState.ARMING,
    ARM_STATE_ARMING_NIGHT: AlarmControlPanelState.ARMING,
    ARM_STATE_NOT_READY: AlarmControlPanelState.DISARMED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NapcoIbridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([NapcoAlarmPanel(entry.runtime_data.coordinator, entry)])


_PANEL_DESCRIPTION = AlarmControlPanelEntityDescription(
    key="panel",
    translation_key="panel",
)


class NapcoAlarmPanel(NapcoIbridgeEntity, AlarmControlPanelEntity):
    """Alarm panel entity backed by the iBridge keypad."""

    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )

    def __init__(
        self,
        coordinator: NapcoIbridgeDataUpdateCoordinator,
        entry: NapcoIbridgeConfigEntry,
    ) -> None:
        super().__init__(coordinator, _PANEL_DESCRIPTION)
        self._entry = entry

    @property
    def _saved_code(self) -> str | None:
        return self._entry.data.get(CONF_CODE) or None

    @property
    def code_arm_required(self) -> bool:
        # Napco arms via long-press buttons that don't require a code; only
        # disarm needs the user code.
        return False

    @property
    def code_format(self) -> CodeFormat | None:
        # Disarm still needs a numeric code if none is saved.
        return CodeFormat.NUMBER if self._saved_code is None else None

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        status = self.coordinator.data
        if status is None:
            return None
        return _STATE_MAP.get(status.arm_status)

    @property
    def extra_state_attributes(self) -> dict[str, str | int] | None:
        status = self.coordinator.data
        if status is None:
            return None
        return {
            "raw_arm_status": status.arm_status,
            "display": f"{status.text_line_1.strip()}\n{status.text_line_2.strip()}",
            "armed_led": status.armed_led,
            "status_led": status.status_led,
            "area": status.area,
        }

    def _resolve_code(self, supplied: str | None) -> str:
        code = supplied or self._saved_code
        if not code:
            raise HomeAssistantError(
                translation_domain="napco_ibridge",
                translation_key="code_required",
            )
        if not code.isdigit():
            raise HomeAssistantError(
                translation_domain="napco_ibridge",
                translation_key="code_required",
            )
        return code

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        digits = self._resolve_code(code)
        sequence = [BUTTONS[DIGIT_BUTTONS[int(d)]] for d in digits]
        sequence.append(BUTTONS["ButtonOnOffEnter"])
        await self.coordinator.client.async_send_keys(sequence)

    async def async_alarm_arm_away(self, _code: str | None = None) -> None:
        await self.coordinator.client.async_send_keys([BUTTONS["ButtonInstantAwayLong"]])

    async def async_alarm_arm_home(self, _code: str | None = None) -> None:
        await self.coordinator.client.async_send_keys([BUTTONS["ButtonInteriorStayLong"]])

    async def async_alarm_arm_night(self, _code: str | None = None) -> None:
        # Two long-presses of Interior Stay.
        await self.coordinator.client.async_send_keys(
            [BUTTONS["ButtonInteriorStayLong"], BUTTONS["ButtonInteriorStayLong"]],
        )
