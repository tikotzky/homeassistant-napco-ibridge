"""Service actions for napco_ibridge."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol

from custom_components.napco_ibridge.api import BUTTONS, DIGIT_BUTTONS, NapcoIbridgeApiClientCommunicationError
from custom_components.napco_ibridge.const import DOMAIN, LOGGER
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv

if TYPE_CHECKING:
    from custom_components.napco_ibridge.data import NapcoIbridgeConfigEntry
    from homeassistant.core import HomeAssistant

SERVICE_SEND_KEYS = "send_keys"
SERVICE_SEND_CODE = "send_code"
ATTR_CONFIG_ENTRY = "config_entry"
ATTR_KEYS = "keys"
ATTR_CODE = "code"
ATTR_ACTION = "action"
ATTR_RESET_FIRST = "reset_first"

# Terminator buttons that make sense after a code.
CODE_ACTION_BUTTONS: tuple[str, ...] = (
    "ButtonOnOffEnter",
    "ButtonInteriorStay",
    "ButtonInteriorStayLong",
    "ButtonInstantAway",
    "ButtonInstantAwayLong",
    "ButtonBypass",
    "ButtonFunctionMenu",
)


def _coerce_key(value: Any) -> int:
    """Accept a button name or a raw integer code; return the wire-byte value."""
    if isinstance(value, str):
        if value in BUTTONS:
            return BUTTONS[value]
        try:
            return int(value)
        except ValueError as err:
            msg = f"Unknown Napco button name: {value!r}"
            raise vol.Invalid(msg) from err
    if isinstance(value, int):
        return value
    msg = f"Keys must be button names or integer codes, got {type(value).__name__}"
    raise vol.Invalid(msg)


def _coerce_action(value: Any) -> str:
    if not isinstance(value, str) or value not in CODE_ACTION_BUTTONS:
        valid = ", ".join(CODE_ACTION_BUTTONS)
        msg = f"action must be one of: {valid}"
        raise vol.Invalid(msg)
    return value


def _coerce_code(value: Any) -> str:
    if not isinstance(value, str) or not value.isdigit() or not value:
        msg = "code must be a non-empty string of digits"
        raise vol.Invalid(msg)
    return value


SEND_KEYS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
        vol.Optional(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_KEYS): vol.All(cv.ensure_list, [_coerce_key], vol.Length(min=1)),
    },
)


SEND_CODE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
        vol.Optional(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_CODE): _coerce_code,
        vol.Required(ATTR_ACTION): _coerce_action,
        vol.Optional(ATTR_RESET_FIRST, default=False): cv.boolean,
    },
)


def _resolve_entry(hass: HomeAssistant, call: ServiceCall) -> NapcoIbridgeConfigEntry:
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        msg = "No Napco iBridge integrations are configured."
        raise ServiceValidationError(msg)

    entry_id = call.data.get(ATTR_CONFIG_ENTRY)
    if entry_id is None and (device_id := call.data.get(ATTR_DEVICE_ID)) is not None:
        device_entry = dr.async_get(hass).async_get(device_id)
        if device_entry is not None:
            for config_entry_id in device_entry.config_entries:
                if any(e.entry_id == config_entry_id for e in entries):
                    entry_id = config_entry_id
                    break

    if entry_id is not None:
        for entry in entries:
            if entry.entry_id == entry_id:
                return entry
        msg = f"No Napco iBridge entry matches {entry_id!r}."
        raise ServiceValidationError(msg)

    if len(entries) > 1:
        msg = "Multiple Napco iBridge panels are configured; specify config_entry or device_id."
        raise ServiceValidationError(msg)
    return entries[0]


async def async_setup_services(hass: HomeAssistant) -> None:
    async def handle_send_keys(call: ServiceCall) -> None:
        entry = _resolve_entry(hass, call)
        keys = call.data[ATTR_KEYS]
        try:
            await entry.runtime_data.client.async_send_keys(list(keys))
        except NapcoIbridgeApiClientCommunicationError as err:
            LOGGER.exception("send_keys failed")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="send_failed",
            ) from err

    async def handle_send_code(call: ServiceCall) -> None:
        entry = _resolve_entry(hass, call)
        code: str = call.data[ATTR_CODE]
        action: str = call.data[ATTR_ACTION]
        digits = [BUTTONS[DIGIT_BUTTONS[int(d)]] for d in code]
        sequence: list[int] = []
        if call.data[ATTR_RESET_FIRST]:
            # Code + Reset silences/acknowledges alarms and clears trouble
            # displays, so the action that follows starts from a clean keypad.
            sequence.extend([*digits, BUTTONS["ButtonReset"]])
        sequence.extend([*digits, BUTTONS[action]])
        try:
            await entry.runtime_data.client.async_send_keys(sequence)
        except NapcoIbridgeApiClientCommunicationError as err:
            LOGGER.exception("send_code failed")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="send_failed",
            ) from err

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_KEYS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_KEYS,
            handle_send_keys,
            schema=SEND_KEYS_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SEND_CODE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_CODE,
            handle_send_code,
            schema=SEND_CODE_SCHEMA,
        )
