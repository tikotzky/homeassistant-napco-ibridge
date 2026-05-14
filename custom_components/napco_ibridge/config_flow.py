"""Config flow for Napco iBridge."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    NapcoIbridgeApiClient,
    NapcoIbridgeApiClientCommunicationError,
    async_discover_panel,
)
from .const import CONF_CODE, CONF_HOST, CONF_SAVE_CODE, DOMAIN, LOGGER

DISCOVER_OPTION = "discover"
MANUAL_OPTION = "manual"


def _details_schema(
    host_default: str = "",
    code_default: str = "",
    save_default: bool = False,
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=host_default): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT),
            ),
            vol.Optional(CONF_SAVE_CODE, default=save_default): BooleanSelector(),
            vol.Optional(CONF_CODE, default=code_default): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD),
            ),
        },
    )


async def _async_probe(host: str) -> None:
    """Open a short-lived connection to verify we can talk to the panel."""
    client = NapcoIbridgeApiClient(host=host)
    try:
        await client.async_connect()
    finally:
        await client.async_disconnect()


class NapcoIbridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow that picks between discovery and manual entry, then validates."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_host: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NapcoIbridgeOptionsFlow:
        return NapcoIbridgeOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_menu(
                step_id="user",
                menu_options=[DISCOVER_OPTION, MANUAL_OPTION],
            )
        return await self.async_step_manual()

    async def async_step_discover(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        try:
            host = await async_discover_panel()
        except NapcoIbridgeApiClientCommunicationError as err:
            LOGGER.warning("Discovery failed: %s", err)
            return self.async_show_form(
                step_id="user",
                errors={"base": "no_discovery"},
            )
        self._discovered_host = host
        return await self.async_step_details()

    async def async_step_manual(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        self._discovered_host = None
        return await self.async_step_details()

    async def async_step_details(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        errors: dict[str, str] = {}
        host_default = self._discovered_host or ""
        if user_input is not None:
            host = user_input[CONF_HOST]
            save_code = user_input.get(CONF_SAVE_CODE, False)
            code = (user_input.get(CONF_CODE) or "").strip()
            if save_code and not code:
                errors[CONF_CODE] = "code_required"
            else:
                try:
                    await _async_probe(host)
                except NapcoIbridgeApiClientCommunicationError as err:
                    LOGGER.warning("Probe of %s failed: %s", host, err)
                    errors["base"] = "cannot_connect"

            if not errors:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                data: dict[str, Any] = {CONF_HOST: host, CONF_SAVE_CODE: save_code}
                if save_code:
                    data[CONF_CODE] = code
                return self.async_create_entry(title=f"Napco iBridge ({host})", data=data)

            host_default = host

        return self.async_show_form(
            step_id="details",
            data_schema=_details_schema(
                host_default=host_default,
                code_default=(user_input or {}).get(CONF_CODE, ""),
                save_default=(user_input or {}).get(CONF_SAVE_CODE, False),
            ),
            errors=errors,
        )


class NapcoIbridgeOptionsFlow(OptionsFlow):
    """Allow toggling the stored-code setting after setup."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if user_input is not None:
            save_code = user_input.get(CONF_SAVE_CODE, False)
            code = (user_input.get(CONF_CODE) or "").strip()
            if save_code and not code:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._schema(),
                    errors={CONF_CODE: "code_required"},
                )
            data = {**self.config_entry.data, CONF_SAVE_CODE: save_code}
            if save_code:
                data[CONF_CODE] = code
            else:
                data.pop(CONF_CODE, None)
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            return self.async_create_entry(title="", data={})
        return self.async_show_form(step_id="init", data_schema=self._schema())

    def _schema(self) -> vol.Schema:
        data = self.config_entry.data
        return vol.Schema(
            {
                vol.Optional(
                    CONF_SAVE_CODE, default=data.get(CONF_SAVE_CODE, False),
                ): BooleanSelector(),
                vol.Optional(CONF_CODE, default=data.get(CONF_CODE, "")): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD),
                ),
            },
        )
